"""模型配置路由。

提供模型配置专属 API。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Query

from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from src.app.plugin_system.api.log_api import get_logger

from ....managers.config import get_model_config_manager
from ....utils.response import BaseResponse
from ....utils.config_types import ModelTestRequest, ModelTestResult

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("model_config_router")


class ModelConfigRouter(BaseRouter):
    """模型配置路由。

    提供模型配置专属操作：
    - POST /api/config-model/reload - 热重载模型配置
    - POST /api/config-model/test - 测试模型连通性
    - GET /api/config-model/providers - 获取提供商列表
    - GET /api/config-model/models - 获取模型列表
    """

    name: str = "config-model"
    description: str = "模型配置 API"
    custom_route_path: str = "/webui/api/config-model"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.manager = get_model_config_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.post(
            "/reload",
            response_model=BaseResponse[None],
            dependencies=[VerifiedDep],
        )
        async def reload_config() -> BaseResponse[None]:
            """热重载模型配置。

            触发 ModelConfig 重新从文件加载，无需重启进程。

            Returns:
                成功响应
            """
            try:
                await self.manager.reload_config()
                return BaseResponse.ok(message="模型配置已热重载")
            except Exception as e:
                logger.error(f"热重载模型配置失败: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"热重载模型配置失败: {str(e)}",
                )

        @self.app.post(
            "/test",
            response_model=BaseResponse[ModelTestResult],
            dependencies=[VerifiedDep],
        )
        async def test_model(request: ModelTestRequest) -> BaseResponse[ModelTestResult]:
            """测试模型连通性。

            Args:
                request: 测试请求

            Returns:
                测试结果
            """
            try:
                result = await self.manager.test_model(request)
                return BaseResponse.ok(data=result, message="模型测试完成")
            except ValueError as e:
                logger.error(f"参数错误: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"模型测试失败: {e}")
                raise HTTPException(status_code=500, detail=f"模型测试失败: {str(e)}")

        @self.app.get(
            "/providers",
            response_model=BaseResponse[list[str]],
            dependencies=[VerifiedDep],
        )
        async def list_providers() -> BaseResponse[list[str]]:
            """获取提供商列表。

            Returns:
                提供商名称列表
            """
            try:
                providers = await self.manager.list_providers()
                return BaseResponse.ok(data=providers, message="获取提供商列表成功")
            except Exception as e:
                logger.error(f"获取提供商列表失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取提供商列表失败: {str(e)}")

        @self.app.get(
            "/models",
            response_model=BaseResponse[list[str]],
            dependencies=[VerifiedDep],
        )
        async def list_models(
            provider: str | None = Query(default=None, description="提供商名称")
        ) -> BaseResponse[list[str]]:
            """获取模型列表。

            Args:
                provider: 提供商名称（不指定则返回所有模型）

            Returns:
                模型名称列表
            """
            try:
                models = await self.manager.list_models(provider)
                return BaseResponse.ok(data=models, message="获取模型列表成功")
            except Exception as e:
                logger.error(f"获取模型列表失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")

    async def startup(self) -> None:
        """Router 启动钩子。"""
        logger.info("模型配置路由已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("模型配置路由已关闭")
