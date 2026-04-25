"""Auth Router 组件。

提供 WebUI 登录与登出接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException
from pydantic import BaseModel, Field

from src.app.plugin_system.api.log_api import get_logger
from src.core.components.base.router import BaseRouter

from ...managers.auth_manager import get_auth_manager
from ...utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("auth_router")


class LoginRequest(BaseModel):
    """登录请求。"""

    password: str = Field(min_length=1, description="登录密码")


class LoginResponse(BaseModel):
    """登录响应。"""

    token: str = Field(description="登录令牌")


class AuthRouter(BaseRouter):
    """认证 Router 组件。"""

    router_name: str = "auth"
    router_description: str = "WebUI 认证 API"
    custom_route_path: str = "/api/auth"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化认证 Router。"""
        super().__init__(plugin)
        self.auth_manager = get_auth_manager()

    def register_endpoints(self) -> None:
        """注册认证端点。"""

        @self.app.post("/login", response_model=BaseResponse[LoginResponse])
        async def login(request: LoginRequest) -> BaseResponse[LoginResponse]:
            """登录接口。"""
            try:
                token = await self.auth_manager.login(request.password)
                return BaseResponse.ok(data=LoginResponse(token=token), message="登录成功")
            except ValueError as exc:
                logger.warning(f"登录失败: {exc}")
                raise HTTPException(status_code=401, detail=str(exc))
            except RuntimeError as exc:
                logger.error(f"登录失败: {exc}")
                raise HTTPException(status_code=500, detail=str(exc))
            except Exception as exc:
                logger.error(f"登录异常: {exc}")
                raise HTTPException(status_code=500, detail="登录服务异常")

        @self.app.post("/logout", response_model=BaseResponse[None])
        async def logout() -> BaseResponse[None]:
            """登出接口。

            当前版本不维护服务端会话，前端删除令牌即完成登出。
            """
            return BaseResponse.ok(data=None, message="登出成功")

    async def startup(self) -> None:
        """Router 启动钩子。"""
        logger.info("Auth Router 已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("Auth Router 已关闭")
