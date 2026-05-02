"""Dashboard Router 组件。

提供 WebUI 首页仪表盘数据接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Query

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ...managers.dashboard_manager import get_dashboard_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("dashboard_router")


class DashboardRouter(BaseRouter):
    """Dashboard Router 组件。"""

    router_name: str = "dashboard"
    router_description: str = "WebUI 仪表盘接口"
    custom_route_path: str = "/api/dashboard"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.dashboard_manager = get_dashboard_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get("/overview", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_dashboard_overview() -> BaseResponse[dict[str, Any]]:
            """获取仪表盘总览数据。"""
            try:
                data = await self.dashboard_manager.get_overview()
                return BaseResponse.ok(data=data, message="获取仪表盘数据成功")
            except Exception as e:
                logger.error(f"获取仪表盘数据失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取仪表盘数据失败: {str(e)}")

        @self.app.get("/message-trend", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_message_trend(
            days: int = Query(default=7, ge=1, le=365, description="统计天数")
        ) -> BaseResponse[dict[str, Any]]:
            """获取消息趋势数据。

            Args:
                days: 统计天数（1-365天）
            """
            try:
                data = await self.dashboard_manager.get_message_trend(days=days)
                return BaseResponse.ok(data=data, message="获取消息趋势数据成功")
            except Exception as e:
                logger.error(f"获取消息趋势数据失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取消息趋势数据失败: {str(e)}")

        @self.app.get("/platform-statistics", response_model=BaseResponse[dict[str, Any]], dependencies=[VerifiedDep])
        async def get_platform_statistics() -> BaseResponse[dict[str, Any]]:
            """获取平台消息统计。"""
            try:
                data = await self.dashboard_manager.get_platform_statistics()
                return BaseResponse.ok(data=data, message="获取平台统计数据成功")
            except Exception as e:
                logger.error(f"获取平台统计数据失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取平台统计数据失败: {str(e)}")
