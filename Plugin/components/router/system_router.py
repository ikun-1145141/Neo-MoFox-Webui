"""系统控制 Router 组件。

提供 Bot 系统重启和关闭接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ...managers.system_manager import get_system_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("system_router")


class SystemRouter(BaseRouter):
    """系统控制 Router 组件。"""

    router_name: str = "system"
    router_description: str = "Bot 系统控制接口"
    custom_route_path: str = "/api/system"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.system_manager = get_system_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.post("/restart", response_model=BaseResponse[dict[str, str]], dependencies=[VerifiedDep])
        async def restart_bot() -> BaseResponse[dict[str, str]]:
            """重启 Bot 系统。"""
            try:
                await self.system_manager.restart_bot()
                return BaseResponse.ok(
                    data={"status": "restarting"}, message="Bot 正在重启，请稍候..."
                )
            except Exception as e:
                logger.error(f"重启 Bot 失败: {e}")
                raise HTTPException(status_code=500, detail=f"重启失败: {str(e)}")

        @self.app.post("/shutdown", response_model=BaseResponse[dict[str, str]], dependencies=[VerifiedDep])
        async def shutdown_bot() -> BaseResponse[dict[str, str]]:
            """关闭 Bot 系统。"""
            try:
                await self.system_manager.shutdown_bot()
                return BaseResponse.ok(
                    data={"status": "shutting_down"}, message="Bot 正在关闭..."
                )
            except Exception as e:
                logger.error(f"关闭 Bot 失败: {e}")
                raise HTTPException(status_code=500, detail=f"关闭失败: {str(e)}")
