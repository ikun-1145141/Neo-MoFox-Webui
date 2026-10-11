"""LLM 请求体检视器 Router 组件。

提供 WebUI 请求体检视器后端接口，用于展示、清理和统计 LLM 请求体。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ...managers.request_inspector_manager import get_request_inspector_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("request_inspector_router")


class RequestInspectorRouter(BaseRouter):
    """WebUI LLM 请求体检视器 Router 组件。"""

    name: str = "request-inspector"
    description: str = "WebUI LLM 请求体检视器接口"
    custom_route_path: str = "/webui/api/request-inspector"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例。
        """
        super().__init__(plugin)
        self.inspector_manager = get_request_inspector_manager()

    def register_endpoints(self) -> None:
        """注册请求体检视器 API 端点。"""

        @self.app.get("/requests", response_model=BaseResponse[list[dict[str, Any]]], dependencies=[VerifiedDep])
        async def list_requests() -> BaseResponse[list[dict[str, Any]]]:
            """获取捕获请求摘要列表。"""
            try:
                data = self.inspector_manager.list_requests()
                return BaseResponse.ok(data=data, message="获取请求体列表成功")
            except Exception as exc:
                logger.error(f"获取请求体列表失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取请求体列表失败: {exc}")

        @self.app.get("/requests/{request_id}", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_request(request_id: int) -> BaseResponse[dict[str, Any]]:
            """获取指定捕获请求详情。"""
            try:
                data = self.inspector_manager.get_request(request_id)
                if data is None:
                    raise HTTPException(status_code=404, detail="请求体记录不存在")
                return BaseResponse.ok(data=data, message="获取请求体详情成功")
            except HTTPException:
                raise
            except Exception as exc:
                logger.error(f"获取请求体详情失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取请求体详情失败: {exc}")

        @self.app.delete("/requests", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def clear_requests() -> BaseResponse[dict[str, Any]]:
            """清空捕获请求列表。"""
            try:
                data = self.inspector_manager.clear_requests()
                return BaseResponse.ok(data=data, message="清空请求体列表成功")
            except Exception as exc:
                logger.error(f"清空请求体列表失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"清空请求体列表失败: {exc}")

        @self.app.get("/analytics", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_analytics() -> BaseResponse[dict[str, Any]]:
            """获取请求体检视器综合统计。"""
            try:
                data = await self.inspector_manager.get_analytics()
                return BaseResponse.ok(data=data, message="获取请求体统计成功")
            except Exception as exc:
                logger.error(f"获取请求体统计失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取请求体统计失败: {exc}")
