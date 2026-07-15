"""LLM 请求体检视器管理器。

承接 WebUI 请求体检视器路由的业务逻辑，统一调用工具层并返回可供前端
展示的归一化数据。
"""

from __future__ import annotations

from typing import Any

from ..utils.request_inspector import RequestInspectorHelper, get_request_inspector_helper


class RequestInspectorManager:
    """LLM 请求体检视器管理器。"""

    def __init__(self) -> None:
        """初始化请求体检视器管理器。"""
        self.inspector_helper: RequestInspectorHelper = get_request_inspector_helper()

    def list_requests(self) -> list[dict[str, Any]]:
        """获取捕获请求摘要列表。"""
        return self.inspector_helper.list_requests()

    def get_request(self, request_id: int) -> dict[str, Any] | None:
        """获取指定捕获请求详情。

        Args:
            request_id: 捕获请求 ID。

        Returns:
            请求详情；不存在时返回 None。
        """
        return self.inspector_helper.get_request(request_id)

    def clear_requests(self) -> dict[str, Any]:
        """清空捕获请求列表。"""
        return self.inspector_helper.clear_requests()

    async def get_analytics(self) -> dict[str, Any]:
        """获取综合统计指标。"""
        return await self.inspector_helper.get_analytics()


_request_inspector_manager: RequestInspectorManager | None = None


def get_request_inspector_manager() -> RequestInspectorManager:
    """获取请求体检视器管理器单例。"""
    global _request_inspector_manager
    if _request_inspector_manager is None:
        _request_inspector_manager = RequestInspectorManager()
    return _request_inspector_manager
