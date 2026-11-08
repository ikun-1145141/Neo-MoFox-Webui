"""聊天消息广播事件处理器。

订阅核心消息收发事件，将 text/image/voice 消息转发给 WebUI 聊天 WebSocket。
"""

from __future__ import annotations

from typing import Any

from src.core.components import BaseEventHandler, EventType
from src.core.models.message import Message
from src.kernel.event import EventDecision
from src.kernel.logger import get_logger

from ...managers.chat_manager import get_chat_manager

logger = get_logger("webui.chat_broadcast", display="WebUI.ChatBroadcast")


class ChatBroadcastHandler(BaseEventHandler):
    """聊天消息广播事件处理器。

    监听核心收到和发送的消息，将可展示消息推送给全局通知和指定流 WebSocket 客户端。
    """

    name: str = "webui_chat_broadcast"
    description: str = "捕获聊天消息并广播给 WebSocket 客户端"
    weight: int = -10
    intercept_message: bool = False
    init_subscribe: list[EventType | str] = [
        EventType.ON_MESSAGE_RECEIVED,
        EventType.ON_MESSAGE_SENT,
    ]

    async def execute(
        self,
        event_name: str,
        params: dict[str, Any],
    ) -> tuple[EventDecision, dict[str, Any]]:
        """处理核心消息事件。

        Args:
            event_name: 事件名称。
            params: 事件参数，需包含 message。

        Returns:
            事件处理决策和原始参数。
        """
        message = params.get("message")
        if not isinstance(message, Message):
            return EventDecision.SUCCESS, params

        try:
            await get_chat_manager().broadcast_message(message)
        except Exception as exc:
            logger.warning(f"广播聊天消息失败: event={event_name}, error={exc}")

        return EventDecision.SUCCESS, params
