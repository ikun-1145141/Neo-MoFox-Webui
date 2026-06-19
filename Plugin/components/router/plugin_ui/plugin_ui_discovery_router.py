"""插件 UI Discovery Router。

提供页面列表和详情查询 API。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ....managers.plugin_ui_manager import get_plugin_ui_manager
from ....utils.plugin_ui.plugin_ui_types import PageDetail, PageSummary
from ....utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("plugin_ui_discovery_router")


class PluginUIDiscoveryRouter(BaseRouter):
    """插件 UI 页面发现路由。

    提供页面列表和详情查询端点。
    """

    router_name: str = "plugin-ui-discovery"
    router_description: str = "插件 UI 页面发现接口"
    custom_route_path: str = "/webui/api/plugin-ui"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Discovery Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self._manager = get_plugin_ui_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get(
            "/list",
            response_model=BaseResponse[list[PageSummary]],
            dependencies=[VerifiedDep],
            summary="获取所有插件 UI 页面列表",
            description="返回所有已注册的插件 UI 页面摘要，按 order 升序排序",
        )
        async def list_all_pages() -> BaseResponse[list[PageSummary]]:
            """获取所有已注册的插件 UI 页面。"""
            pages = self._manager.list_pages()
            return BaseResponse.ok(data=pages)

        @self.app.get(
            "/list/{plugin_name}",
            response_model=BaseResponse[list[PageSummary]],
            dependencies=[VerifiedDep],
            summary="获取指定插件的 UI 页面列表",
            description="按插件名过滤，返回该插件所有已注册页面",
        )
        async def list_plugin_pages(
            plugin_name: str,
        ) -> BaseResponse[list[PageSummary]]:
            """获取指定插件的 UI 页面列表。

            Args:
                plugin_name: 插件名称
            """
            pages = self._manager.list_pages(filter_plugin=plugin_name)
            return BaseResponse.ok(data=pages)

        @self.app.get(
            "/detail/{plugin_name}/{page_id}",
            response_model=BaseResponse[PageDetail],
            dependencies=[VerifiedDep],
            summary="获取页面详情",
            description="获取指定页面的详细信息，包含 assets URL（不含 XML 原文）",
        )
        async def get_page_detail(
            plugin_name: str, page_id: str
        ) -> BaseResponse[PageDetail]:
            """获取页面详情。

            Args:
                plugin_name: 插件名称
                page_id: 页面标识
            """
            detail = self._manager.get_detail(plugin_name, page_id)
            if detail is None:
                return BaseResponse.error(
                    code=404,
                    message=f"页面不存在: {plugin_name}/{page_id}",
                )
            return BaseResponse.ok(data=detail)
