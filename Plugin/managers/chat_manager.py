"""聊天消息管理器。

提供聊天流列表、消息窗口查询、WebSocket 广播和发送消息的业务逻辑。
"""

from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, Field

from src.core.managers.adapter_manager import get_adapter_manager
from src.core.managers.media_manager import get_media_manager
from src.core.models.message import Message, MessageType
from src.core.models.sql_alchemy import ChatStreams, Messages, PersonInfo
from src.core.transport.message_send.message_sender import get_message_sender
from src.kernel.db import CRUDBase, QueryBuilder
from src.kernel.logger import get_logger

from ..utils.chat_message_parser import (
    SEGMENT_DATA_KEY,
    parse_message_content,
    parse_segments,
    segments_to_plain_text,
    split_reply_preview,
)

logger = get_logger("webui.chat_manager", display="WebUI.ChatManager")

SUPPORTED_MESSAGE_TYPES: frozenset[str] = frozenset({"text", "image", "emoji", "voice", "video", "file"})
DEFAULT_MESSAGE_LIMIT = 30
MAX_MESSAGE_LIMIT = 100


MEDIA_MESSAGE_TYPES: frozenset[str] = frozenset({"image", "emoji", "voice"})
BASE64_PATTERN = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
DATA_URL_PATTERN = re.compile(r"^data:(?P<mime>[^;,]+)?;base64,(?P<data>.*)$", re.DOTALL)
BASE64_URL_PREFIX = "base64://"
VOICE_MIME_TYPE = "audio/wav"
MEDIA_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
BASE64_PIPE_PREFIX = "base64|"
# 实时消息内联媒体的最大 base64 长度，超出则只给 media_id，由前端按需拉取
INLINE_MEDIA_MAX_CHARS = 6 * 1024 * 1024
UNKNOWN_SENDER = "未知用户"
# 按需拉取媒体的最大 base64 长度（约 24MB 原文件）
MAX_MEDIA_RESPONSE_CHARS = 32 * 1024 * 1024
PERSON_QUERY_CHUNK = 500

ChatMessageKind = Literal["text", "image", "emoji", "voice", "video", "file"]
ChatSegmentKind = Literal["text", "at", "image", "emoji", "voice", "video", "file"]


class ChatStreamInfo(BaseModel):
    """前端聊天流列表项。"""

    stream_id: str = Field(description="聊天流 ID")
    platform: str = Field(description="平台标识")
    chat_type: str = Field(description="聊天类型")
    display_name: str = Field(description="前端显示名称")
    group_id: str | None = Field(default=None, description="群组 ID")
    group_name: str | None = Field(default=None, description="群组名称")
    person_id: str = Field(description="用户 person_id")
    peer_user_id: str | None = Field(default=None, description="私聊对象的平台用户 ID")
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


class ChatMessageMediaDTO(BaseModel):
    """前端可渲染的媒体消息内容。"""

    mime_type: str = Field(description="媒体 MIME 类型")
    base64: str = Field(description="不含 data URL 前缀的 base64 内容")
    data_url: str = Field(description="可直接用于 src 的 data URL")


class ChatMessageSegmentDTO(BaseModel):
    """消息正文片段。"""

    type: ChatSegmentKind = Field(description="片段类型")
    text: str = Field(default="", description="文本、@ 昵称或媒体描述")
    user_id: str | None = Field(default=None, description="@ 目标的平台用户 ID")
    media_id: str | None = Field(default=None, description="媒体哈希，可经 /media/{media_id} 拉取")
    data_url: str | None = Field(default=None, description="内联媒体 data URL")


class ChatReplyDTO(BaseModel):
    """被引用消息摘要。"""

    message_id: str | None = Field(default=None, description="被引用消息 ID")
    sender_id: str | None = Field(default=None, description="被引用消息发送者平台 ID")
    sender_name: str = Field(default="", description="被引用消息发送者名称")
    is_self: bool = Field(default=False, description="被引用的是否为机器人消息")
    segments: list[ChatMessageSegmentDTO] = Field(default_factory=list, description="被引用消息正文片段")
    preview: str = Field(default="", description="被引用消息单行预览")
    found: bool = Field(default=False, description="被引用消息是否在消息记录中")


class ChatMessageDTO(BaseModel):
    """前端可渲染的聊天消息。"""

    message_id: str = Field(description="消息 ID")
    stream_id: str = Field(description="聊天流 ID")
    platform: str = Field(default="", description="平台标识")
    message_type: ChatMessageKind = Field(description="消息类型")
    content: str = Field(default="", description="消息内容或媒体 base64/路径")
    media: ChatMessageMediaDTO | None = Field(default=None, description="图片或语音媒体内容")
    processed_plain_text: str | None = Field(default=None, description="处理后的纯文本")
    reply_to: str | None = Field(default=None, description="引用消息 ID")
    sender_id: str | None = Field(default=None, description="发送者 ID")
    sender_name: str = Field(default="", description="发送者名称")
    sender_role: str | None = Field(default=None, description="发送者角色")
    time: float = Field(description="消息时间戳")
    is_self: bool = Field(default=False, description="是否为机器人自己发送")
    segments: list[ChatMessageSegmentDTO] = Field(default_factory=list, description="解析后的正文片段")
    reply: ChatReplyDTO | None = Field(default=None, description="被引用消息摘要")


class ChatMediaDTO(BaseModel):
    """按需拉取的聊天媒体。"""

    media_id: str = Field(description="媒体哈希")
    mime_type: str = Field(description="媒体 MIME 类型")
    data_url: str = Field(description="可直接用于 src 的 data URL")


@dataclass
class _MessageBody:
    """消息内容解析结果。"""

    reply_preview: dict[str, str] | None
    segments: list[ChatMessageSegmentDTO]
    media: ChatMessageMediaDTO | None
    content: str


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
        people = await self._load_people(
            [record.person_id for record in records if record.chat_type != "group"]
        )
        groups: dict[tuple[str, str], list[ChatStreamInfo]] = defaultdict(list)

        for record in records:
            stream = await self._build_stream_info(record, people)
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
            messages=await self._records_to_dtos(cast(list[Messages], sliced)),
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
            messages=await self._records_to_dtos(ordered),
            found=True,
        )

    async def get_media(self, media_id: str) -> ChatMediaDTO | None:
        """按媒体哈希读取已落盘的图片、表情包或语音。

        Args:
            media_id: 媒体哈希（image_id / voice_id）。

        Returns:
            可直接用于 src 的媒体内容；哈希非法、文件不存在或过大时返回 None。
        """
        if not MEDIA_ID_PATTERN.fullmatch(media_id):
            return None
        try:
            data = await get_media_manager().get_media_file(media_id)
        except Exception as exc:
            logger.warning(f"读取聊天媒体失败: media_id={media_id[:8]}, error={exc}")
            return None
        if not data:
            return None

        base64_data = self._strip_base64_prefix(data)
        if len(base64_data) > MAX_MEDIA_RESPONSE_CHARS:
            return None
        mime_type = self._sniff_media_mime("image", base64_data)
        return ChatMediaDTO(
            media_id=media_id,
            mime_type=mime_type,
            data_url=f"data:{mime_type};base64,{base64_data}",
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
            message=await self.runtime_message_to_dto(message) if ok else None,
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
        dto = await self.runtime_message_to_dto(message)
        stream = await self._stream_crud.get_by(stream_id=message.stream_id)
        display_name = await self._stream_display_name(stream) if stream else message.stream_id
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

    async def runtime_message_to_dto(self, message: Message) -> ChatMessageDTO:
        """将运行时 Message 转换为前端消息 DTO。"""
        message_type = self._normalize_message_type(message.message_type.value)
        bot_info = await self._get_bot_info(message.platform)
        sender_id = str(message.sender_id or "") or None
        is_self = message.sender_role == "bot" or bool(
            bot_info.get("bot_id") and sender_id == bot_info["bot_id"]
        )
        if is_self:
            sender_name = bot_info.get("bot_name") or message.sender_name or "Bot"
        else:
            sender_name = message.sender_cardname or message.sender_name or sender_id or UNKNOWN_SENDER

        body = self._build_body(message_type, message.content, message.processed_plain_text)
        reply = None
        if message.reply_to:
            target = await self._message_crud.get_by(stream_id=message.stream_id, message_id=message.reply_to)
            if target is not None:
                people = await self._load_people([target.person_id or ""])
                reply = self._target_reply_dto(target, people, bot_info)
        if reply is None and (message.reply_to or body.reply_preview is not None):
            reply = self._preview_reply_dto(message.reply_to, body.reply_preview, bot_info)

        return ChatMessageDTO(
            message_id=message.message_id,
            stream_id=message.stream_id,
            platform=message.platform,
            message_type=message_type,  # type: ignore[arg-type]
            content=body.content,
            media=body.media,
            processed_plain_text=message.processed_plain_text,
            reply_to=message.reply_to,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_role=message.sender_role,
            time=self._normalize_time(message.time),
            is_self=is_self,
            segments=body.segments,
            reply=reply,
        )

    async def _build_stream_info(self, record: ChatStreams, people: dict[str, PersonInfo]) -> ChatStreamInfo:
        """构建前端聊天流列表项。"""
        last_message = await self._get_last_message(record.stream_id)
        person = people.get(record.person_id) if record.chat_type != "group" else None
        return ChatStreamInfo(
            stream_id=record.stream_id,
            platform=record.platform,
            chat_type=record.chat_type,
            display_name=self._resolve_display_name(record, person),
            group_id=record.group_id,
            group_name=record.group_name,
            person_id=record.person_id,
            peer_user_id=str(person.user_id) if person is not None and person.user_id else None,
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

    async def _records_to_dtos(self, records: list[Messages]) -> list[ChatMessageDTO]:
        """批量将数据库消息记录转换为前端 DTO，统一查询发送者昵称与被引用消息。"""
        if not records:
            return []

        reply_targets: dict[str, Messages] = {}
        reply_ids = sorted({record.reply_to for record in records if record.reply_to})
        if reply_ids:
            stream_ids = sorted({record.stream_id for record in records})
            targets = await (
                QueryBuilder(Messages)
                .filter(message_id__in=reply_ids, stream_id__in=stream_ids)
                .all()
            )
            reply_targets = {target.message_id: target for target in cast(list[Messages], targets)}

        people = await self._load_people(
            [record.person_id or "" for record in [*records, *reply_targets.values()]]
        )
        bot_infos: dict[str, dict[str, str]] = {}
        for platform in {record.platform or "" for record in records}:
            bot_infos[platform] = await self._get_bot_info(platform)

        return [
            self._message_record_to_dto(record, people, bot_infos[record.platform or ""], reply_targets)
            for record in records
        ]

    def _message_record_to_dto(
        self,
        record: Messages,
        people: dict[str, PersonInfo],
        bot_info: dict[str, str],
        reply_targets: dict[str, Messages],
    ) -> ChatMessageDTO:
        """将数据库消息记录转换为前端 DTO。"""
        message_type = self._normalize_message_type(record.message_type)
        sender_id, sender_name, is_self = self._record_sender(record, people, bot_info)
        body = self._build_body(message_type, record.content, record.processed_plain_text)

        reply = None
        target = reply_targets.get(record.reply_to) if record.reply_to else None
        if target is not None:
            reply = self._target_reply_dto(target, people, bot_info)
        elif record.reply_to or body.reply_preview is not None:
            reply = self._preview_reply_dto(record.reply_to, body.reply_preview, bot_info)

        return ChatMessageDTO(
            message_id=record.message_id,
            stream_id=record.stream_id,
            platform=record.platform or "",
            message_type=message_type,  # type: ignore[arg-type]
            content=body.content,
            media=body.media,
            processed_plain_text=record.processed_plain_text,
            reply_to=record.reply_to,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_role="bot" if record.person_id == "bot" else None,
            time=record.time,
            is_self=is_self,
            segments=body.segments,
            reply=reply,
        )

    def _record_sender(
        self,
        record: Messages,
        people: dict[str, PersonInfo],
        bot_info: dict[str, str],
    ) -> tuple[str | None, str, bool]:
        """解析数据库消息的发送者 (平台用户 ID, 显示名称, 是否机器人)。"""
        if record.person_id == "bot":
            return bot_info.get("bot_id") or None, bot_info.get("bot_name") or "Bot", True

        person = people.get(record.person_id or "")
        if person is None:
            return None, UNKNOWN_SENDER, False
        user_id = str(person.user_id or "") or None
        name = person.cardname or person.nickname or user_id or UNKNOWN_SENDER
        is_self = bool(user_id and bot_info.get("bot_id") and user_id == bot_info["bot_id"])
        return user_id, name, is_self

    def _target_reply_dto(
        self,
        target: Messages,
        people: dict[str, PersonInfo],
        bot_info: dict[str, str],
    ) -> ChatReplyDTO:
        """用消息记录中找到的被引用消息构建引用摘要。"""
        sender_id, sender_name, is_self = self._record_sender(target, people, bot_info)
        body = self._build_body(
            self._normalize_message_type(target.message_type),
            target.content,
            target.processed_plain_text,
        )
        return ChatReplyDTO(
            message_id=target.message_id,
            sender_id=sender_id,
            sender_name=sender_name,
            is_self=is_self,
            segments=body.segments,
            preview=self._segments_preview(body.segments),
            found=True,
        )

    def _preview_reply_dto(
        self,
        reply_to: str | None,
        preview: dict[str, str] | None,
        bot_info: dict[str, str],
    ) -> ChatReplyDTO:
        """被引用消息不在记录中时，用适配器写入的引用预览文本构建摘要。"""
        preview = preview or {"sender_name": "", "sender_id": "", "text": ""}
        sender_id = preview["sender_id"] or None
        # 适配器在被引用者是机器人自己时把昵称写成「你」
        is_self = preview["sender_name"] == "你" or bool(
            sender_id and bot_info.get("bot_id") and sender_id == bot_info["bot_id"]
        )
        sender_name = (bot_info.get("bot_name") or "Bot") if is_self else preview["sender_name"]
        segments = [self._segment_to_dto(segment) for segment in parse_segments(preview["text"])]
        return ChatReplyDTO(
            message_id=reply_to,
            sender_id=sender_id,
            sender_name=sender_name,
            is_self=is_self,
            segments=segments,
            preview=self._segments_preview(segments),
            found=False,
        )

    def _build_body(
        self,
        message_type: str,
        raw_content: Any,
        processed_text: str | None,
    ) -> _MessageBody:
        """把消息内容解析为引用预览、正文片段和兼容旧格式的媒体。"""
        text, media_items = parse_message_content(raw_content)
        legacy_media = None
        if not media_items:
            legacy_media = self._build_media_dto(message_type, raw_content, self._normalize_content(raw_content))

        # 旧格式的 content 是裸 base64，不能当正文解析
        body_text = (processed_text or "") if legacy_media is not None else (processed_text or text)
        reply_preview, body_text = split_reply_preview(body_text)
        segments = [self._segment_to_dto(segment) for segment in parse_segments(body_text, media_items)]

        if legacy_media is not None:
            legacy_type = message_type if message_type in MEDIA_MESSAGE_TYPES else "image"
            slot = next(
                (segment for segment in segments if segment.type == legacy_type and segment.data_url is None),
                None,
            )
            if slot is not None:
                slot.data_url = legacy_media.data_url
            else:
                segments.append(ChatMessageSegmentDTO(type=legacy_type, data_url=legacy_media.data_url))  # type: ignore[arg-type]

        content = text if media_items else self._normalize_content(raw_content)
        return _MessageBody(reply_preview=reply_preview, segments=segments, media=legacy_media, content=content)

    def _segment_to_dto(self, segment: dict[str, Any]) -> ChatMessageSegmentDTO:
        """把解析出的片段转换为 DTO，内联媒体数据转换为 data URL。"""
        data = segment.pop(SEGMENT_DATA_KEY, None)
        dto = ChatMessageSegmentDTO(**segment)
        if isinstance(data, str) and data:
            dto.data_url = self._inline_media_url(dto.type, data)
        return dto

    def _inline_media_url(self, segment_type: str, value: str) -> str | None:
        """把运行时媒体数据转换为可直接渲染的地址；视频和过大的媒体交给前端按需拉取。"""
        if segment_type not in MEDIA_MESSAGE_TYPES:
            return None
        value = value.strip()
        if value.startswith(("http://", "https://")):
            return value
        if len(value) > INLINE_MEDIA_MAX_CHARS:
            return None
        if value.startswith("data:"):
            return value if DATA_URL_PATTERN.match(value) else None

        base64_data = self._strip_base64_prefix(value)
        if not base64_data or not BASE64_PATTERN.fullmatch(base64_data[:256].rstrip("=")):
            return None
        mime_type = self._sniff_media_mime(segment_type, base64_data)
        return f"data:{mime_type};base64,{base64_data}"

    def _segments_preview(self, segments: list[ChatMessageSegmentDTO]) -> str:
        """生成片段的单行预览。"""
        return segments_to_plain_text([segment.model_dump() for segment in segments])

    async def _load_people(self, person_ids: list[str]) -> dict[str, PersonInfo]:
        """批量查询用户信息。"""
        unique_ids = sorted({person_id for person_id in person_ids if person_id and person_id != "bot"})
        people: dict[str, PersonInfo] = {}
        for index in range(0, len(unique_ids), PERSON_QUERY_CHUNK):
            chunk = unique_ids[index:index + PERSON_QUERY_CHUNK]
            records = await QueryBuilder(PersonInfo).filter(person_id__in=chunk).all()
            for record in cast(list[PersonInfo], records):
                people[record.person_id] = record
        return people

    async def _get_bot_info(self, platform: str | None) -> dict[str, str]:
        """获取平台对应的机器人 ID 与昵称，查询失败时返回空字典。"""
        if not platform:
            return {}
        try:
            info = await get_adapter_manager().get_bot_info_by_platform(platform)
        except Exception as exc:
            logger.debug(f"获取机器人信息失败: platform={platform}, error={exc}")
            return {}
        if not info:
            return {}
        return {
            "bot_id": str(info.get("bot_id") or ""),
            "bot_name": str(info.get("bot_name") or ""),
        }

    async def _stream_display_name(self, record: ChatStreams) -> str:
        """推断单个聊天流的显示名称（私聊会查询对方昵称）。"""
        person = None
        if record.chat_type != "group" and not record.group_name:
            person = (await self._load_people([record.person_id])).get(record.person_id)
        return self._resolve_display_name(record, person)

    def _resolve_display_name(self, record: ChatStreams | None, person: PersonInfo | None = None) -> str:
        """推断聊天流显示名称。"""
        if record is None:
            return "未知会话"
        if record.group_name:
            return record.group_name
        if person is not None:
            name = person.nickname or person.cardname or person.user_id
            if name:
                return str(name)
        return record.group_id or record.stream_id[:12]

    def _preview_message(self, message: Messages | None) -> str:
        """生成消息预览文本。"""
        if message is None:
            return ""
        body = self._build_body(
            self._normalize_message_type(message.message_type),
            message.content,
            message.processed_plain_text,
        )
        return self._segments_preview(body.segments)

    def _normalize_message_type(self, value: str) -> str:
        """未知消息类型按文本处理。"""
        return value if value in SUPPORTED_MESSAGE_TYPES else "text"

    def _normalize_content(self, content: Any) -> str:
        """将消息内容规范化为前端字符串。"""
        if isinstance(content, str):
            parsed = self._try_parse_json(content)
            if parsed is not None:
                return self._normalize_content(parsed)
            return content
        if isinstance(content, dict):
            value = (
                content.get("base64")
                or content.get("data")
                or content.get("file")
                or content.get("path")
                or content.get("url")
                or content.get("text")
            )
            return str(value or "")
        return str(content or "")

    def _build_media_dto(
        self,
        message_type: str,
        raw_content: Any,
        normalized_content: str,
    ) -> ChatMessageMediaDTO | None:
        """从图片或语音消息内容构建媒体 DTO。"""
        if message_type not in MEDIA_MESSAGE_TYPES:
            return None

        media_value = self._extract_media_value(raw_content) or normalized_content
        media_value = media_value.strip()
        if not media_value:
            return None

        data_url_match = DATA_URL_PATTERN.match(media_value)
        if data_url_match:
            mime_type = data_url_match.group("mime") or self._default_media_mime_type(message_type)
            base64_data = data_url_match.group("data")
            return ChatMessageMediaDTO(
                mime_type=mime_type,
                base64=base64_data,
                data_url=f"data:{mime_type};base64,{base64_data}",
            )

        if media_value.startswith(BASE64_URL_PREFIX):
            base64_data = media_value.removeprefix(BASE64_URL_PREFIX)
            mime_type = self._guess_media_mime_type(message_type, "")
            return ChatMessageMediaDTO(
                mime_type=mime_type,
                base64=base64_data,
                data_url=f"data:{mime_type};base64,{base64_data}",
            )

        if self._looks_like_base64(media_value):
            mime_type = self._guess_media_mime_type(message_type, media_value)
            return ChatMessageMediaDTO(
                mime_type=mime_type,
                base64=media_value,
                data_url=f"data:{mime_type};base64,{media_value}",
            )

        return None

    def _extract_media_value(self, content: Any) -> str:
        """从结构化消息内容中提取媒体数据。"""
        if isinstance(content, str):
            parsed = self._try_parse_json(content)
            if parsed is not None:
                return self._extract_media_value(parsed)
            return content
        if isinstance(content, dict):
            value = (
                content.get("base64")
                or content.get("data")
                or content.get("file")
                or content.get("path")
                or content.get("url")
            )
            return str(value or "")
        return str(content or "")

    def _try_parse_json(self, content: str) -> Any | None:
        """尝试解析数据库中以 JSON 字符串保存的结构化消息。"""
        stripped = content.strip()
        if not stripped or stripped[0] not in "[{":
            return None
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None

    def _looks_like_base64(self, value: str) -> bool:
        """判断字符串是否像 base64 内容。"""
        compact_value = "".join(value.split())
        if len(compact_value) < 16 or len(compact_value) % 4 != 0:
            return False
        if not BASE64_PATTERN.fullmatch(compact_value):
            return False
        try:
            base64.b64decode(compact_value, validate=True)
        except ValueError:
            return False
        return True

    def _strip_base64_prefix(self, value: str) -> str:
        """去掉 ``base64|`` / ``base64://`` 前缀与空白。"""
        value = value.strip()
        for prefix in (BASE64_PIPE_PREFIX, BASE64_URL_PREFIX):
            if value.startswith(prefix):
                value = value[len(prefix):]
                break
        return "".join(value.split())

    def _sniff_media_mime(self, segment_type: str, base64_data: str) -> str:
        """根据文件头推断媒体 MIME 类型。"""
        try:
            header = base64.b64decode(base64_data[:64] + "=" * (-len(base64_data[:64]) % 4), validate=False)[:16]
        except ValueError:
            header = b""
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if header.startswith((b"GIF87a", b"GIF89a")):
            return "image/gif"
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "image/webp"
        if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
            return "audio/wav"
        if header.startswith(b"ID3") or header[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            return "audio/mpeg"
        if header.startswith(b"OggS"):
            return "audio/ogg"
        if header.startswith(b"#!AMR"):
            return "audio/amr"
        return VOICE_MIME_TYPE if segment_type == "voice" else "image/png"

    def _guess_media_mime_type(self, message_type: str, base64_data: str) -> str:
        """推断媒体 MIME 类型。"""
        if message_type == "voice":
            return VOICE_MIME_TYPE
        if not base64_data:
            return self._default_media_mime_type(message_type)
        try:
            header = base64.b64decode(base64_data[:64], validate=False)[:16]
        except ValueError:
            return self._default_media_mime_type(message_type)
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return "image/gif"
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "image/webp"
        return self._default_media_mime_type(message_type)

    def _default_media_mime_type(self, message_type: str) -> str:
        """返回指定媒体消息类型的默认 MIME 类型。"""
        if message_type == "voice":
            return VOICE_MIME_TYPE
        guessed = mimetypes.guess_type(f"fallback.{Path('image.png').suffix.lstrip('.')}")[0]
        return guessed or "image/png"

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
