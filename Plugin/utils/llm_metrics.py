"""LLM 指标查询工具。

统一封装 LLM 运营指标的读取与归一化逻辑，避免在 Router/Manager
中重复拼装请求量、Token、花费和延迟等统计字段。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.kernel.llm import get_global_collector # type: ignore


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

    def list_models(self) -> list[dict[str, Any]]:
        """获取各模型维度指标列表。"""
        model_stats = self._collector.get_stats()
        if isinstance(model_stats, list):
            return model_stats
        return [model_stats]

    def get_model(self, model_name: str) -> dict[str, Any]:
        """获取单模型指标。

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


_llm_metrics_helper: LLMMetricsHelper | None = None


def get_llm_metrics_helper() -> LLMMetricsHelper:
    """获取全局 LLM 指标工具实例。"""
    global _llm_metrics_helper
    if _llm_metrics_helper is None:
        _llm_metrics_helper = LLMMetricsHelper()
    return _llm_metrics_helper
