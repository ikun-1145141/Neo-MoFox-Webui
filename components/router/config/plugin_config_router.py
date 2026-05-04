"""插件配置路由。

提供插件配置专属 API。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from src.app.plugin_system.api.log_api import get_logger

from ....managers.config import get_plugin_config_manager
from ....utils.response import BaseResponse
from ....utils.config_types import PluginConfigEntry, SectionSchema

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("plugin_config_router")


class PluginConfigRouter(BaseRouter):
    """插件配置路由。

    提供插件配置专属操作：
    - GET /api/config-plugin/list - 获取可配置插件列表
    - GET /api/config-plugin/{plugin_name}/schema - 获取插件配置 Schema
    """

    router_name: str = "config-plugin"
    router_description: str = "插件配置 API"
    custom_route_path: str = "/webui/api/config-plugin"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.manager = get_plugin_config_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get(
            "/list",
            response_model=BaseResponse[list[PluginConfigEntry]],
            dependencies=[VerifiedDep],
        )
        async def list_plugin_configs() -> BaseResponse[list[PluginConfigEntry]]:
            """获取可配置插件列表。

            Returns:
                插件配置摘要列表
            """
            try:
                entries = await self.manager.list_plugin_configs()
                return BaseResponse.ok(data=entries, message="获取插件配置列表成功")
            except Exception as e:
                logger.error(f"获取插件配置列表失败: {e}")
                raise HTTPException(
                    status_code=500, detail=f"获取插件配置列表失败: {str(e)}"
                )

        @self.app.get(
            "/{plugin_name}/schema",
            response_model=BaseResponse[list[SectionSchema]],
            dependencies=[VerifiedDep],
        )
        async def get_plugin_schema(plugin_name: str) -> BaseResponse[list[SectionSchema]]:
            """获取插件配置 Schema。

            Args:
                plugin_name: 插件名

            Returns:
                配置节 Schema 列表
            """
            try:
                schema = await self.manager.get_plugin_config_schema(plugin_name)
                return BaseResponse.ok(data=schema, message="获取插件配置 Schema 成功")
            except ValueError as e:
                logger.error(f"参数错误: {e}")
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"获取插件配置 Schema 失败: {e}")
                raise HTTPException(
                    status_code=500, detail=f"获取插件配置 Schema 失败: {str(e)}"
                )

    async def startup(self) -> None:
        """Router 启动钩子。"""
        logger.info("插件配置路由已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("插件配置路由已关闭")
