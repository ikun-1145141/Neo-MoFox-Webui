"""插件市场 REST API 路由。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Query

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.base import BaseRouter
from src.core.utils.security import VerifiedDep

from ...managers.plugin_market_manager import (
    PluginMarketError,
    get_plugin_market_manager,
)
from ...plugin_market_config import WebUIConfig
from ...utils.plugin_market_types import (
    InstallPlan,
    InstallPlanRequest,
    MarketCapabilities,
    MarketOperation,
    MarketPluginDetail,
    MarketPluginList,
    StartInstallRequest,
)
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.app.plugin_system.base import BasePlugin

logger = get_logger("plugin_market_router")


class PluginMarketRouter(BaseRouter):
    """向新版 WebUI 暴露插件市场能力。"""

    name = "plugin-market"
    description = "插件市场查询、安装与卸载接口"
    custom_route_path = "/webui/api/plugin-market"
    cors_origins: list[str] = ["*"]
    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        if not isinstance(plugin.config, WebUIConfig):
            raise RuntimeError("WebUI 插件市场配置未加载")
        self._manager = get_plugin_market_manager(plugin.config)
        super().__init__(plugin)

    def register_endpoints(self) -> None:
        """注册认证后的市场端点。"""

        @self.app.get(
            "/capabilities",
            response_model=BaseResponse[MarketCapabilities],
            dependencies=[VerifiedDep],
        )
        async def get_capabilities() -> BaseResponse[MarketCapabilities]:
            return BaseResponse.ok(self._manager.capabilities())

        @self.app.get(
            "/plugins",
            response_model=BaseResponse[MarketPluginList],
            dependencies=[VerifiedDep],
        )
        async def list_plugins(
            refresh: bool = Query(default=False),
        ) -> BaseResponse[MarketPluginList]:
            try:
                return BaseResponse.ok(await self._manager.list_plugins(refresh=refresh))
            except PluginMarketError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error
            except Exception as error:
                logger.error(f"读取插件市场失败: {error}", exc_info=True)
                raise HTTPException(status_code=500, detail="读取插件市场失败") from error

        @self.app.get(
            "/plugins/{plugin_id}",
            response_model=BaseResponse[MarketPluginDetail],
            dependencies=[VerifiedDep],
        )
        async def get_plugin(plugin_id: str) -> BaseResponse[MarketPluginDetail]:
            try:
                return BaseResponse.ok(await self._manager.get_plugin_detail(plugin_id))
            except PluginMarketError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            except Exception as error:
                logger.error(f"读取市场插件详情失败: {error}", exc_info=True)
                raise HTTPException(status_code=500, detail="读取市场插件详情失败") from error

        @self.app.post(
            "/plugins/{plugin_id}/install-plan",
            response_model=BaseResponse[InstallPlan],
            dependencies=[VerifiedDep],
        )
        async def create_install_plan(
            plugin_id: str,
            request: InstallPlanRequest,
        ) -> BaseResponse[InstallPlan]:
            try:
                return BaseResponse.ok(
                    await self._manager.create_install_plan(plugin_id, request.version)
                )
            except PluginMarketError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error

        @self.app.post(
            "/plugins/{plugin_id}/install",
            response_model=BaseResponse[MarketOperation],
            dependencies=[VerifiedDep],
            status_code=202,
        )
        async def install_plugin(
            plugin_id: str,
            request: StartInstallRequest,
        ) -> BaseResponse[MarketOperation]:
            try:
                return BaseResponse.ok(
                    await self._manager.start_install(plugin_id, request.version),
                    message="安装任务已创建",
                )
            except PluginMarketError as error:
                message = str(error)
                status_code = 429 if "频繁" in message else 409
                raise HTTPException(status_code=status_code, detail=message) from error

        @self.app.post(
            "/plugins/{plugin_id}/uninstall",
            response_model=BaseResponse[MarketOperation],
            dependencies=[VerifiedDep],
            status_code=202,
        )
        async def uninstall_plugin(plugin_id: str) -> BaseResponse[MarketOperation]:
            try:
                return BaseResponse.ok(
                    await self._manager.start_uninstall(plugin_id),
                    message="卸载任务已创建",
                )
            except PluginMarketError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error

        @self.app.get(
            "/operations/{operation_id}",
            response_model=BaseResponse[MarketOperation],
            dependencies=[VerifiedDep],
        )
        async def get_operation(operation_id: str) -> BaseResponse[MarketOperation]:
            try:
                return BaseResponse.ok(self._manager.get_operation(operation_id))
            except PluginMarketError as error:
                raise HTTPException(status_code=404, detail=str(error)) from error


__all__ = ["PluginMarketRouter"]
