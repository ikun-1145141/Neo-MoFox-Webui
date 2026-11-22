"""插件管理路由组件。

提供插件管理的 RESTful API 端点。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import File, Form, HTTPException, Query, UploadFile

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.router import BaseRouter  # type: ignore
from src.core.utils.security import VerifiedDep  # type: ignore

from ...managers.plugin_manager import get_plugin_management_manager
from ...utils.plugin_package import PluginPackageError, PluginPackageTooLargeError
from ...utils.response import BaseResponse
from ...utils.plugin_types import (
    PluginComponentInfo,
    PluginDetail,
    PluginImportResult,
    PluginLoadResult,
    PluginReloadResult,
    PluginSummary,
    PluginUnloadResult,
)

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("plugin_router")


class PluginRouter(BaseRouter):
    """插件管理路由组件。"""

    name: str = "plugin"
    description: str = "插件管理接口"
    custom_route_path: str = "/webui/api/plugin"
    cors_origins: list[str] = ["*"]

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化 Router。

        Args:
            plugin: 所属插件实例
        """
        super().__init__(plugin)
        self.plugin_manager = get_plugin_management_manager()

    def register_endpoints(self) -> None:
        """注册 API 端点。"""

        @self.app.get(
            "/list",
            response_model=BaseResponse[list[PluginSummary]],
            dependencies=[VerifiedDep],
            summary="获取插件列表",
            description="获取所有已加载插件的摘要信息列表",
        )
        async def get_plugin_list() -> BaseResponse[list[PluginSummary]]:
            """获取插件列表。"""
            try:
                plugins = await self.plugin_manager.list_plugins()
                return BaseResponse.ok(data=plugins, message="获取插件列表成功")
            except Exception as e:
                logger.error(f"获取插件列表失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取插件列表失败: {str(e)}")

        @self.app.post(
            "/import",
            response_model=BaseResponse[PluginImportResult],
            dependencies=[VerifiedDep],
            summary="导入插件包",
            description="上传 .zip / .mfp 插件包，校验后写入插件目录并尝试热加载",
        )
        async def import_plugin_package(
            file: UploadFile = File(..., description="插件包文件（.zip / .mfp）"),
            overwrite: bool = Form(False, description="检测到同名插件时是否直接覆盖"),
        ) -> BaseResponse[PluginImportResult]:
            """导入插件包。

            Args:
                file: 上传的插件包文件
                overwrite: 是否覆盖同名插件
            """
            try:
                result = await self.plugin_manager.import_plugin_package(
                    file=file,
                    overwrite=overwrite,
                    protected_name=self.plugin.plugin_name,
                )
                if result.conflict:
                    return BaseResponse.ok(data=result, message="已存在同名插件，请确认是否覆盖")
                if result.restart_required:
                    message = "插件包已写入，热加载失败，请重启 Neo-MoFox 后生效"
                else:
                    message = "插件包导入成功"
                return BaseResponse.ok(data=result, message=message)
            except PluginPackageTooLargeError as e:
                logger.warning(f"导入插件包被拒绝: {e}")
                raise HTTPException(status_code=413, detail=str(e))
            except PluginPackageError as e:
                logger.warning(f"导入插件包被拒绝: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"导入插件包失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"导入插件包失败: {str(e)}")

        @self.app.get(
            "/{plugin_name}",
            response_model=BaseResponse[PluginDetail],
            dependencies=[VerifiedDep],
            summary="获取插件详情",
            description="获取指定插件的详细信息，包括完整组件列表",
        )
        async def get_plugin_detail(plugin_name: str) -> BaseResponse[PluginDetail]:
            """获取插件详情。

            Args:
                plugin_name: 插件名称
            """
            try:
                detail = await self.plugin_manager.get_plugin_detail(plugin_name)
                return BaseResponse.ok(data=detail, message="获取插件详情成功")
            except ValueError as e:
                logger.warning(f"插件 {plugin_name} 未找到: {e}")
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"获取插件详情失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取插件详情失败: {str(e)}")

        @self.app.post(
            "/{plugin_name}/reload",
            response_model=BaseResponse[PluginReloadResult],
            dependencies=[VerifiedDep],
            summary="重载插件",
            description="重载指定插件（卸载后重新加载）",
        )
        async def reload_plugin(plugin_name: str) -> BaseResponse[PluginReloadResult]:
            """重载插件。

            Args:
                plugin_name: 插件名称
            """
            try:
                result = await self.plugin_manager.reload_plugin_operation(plugin_name)
                if result.success:
                    return BaseResponse.ok(data=result, message="插件重载成功")
                else:
                    return BaseResponse.error(
                        code=500, data=result, message=result.error_message or "插件重载失败"
                    )
            except Exception as e:
                logger.error(f"插件重载异常: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"插件重载异常: {str(e)}")

        @self.app.get(
            "/{plugin_name}/components",
            response_model=BaseResponse[list[PluginComponentInfo]],
            dependencies=[VerifiedDep],
            summary="获取插件组件列表",
            description="获取指定插件的所有组件，支持按类型筛选",
        )
        async def get_plugin_components(
            plugin_name: str, component_type: str | None = Query(default=None, description="组件类型筛选")
        ) -> BaseResponse[list[PluginComponentInfo]]:
            """获取插件组件列表。

            Args:
                plugin_name: 插件名称
                component_type: 可选的组件类型筛选
            """
            try:
                components = await self.plugin_manager.get_plugin_components(plugin_name, component_type)
                return BaseResponse.ok(data=components, message="获取组件列表成功")
            except ValueError as e:
                logger.warning(f"获取组件列表失败: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"获取组件列表失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取组件列表失败: {str(e)}")

        @self.app.post(
            "/load",
            response_model=BaseResponse[PluginLoadResult],
            dependencies=[VerifiedDep],
            summary="加载插件",
            description="从指定路径加载插件",
        )
        async def load_plugin_endpoint(
            plugin_path: str = Query(..., description="插件路径")
        ) -> BaseResponse[PluginLoadResult]:
            """加载插件。

            Args:
                plugin_path: 插件路径
            """
            try:
                result = await self.plugin_manager.load_plugin_operation(plugin_path)
                if result.success:
                    return BaseResponse.ok(data=result, message="插件加载成功")
                else:
                    return BaseResponse.error(
                        code=500, data=result, message=result.error_message or "插件加载失败"
                    )
            except Exception as e:
                logger.error(f"插件加载异常: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"插件加载异常: {str(e)}")

        @self.app.post(
            "/{plugin_name}/unload",
            response_model=BaseResponse[PluginUnloadResult],
            dependencies=[VerifiedDep],
            summary="卸载插件",
            description="卸载指定插件",
        )
        async def unload_plugin_endpoint(plugin_name: str) -> BaseResponse[PluginUnloadResult]:
            """卸载插件。

            Args:
                plugin_name: 插件名称
            """
            try:
                result = await self.plugin_manager.unload_plugin_operation(plugin_name)
                if result.success:
                    return BaseResponse.ok(data=result, message="插件卸载成功")
                else:
                    return BaseResponse.error(
                        code=500, data=result, message=result.error_message or "插件卸载失败"
                    )
            except Exception as e:
                logger.error(f"插件卸载异常: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"插件卸载异常: {str(e)}")


__all__ = ["PluginRouter"]
