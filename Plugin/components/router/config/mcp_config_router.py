"""MCP 配置路由。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from src.app.plugin_system.api.log_api import get_logger
from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep

from ....managers.config import get_mcp_config_manager
from ....utils.config_types import McpTestRequest, McpTestResult
from ....utils.response import BaseResponse

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("mcp_config_router")


class McpConfigRouter(BaseRouter):
    """MCP 配置路由。"""

    router_name: str = "config-mcp"
    router_description: str = "MCP 配置 API"
    custom_route_path: str = "/webui/api/config-mcp"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        super().__init__(plugin)
        self.manager = get_mcp_config_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.post(
            "/test",
            response_model=BaseResponse[McpTestResult],
            dependencies=[VerifiedDep],
        )
        async def test_mcp_server(request: McpTestRequest) -> BaseResponse[McpTestResult]:
            """测试 MCP 服务连通性。"""
            try:
                result = await self.manager.test_server(request)
                return BaseResponse.ok(data=result, message="MCP 服务测试完成")
            except ValueError as e:
                logger.error(f"参数错误: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"MCP 服务测试失败: {e}")
                raise HTTPException(status_code=500, detail=f"MCP 服务测试失败: {str(e)}")

    async def startup(self) -> None:
        """Router 启动钩子。"""
        logger.info("MCP 配置路由已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("MCP 配置路由已关闭")
