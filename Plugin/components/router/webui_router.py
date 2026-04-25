"""WebUI Router 组件。

提供 WebUI 的 HTTP API 接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from pydantic import BaseModel

from src.core.components.base.router import BaseRouter
from src.app.plugin_system.api.log_api import get_logger
from src.core.utils.security import VerifiedDep

from ...managers.config_manager import get_config_manager
from ...storage.settings import WebuiSettings
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("webui_router")


class UpdateSettingsRequest(BaseModel):
    """更新设置请求模型。

    Attributes:
        updates: 要更新的字段字典
    """

    updates: dict[str, Any]


class ReplaceSettingsRequest(BaseModel):
    """替换设置请求模型。

    Attributes:
        settings: 新的设置对象
    """

    settings: WebuiSettings


class WebuiSettingsRouter(BaseRouter):
    """WebuiSettings Router 组件。

    提供以下接口：
    - GET /settings - 获取当前设置
    - POST /settings - 更新设置（部分更新）
    - PUT /settings - 替换设置（完全替换）
    - POST /settings/reset - 重置设置为默认值
    """

    router_name: str = "webui"
    router_description: str = "WebUI API 接口"
    custom_route_path: str = "/api/webui"
    cors_origins: list[str] = ["*"]  # 开发环境允许所有来源，生产环境应该限制

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.config_manager = get_config_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get("/settings", response_model=BaseResponse[WebuiSettings], dependencies=[VerifiedDep])
        async def get_settings() -> BaseResponse[WebuiSettings]:
            """获取当前设置。

            Returns:
                包含设置对象的响应
            """
            try:
                settings = await self.config_manager.get_settings()
                return BaseResponse.ok(data=settings, message="获取设置成功")
            except Exception as e:
                logger.error(f"获取设置失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取设置失败: {str(e)}")

        @self.app.post("/settings", response_model=BaseResponse[WebuiSettings], dependencies=[VerifiedDep])
        async def update_settings(request: UpdateSettingsRequest) -> BaseResponse[WebuiSettings]:
            """更新设置（部分更新）。

            Args:
                request: 更新请求，包含要更新的字段

            Returns:
                包含更新后设置对象的响应
            """
            try:
                settings = await self.config_manager.update_settings(request.updates)
                return BaseResponse.ok(data=settings, message="更新设置成功")
            except Exception as e:
                logger.error(f"更新设置失败: {e}")
                raise HTTPException(status_code=400, detail=f"更新设置失败: {str(e)}")

        @self.app.put("/settings", response_model=BaseResponse[WebuiSettings], dependencies=[VerifiedDep])
        async def replace_settings(request: ReplaceSettingsRequest) -> BaseResponse[WebuiSettings]:
            """替换设置（完全替换）。

            Args:
                request: 替换请求，包含新的设置对象

            Returns:
                包含保存后设置对象的响应
            """
            try:
                settings = await self.config_manager.replace_settings(request.settings)
                return BaseResponse.ok(data=settings, message="替换设置成功")
            except Exception as e:
                logger.error(f"替换设置失败: {e}")
                raise HTTPException(status_code=400, detail=f"替换设置失败: {str(e)}")

        @self.app.post("/settings/reset", response_model=BaseResponse[WebuiSettings], dependencies=[VerifiedDep])
        async def reset_settings() -> BaseResponse[WebuiSettings]:
            """重置设置为默认值。

            Returns:
                包含重置后设置对象的响应
            """
            try:
                settings = await self.config_manager.reset_settings()
                return BaseResponse.ok(data=settings, message="重置设置成功")
            except Exception as e:
                logger.error(f"重置设置失败: {e}")
                raise HTTPException(status_code=500, detail=f"重置设置失败: {str(e)}")

        @self.app.get("/health")
        async def health_check() -> BaseResponse[dict[str, str]]:
            """健康检查接口。

            Returns:
                健康状态响应
            """
            return BaseResponse.ok(data={"status": "healthy"}, message="WebUI 后端运行正常")

    async def startup(self) -> None:
        """Router 启动钩子。

        初始化配置管理器。
        """
        await self.config_manager.initialize()
        logger.info("WebUI Router 已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("WebUI Router 已关闭")
