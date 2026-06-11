"""LLM 统计管理器。

负责承接 WebUI LLM 统计路由的业务逻辑，统一调用底层指标工具并向路由层返回
已归一化的数据结构。
"""

from __future__ import annotations

from typing import Any

from src.core.managers.stream_manager import get_stream_manager

from ..utils import get_llm_metrics_helper
from ..utils.llm_metrics import LLMMetricsHelper


class LLMMetricsManager:
    """WebUI LLM 统计管理器。"""

    def __init__(self) -> None:
        """初始化 LLM 统计管理器。"""
        self.metrics_helper: LLMMetricsHelper = get_llm_metrics_helper()

    async def get_overview(self) -> dict[str, Any]:
        """获取数据库中的 LLM 统计摘要。

        Returns:
            数据库统计后端的请求数、Token、成本、延迟和缓存命中率摘要。
        """
        return await self.metrics_helper.get_overview()

    async def get_recent_requests_by_hours(
        self,
        *,
        hours: float = 5.0,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """获取最近若干小时内的 LLM 请求明细。

        Args:
            hours: 向前查询的小时数。
            limit: 返回数量上限。
            offset: 分页偏移量。

        Returns:
            最近指定小时内的请求记录列表。
        """
        return await self.metrics_helper.get_recent_requests_by_hours(
            hours=hours,
            limit=limit,
            offset=offset,
        )

    async def list_streams(self) -> list[dict[str, Any]]:
        """获取按 stream_id 分组并补齐会话来源信息的持久化统计。

        Returns:
            聊天流维度的持久化统计列表，包含平台、聊天类型、群号、群名、
            私聊标识和群聊标识等前端展示字段。
        """
        rows = await self.metrics_helper.list_streams()
        stream_manager = get_stream_manager()
        enriched_rows: list[dict[str, Any]] = []

        for row in rows:
            # logger.debug(f"Enriching stream stats row: {row}")
            stream_id = str(row.get("stream_id") or "")
            stream_info = await stream_manager.get_stream_info(stream_id) if stream_id else None
            chat_type = str((stream_info or {}).get("chat_type") or "unknown")

            enriched_rows.append({
                **row,
                "platform": (stream_info or {}).get("platform") or "unknown",
                "chat_type": chat_type,
                "group_id": (stream_info or {}).get("group_id"),
                "group_name": (stream_info or {}).get("group_name"),
                "person_id": (stream_info or {}).get("person_id"),
                "message_count": (stream_info or {}).get("message_count", 0),
                "is_group_chat": chat_type in {"group", "discuss"},
                "is_private_chat": chat_type == "private",
            })

        return enriched_rows

    async def get_last_hours_summary(self, *, hours: float = 5.0) -> dict[str, Any]:
        """获取最近若干小时的持久化统计摘要。

        Args:
            hours: 向前统计的小时数。

        Returns:
            最近指定小时内的统计摘要。
        """
        return await self.metrics_helper.get_last_hours_summary(hours=hours)


_llm_metrics_manager_instance: LLMMetricsManager | None = None


def get_llm_metrics_manager() -> LLMMetricsManager:
    """获取 LLM 统计管理器单例。

    Returns:
        LLM 统计管理器实例。
    """
    global _llm_metrics_manager_instance
    if _llm_metrics_manager_instance is None:
        _llm_metrics_manager_instance = LLMMetricsManager()
    return _llm_metrics_manager_instance
