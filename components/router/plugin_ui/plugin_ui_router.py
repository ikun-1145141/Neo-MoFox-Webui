"""插件 UI Router（合并 Discovery + Schema）。

提供页面列表、详情查询和页面渲染 schema 查询 API。
由于 BaseRouter 按 custom_route_path 注册 FastAPI sub-app，
相同路径前缀的端点必须归属同一个 Router，否则后注册者覆盖前者。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Query

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ....managers.plugin_ui_manager import get_plugin_ui_manager
from ....utils.plugin_ui.plugin_ui_types import PageDetail, PageSchemaResponse, PageSummary
from ....utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("plugin_ui_router")


class PluginUIRouter(BaseRouter):
    """插件 UI 页面发现与 Schema 路由。

    合并原 PluginUIDiscoveryRouter 和 PluginUISchemaRouter，
    统一挂载在 /webui/api/plugin-ui 路径下。
    """

    router_name: str = "plugin-ui"
    router_description: str = "插件 UI 页面发现与 Schema 接口"
    custom_route_path: str = "/webui/api/plugin-ui"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Plugin UI Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self._manager = get_plugin_ui_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""
        self._register_discovery_endpoints()
        self._register_schema_endpoints()

    # === Discovery 端点 ===

    def _register_discovery_endpoints(self) -> None:
        """注册页面发现相关端点。"""

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

    # === Schema 端点 ===

    def _register_schema_endpoints(self) -> None:
        """注册页面 Schema 相关端点。"""

        @self.app.get(
            "/schema/{plugin_name}/{page_id}",
            response_model=BaseResponse[PageSchemaResponse],
            dependencies=[VerifiedDep],
            summary="获取页面渲染 Schema",
            description=(
                "返回指定页面的渲染数据：XML 模式返回 XML 原文，"
                "HTML 模式返回 assets URL bundle"
            ),
        )
        async def get_page_schema(
            plugin_name: str,
            page_id: str,
            variant: str = Query(
                default="desktop",
                description="变体类型：desktop 或 mobile",
                pattern="^(desktop|mobile)$",
            ),
        ) -> BaseResponse[PageSchemaResponse]:
            """获取页面渲染 schema。

            Args:
                plugin_name: 插件名称
                page_id: 页面标识
                variant: 变体类型

            Returns:
                成功时返回 schema 内容；当页面存在但请求的 variant 缺失
                （例如请求 mobile 但插件未提供 mobile variant）时，
                返回 code=200, data=None, message="no_variant"，
                由前端决定是否回退到 desktop variant。
                仅当页面本身不存在时才返回 code=404 错误。
            """
            schema = self._manager.get_schema(plugin_name, page_id, variant)  # type: ignore[arg-type]

            if schema is None:
                # 页面本身不存在 → 真错误
                page = self._manager.get_detail(plugin_name, page_id)
                if page is None:
                    return BaseResponse.error(
                        code=404,
                        message=f"页面不存在: {plugin_name}/{page_id}",
                    )
                # 页面存在但请求的 variant 不存在 → 视为正常响应，data=None
                # 让前端通过 detail.has_mobile 与该响应共同决定 fallback
                return BaseResponse.ok(data=None, message="no_variant")

            return BaseResponse.ok(data=schema)
