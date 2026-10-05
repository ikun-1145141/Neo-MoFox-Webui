"""聊天 Router 组件。

提供聊天流列表、全局消息通知 WebSocket 和指定流 WebSocket 会话协议。
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket, WebSocketDisconnect

from src.app.plugin_system.api.log_api import get_logger
from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep, verify_websocket_token

from ...managers.chat_manager import SendMessageRequest, get_chat_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("webui.chat_router", display="WebUI.ChatRouter")


class ChatRouter(BaseRouter):
    """聊天 Router 组件。

    提供聊天流 HTTP 列表、全局新消息通知和指定流会话 WebSocket。
    """

    name: str = "chat"
    description: str = "聊天消息 API（HTTP 列表 + WebSocket 会话）"
    custom_route_path: str = "/webui/api/chat"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化聊天 Router。

        Args:
            plugin: 所属插件实例。
        """
        super().__init__(plugin)

    def register_endpoints(self) -> None:
        """注册聊天相关端点。"""

        @self.app.get("/streams", response_model=BaseResponse, dependencies=[VerifiedDep])
        async def list_streams() -> BaseResponse:
            """获取聊天流列表。"""
            chat_manager = get_chat_manager()
            return BaseResponse.ok(await chat_manager.list_streams())

        @self.app.websocket("/ws/notifications")
        async def websocket_notifications(websocket: WebSocket) -> None:
            """全局消息通知 WebSocket。"""
            if not await verify_websocket_token(websocket):
                return
            await websocket.accept()

            chat_manager = get_chat_manager()
            queue = await chat_manager.register_global_client()
            try:
                send_task = asyncio.create_task(self._send_queue_messages(websocket, queue))
                recv_task = asyncio.create_task(self._receive_global_messages(websocket))
                done, pending = await asyncio.wait(
                    [send_task, recv_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    task.result()
            except WebSocketDisconnect:
                pass
            except Exception as exc:
                logger.warning(f"全局聊天通知 WS 断开: {exc}")
            finally:
                await chat_manager.unregister_global_client(queue)

        @self.app.websocket("/ws/streams/{stream_id}")
        async def websocket_stream(websocket: WebSocket, stream_id: str) -> None:
            """指定聊天流 WebSocket。"""
            if not await verify_websocket_token(websocket):
                return
            await websocket.accept()

            chat_manager = get_chat_manager()
            queue = await chat_manager.register_stream_client(stream_id)
            try:
                send_task = asyncio.create_task(self._send_queue_messages(websocket, queue))
                recv_task = asyncio.create_task(self._receive_stream_messages(websocket, stream_id))
                done, pending = await asyncio.wait(
                    [send_task, recv_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                for task in done:
                    task.result()
            except WebSocketDisconnect:
                pass
            except Exception as exc:
                logger.warning(f"指定流聊天 WS 断开: stream_id={stream_id}, error={exc}")
            finally:
                await chat_manager.unregister_stream_client(stream_id, queue)

    async def _send_queue_messages(
        self,
        websocket: WebSocket,
        queue: asyncio.Queue[dict[str, Any]],
    ) -> None:
        """持续发送队列中的服务端消息。"""
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)

    async def _receive_global_messages(self, websocket: WebSocket) -> None:
        """接收全局通知 WS 的客户端消息。"""
        while True:
            raw = await websocket.receive_text()
            message = self._parse_ws_message(raw)
            if message.get("event") == "ping":
                await websocket.send_json({"event": "pong", "data": None})

    async def _receive_stream_messages(self, websocket: WebSocket, stream_id: str) -> None:
        """接收指定流 WS 的客户端消息并执行协议动作。"""
        chat_manager = get_chat_manager()
        while True:
            raw = await websocket.receive_text()
            message = self._parse_ws_message(raw)
            event = str(message.get("event") or "")
            raw_data = message.get("data")
            data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}

            try:
                if event == "ping":
                    await websocket.send_json({"event": "pong", "data": None})
                elif event == "load_window":
                    direction = data.get("direction", "up")
                    result = await chat_manager.load_window(
                        stream_id=stream_id,
                        anchor_message_id=data.get("anchor_message_id"),
                        direction=direction if direction in {"up", "down"} else "up",
                        limit=int(data.get("limit", 30)),
                    )
                    await websocket.send_json({"event": "messages_window", "data": result.model_dump()})
                elif event == "load_around":
                    result = await chat_manager.load_around(
                        stream_id=stream_id,
                        message_id=str(data.get("message_id") or ""),
                        before=int(data.get("before", 10)),
                        after=int(data.get("after", 10)),
                    )
                    await websocket.send_json({"event": "messages_around", "data": result.model_dump()})
                elif event == "send_message":
                    request = SendMessageRequest.model_validate(data)
                    result = await chat_manager.send_message(stream_id, request)
                    await websocket.send_json({"event": "send_result", "data": result.model_dump()})
                else:
                    await websocket.send_json({"event": "error", "data": {"message": "未知事件类型"}})
            except Exception as exc:
                logger.warning(f"处理聊天 WS 消息失败: event={event}, error={exc}")
                await websocket.send_json({"event": "error", "data": {"message": str(exc)}})

    def _parse_ws_message(self, raw: str) -> dict[str, Any]:
        """解析前端 WebSocket 消息。"""
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            return {"event": "", "data": {}}
        return message if isinstance(message, dict) else {"event": "", "data": {}}
