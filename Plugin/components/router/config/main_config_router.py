"""主配置路由。

提供统一的配置读写 API。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from fastapi import HTTPException, Query

from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from src.app.plugin_system.api.log_api import get_logger

from ....managers.config import get_main_config_manager
from ....utils.response import BaseResponse
from ....utils.config_types import (
    EnhancedConfigResponse,
    FullWriteRequest,
    PatchWriteRequest,
)

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin

logger = get_logger("main_config_router")


class MainConfigRouter(BaseRouter):
    """主配置路由。

    提供统一的配置读写接口：
    - GET /api/config/read/{config_type} - 获取增强配置
    - PUT /api/config/write/{config_type} - 全量写入配置
    - PATCH /api/config/patch/{config_type} - 增量写入配置
    """

    router_name: str = "config"
    router_description: str = "配置管理 API"
    custom_route_path: str = "/api/config"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.manager = get_main_config_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get(
            "/read/{config_type}",
            response_model=BaseResponse[EnhancedConfigResponse],
            dependencies=[VerifiedDep],
        )
        async def get_config(
            config_type: Literal["bot", "model", "plugin"],
            plugin_name: str | None = Query(default=None),
        ) -> BaseResponse[EnhancedConfigResponse]:
            """获取增强配置。

            Args:
                config_type: 配置类型（"bot", "model", "plugin"）
                plugin_name: 插件名（config_type="plugin" 时必填）

            Returns:
                包含配置 Schema 和数据的响应
            """
            try:
                config = await self.manager.get_config(config_type, plugin_name)
                return BaseResponse.ok(data=config, message="获取配置成功")
            except FileNotFoundError as e:
                logger.error(f"配置文件不存在: {e}")
                raise HTTPException(status_code=404, detail=str(e))
            except ValueError as e:
                logger.error(f"参数错误: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"获取配置失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

        @self.app.get(
            "/raw/{config_type}",
            response_model=BaseResponse[str],
            dependencies=[VerifiedDep],
        )
        async def get_raw_toml(
            config_type: Literal["bot", "model", "plugin"],
            plugin_name: str | None = Query(default=None),
        ) -> BaseResponse[str]:
            """获取原始 TOML 文件内容。

            Args:
                config_type: 配置类型（"bot", "model", "plugin"）
                plugin_name: 插件名（config_type="plugin" 时必填）

            Returns:
                TOML 文件的原始字符串内容
            """
            try:
                raw_content = await self.manager.get_raw_toml(config_type, plugin_name)
                return BaseResponse.ok(data=raw_content, message="获取原始配置成功")
            except FileNotFoundError as e:
                logger.error(f"配置文件不存在: {e}")
                raise HTTPException(status_code=404, detail=str(e))
            except ValueError as e:
                logger.error(f"参数错误: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"获取原始配置失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取原始配置失败: {str(e)}")

        @self.app.put(
            "/write/{config_type}",
            response_model=BaseResponse[EnhancedConfigResponse],
            dependencies=[VerifiedDep],
        )
        async def full_write_config(
            config_type: Literal["bot", "model", "plugin"],
            request: FullWriteRequest,
            plugin_name: str | None = Query(default=None),
        ) -> BaseResponse[EnhancedConfigResponse]:
            """全量写入配置。

            Args:
                config_type: 配置类型
                request: 写入请求（包含完整配置数据）
                plugin_name: 插件名（plugin 类型时必填）

            Returns:
                写入后的配置响应
            """
            try:
                config = await self.manager.full_write(
                    config_type, request.data, plugin_name
                )
                return BaseResponse.ok(data=config, message="配置写入成功")
            except ValueError as e:
                logger.error(f"配置验证失败: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"写入配置失败: {e}")
                raise HTTPException(status_code=500, detail=f"写入配置失败: {str(e)}")

        @self.app.patch(
            "/patch/{config_type}",
            response_model=BaseResponse[EnhancedConfigResponse],
            dependencies=[VerifiedDep],
        )
        async def patch_write_config(
            config_type: Literal["bot", "model", "plugin"],
            request: PatchWriteRequest,
            plugin_name: str | None = Query(default=None),
        ) -> BaseResponse[EnhancedConfigResponse]:
            """增量写入配置。

            Args:
                config_type: 配置类型
                request: 写入请求（包含部分配置数据）
                plugin_name: 插件名（plugin 类型时必填）

            Returns:
                合并后的配置响应
            """
            try:
                config = await self.manager.patch_write(
                    config_type, request.data, plugin_name
                )
                return BaseResponse.ok(data=config, message="配置更新成功")
            except ValueError as e:
                logger.error(f"配置验证失败: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"更新配置失败: {e}")
                raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

    async def startup(self) -> None:
        """Router 启动钩子。"""
        logger.info("主配置路由已启动")

    async def shutdown(self) -> None:
        """Router 关闭钩子。"""
        logger.info("主配置路由已关闭")
