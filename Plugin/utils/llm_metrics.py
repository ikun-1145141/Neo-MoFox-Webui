"""LLM 指标查询工具。

统一封装 LLM 运营指标的读取与归一化逻辑，避免在 Router/Manager
中重复拼装请求量、Token、花费、延迟、缓存命中率和请求明细等统计字段。
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from src.kernel.llm import get_global_collector  # type: ignore
from src.kernel.llm.stats import get_llm_stats_collector  # type: ignore


class LLMMetricsHelper:
    """LLM 指标查询工具类。"""

    def __init__(self) -> None:
        """初始化工具类。"""
        self._collector = get_global_collector()

    def get_overview(self) -> dict[str, Any]:
        """获取跨模型汇总指标。

        Returns:
            统一口径的 LLM 运营指标。
        """
        model_stats = self._collector.get_stats()

        if not isinstance(model_stats, list):
            model_stats = [model_stats]

        total_requests = int(sum(int(item.get("total_requests", 0)) for item in model_stats))
        success_count = int(sum(int(item.get("success_count", 0)) for item in model_stats))
        error_count = int(sum(int(item.get("error_count", 0)) for item in model_stats))

        total_latency = float(sum(float(item.get("total_latency", 0.0)) for item in model_stats))
        total_tokens_in = int(sum(int(item.get("total_tokens_in", 0)) for item in model_stats))
        total_tokens_out = int(sum(int(item.get("total_tokens_out", 0)) for item in model_stats))
        total_cost = float(sum(float(item.get("total_cost", 0.0)) for item in model_stats))

        success_rate = (success_count / total_requests) if total_requests > 0 else 0.0
        avg_latency_sec = (total_latency / total_requests) if total_requests > 0 else 0.0

        return {
            "model_count": len(model_stats),
            "total_requests": total_requests,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": round(success_rate, 6),
            "avg_latency_seconds": round(avg_latency_sec, 6),
            "avg_latency_ms": round(avg_latency_sec * 1000, 3),
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_cost": round(total_cost, 8),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    async def get_persistent_overview(self) -> dict[str, Any]:
        """获取持久化 LLM 统计摘要。

        Returns:
            来自独立 LLM 统计后端的窗口化摘要，包含请求数、Token、成本、
            延迟和缓存命中率等字段。
        """
        summary = await get_llm_stats_collector().get_summary()
        return {
            **summary,
            "avg_latency_ms": round(float(summary.get("avg_latency", 0.0)) * 1000, 3),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    async def get_combined_overview(self) -> dict[str, Any]:
        """获取内存指标和持久化统计的组合视图。

        Returns:
            同时包含 legacy 内存指标与 persistent 持久化指标的字典。
        """
        return {
            "legacy": self.get_overview(),
            "persistent": await self.get_persistent_overview(),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def list_models(self) -> list[dict[str, Any]]:
        """获取内存收集器中的各模型维度指标列表。"""
        model_stats = self._collector.get_stats()
        if isinstance(model_stats, list):
            return model_stats
        return [model_stats]

    async def list_persistent_models(self) -> list[dict[str, Any]]:
        """获取持久化统计后端中的按模型分组统计。"""
        return await get_llm_stats_collector().get_by_model()

    def get_model(self, model_name: str) -> dict[str, Any]:
        """获取内存收集器中的单模型指标。

        Args:
            model_name: 模型名称。

        Returns:
            单模型统计字典。
        """
        result = self._collector.get_stats(model_name=model_name)
        if isinstance(result, dict):
            return result
        return {
            "model_name": model_name,
            "total_requests": 0,
            "success_count": 0,
            "error_count": 0,
            "success_rate": 0.0,
            "total_latency": 0.0,
            "avg_latency": 0.0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_cost": 0.0,
            "avg_cost": 0.0,
            "error_types": {},
        }

    async def list_request_names(self) -> list[dict[str, Any]]:
        """获取按 request_name 分组的持久化统计。"""
        return await get_llm_stats_collector().get_by_request_name()

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
            按总 Token 倒序排列的请求名称聚合统计列表。
        """
        return await get_llm_stats_collector().get_request_name_window_summary(
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
        return await get_llm_stats_collector().get_recent(limit=limit, offset=offset)

    def get_recent_memory_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取内存收集器中的最近请求历史。

        Args:
            limit: 返回数量上限。

        Returns:
            已转换为字典的请求指标列表。
        """
        return [vars(item) for item in self._collector.get_recent_history(limit=limit)]

    async def get_cache_hit_rate(self, stream_id: str | None = None) -> dict[str, Any]:
        """获取持久化统计后端中的缓存命中率。

        Args:
            stream_id: 可选聊天流 ID，为空时返回全局缓存命中率。

        Returns:
            缓存命中率、命中 Token 和未命中 Token 统计。
        """
        return await get_llm_stats_collector().get_cache_hit_rate(stream_id=stream_id)

    async def list_streams(self) -> list[dict[str, Any]]:
        """获取按 stream_id 分组的持久化统计。"""
        return await get_llm_stats_collector().get_by_stream()

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
        return await get_llm_stats_collector().get_by_time_range(start_ts, end_ts)

    async def get_last_hours_summary(self, *, hours: float = 5.0) -> dict[str, Any]:
        """获取最近若干小时的持久化统计摘要。

        Args:
            hours: 向前统计的小时数。

        Returns:
            最近指定小时内的统计摘要。
        """
        end_ts = time.time()
        start_ts = end_ts - max(hours, 0.0) * 3600
        return await self.get_time_range_summary(start_ts=start_ts, end_ts=end_ts)

_llm_metrics_helper: LLMMetricsHelper | None = None


def get_llm_metrics_helper() -> LLMMetricsHelper:
    """获取全局 LLM 指标工具实例。"""
    global _llm_metrics_helper
    if _llm_metrics_helper is None:
        _llm_metrics_helper = LLMMetricsHelper()
    return _llm_metrics_helper
