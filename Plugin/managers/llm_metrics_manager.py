"""LLM 统计管理器。

负责承接 WebUI LLM 统计路由的业务逻辑，统一调用底层指标工具并向路由层返回
已归一化的数据结构。
"""

from __future__ import annotations

from typing import Any

from ..utils import get_llm_metrics_helper
from ..utils.llm_metrics import LLMMetricsHelper


class LLMMetricsManager:
    """WebUI LLM 统计管理器。"""

    def __init__(self) -> None:
        """初始化 LLM 统计管理器。"""
        self.metrics_helper: LLMMetricsHelper = get_llm_metrics_helper()

    async def get_overview(self) -> dict[str, Any]:
        """获取内存指标和持久化统计的组合总览。

        Returns:
            同时包含 legacy 内存指标与 persistent 持久化指标的统计总览。
        """
        return await self.metrics_helper.get_combined_overview()

    def get_memory_overview(self) -> dict[str, Any]:
        """获取旧内存收集器的 LLM 指标总览。

        Returns:
            内存收集器中的跨模型汇总指标。
        """
        return self.metrics_helper.get_overview()

    async def get_persistent_overview(self) -> dict[str, Any]:
        """获取持久化 LLM 统计后端的摘要。

        Returns:
            持久化统计后端的请求数、Token、成本、延迟和缓存命中率摘要。
        """
        return await self.metrics_helper.get_persistent_overview()

    async def list_models(self) -> list[dict[str, Any]]:
        """获取持久化统计后端中的按模型分组统计。

        Returns:
            模型维度的持久化统计列表。
        """
        return await self.metrics_helper.list_persistent_models()

    def list_memory_models(self) -> list[dict[str, Any]]:
        """获取内存收集器中的按模型分组指标。

        Returns:
            模型维度的内存统计列表。
        """
        return self.metrics_helper.list_models()

    def get_model(self, model_name: str) -> dict[str, Any]:
        """获取内存收集器中的单模型指标。

        Args:
            model_name: 模型名称或模型标识符。

        Returns:
            指定模型的内存统计数据。
        """
        return self.metrics_helper.get_model(model_name)

    async def list_request_names(self) -> list[dict[str, Any]]:
        """获取按 request_name 分组的持久化统计。

        Returns:
            请求名称维度的持久化统计列表。
        """
        return await self.metrics_helper.list_request_names()

    async def get_request_name_window_summary(
        self,
        *,
        start_ts: float,
        end_ts: float,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """获取指定时间窗口内的 Top request_name 聚合统计。

        Args:
            start_ts: 起始 Unix 时间戳。
            end_ts: 结束 Unix 时间戳。
            limit: 返回数量上限。

        Returns:
            指定时间窗口内按总 Token 排序的请求名称聚合统计列表。
        """
        return await self.metrics_helper.get_request_name_window_summary(
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
        )

    async def get_recent_requests(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """获取最近的持久化 LLM 请求明细。

        Args:
            limit: 返回数量上限。
            offset: 分页偏移量。

        Returns:
            最近请求记录列表。
        """
        return await self.metrics_helper.get_recent_requests(limit=limit, offset=offset)

    def get_recent_memory_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取内存收集器中的最近 LLM 请求历史。

        Args:
            limit: 返回数量上限。

        Returns:
            内存收集器中的最近请求历史列表。
        """
        return self.metrics_helper.get_recent_memory_history(limit=limit)

    async def get_cache_hit_rate(self, stream_id: str | None = None) -> dict[str, Any]:
        """获取全局或指定聊天流的缓存命中率。

        Args:
            stream_id: 可选聊天流 ID，为空时返回全局缓存命中率。

        Returns:
            缓存命中率、命中 Token 和未命中 Token 统计。
        """
        return await self.metrics_helper.get_cache_hit_rate(stream_id=stream_id)

    async def list_streams(self) -> list[dict[str, Any]]:
        """获取按 stream_id 分组的持久化统计。

        Returns:
            聊天流维度的持久化统计列表。
        """
        return await self.metrics_helper.list_streams()

    async def get_time_range_summary(
        self,
        *,
        start_ts: float,
        end_ts: float,
    ) -> dict[str, Any]:
        """获取指定时间范围内的持久化统计摘要。

        Args:
            start_ts: 起始 Unix 时间戳。
            end_ts: 结束 Unix 时间戳。

        Returns:
            时间范围内的请求量、Token、成本和缓存命中统计。
        """
        return await self.metrics_helper.get_time_range_summary(start_ts=start_ts, end_ts=end_ts)

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
