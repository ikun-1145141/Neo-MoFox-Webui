"""LLM 指标查询工具。

统一封装 LLM 运营指标的读取与归一化逻辑，避免在 Router/Manager
中重复拼装请求量、Token、花费、延迟、缓存命中率和请求明细等统计字段。
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from src.kernel.llm.stats import get_llm_stats_collector


class LLMMetricsHelper:
    """LLM 指标查询工具类。"""

    async def get_overview(self) -> dict[str, Any]:
        """获取数据库中的 LLM 统计摘要。

        Returns:
            来自数据库统计后端的窗口化摘要，包含请求数、Token、成本、
            延迟和缓存命中率等字段。
        """
        summary = await get_llm_stats_collector().get_summary()
        return {
            **summary,
            "avg_latency_ms": round(float(summary.get("avg_latency", 0.0)) * 1000, 3),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

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
            最近指定小时内按时间倒序排列的请求记录列表。
        """
        end_ts = time.time()
        start_ts = end_ts - max(hours, 0.0) * 3600
        return await get_llm_stats_collector().list_requests_by_time_range(
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
            offset=offset,
        )

    async def list_streams(self) -> list[dict[str, Any]]:
        """获取数据库中按 stream_id 分组的统计。

        Returns:
            聊天流维度的持久化统计列表。
        """
        return await get_llm_stats_collector().get_by_stream()

    async def get_last_hours_summary(self, *, hours: float = 5.0) -> dict[str, Any]:
        """获取最近若干小时的持久化统计摘要。

        Args:
            hours: 向前统计的小时数。

        Returns:
            最近指定小时内的统计摘要。
        """
        end_ts = time.time()
        start_ts = end_ts - max(hours, 0.0) * 3600
        return await get_llm_stats_collector().get_by_time_range(start_ts, end_ts)


_llm_metrics_helper: LLMMetricsHelper | None = None


def get_llm_metrics_helper() -> LLMMetricsHelper:
    """获取全局 LLM 指标工具实例。"""
    global _llm_metrics_helper
    if _llm_metrics_helper is None:
        _llm_metrics_helper = LLMMetricsHelper()
    return _llm_metrics_helper
