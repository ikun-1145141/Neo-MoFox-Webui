"""插件市场路由组件。

为前端提供 WebUI 插件市场 API，统一封装远端市场数据与本机安装操作。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Query

from src.app.plugin_system.api.log_api import get_logger
from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep

from ...managers.plugin_market_manager import get_plugin_market_manager
from ...utils.market_types import (
    InstalledPluginListResponse,
    MarketPlugin,
    MarketPluginListResponse,
    MarketPluginQuery,
    MarketPluginReadmeResponse,
    MarketPluginVersion,
    MarketPluginVersionListResponse,
    PluginInstallRequest,
    PluginInstallResult,
    PluginVersionSwitchRequest,
)
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("plugin_market_router")


class PluginMarketRouter(BaseRouter):
    """插件市场 Router 组件。"""

    router_name: str = "plugin-market"
    router_description: str = "WebUI 插件市场接口"
    custom_route_path: str = "/webui/api/plugin-market"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化插件市场 Router。

        Args:
            plugin: 所属插件实例。
        """

        super().__init__(plugin)
        self.market_manager = get_plugin_market_manager()

    def register_endpoints(self) -> None:
        """注册插件市场 API 端点。"""

        @self.app.get(
            "/plugins",
            response_model=BaseResponse[MarketPluginListResponse],
            summary="获取市场插件列表",
            description="从远端插件市场分页获取插件列表，支持搜索、分类、标签、信任等级和排序。",
        )
        async def list_market_plugins(
            q: str | None = Query(default=None, description="搜索关键字"),
            status: str | None = Query(default=None, description="发布状态"),
            category: str | None = Query(default=None, description="分类"),
            tag: str | None = Query(default=None, description="标签"),
            trust_level: str | None = Query(default=None, description="信任等级"),
            sort: str = Query(default="updated", description="排序方式"),
            offset: int = Query(default=0, ge=0, description="分页偏移"),
            limit: int = Query(default=50, ge=1, le=100, description="分页大小"),
        ) -> BaseResponse[MarketPluginListResponse]:
            """获取市场插件列表。"""

            try:
                query = MarketPluginQuery(
                    q=q,
                    status=status,
                    category=category,
                    tag=tag,
                    trust_level=trust_level,
                    sort=sort,
                    offset=offset,
                    limit=limit,
                )
                result = await self.market_manager.list_market_plugins(query)
                return BaseResponse.ok(data=result, message="获取市场插件列表成功")
            except Exception as exc:
                logger.error(f"获取市场插件列表失败: {exc}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"获取市场插件列表失败: {exc}") from exc

        @self.app.get(
            "/plugins/{plugin_id}",
            response_model=BaseResponse[MarketPlugin],
            summary="获取市场插件详情",
            description="从远端插件市场获取指定插件的详细数据。",
        )
        async def get_market_plugin(plugin_id: str) -> BaseResponse[MarketPlugin]:
            """获取市场插件详情。

            Args:
                plugin_id: 插件 ID。
            """

            try:
                result = await self.market_manager.get_market_plugin(plugin_id)
                return BaseResponse.ok(data=result, message="获取市场插件详情成功")
            except Exception as exc:
                logger.error(f"获取市场插件详情失败: {plugin_id}: {exc}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"获取市场插件详情失败: {exc}") from exc

        @self.app.get(
            "/plugins/{plugin_id}/readme",
            response_model=BaseResponse[MarketPluginReadmeResponse],
            summary="获取市场插件 README",
            description="获取远端市场已渲染的 README HTML。",
        )
        async def get_plugin_readme(plugin_id: str) -> BaseResponse[MarketPluginReadmeResponse]:
            """获取市场插件 README。

            Args:
                plugin_id: 插件 ID。
            """

            try:
                result = await self.market_manager.get_plugin_readme(plugin_id)
                return BaseResponse.ok(data=result, message="获取插件 README 成功")
            except Exception as exc:
                logger.error(f"获取插件 README 失败: {plugin_id}: {exc}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"获取插件 README 失败: {exc}") from exc

        @self.app.get(
            "/plugins/{plugin_id}/versions",
            response_model=BaseResponse[MarketPluginVersionListResponse],
            summary="获取市场插件版本列表",
            description="获取指定市场插件的所有版本。",
        )
        async def list_plugin_versions(plugin_id: str) -> BaseResponse[MarketPluginVersionListResponse]:
            """获取插件版本列表。

            Args:
                plugin_id: 插件 ID。
            """

            try:
                result = await self.market_manager.list_plugin_versions(plugin_id)
                return BaseResponse.ok(data=result, message="获取插件版本列表成功")
            except Exception as exc:
                logger.error(f"获取插件版本列表失败: {plugin_id}: {exc}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"获取插件版本列表失败: {exc}") from exc

        @self.app.get(
            "/plugins/{plugin_id}/versions/{version}",
            response_model=BaseResponse[MarketPluginVersion],
            summary="获取市场插件版本详情",
            description="获取指定插件的指定版本元数据。",
        )
        async def get_plugin_version(plugin_id: str, version: str) -> BaseResponse[MarketPluginVersion]:
            """获取插件版本详情。

            Args:
                plugin_id: 插件 ID。
                version: 版本号。
            """

            try:
                result = await self.market_manager.get_plugin_version(plugin_id, version)
                return BaseResponse.ok(data=result, message="获取插件版本详情成功")
            except Exception as exc:
                logger.error(f"获取插件版本详情失败: {plugin_id}@{version}: {exc}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"获取插件版本详情失败: {exc}") from exc

        @self.app.get(
            "/installed",
            response_model=BaseResponse[InstalledPluginListResponse],
            dependencies=[VerifiedDep],
            summary="获取本机已安装插件",
            description="直接从核心插件管理器获取已加载和未加载的本机插件，并尝试与市场插件逐项匹配。",
        )
        async def list_installed_plugins() -> BaseResponse[InstalledPluginListResponse]:
            """获取本机已安装插件。"""

            try:
                result = await self.market_manager.list_installed_plugins()
                return BaseResponse.ok(data=result, message="获取已安装插件成功")
            except Exception as exc:
                logger.error(f"获取已安装插件失败: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取已安装插件失败: {exc}") from exc

        @self.app.post(
            "/plugins/{plugin_id}/install",
            response_model=BaseResponse[PluginInstallResult],
            dependencies=[VerifiedDep],
            summary="安装市场插件",
            description="下载指定市场插件的压缩包文件并直接放入插件目录，不执行解压。",
        )
        async def install_plugin(plugin_id: str, request: PluginInstallRequest) -> BaseResponse[PluginInstallResult]:
            """安装市场插件。

            Args:
                plugin_id: 插件 ID。
                request: 安装请求。
            """

            try:
                result = await self.market_manager.install_plugin(plugin_id, request)
                if result.success:
                    return BaseResponse.ok(data=result, message="安装插件成功")
                return BaseResponse.error(code=500, data=result, message=result.message)
            except Exception as exc:
                logger.error(f"安装插件失败: {plugin_id}: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"安装插件失败: {exc}") from exc

        @self.app.post(
            "/plugins/{plugin_id}/update",
            response_model=BaseResponse[PluginInstallResult],
            dependencies=[VerifiedDep],
            summary="更新市场插件",
            description="更新前会备份原插件；文件夹插件压缩备份，压缩包或插件文件直接改后缀备份。",
        )
        async def update_plugin(plugin_id: str, request: PluginInstallRequest) -> BaseResponse[PluginInstallResult]:
            """更新市场插件。

            Args:
                plugin_id: 插件 ID。
                request: 更新请求。
            """

            try:
                result = await self.market_manager.update_plugin(plugin_id, request)
                if result.success:
                    return BaseResponse.ok(data=result, message="更新插件成功")
                return BaseResponse.error(code=500, data=result, message=result.message)
            except Exception as exc:
                logger.error(f"更新插件失败: {plugin_id}: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"更新插件失败: {exc}") from exc

        @self.app.post(
            "/plugins/{plugin_id}/versions/switch",
            response_model=BaseResponse[PluginInstallResult],
            dependencies=[VerifiedDep],
            summary="切换或降级市场插件版本",
            description="将已安装插件切换到指定版本，可用于降级，切换前同样执行备份。",
        )
        async def switch_plugin_version(
            plugin_id: str, request: PluginVersionSwitchRequest
        ) -> BaseResponse[PluginInstallResult]:
            """切换或降级插件版本。

            Args:
                plugin_id: 插件 ID。
                request: 版本切换请求。
            """

            try:
                result = await self.market_manager.switch_plugin_version(plugin_id, request)
                if result.success:
                    return BaseResponse.ok(data=result, message="切换插件版本成功")
                return BaseResponse.error(code=500, data=result, message=result.message)
            except Exception as exc:
                logger.error(f"切换插件版本失败: {plugin_id}: {exc}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"切换插件版本失败: {exc}") from exc


__all__ = ["PluginMarketRouter"]
