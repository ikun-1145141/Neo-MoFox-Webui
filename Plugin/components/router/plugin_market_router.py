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
    MarketPluginReadme,
    StartInstallRequest,
)
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.app.plugin_system.base import BasePlugin

logger = get_logger("plugin_market_router")


class PluginMarketRouter(BaseRouter):
    """向 WebUI 暴露经过认证的插件市场 REST API。

    Router 仅负责请求校验、响应模型和 HTTP 错误映射；市场查询、本地状态
    合并以及安装任务等业务逻辑由 :class:`PluginMarketManager` 处理。
    """

    name = "plugin-market"
    description = "插件市场查询与安装接口"
    custom_route_path = "/webui/api/plugin-market"
    cors_origins: list[str] = ["*"]
    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """使用 WebUI 插件配置初始化市场 Manager。

        Args:
            plugin: 已由 Neo-MoFox 插件系统实例化的 WebUI 插件。

        Raises:
            RuntimeError: WebUI 配置未加载或配置类型不正确。
        """
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
            summary="读取插件市场能力",
            description="返回市场浏览和安装功能的当前配置开关。",
        )
        async def get_capabilities() -> BaseResponse[MarketCapabilities]:
            """返回当前配置允许前端使用的插件市场能力。"""
            return BaseResponse.ok(self._manager.capabilities())

        @self.app.get(
            "/plugins",
            response_model=BaseResponse[MarketPluginList],
            dependencies=[VerifiedDep],
            summary="读取插件市场列表",
            description="读取完整市场列表，并合并本地安装、加载和更新状态。",
        )
        async def list_plugins(
            refresh: bool = Query(
                default=False,
                description="是否跳过 WebUI 后端的短期市场列表缓存。",
            ),
        ) -> BaseResponse[MarketPluginList]:
            """读取市场插件列表。

            Args:
                refresh: 是否强制重新读取上游市场分页数据。

            Returns:
                包含市场插件和本地状态的统一响应。

            Raises:
                HTTPException: 上游市场不可用或列表处理失败。
            """
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
            summary="读取市场插件详情",
            description="读取指定插件的元数据、版本、依赖、兼容性和本地状态。",
        )
        async def get_plugin(plugin_id: str) -> BaseResponse[MarketPluginDetail]:
            """读取指定市场插件的完整详情。

            Args:
                plugin_id: 市场中的插件唯一标识。

            Returns:
                包含版本、依赖和本地状态的详情响应。

            Raises:
                HTTPException: 插件标识无效、插件不存在或详情处理失败。
            """
            try:
                return BaseResponse.ok(await self._manager.get_plugin_detail(plugin_id))
            except PluginMarketError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            except Exception as error:
                logger.error(f"读取市场插件详情失败: {error}", exc_info=True)
                raise HTTPException(status_code=500, detail="读取市场插件详情失败") from error

        @self.app.get(
            "/plugins/{plugin_id}/readme",
            response_model=BaseResponse[MarketPluginReadme],
            dependencies=[VerifiedDep],
            summary="读取市场插件文档",
            description="读取市场服务为指定插件渲染的 README 文档。",
        )
        async def get_plugin_readme(plugin_id: str) -> BaseResponse[MarketPluginReadme]:
            """读取指定市场插件的渲染后 README。

            Args:
                plugin_id: 市场中的插件唯一标识。

            Returns:
                README 是否存在及其渲染后 HTML。

            Raises:
                HTTPException: 插件标识无效、市场不可用或文档响应无效。
            """
            try:
                return BaseResponse.ok(await self._manager.get_plugin_readme(plugin_id))
            except PluginMarketError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            except Exception as error:
                logger.error(f"读取市场插件文档失败: {error}", exc_info=True)
                raise HTTPException(status_code=500, detail="读取市场插件文档失败") from error

        @self.app.post(
            "/plugins/{plugin_id}/install-plan",
            response_model=BaseResponse[InstallPlan],
            dependencies=[VerifiedDep],
            summary="生成插件安装计划",
            description="校验所选版本、兼容性、依赖和本地覆盖条件，不执行写入。",
        )
        async def create_install_plan(
            plugin_id: str,
            request: InstallPlanRequest,
        ) -> BaseResponse[InstallPlan]:
            """生成安装或更新前由用户确认的计划。

            Args:
                plugin_id: 待安装或更新的插件唯一标识。
                request: 可选目标版本。

            Returns:
                安装动作、阻塞原因和风险提示。

            Raises:
                HTTPException: 插件、版本或安装条件无效。
            """
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
            summary="创建插件安装任务",
            description="根据真实安装计划创建异步安装或更新任务，并返回可轮询状态。",
        )
        async def install_plugin(
            plugin_id: str,
            request: StartInstallRequest,
        ) -> BaseResponse[MarketOperation]:
            """创建插件安装或更新任务。

            Args:
                plugin_id: 待安装或更新的插件唯一标识。
                request: 可选目标版本。

            Returns:
                已进入队列的异步操作状态。

            Raises:
                HTTPException: 安装被阻止、存在冲突或触发频率限制。
            """
            try:
                return BaseResponse.ok(
                    await self._manager.start_install(plugin_id, request.version),
                    message="安装任务已创建",
                )
            except PluginMarketError as error:
                message = str(error)
                status_code = 429 if "频繁" in message else 409
                raise HTTPException(status_code=status_code, detail=message) from error

        @self.app.get(
            "/operations/{operation_id}",
            response_model=BaseResponse[MarketOperation],
            dependencies=[VerifiedDep],
            summary="读取插件市场操作状态",
            description="返回安装任务的当前阶段、进度和结果。",
        )
        async def get_operation(operation_id: str) -> BaseResponse[MarketOperation]:
            """读取可轮询的市场写操作状态。

            Args:
                operation_id: 创建安装任务时返回的操作标识。

            Returns:
                操作阶段、进度、结果或错误信息。

            Raises:
                HTTPException: 操作记录不存在或已过期。
            """
            try:
                return BaseResponse.ok(self._manager.get_operation(operation_id))
            except PluginMarketError as error:
                raise HTTPException(status_code=404, detail=str(error)) from error


__all__ = ["PluginMarketRouter"]
