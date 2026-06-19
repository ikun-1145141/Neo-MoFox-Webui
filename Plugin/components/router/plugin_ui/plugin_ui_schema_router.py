"""插件 UI Schema Router。

提供页面渲染 schema 查询 API（XML 内容或 HTML assets URL）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Query

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ....managers.plugin_ui_manager import get_plugin_ui_manager
from ....utils.plugin_ui.plugin_ui_types import PageSchemaResponse
from ....utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("plugin_ui_schema_router")


class PluginUISchemaRouter(BaseRouter):
    """插件 UI Schema 路由。

    提供页面渲染 schema 拉取端点。
    """

    router_name: str = "plugin-ui-schema"
    router_description: str = "插件 UI 页面 Schema 接口"
    custom_route_path: str = "/webui/api/plugin-ui"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Schema Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self._manager = get_plugin_ui_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

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
            """
            schema = self._manager.get_schema(plugin_name, page_id, variant)  # type: ignore[arg-type]

            if schema is None:
                # 区分：页面不存在 vs mobile variant 缺失
                page = self._manager.get_detail(plugin_name, page_id)
                if page is None:
                    return BaseResponse.error(
                        code=404,
                        message=f"页面不存在: {plugin_name}/{page_id}",
                    )
                # 页面存在但 mobile variant 不存在
                return BaseResponse.error(
                    code=204,
                    message="no_mobile_variant",
                )

            return BaseResponse.ok(data=schema)
