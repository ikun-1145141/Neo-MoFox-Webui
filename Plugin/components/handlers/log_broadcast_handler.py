"""日志广播事件处理器。

订阅内核日志事件 (log_output)，将实时日志转发给 WebSocket 客户端。
"""

from __future__ import annotations

from typing import Any

from src.core.components import BaseEventHandler, EventType
from src.kernel.event import EventDecision
from src.kernel.logger import get_logger
from src.kernel.logger.logger import LOG_OUTPUT_EVENT

from ...managers.log_manager import get_log_manager

logger = get_logger("webui.log_broadcast", display="WebUI.LogBroadcast")


class LogBroadcastHandler(BaseEventHandler):
    """日志广播事件处理器。

    订阅内核的 log_output 事件，将日志数据推送到 LogManager
    的缓冲区和所有已连接的 WebSocket 客户端。
    """

    handler_name: str = "webui_log_broadcast"
    handler_description: str = "捕获实时日志并广播给 WebSocket 客户端"
    weight: int = -10  # 低优先级，不影响其他处理器
    intercept_message: bool = False
    init_subscribe: list[EventType | str] = [LOG_OUTPUT_EVENT]

    async def execute(
        self,
        event_name: str,
        params: dict[str, Any],
    ) -> tuple[EventDecision, dict[str, Any]]:
        """处理日志输出事件。

        接收内核发布的日志数据，转发给 LogManager 进行缓冲和广播。

        Args:
            event_name: 触发的事件名称（应为 "log_output"）
            params: 事件参数字典，包含日志数据

        Returns:
            事件处理决策和原始参数（不修改参数，继续传播）
        """
        try:
            log_manager = get_log_manager()
            await log_manager.push_log(params)
        except Exception:
            # 日志广播失败不应影响系统运行
            pass

        return EventDecision.SUCCESS, params
