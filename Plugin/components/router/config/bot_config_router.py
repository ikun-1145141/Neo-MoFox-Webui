"""机器人配置路由。

提供机器人配置专属 API。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from src.app.plugin_system.api.log_api import get_logger

from ....managers.config import get_bot_config_manager
from ....utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("bot_config_router")


class BotConfigRouter(BaseRouter):
    """机器人配置路由。

    提供机器人配置专属操作：
    - POST /api/config-bot/reload - 热重载机器人配置
    """

    router_name: str = "config-bot"
    router_description: str = "机器人配置 API"
    custom_route_path: str = "/api/config-bot"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.manager = get_bot_config_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.post(
            "/reload",
            response_model=BaseResponse[None],
            dependencies=[VerifiedDep],
        )
        async def reload_config() -> BaseResponse[None]:
            """热重载机器人配置。

            触发 CoreConfig 重新从文件加载，无需重启进程。

            Returns:
                成功响应
            """
            try:
                await self.manager.reload_config()
                return BaseResponse.ok(message="配置已热重载")
            except Exception as e:
                logger.error(f"热重载配置失败: {e}")
                raise HTTPException(status_code=500, detail=f"热重载配置失败: {str(e)}")

    async def startup(self) -> None:
        """Router 启动钩子。"""
        logger.info("机器人配置路由已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("机器人配置路由已关闭")
