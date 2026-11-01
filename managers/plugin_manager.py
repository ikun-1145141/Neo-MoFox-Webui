"""插件管理器。

提供插件查询、组件信息提取和插件重载等核心业务逻辑。
"""

from __future__ import annotations

import asyncio
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from src.app.plugin_system.api.config_api import get_config  # type: ignore
from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.app.plugin_system.api.plugin_api import (  # type: ignore
    get_manifest,
    get_plugin,
    get_plugin_path,
    is_plugin_loaded,
    list_loaded_plugins,
    list_unloaded_plugins,
    load_plugin,
    reload_plugin,
    unload_plugin,
)
from src.app.plugin_system.api.adapter_api import is_adapter_active  # type: ignore
from src.app.plugin_system.api.router_api import get_mounted_router  # type: ignore
from src.core.components.loader import (  # type: ignore
    PluginLoader,
    _split_plugin_dependency_ref,
    load_manifest as load_plugin_manifest,
)
from src.core.components.registry import get_global_registry  # type: ignore
from src.core.components.types import ComponentType, parse_signature  # type: ignore
from src.core.config.core_config import get_core_config  # type: ignore

from ..utils.plugin_package import (
    MAX_PACKAGE_SIZE_MB,
    PACKAGE_SUFFIXES,
    PluginPackageError,
    PluginPackageTooLargeError,
    validate_plugin_id,
    validate_plugin_package,
)
from ..utils.plugin_types import (
    PluginComponentInfo,
    PluginDetail,
    PluginImportResult,
    PluginLoadResult,
    PluginReloadResult,
    PluginSummary,
    PluginUnloadResult,
)

logger = get_logger("plugin_manager")

# 上传流式读取的分块大小
_UPLOAD_CHUNK_BYTES = 1024 * 1024
# 暂存目录名，以 "." 开头，插件发现逻辑会跳过
_STAGING_DIR_NAME = ".import-staging"
# 未显式传入受保护插件名时的兜底值
_DEFAULT_PROTECTED_PLUGIN = "neo-mofox-webui"

# 写入类操作（导入/覆盖）共用的串行锁
_import_lock = asyncio.Lock()


class PluginManagementManager:
    """插件管理器。

    负责聚合插件信息、组件状态查询和插件重载操作。
    """

    def __init__(self) -> None:
        """初始化插件管理器。"""
        self._registry = get_global_registry()

    async def list_plugins(self) -> list[PluginSummary]:
        """获取所有插件的摘要列表（包括已加载和未加载的插件）。

        Returns:
            插件摘要列表
        """
        plugin_summaries: list[PluginSummary] = []

        # 获取已加载插件
        plugin_names = list_loaded_plugins()
        tasks = [self._get_plugin_summary(name) for name in plugin_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"获取已加载插件信息失败: {result}")
                continue
            if isinstance(result, PluginSummary):
                plugin_summaries.append(result)

        # 获取未加载插件
        try:
            unloaded_plugins_info = await list_unloaded_plugins()
            for plugin_name, plugin_info in unloaded_plugins_info.items():
                summary = self._convert_unloaded_to_summary(plugin_name, plugin_info)
                if summary is not None:
                    plugin_summaries.append(summary)
        except Exception as e:
            logger.error(f"获取未加载插件信息失败: {e}", exc_info=True)

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

            # 获取插件路径（使用新的 API）
            plugin_path = get_plugin_path(plugin_name)

            return PluginSummary(
                plugin_name=plugin_name,
                plugin_description=manifest.description or "",
                plugin_version=manifest.version or "1.0.0",
                is_loaded=True,
                has_config=has_config,
                component_count=component_count,
                component_types=sorted(list(component_types)),
                plugin_path=plugin_path,
            )
        except Exception as e:
            logger.error(f"获取插件 {plugin_name} 摘要信息失败: {e}", exc_info=True)
            return None

    def _convert_unloaded_to_summary(self, plugin_name: str, plugin_info: dict[str, Any]) -> PluginSummary | None:
        """将未加载插件信息转换为 PluginSummary 格式。

        Args:
            plugin_name: 插件名称
            plugin_info: 未加载插件的信息字典（来自 list_unloaded_plugins）

        Returns:
            插件摘要，失败返回 None
        """
        try:
            return PluginSummary(
                plugin_name=plugin_name,
                plugin_description=plugin_info.get("description", ""),
                plugin_version=plugin_info.get("version", "1.0.0"),
                is_loaded=False,
                has_config=False,  # 未加载的插件无法确定是否有配置
                component_count=0,  # 未加载的插件无法获取组件数量
                component_types=[],  # 未加载的插件无法获取组件类型
                plugin_path=plugin_info.get("path"),  # 包含插件路径用于加载操作
            )
        except Exception as e:
            logger.error(f"转换未加载插件 {plugin_name} 信息失败: {e}", exc_info=True)
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
                # 注意: usables 可能包含 Protocol 类型，需转换为可序列化格式
                raw_usables = getattr(component_cls, "usables", [])
                extra["usables"] = self._serialize_usables(raw_usables)

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

    def _serialize_usables(self, usables: Any) -> list[str]:
        """将 usables 转换为可序列化的格式。

        Args:
            usables: 原始 usables 数据（可能包含 Protocol 类型）

        Returns:
            字符串列表（类型名称）
        """
        if not usables:
            return []

        result: list[str] = []
        if not isinstance(usables, list):
            usables = [usables]

        for item in usables:
            try:
                # 如果是类型对象，获取其名称
                if hasattr(item, "__name__"):
                    result.append(item.__name__)
                elif hasattr(item, "__class__"):
                    result.append(item.__class__.__name__)
                else:
                    # 尝试转换为字符串
                    result.append(str(item))
            except Exception as e:
                logger.debug(f"序列化 usable 失败: {e}")
                continue

        return result

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
        """卸载插件并删除插件文件。

        卸载成功后会直接删除插件的目录文件，此操作不可逆。

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

        # 在卸载前获取插件路径，卸载后可能无法获取
        plugin_path = get_plugin_path(plugin_name)

        try:
            # 执行卸载
            success = await unload_plugin(plugin_name)
            logger.info(str(success))
            unload_time = datetime.now(timezone.utc).isoformat(timespec="seconds")

            if not success:
                logger.warning(f"插件 {plugin_name} 卸载失败")
                return PluginUnloadResult(
                    success=False,
                    plugin_name=plugin_name,
                    unload_time=unload_time,
                    error_message="卸载操作返回失败",
                )

            logger.info(f"插件 {plugin_name} 卸载成功")

            # 卸载成功后删除插件文件
            delete_error = self._delete_plugin_files(plugin_name, plugin_path)
            if delete_error is not None:
                # 卸载已成功，但文件删除失败，记录警告但不影响卸载结果
                logger.warning(
                    f"插件 {plugin_name} 卸载成功，但文件删除失败: {delete_error}"
                )
                return PluginUnloadResult(
                    success=True,
                    plugin_name=plugin_name,
                    unload_time=unload_time,
                    error_message=f"插件已卸载，但文件删除失败: {delete_error}",
                )

            logger.info(f"插件 {plugin_name} 文件已删除: {plugin_path}")
            return PluginUnloadResult(
                success=True,
                plugin_name=plugin_name,
                unload_time=unload_time,
                error_message=None,
            )
        except Exception as e:
            logger.error(f"插件 {plugin_name} 卸载异常: {e}", exc_info=True)
            return PluginUnloadResult(
                success=False,
                plugin_name=plugin_name,
                unload_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                error_message=str(e),
            )

    async def import_plugin_package(
        self,
        file: UploadFile,
        overwrite: bool = False,
        protected_name: str = _DEFAULT_PROTECTED_PLUGIN,
    ) -> PluginImportResult:
        """从上传的 .zip / .mfp 插件包导入插件。

        流程为：流式落盘到暂存区 → 包结构安全校验 → 兼容性预检 → 同名冲突处理
        → 原子替换到插件根目录 → 热加载。覆盖正在运行的插件时先卸载再替换。

        Args:
            file: 上传的插件包文件
            overwrite: 检测到同名插件时是否直接覆盖
            protected_name: 禁止被覆盖的插件名（默认 WebUI 自身）

        Returns:
            导入结果；检测到同名冲突且 overwrite 为 False 时返回 conflict=True，
            不修改任何文件
        """
        import_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
        plugins_root = Path(get_core_config().bot.plugins_dir).resolve()
        suffix = self._normalize_package_suffix(file.filename)
        staged: Path | None = None

        async with _import_lock:
            try:
                plugins_root.mkdir(parents=True, exist_ok=True)
                staging_dir = plugins_root / _STAGING_DIR_NAME
                staging_dir.mkdir(parents=True, exist_ok=True)
                staged = staging_dir / f"{uuid4().hex}{suffix}"

                await self._stream_upload_to_file(file, staged)
                manifest_data = await asyncio.to_thread(
                    validate_plugin_package,
                    staged,
                    MAX_PACKAGE_SIZE_MB * 1024 * 1024,
                )

                plugin_name = str(manifest_data.get("name") or "").strip()
                validate_plugin_id(plugin_name)
                if plugin_name == protected_name:
                    raise PluginPackageError(
                        f"不能通过导入覆盖当前提供该接口的插件 {protected_name}"
                    )

                manifest = await load_plugin_manifest(str(staged))
                if manifest is None:
                    raise PluginPackageError("插件清单解析失败")

                compatible, reason = PluginLoader()._check_version_compatibility(manifest)
                if not compatible:
                    raise PluginPackageError(f"插件与当前 Neo-MoFox 不兼容: {reason}")

                warnings = self._collect_import_warnings(manifest)
                existing = await self._find_local_plugin(plugin_name)

                if existing is not None:
                    existing_path: Path = existing["path"]
                    if not existing_path.is_file() or existing_path.parent != plugins_root:
                        raise PluginPackageError(
                            "已存在的同名插件不是插件目录根级的 .zip/.mfp 包，"
                            "必须由管理员手动管理"
                        )
                    if not overwrite:
                        return PluginImportResult(
                            success=False,
                            conflict=True,
                            plugin_name=plugin_name,
                            plugin_version=manifest.version,
                            existing_version=existing["version"],
                            existing_loaded=existing["loaded"],
                            dependents=self._find_dependent_plugins(plugin_name),
                            import_time=import_time,
                        )

                destination = (plugins_root / f"{plugin_name}{suffix}").resolve()
                if destination.parent != plugins_root:
                    raise PluginPackageError("插件安装路径无效")
                # 目标文件名被另一个插件的包占用时拒绝，避免误覆盖无关插件
                if destination.exists() and (
                    existing is None or existing["path"] != destination
                ):
                    raise PluginPackageError(
                        f"插件目录中已存在文件 {destination.name}，但不属于插件 {plugin_name}"
                    )

                if existing is not None and existing["loaded"]:
                    if not await unload_plugin(plugin_name):
                        raise PluginPackageError(
                            f"覆盖前卸载插件 {plugin_name} 失败，已取消导入"
                        )

                await asyncio.to_thread(os.replace, staged, destination)
                staged = None

                # 后缀变化时必须删除旧包，否则下次启动会出现两个同名插件
                if existing is not None and existing["path"] != destination:
                    delete_error = self._delete_plugin_files(
                        plugin_name, str(existing["path"])
                    )
                    if delete_error is not None:
                        warnings.append(f"旧插件包未能删除: {delete_error}")

                loaded, load_message = await self._hot_load_imported(
                    plugin_name, str(destination)
                )

                logger.info(
                    f"插件包导入完成: plugin={plugin_name}, version={manifest.version}, "
                    f"path={destination}, replaced={existing is not None}, loaded={loaded}"
                )
                return PluginImportResult(
                    success=True,
                    plugin_name=plugin_name,
                    plugin_version=manifest.version,
                    plugin_path=str(destination),
                    existing_version=existing["version"] if existing else None,
                    existing_loaded=existing["loaded"] if existing else False,
                    replaced=existing is not None,
                    loaded=loaded,
                    restart_required=not loaded,
                    warnings=warnings,
                    import_time=import_time,
                    error_message=None if loaded else load_message,
                )
            finally:
                if staged is not None:
                    await asyncio.to_thread(staged.unlink, missing_ok=True)

    @staticmethod
    def _normalize_package_suffix(filename: str | None) -> str:
        """校验上传文件名后缀，返回规范化后的后缀。

        Args:
            filename: 上传时的原始文件名。

        Returns:
            小写的 ``.zip`` 或 ``.mfp``。

        Raises:
            PluginPackageError: 文件名为空或后缀不在白名单内。
        """
        name = (filename or "").strip()
        suffix = Path(name).suffix.lower() if name else ""
        if suffix not in PACKAGE_SUFFIXES:
            raise PluginPackageError("仅支持 .zip 或 .mfp 格式的插件包")
        return suffix

    async def _stream_upload_to_file(self, file: UploadFile, target: Path) -> None:
        """按分块流式写入上传内容，超限立即中止。

        不使用 ``await file.read()`` 整体读入内存，避免大包占用过多内存。

        Args:
            file: 上传的插件包文件。
            target: 暂存文件路径。

        Raises:
            PluginPackageError: 内容为空或超过体积上限。
        """
        max_bytes = MAX_PACKAGE_SIZE_MB * 1024 * 1024
        written = 0

        def _open() -> Any:
            return target.open("wb")

        handle = await asyncio.to_thread(_open)
        try:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise PluginPackageTooLargeError(
                        f"插件包不能超过 {MAX_PACKAGE_SIZE_MB}MB"
                    )
                await asyncio.to_thread(handle.write, chunk)
        finally:
            await asyncio.to_thread(handle.close)

        if written == 0:
            raise PluginPackageError("上传的插件包为空")

    async def _hot_load_imported(
        self, plugin_name: str, plugin_path: str
    ) -> tuple[bool, str]:
        """导入落盘后尝试加载插件包。

        已加载的同名插件已在写入前卸载，因此这里统一走 ``load_plugin``。

        Args:
            plugin_name: 插件名称。
            plugin_path: 已落盘的插件包绝对路径。

        Returns:
            (是否加载成功, 失败原因)。
        """
        try:
            if await load_plugin(plugin_path):
                return True, ""
            return False, "加载操作返回失败"
        except Exception as error:
            logger.warning(
                f"导入的插件热加载失败，需重启生效: plugin={plugin_name}, error={error}",
                exc_info=True,
            )
            return False, str(error)

    def _collect_import_warnings(self, manifest: Any) -> list[str]:
        """收集不阻断导入的提示信息。

        Args:
            manifest: 包内清单对象。

        Returns:
            提示信息列表。
        """
        warnings: list[str] = []
        if manifest.python_dependencies:
            warnings.append(
                "该插件声明了 Python 依赖，导入流程不会自动安装，"
                "若加载失败请安装依赖后重启 Neo-MoFox"
            )
        loaded = set(list_loaded_plugins())
        missing = [
            str(item)
            for item in manifest.dependencies.get("plugins", [])
            if _split_plugin_dependency_ref(item)[0] not in loaded
        ]
        if missing:
            warnings.append("以下依赖插件当前未加载: " + ", ".join(missing))
        return warnings

    async def _find_local_plugin(self, plugin_name: str) -> dict[str, Any] | None:
        """查找插件目录中指定名称的已有插件。

        先查已加载插件，再扫描未加载的插件包与插件目录。

        Args:
            plugin_name: 插件名称。

        Returns:
            包含 ``path`` / ``version`` / ``loaded`` 的字典，未找到返回 None。
        """
        if is_plugin_loaded(plugin_name):
            plugin_path = get_plugin_path(plugin_name)
            manifest = get_manifest(plugin_name)
            if plugin_path:
                return {
                    "path": Path(plugin_path).resolve(),
                    "version": getattr(manifest, "version", None),
                    "loaded": True,
                }

        plugins_root = Path(get_core_config().bot.plugins_dir).resolve()
        for discovered in await PluginLoader().discover_plugins(str(plugins_root)):
            manifest = await load_plugin_manifest(discovered)
            if manifest is None or manifest.name != plugin_name:
                continue
            return {
                "path": Path(discovered).resolve(),
                "version": manifest.version,
                "loaded": False,
            }
        return None

    def _find_dependent_plugins(self, plugin_name: str) -> list[str]:
        """列出依赖指定插件的已加载插件。

        Args:
            plugin_name: 被依赖的插件名称。

        Returns:
            依赖方插件名称列表。
        """
        dependents: list[str] = []
        for other in list_loaded_plugins():
            if other == plugin_name:
                continue
            manifest = get_manifest(other)
            if manifest is None:
                continue
            for dependency in manifest.dependencies.get("plugins", []):
                if _split_plugin_dependency_ref(dependency)[0] == plugin_name:
                    dependents.append(other)
                    break
        return sorted(set(dependents))

    def _delete_plugin_files(self, plugin_name: str, plugin_path: str | None) -> str | None:
        """删除插件目录或压缩包文件。

        支持插件目录与插件压缩包（.mfp / .zip），二者均可能由相对路径标识。
        采用白名单校验：插件路径必须严格位于配置的插件根目录之内且为其直接子项，
        从而拒绝删除插件根目录本身、主程序目录、家目录或任意插件目录外的路径。

        Args:
            plugin_name: 插件名称
            plugin_path: 插件路径（卸载前获取，可为相对或绝对路径）

        Returns:
            删除失败时返回错误信息，成功返回 None
        """
        if not plugin_path:
            return f"无法获取插件 {plugin_name} 的路径"

        try:
            # 解析为绝对路径，使后续白名单校验对相对路径同样生效。
            path = Path(plugin_path).resolve()
            if not path.exists():
                return f"插件路径不存在: {plugin_path}"

            # 白名单校验：插件根目录取自核心配置（默认 "plugins"），同样解析为绝对路径。
            plugins_root = Path(get_core_config().bot.plugins_dir).resolve()

            # 拒绝删除插件根目录本身（防止清空整个插件目录）。
            if path == plugins_root:
                return f"插件路径指向插件根目录，拒绝删除: {plugin_path}"

            # 插件路径必须是插件根目录的直接子项（如 plugins/xxx 或 plugins/xxx.mfp），
            # 任何跳出插件目录的路径（主程序目录、家目录、/ 等）一律拒绝。
            if path.parent != plugins_root:
                return f"插件路径不在插件目录内，拒绝删除: {plugin_path}"

            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
            else:
                return f"插件路径既不是目录也不是文件: {plugin_path}"

            return None
        except Exception as e:
            return f"删除插件文件异常: {e}"


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
