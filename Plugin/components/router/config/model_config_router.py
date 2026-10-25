"""模型配置路由。

提供模型配置专属 API。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import HTTPException, Query, Request

from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from src.app.plugin_system.api.log_api import get_logger

from ....managers.config import get_model_config_manager
from ....utils.response import BaseResponse
from ....utils.config_types import (
    ModelTestRequest, ModelTestResult, RemoteModelListRequest, RemoteModelOption,
)

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("model_config_router")


class ModelConfigRouter(BaseRouter):
    """模型配置路由。

    提供模型配置专属操作：
    - POST /api/config-model/reload - 热重载模型配置
    - POST /api/config-model/test - 测试模型连通性
    - GET /api/config-model/providers - 获取提供商列表
    - GET /api/config-model/models - 获取已配置的模型列表
    - POST /api/config-model/remote-models - 从供应商获取可用模型列表
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
            "/remote-models",
            response_model=BaseResponse[list[RemoteModelOption]],
            dependencies=[VerifiedDep],
        )
        async def list_remote_models(
            request: RemoteModelListRequest,
        ) -> BaseResponse[list[RemoteModelOption]]:
            """读取远程模型列表，不持久化请求中的供应商信息。"""
            return await self.manager.list_remote_models(request)

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
        async def test_model(request: ModelTestRequest, connection: Request) -> BaseResponse[ModelTestResult]:
            """执行单项能力测试，断开连接时关闭当前请求。"""
            async def wait_for_disconnect() -> None:
                while not await connection.is_disconnected():
                    await asyncio.sleep(0.1)

            operation = asyncio.create_task(self.manager.test_model(request))
            disconnected = asyncio.create_task(wait_for_disconnect())
            try:
                done, _ = await asyncio.wait({operation, disconnected}, return_when=asyncio.FIRST_COMPLETED)
                if operation not in done:
                    raise HTTPException(status_code=499, detail="模型测试已取消")
                result = await operation
                return BaseResponse.ok(data=result, message="模型测试完成")
            except ValueError as exc:
                logger.warning("模型测试参数无效")
                raise HTTPException(status_code=400, detail=str(exc)) from None
            except HTTPException:
                raise
            except Exception:
                logger.error("模型能力测试失败")
                raise HTTPException(status_code=500, detail="模型测试失败，请稍后重试") from None
            finally:
                # 取消未完成的任务并等待资源释放，不让模型请求留在后台继续执行。
                for task in (operation, disconnected):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(operation, disconnected, return_exceptions=True)

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
