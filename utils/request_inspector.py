"""LLM 请求体检视器工具。

封装 LLM 请求体捕获记录的读取、清理、摘要统计与结构化渲染逻辑，
供 Manager 层调用，避免 Router 直接依赖底层检视器内部结构。
"""

from __future__ import annotations

import time
from typing import Any

from src.kernel.llm.request_inspector import (  # type: ignore
    build_render_view,
    get_inspector,
)
from src.kernel.llm.stats import get_llm_stats_collector  # type: ignore


class RequestInspectorHelper:
    """LLM 请求体检视器工具类。"""

    def list_requests(self) -> list[dict[str, Any]]:
        """获取捕获请求摘要列表。

        Returns:
            按捕获顺序排列的请求摘要列表。
        """
        inspector = get_inspector()
        records = getattr(inspector, "_records", [])
        return [record.to_summary() for record in records]

    def get_request(self, request_id: int) -> dict[str, Any] | None:
        """获取指定请求的完整详情。

        Args:
            request_id: 捕获请求 ID。

        Returns:
            请求完整详情；不存在时返回 None。
        """
        inspector = get_inspector()
        records = getattr(inspector, "_records", [])
        for record in reversed(records):
            if record.id == request_id:
                return record.to_full()
        return None

    def clear_requests(self) -> dict[str, Any]:
        """清空内存中的捕获请求。"""
        inspector = get_inspector()
        records = getattr(inspector, "_records", None)
        if records is not None:
            records.clear()
        return {"ok": True, "cleared_at": time.time()}

    async def get_analytics(self) -> dict[str, Any]:
        """获取 LLM 请求体检视器综合统计。"""
        collector = get_llm_stats_collector()
        summary = await collector.get_summary()
        by_model = await collector.get_by_model()
        by_request = await collector.get_by_request_name()
        by_stream = await collector.get_by_stream()
        return {
            "summary": summary,
            "by_model": by_model,
            "by_request_name": by_request,
            "by_stream": by_stream,
        }

    def render_payload(
        self,
        *,
        api_name: str,
        model: str,
        params: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """将请求体转换为前端可渲染结构。

        Args:
            api_name: API 调用名称。
            model: 模型名称。
            params: 请求体参数。
            metadata: 请求元数据。

        Returns:
            包含 overview、tools 和 messages 的结构化渲染模型。
        """
        return build_render_view(api_name, model, params, metadata)


_request_inspector_helper: RequestInspectorHelper | None = None


def get_request_inspector_helper() -> RequestInspectorHelper:
    """获取请求体检视器工具单例。"""
    global _request_inspector_helper
    if _request_inspector_helper is None:
        _request_inspector_helper = RequestInspectorHelper()
    return _request_inspector_helper
