"""插件管理器。

提供插件查询、组件信息提取和插件重载等核心业务逻辑。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from src.app.plugin_system.api.config_api import get_config  # type: ignore
from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.app.plugin_system.api.plugin_api import (  # type: ignore
    get_manifest,
    get_plugin,
    is_plugin_loaded,
    list_loaded_plugins,
    load_plugin,
    reload_plugin,
    unload_plugin,
)
from src.app.plugin_system.api.adapter_api import is_adapter_active  # type: ignore
from src.app.plugin_system.api.router_api import get_mounted_router  # type: ignore
from src.core.components.registry import get_global_registry  # type: ignore
from src.core.components.types import ComponentType, parse_signature  # type: ignore

from ..utils.plugin_types import (
    PluginComponentInfo,
    PluginDetail,
    PluginLoadResult,
    PluginReloadResult,
    PluginSummary,
    PluginUnloadResult,
)

logger = get_logger("plugin_manager")


class PluginManagementManager:
    """插件管理器。

    负责聚合插件信息、组件状态查询和插件重载操作。
    """

    def __init__(self) -> None:
        """初始化插件管理器。"""
        self._registry = get_global_registry()

    async def list_plugins(self) -> list[PluginSummary]:
        """获取所有已加载插件的摘要列表。

        Returns:
            插件摘要列表
        """
        plugin_names = list_loaded_plugins()
        plugin_summaries: list[PluginSummary] = []

        # 并行获取所有插件信息
        tasks = [self._get_plugin_summary(name) for name in plugin_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"获取插件信息失败: {result}")
                continue
            # 此时 result 类型为 PluginSummary | None
            if result is not None:
                plugin_summaries.append(result)

        return plugin_summaries

    async def _get_plugin_summary(self, plugin_name: str) -> PluginSummary | None:
        """获取单个插件的摘要信息。

        Args:
            plugin_name: 插件名称

        Returns:
            插件摘要，失败返回 None
        """
        try:
            # 获取清单信息
            manifest = get_manifest(plugin_name)
            if manifest is None:
                logger.warning(f"插件 {plugin_name} 清单不存在")
                return None

            # 获取配置信息
            has_config = get_config(plugin_name) is not None

            # 获取组件信息
            components = self._registry.get_by_plugin(plugin_name)
            component_count = len(components)

            # 统计组件类型
            component_types = set()
            for signature in components:
                try:
                    sig = parse_signature(signature)
                    component_types.add(sig["component_type"].value)
                except ValueError:
                    continue

            return PluginSummary(
                plugin_name=plugin_name,
                plugin_description=manifest.description or "",
                plugin_version=manifest.version or "1.0.0",
                is_loaded=True,
                has_config=has_config,
                component_count=component_count,
                component_types=sorted(list(component_types)),
            )
        except Exception as e:
            logger.error(f"获取插件 {plugin_name} 摘要信息失败: {e}", exc_info=True)
            return None

    async def get_plugin_detail(self, plugin_name: str) -> PluginDetail:
        """获取插件详细信息。

        Args:
            plugin_name: 插件名称

        Returns:
            插件详细信息

        Raises:
            ValueError: 插件未找到或未加载
        """
        # 校验插件是否已加载
        if not is_plugin_loaded(plugin_name):
            raise ValueError(f"插件 {plugin_name} 未加载")

        # 获取插件实例
        plugin = get_plugin(plugin_name)
        if plugin is None:
            raise ValueError(f"插件 {plugin_name} 未找到")

        # 获取清单
        manifest = get_manifest(plugin_name)
        if manifest is None:
            raise ValueError(f"插件 {plugin_name} 清单不存在")

        # 获取配置信息
        has_config = get_config(plugin_name) is not None

        # 获取所有组件
        components_dict = self._registry.get_by_plugin(plugin_name)
        components: list[PluginComponentInfo] = []

        for signature in components_dict:
            component_info = await self._extract_component_info(signature, components_dict[signature])
            if component_info is not None:
                components.append(component_info)

        # 统计组件类型
        component_types = set()
        for comp in components:
            component_types.add(comp.component_type)

        # 提取依赖列表
        dependencies: list[str] = []
        manifest_dict = manifest.model_dump() if hasattr(manifest, "model_dump") else {}
        if "dependencies" in manifest_dict and isinstance(manifest_dict["dependencies"], dict):
            deps_components = manifest_dict["dependencies"].get("components", [])
            if isinstance(deps_components, list):
                dependencies = deps_components

        # 获取插件路径
        plugin_path = getattr(plugin, "_plugin_path", "")

        return PluginDetail(
            plugin_name=plugin_name,
            plugin_description=manifest.description or "",
            plugin_version=manifest.version or "1.0.0",
            is_loaded=True,
            has_config=has_config,
            component_count=len(components),
            component_types=sorted(list(component_types)),
            plugin_path=plugin_path,
            manifest=manifest_dict,
            components=components,
            dependencies=dependencies,
        )

    async def _extract_component_info(
        self, signature: str, component_cls: type
    ) -> PluginComponentInfo | None:
        """提取组件详细信息。

        Args:
            signature: 组件签名
            component_cls: 组件类

        Returns:
            组件信息，失败返回 None
        """
        try:
            # 解析签名
            sig = parse_signature(signature)
            plugin_name = sig["plugin_name"]
            component_type = sig["component_type"]
            component_name = sig["component_name"]

            # 获取组件描述
            description = getattr(component_cls, "__doc__", "") or ""
            description = description.strip().split("\n")[0] if description else ""

            # 判断组件状态
            status: str = "active"
            if component_type == ComponentType.ROUTER:
                router = get_mounted_router(signature)
                status = "active" if router is not None else "inactive"
            elif component_type == ComponentType.ADAPTER:
                status = "active" if is_adapter_active(signature) else "inactive"
            # 其他组件类型默认为 active

            # 提取扩展属性
            extra: dict[str, Any] = {}
            if component_type == ComponentType.ROUTER:
                extra["custom_route_path"] = getattr(component_cls, "custom_route_path", None)
                extra["cors_origins"] = getattr(component_cls, "cors_origins", [])
            elif component_type == ComponentType.ADAPTER:
                extra["platform"] = getattr(component_cls, "platform", None)
            elif component_type == ComponentType.COMMAND:
                extra["permission_level"] = str(getattr(component_cls, "permission_level", "USER"))
                extra["command_name"] = getattr(component_cls, "command_name", None)
            elif component_type == ComponentType.ACTION:
                extra["primary_action"] = getattr(component_cls, "primary_action", False)
                extra["action_name"] = getattr(component_cls, "action_name", None)
            elif component_type == ComponentType.AGENT:
                extra["agent_name"] = getattr(component_cls, "agent_name", None)
                # usables 通常在实例化后才有，这里尝试获取类级别的定义
                extra["usables"] = getattr(component_cls, "usables", [])

            return PluginComponentInfo(
                signature=signature,
                component_type=component_type.value,
                component_name=component_name,
                description=description,
                status=status,
                extra=extra if extra else None,
            )
        except Exception as e:
            logger.error(f"提取组件 {signature} 信息失败: {e}", exc_info=True)
            return None

    async def reload_plugin_operation(self, plugin_name: str) -> PluginReloadResult:
        """重载插件。

        Args:
            plugin_name: 插件名称

        Returns:
            重载结果
        """
        # 校验插件是否存在
        if not is_plugin_loaded(plugin_name):
            return PluginReloadResult(
                success=False,
                plugin_name=plugin_name,
                reload_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                error_message=f"插件 {plugin_name} 未加载",
            )

        try:
            # 执行重载
            success = await reload_plugin(plugin_name)
            reload_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

            if success:
                logger.info(f"插件 {plugin_name} 重载成功")
                return PluginReloadResult(
                    success=True, plugin_name=plugin_name, reload_time=reload_time, error_message=None
                )
            else:
                logger.warning(f"插件 {plugin_name} 重载失败")
                return PluginReloadResult(
                    success=False,
                    plugin_name=plugin_name,
                    reload_time=reload_time,
                    error_message="重载操作返回失败",
                )
        except Exception as e:
            logger.error(f"插件 {plugin_name} 重载异常: {e}", exc_info=True)
            return PluginReloadResult(
                success=False,
                plugin_name=plugin_name,
                reload_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                error_message=str(e),
            )

    async def get_plugin_components(
        self, plugin_name: str, component_type: str | None = None
    ) -> list[PluginComponentInfo]:
        """获取插件的组件列表，支持按类型筛选。

        Args:
            plugin_name: 插件名称
            component_type: 可选的组件类型筛选

        Returns:
            组件信息列表

        Raises:
            ValueError: 插件未找到或组件类型无效
        """
        # 校验插件是否已加载
        if not is_plugin_loaded(plugin_name):
            raise ValueError(f"插件 {plugin_name} 未加载")

        # 获取组件
        if component_type is not None:
            # 验证组件类型
            try:
                comp_type = ComponentType(component_type)
            except ValueError:
                raise ValueError(f"无效的组件类型: {component_type}")

            components_dict = self._registry.get_by_plugin_and_type(plugin_name, comp_type)
        else:
            components_dict = self._registry.get_by_plugin(plugin_name)

        # 提取组件信息
        components: list[PluginComponentInfo] = []
        for signature, component_cls in components_dict.items():
            component_info = await self._extract_component_info(signature, component_cls)
            if component_info is not None:
                components.append(component_info)

        return components

    async def load_plugin_operation(self, plugin_path: str) -> PluginLoadResult:
        """加载插件。

        Args:
            plugin_path: 插件路径

        Returns:
            加载结果
        """
        try:
            # 执行加载
            success = await load_plugin(plugin_path)
            load_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

            if success:
                # 尝试获取插件名称（从路径推断或加载后获取）
                plugin_name = plugin_path.split("/")[-1].split("\\")[-1]
                logger.info(f"插件 {plugin_name} 从路径 {plugin_path} 加载成功")
                return PluginLoadResult(
                    success=True,
                    plugin_name=plugin_name,
                    plugin_path=plugin_path,
                    load_time=load_time,
                    error_message=None,
                )
            else:
                logger.warning(f"从路径 {plugin_path} 加载插件失败")
                return PluginLoadResult(
                    success=False,
                    plugin_name="",
                    plugin_path=plugin_path,
                    load_time=load_time,
                    error_message="加载操作返回失败",
                )
        except Exception as e:
            logger.error(f"从路径 {plugin_path} 加载插件异常: {e}", exc_info=True)
            return PluginLoadResult(
                success=False,
                plugin_name="",
                plugin_path=plugin_path,
                load_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                error_message=str(e),
            )

    async def unload_plugin_operation(self, plugin_name: str) -> PluginUnloadResult:
        """卸载插件。

        Args:
            plugin_name: 插件名称

        Returns:
            卸载结果
        """
        # 校验插件是否存在
        if not is_plugin_loaded(plugin_name):
            return PluginUnloadResult(
                success=False,
                plugin_name=plugin_name,
                unload_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                error_message=f"插件 {plugin_name} 未加载",
            )

        try:
            # 执行卸载
            success = await unload_plugin(plugin_name)
            unload_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

            if success:
                logger.info(f"插件 {plugin_name} 卸载成功")
                return PluginUnloadResult(
                    success=True, plugin_name=plugin_name, unload_time=unload_time, error_message=None
                )
            else:
                logger.warning(f"插件 {plugin_name} 卸载失败")
                return PluginUnloadResult(
                    success=False,
                    plugin_name=plugin_name,
                    unload_time=unload_time,
                    error_message="卸载操作返回失败",
                )
        except Exception as e:
            logger.error(f"插件 {plugin_name} 卸载异常: {e}", exc_info=True)
            return PluginUnloadResult(
                success=False,
                plugin_name=plugin_name,
                unload_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                error_message=str(e),
            )


# 单例实例
_plugin_management_manager: PluginManagementManager | None = None


def get_plugin_management_manager() -> PluginManagementManager:
    """获取插件管理器单例。

    Returns:
        插件管理器实例
    """
    global _plugin_management_manager
    if _plugin_management_manager is None:
        _plugin_management_manager = PluginManagementManager()
    return _plugin_management_manager


__all__ = ["PluginManagementManager", "get_plugin_management_manager"]
