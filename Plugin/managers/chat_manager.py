"""聊天消息管理器。

提供聊天流列表、消息窗口查询、WebSocket 广播和发送消息的业务逻辑。
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, Field

from src.core.models.message import Message, MessageType
from src.core.models.sql_alchemy import ChatStreams, Messages
from src.core.transport.message_send.message_sender import get_message_sender
from src.kernel.db import CRUDBase, QueryBuilder
from src.kernel.logger import get_logger

logger = get_logger("webui.chat_manager", display="WebUI.ChatManager")

SUPPORTED_MESSAGE_TYPES: frozenset[str] = frozenset({"text", "image", "voice"})
DEFAULT_MESSAGE_LIMIT = 30
MAX_MESSAGE_LIMIT = 100


class ChatStreamInfo(BaseModel):
    """前端聊天流列表项。"""

    stream_id: str = Field(description="聊天流 ID")
    platform: str = Field(description="平台标识")
    chat_type: str = Field(description="聊天类型")
    display_name: str = Field(description="前端显示名称")
    group_id: str | None = Field(default=None, description="群组 ID")
    group_name: str | None = Field(default=None, description="群组名称")
    person_id: str = Field(description="用户 person_id")
    last_active_time: float = Field(description="最后活跃时间")
    last_message_preview: str = Field(default="", description="最近消息预览")
    last_message_type: str = Field(default="text", description="最近消息类型")


class ChatStreamGroup(BaseModel):
    """按平台与聊天类型分组的聊天流。"""

    platform: str = Field(description="平台标识")
    chat_type: str = Field(description="聊天类型")
    streams: list[ChatStreamInfo] = Field(description="聊天流列表")


class ChatStreamsResponse(BaseModel):
    """聊天流列表响应。"""

    groups: list[ChatStreamGroup] = Field(description="分组聊天流列表")


class ChatMessageDTO(BaseModel):
    """前端可渲染的聊天消息。"""

    message_id: str = Field(description="消息 ID")
    stream_id: str = Field(description="聊天流 ID")
    platform: str = Field(default="", description="平台标识")
    message_type: Literal["text", "image", "voice"] = Field(description="消息类型")
    content: str = Field(default="", description="消息内容或媒体 base64/路径")
    processed_plain_text: str | None = Field(default=None, description="处理后的纯文本")
    reply_to: str | None = Field(default=None, description="引用消息 ID")
    sender_id: str | None = Field(default=None, description="发送者 ID")
    sender_name: str = Field(default="", description="发送者名称")
    sender_role: str | None = Field(default=None, description="发送者角色")
    time: float = Field(description="消息时间戳")
    is_self: bool = Field(default=False, description="是否为机器人自己发送")


class MessageWindowResponse(BaseModel):
    """指定锚点消息窗口响应。"""

    stream_id: str = Field(description="聊天流 ID")
    anchor_message_id: str | None = Field(default=None, description="锚点消息 ID")
    direction: Literal["up", "down"] = Field(description="加载方向")
    messages: list[ChatMessageDTO] = Field(description="消息列表")
    has_more: bool = Field(description="该方向是否还有更多消息")


class MessageAroundResponse(BaseModel):
    """指定消息周围上下文响应。"""

    stream_id: str = Field(description="聊天流 ID")
    message_id: str = Field(description="目标消息 ID")
    messages: list[ChatMessageDTO] = Field(description="目标消息及其周围消息")
    found: bool = Field(description="是否找到目标消息")


class SendMessageRequest(BaseModel):
    """发送消息请求。"""

    message_type: Literal["text", "image", "voice"] = Field(description="消息类型")
    content: str = Field(description="文本或 base64 内容")
    reply_to: str | None = Field(default=None, description="引用消息 ID")
    client_message_id: str | None = Field(default=None, description="前端临时消息 ID")


class SendMessageResult(BaseModel):
    """发送消息结果。"""

    ok: bool = Field(description="是否发送成功")
    client_message_id: str | None = Field(default=None, description="前端临时消息 ID")
    message: ChatMessageDTO | None = Field(default=None, description="发送成功后的消息")
    error: str | None = Field(default=None, description="失败原因")


class ChatNotification(BaseModel):
    """全局新消息通知。"""

    stream_id: str = Field(description="聊天流 ID")
    platform: str = Field(description="平台标识")
    chat_type: str = Field(description="聊天类型")
    display_name: str = Field(description="聊天流显示名称")
    message: ChatMessageDTO = Field(description="新消息摘要")


class ChatManager:
    """聊天消息管理器。

    负责核心数据库只读查询、实时消息广播和指定流发送消息委托。
    """

    def __init__(self) -> None:
        """初始化聊天管理器。"""
        self._stream_crud: CRUDBase[ChatStreams] = CRUDBase(ChatStreams)
        self._message_crud: CRUDBase[Messages] = CRUDBase(Messages)
        self._global_clients: set[asyncio.Queue[dict[str, Any]]] = set()
        self._stream_clients: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def list_streams(self) -> ChatStreamsResponse:
        """获取按平台与聊天类型分组的聊天流列表。"""
        records = await QueryBuilder(ChatStreams).order_by("-last_active_time").all()
        groups: dict[tuple[str, str], list[ChatStreamInfo]] = defaultdict(list)

        for record in records:
            stream = await self._build_stream_info(record)
            groups[(stream.platform, stream.chat_type)].append(stream)

        return ChatStreamsResponse(
            groups=[
                ChatStreamGroup(platform=platform, chat_type=chat_type, streams=items)
                for (platform, chat_type), items in sorted(groups.items())
            ]
        )

    async def load_window(
        self,
        stream_id: str,
        anchor_message_id: str | None,
        direction: Literal["up", "down"],
        limit: int = DEFAULT_MESSAGE_LIMIT,
    ) -> MessageWindowResponse:
        """按锚点消息向上或向下加载消息窗口。"""
        safe_limit = self._normalize_limit(limit)
        anchor = None
        if anchor_message_id:
            anchor = await self._message_crud.get_by(
                stream_id=stream_id,
                message_id=anchor_message_id,
            )

        query = QueryBuilder(Messages).filter(
            stream_id=stream_id,
            message_type__in=list(SUPPORTED_MESSAGE_TYPES),
        )
        if anchor is not None:
            if direction == "up":
                query = query.filter(time__lt=anchor.time).order_by("-time")
            else:
                query = query.filter(time__gt=anchor.time).order_by("time")
        else:
            query = query.order_by("-time")

        records = await query.limit(safe_limit + 1).all()
        has_more = len(records) > safe_limit
        sliced = records[:safe_limit]
        if direction == "up" or anchor is None:
            sliced = list(reversed(sliced))

        return MessageWindowResponse(
            stream_id=stream_id,
            anchor_message_id=anchor_message_id,
            direction=direction,
            messages=[self._message_record_to_dto(record) for record in sliced],
            has_more=has_more,
        )

    async def load_around(
        self,
        stream_id: str,
        message_id: str,
        before: int = 10,
        after: int = 10,
    ) -> MessageAroundResponse:
        """加载指定消息本身以及前后上下文。"""
        target = await self._message_crud.get_by(stream_id=stream_id, message_id=message_id)
        if target is None or target.message_type not in SUPPORTED_MESSAGE_TYPES:
            return MessageAroundResponse(stream_id=stream_id, message_id=message_id, messages=[], found=False)

        before_records = await (
            QueryBuilder(Messages)
            .filter(stream_id=stream_id, message_type__in=list(SUPPORTED_MESSAGE_TYPES), time__lt=target.time)
            .order_by("-time")
            .limit(self._normalize_limit(before))
            .all()
        )
        after_records = await (
            QueryBuilder(Messages)
            .filter(stream_id=stream_id, message_type__in=list(SUPPORTED_MESSAGE_TYPES), time__gt=target.time)
            .order_by("time")
            .limit(self._normalize_limit(after))
            .all()
        )
        ordered = cast(list[Messages], list(reversed(before_records)) + [target] + list(after_records))
        return MessageAroundResponse(
            stream_id=stream_id,
            message_id=message_id,
            messages=[self._message_record_to_dto(record) for record in ordered],
            found=True,
        )

    async def send_message(
        self,
        stream_id: str,
        request: SendMessageRequest,
    ) -> SendMessageResult:
        """向指定聊天流发送消息。"""
        stream = await self._stream_crud.get_by(stream_id=stream_id)
        if stream is None:
            return SendMessageResult(ok=False, client_message_id=request.client_message_id, error="聊天流不存在")

        message = Message(
            message_id=f"webui_{uuid.uuid4().hex}",
            time=time.time(),
            reply_to=request.reply_to,
            content=request.content,
            processed_plain_text=request.content if request.message_type == "text" else None,
            message_type=MessageType(request.message_type),
            sender_id="",
            sender_name="WebUI",
            sender_role="bot",
            platform=stream.platform,
            chat_type=stream.chat_type,
            stream_id=stream_id,
            target_group_id=stream.group_id or "",
            target_group_name=stream.group_name or "",
        )
        ok = await get_message_sender().send_message(message)
        return SendMessageResult(
            ok=ok,
            client_message_id=request.client_message_id,
            message=self.runtime_message_to_dto(message) if ok else None,
            error=None if ok else "消息发送失败",
        )

    async def register_global_client(self) -> asyncio.Queue[dict[str, Any]]:
        """注册全局消息通知客户端。"""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        async with self._lock:
            self._global_clients.add(queue)
        return queue

    async def unregister_global_client(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """注销全局消息通知客户端。"""
        async with self._lock:
            self._global_clients.discard(queue)

    async def register_stream_client(self, stream_id: str) -> asyncio.Queue[dict[str, Any]]:
        """注册指定聊天流客户端。"""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        async with self._lock:
            self._stream_clients[stream_id].add(queue)
        return queue

    async def unregister_stream_client(self, stream_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """注销指定聊天流客户端。"""
        async with self._lock:
            clients = self._stream_clients.get(stream_id)
            if clients is None:
                return
            clients.discard(queue)
            if not clients:
                self._stream_clients.pop(stream_id, None)

    async def broadcast_message(self, message: Message) -> None:
        """广播核心消息事件到全局和指定流 WebSocket 客户端。"""
        if message.message_type.value not in SUPPORTED_MESSAGE_TYPES:
            return
        dto = self.runtime_message_to_dto(message)
        stream = await self._stream_crud.get_by(stream_id=message.stream_id)
        display_name = self._resolve_display_name(stream) if stream else message.stream_id
        notification = ChatNotification(
            stream_id=message.stream_id,
            platform=message.platform,
            chat_type=message.chat_type,
            display_name=display_name,
            message=dto,
        )
        await self._broadcast_to_queues(
            self._global_clients,
            {"event": "message_notify", "data": notification.model_dump()},
        )
        await self._broadcast_to_queues(
            self._stream_clients.get(message.stream_id, set()),
            {"event": "message_new", "data": dto.model_dump()},
        )

    def runtime_message_to_dto(self, message: Message) -> ChatMessageDTO:
        """将运行时 Message 转换为前端消息 DTO。"""
        message_type = message.message_type.value
        if message_type not in SUPPORTED_MESSAGE_TYPES:
            message_type = "text"
        return ChatMessageDTO(
            message_id=message.message_id,
            stream_id=message.stream_id,
            platform=message.platform,
            message_type=message_type,  # type: ignore[arg-type]
            content=self._normalize_content(message.content),
            processed_plain_text=message.processed_plain_text,
            reply_to=message.reply_to,
            sender_id=message.sender_id,
            sender_name=message.sender_name or "未知用户",
            sender_role=message.sender_role,
            time=self._normalize_time(message.time),
            is_self=message.sender_role == "bot",
        )

    async def _build_stream_info(self, record: ChatStreams) -> ChatStreamInfo:
        """构建前端聊天流列表项。"""
        last_message = await self._get_last_message(record.stream_id)
        return ChatStreamInfo(
            stream_id=record.stream_id,
            platform=record.platform,
            chat_type=record.chat_type,
            display_name=self._resolve_display_name(record),
            group_id=record.group_id,
            group_name=record.group_name,
            person_id=record.person_id,
            last_active_time=record.last_active_time,
            last_message_preview=self._preview_message(last_message) if last_message else "",
            last_message_type=last_message.message_type if last_message else "text",
        )

    async def _get_last_message(self, stream_id: str) -> Messages | None:
        """获取指定流最近一条可展示消息。"""
        records = await (
            QueryBuilder(Messages)
            .filter(stream_id=stream_id, message_type__in=list(SUPPORTED_MESSAGE_TYPES))
            .order_by("-time")
            .limit(1)
            .all()
        )
        return records[0] if records else None

    def _message_record_to_dto(self, record: Messages) -> ChatMessageDTO:
        """将数据库消息记录转换为前端 DTO。"""
        message_type = record.message_type if record.message_type in SUPPORTED_MESSAGE_TYPES else "text"
        return ChatMessageDTO(
            message_id=record.message_id,
            stream_id=record.stream_id,
            platform=record.platform or "",
            message_type=message_type,  # type: ignore[arg-type]
            content=record.content,
            processed_plain_text=record.processed_plain_text,
            reply_to=record.reply_to,
            sender_id=record.person_id,
            sender_name="Bot" if record.person_id == "bot" else (record.person_id or "未知用户"),
            sender_role="bot" if record.person_id == "bot" else None,
            time=record.time,
            is_self=record.person_id == "bot",
        )

    def _resolve_display_name(self, record: ChatStreams | None) -> str:
        """推断聊天流显示名称。"""
        if record is None:
            return "未知会话"
        if record.chat_type == "group" and record.group_name:
            return record.group_name
        if record.group_name:
            return record.group_name
        return record.person_id or record.stream_id[:12]

    def _preview_message(self, message: Messages | None) -> str:
        """生成消息预览文本。"""
        if message is None:
            return ""
        if message.message_type == "image":
            return "[图片]"
        if message.message_type == "voice":
            return "[语音]"
        return (message.processed_plain_text or message.content or "").strip()[:80]

    def _normalize_content(self, content: Any) -> str:
        """将消息内容规范化为前端字符串。"""
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            value = content.get("data") or content.get("path") or content.get("url") or content.get("text")
            return str(value or "")
        return str(content or "")

    def _normalize_time(self, value: datetime | float) -> float:
        """将消息时间规范化为 Unix 时间戳。"""
        if isinstance(value, datetime):
            return value.timestamp()
        return float(value)

    def _normalize_limit(self, limit: int) -> int:
        """限制消息加载数量范围。"""
        return max(1, min(limit, MAX_MESSAGE_LIMIT))

    async def _broadcast_to_queues(
        self,
        queues: set[asyncio.Queue[dict[str, Any]]],
        payload: dict[str, Any],
    ) -> None:
        """向队列集合广播消息，并清理已阻塞队列。"""
        disconnected: list[asyncio.Queue[dict[str, Any]]] = []
        async with self._lock:
            for queue in queues:
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    try:
                        queue.get_nowait()
                        queue.put_nowait(payload)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        disconnected.append(queue)

            for queue in disconnected:
                queues.discard(queue)


_chat_manager: ChatManager | None = None


def get_chat_manager() -> ChatManager:
    """获取全局聊天管理器。"""
    global _chat_manager
    if _chat_manager is None:
        _chat_manager = ChatManager()
    return _chat_manager
