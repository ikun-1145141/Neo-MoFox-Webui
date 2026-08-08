"""插件市场业务逻辑与安全安装操作。"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import tempfile
import time
import zipfile
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import aiohttp
from packaging.version import InvalidVersion, Version
from yarl import URL

from src.app.plugin_system.api.config_api import get_config
from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.plugin_api import (
    get_manifest,
    get_plugin_path,
    list_loaded_plugins,
    load_plugin,
    reload_plugin,
)
from src.core.components.loader import PluginLoader, PluginManifest, load_manifest
from src.core.config import CORE_VERSION
from src.core.config.core_config import get_core_config
from src.kernel.concurrency import get_task_manager

from ..storage.settings import SettingsStorage
from ..utils.plugin_market_types import (
    CompatibilityInfo,
    InstallPlan,
    MarketCapabilities,
    MarketDependency,
    MarketLocalState,
    MarketOperation,
    MarketOperationResult,
    MarketPlugin,
    MarketPluginDetail,
    MarketPluginList,
    MarketPluginReadme,
    MarketVersion,
    OperationKind,
    UpstreamDependencyList,
    UpstreamInstallInfo,
    UpstreamPluginList,
    UpstreamVersionList,
)

logger = get_logger("plugin_market_manager")

_PLUGIN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_DEPENDENCY_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)(?P<spec>\s*(?:===|==|!=|~=|>=|<=|>|<).+)?$"
)
_JSON_LIMIT_BYTES = 8 * 1024 * 1024
_MAX_REDIRECTS = 10
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}

# 插件市场技术性边界常量（不暴露到插件配置或 UI 设置）
_REQUEST_TIMEOUT_SECONDS = 30
_PAGE_SIZE = 50
_CACHE_SECONDS = 30
_MAX_PACKAGE_SIZE_MB = 50
_TRUST_ENV = False


class PluginMarketError(RuntimeError):
    """市场请求或本地操作无法安全完成。"""


@dataclass(frozen=True)
class LocalPluginRecord:
    """本地插件清单与来源路径。"""

    manifest: PluginManifest
    path: Path
    loaded: bool
    has_config: bool


class PluginMarketManager:
    """聚合市场数据、本地插件状态和受控写操作。

    Manager 负责上游分页查询与缓存、本地插件发现、兼容性和依赖判断，
    并在 HTTPS、响应大小、哈希、ZIP 结构和目标路径校验后执行安装。
    Router 只调用这里的公开方法，不直接承载市场业务逻辑。
    """

    def __init__(self, settings_storage: SettingsStorage) -> None:
        """初始化使用 WebUI 设置存储的市场 Manager。

        Args:
            settings_storage: WebUI 设置存储实例，用于读取市场地址。
        """
        self._settings_storage = settings_storage
        self._cache: list[MarketPlugin] | None = None
        self._cache_at = 0.0
        self._cache_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        # 任务状态会由请求协程和后台任务跨异步上下文访问，使用同步锁保护短临界区。
        self._operation_state_lock = Lock()
        self._operations: dict[str, MarketOperation] = {}

    async def _get_market_settings(self):
        """读取当前 WebUI 设置中的插件市场子配置。"""
        return (await self._settings_storage.get_settings()).plugin_market

    async def capabilities(self) -> MarketCapabilities:
        """返回当前设置允许前端使用的市场能力。

        Returns:
            市场安装和进度传输能力开关。
        """
        return MarketCapabilities(
            install_enabled=True,
            supports_streaming_progress=False,
        )

    async def list_plugins(self, *, refresh: bool = False) -> MarketPluginList:
        """读取全部市场插件并合并本地安装状态。

        Args:
            refresh: 是否跳过短期列表缓存并重新读取上游市场。

        Returns:
            带本地安装、加载、配置和更新状态的插件列表。

        Raises:
            PluginMarketError: 上游市场数据无法安全读取。
        """
        market_plugins = await self._get_market_plugins(refresh=refresh)
        local_records = await self._load_local_plugins()
        dependents = self._build_dependents(local_records)
        plugins = [
            plugin.model_copy(
                update={
                    "local_state": self._local_state(
                        plugin.plugin_id,
                        plugin.latest_version,
                        local_records,
                        dependents,
                    )
                }
            )
            for plugin in market_plugins
        ]
        return MarketPluginList(
            plugins=plugins,
            total=len(plugins),
            refreshed_at=self._now(),
        )

    async def get_plugin_detail(self, plugin_id: str) -> MarketPluginDetail:
        """读取插件详情、版本、依赖和本地状态。

        Args:
            plugin_id: 市场插件唯一标识。

        Returns:
            包含兼容性、依赖满足情况和推荐版本的插件详情。

        Raises:
            PluginMarketError: 插件标识无效、市场记录不存在或响应无效。
        """
        self._validate_plugin_id(plugin_id)
        plugin_payload, versions_payload, dependencies_payload = await asyncio.gather(
            self._get_json(f"/api/v1/plugins/{plugin_id}"),
            self._get_json(f"/api/v1/plugins/{plugin_id}/versions"),
            self._get_json(f"/api/v1/plugins/{plugin_id}/dependencies"),
        )
        plugin = MarketPlugin.model_validate(plugin_payload)
        versions = UpstreamVersionList.model_validate(versions_payload).items
        dependencies = UpstreamDependencyList.model_validate(dependencies_payload).items
        local_records = await self._load_local_plugins()
        dependents = self._build_dependents(local_records)
        local_state = self._local_state(
            plugin_id,
            plugin.latest_version,
            local_records,
            dependents,
        )
        plugin = plugin.model_copy(update={"local_state": local_state})
        checked_versions = [self._with_compatibility(item) for item in versions]
        checked_dependencies = self._with_dependency_state(dependencies, local_records)
        recommended = next(
            (
                item
                for item in checked_versions
                if item.status == "published"
                and not item.is_yanked
                and not item.is_prerelease
                and item.compatibility.status == "compatible"
            ),
            None,
        )
        return MarketPluginDetail(
            plugin=plugin,
            versions=checked_versions,
            dependencies=checked_dependencies,
            recommended_version=recommended,
        )

    async def get_plugin_readme(self, plugin_id: str) -> MarketPluginReadme:
        """读取市场为插件详情页渲染的 README 文档。

        Args:
            plugin_id: 市场插件唯一标识。

        Returns:
            README 是否存在及其渲染后 HTML。

        Raises:
            PluginMarketError: 插件标识无效或市场响应无法安全读取。
        """
        self._validate_plugin_id(plugin_id)
        payload = await self._get_json(f"/api/v1/plugins/{plugin_id}/readme")
        return MarketPluginReadme.model_validate(payload)

    async def create_install_plan(
        self,
        plugin_id: str,
        version: str | None,
    ) -> InstallPlan:
        """生成安装或更新前必须展示的真实计划。

        Args:
            plugin_id: 待安装或更新的插件唯一标识。
            version: 指定版本；为 ``None`` 时选择推荐版本。

        Returns:
            包含动作、依赖、阻塞原因和风险提示的安装计划。

        Raises:
            PluginMarketError: 插件或指定版本不存在，或上游响应无效。
        """
        detail = await self.get_plugin_detail(plugin_id)
        selected = await self._select_version(detail, version)
        action = "update" if detail.plugin.local_state.installed else "install"
        blocking: list[str] = []
        warnings: list[str] = []

        if selected.status != "published" or selected.is_yanked:
            blocking.append("所选版本已撤回或未发布")
        if selected.compatibility.status == "incompatible":
            blocking.extend(selected.compatibility.reasons or [selected.compatibility.summary])
        elif selected.compatibility.status == "unknown":
            warnings.append(selected.compatibility.summary)
        if not selected.asset_download_url or not selected.checksum_sha256:
            blocking.append("市场未提供完整的下载地址和 SHA-256")

        local = detail.plugin.local_state
        if local.installed and not local.can_uninstall:
            blocking.append(local.uninstall_reason or "当前安装来源不能由市场安全覆盖")
        if local.installed and local.installed_version == selected.version:
            blocking.append("本地已安装该版本")

        unsatisfied = [item.plugin_id for item in detail.dependencies if not item.satisfied]
        if unsatisfied:
            blocking.append("缺少依赖插件: " + ", ".join(unsatisfied))
        if detail.plugin.risk_notice:
            warnings.append(detail.plugin.risk_notice)
        if detail.plugin.trust_level == "community":
            warnings.append("这是社区插件，安装前请确认作者和代码仓库来源")

        return InstallPlan(
            plugin=detail.plugin,
            version=selected,
            dependencies=detail.dependencies,
            action=action,
            can_install=not blocking,
            blocking_reasons=blocking,
            warnings=warnings,
        )

    async def start_install(
        self,
        plugin_id: str,
        version: str | None,
    ) -> MarketOperation:
        """创建受任务管理器追踪的安装或更新任务。

        Args:
            plugin_id: 待安装或更新的插件唯一标识。
            version: 指定版本；为 ``None`` 时选择推荐版本。

        Returns:
            可由前端轮询的排队中操作状态。

        Raises:
            PluginMarketError: 计划被阻止或存在活动任务。
        """
        plan = await self.create_install_plan(plugin_id, version)
        if not plan.can_install:
            raise PluginMarketError("；".join(plan.blocking_reasons))
        self._ensure_no_active_operation(plugin_id)

        operation = self._new_operation(plugin_id, "install", "等待安装", "任务已进入队列")
        get_task_manager().create_task(
            self._run_install(operation.operation_id, plan),
            name=f"plugin-market-install-{plugin_id}",
            timeout=float(_REQUEST_TIMEOUT_SECONDS) + 180.0,
            metadata={"plugin_id": plugin_id, "operation_id": operation.operation_id},
        )
        return operation

    def get_operation(self, operation_id: str) -> MarketOperation:
        """读取可轮询的操作状态快照。

        Args:
            operation_id: 创建写操作时返回的唯一标识。

        Returns:
            与内部状态隔离的操作深拷贝。

        Raises:
            PluginMarketError: 操作记录不存在或已被清理。
        """
        with self._operation_state_lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                raise PluginMarketError("操作记录不存在或已过期")
            return operation.model_copy(deep=True)

    async def _run_install(self, operation_id: str, plan: InstallPlan) -> None:
        """串行执行下载、校验、原子写入和热加载，并持续更新操作状态。"""
        async with self._operation_lock:
            try:
                self._update_operation(
                    operation_id,
                    status="running",
                    stage="downloading",
                    progress=5,
                    message="正在下载插件包",
                )
                destination = await self._download_and_store(
                    operation_id,
                    plan.plugin.plugin_id,
                    plan.version,
                    plan.plugin.local_state.plugin_path,
                )
                self._cache = None
                self._update_operation(
                    operation_id,
                    stage="loading",
                    progress=92,
                    message="正在热加载插件",
                )
                loaded, load_message = await self._hot_load_plugin(
                    plan.plugin.plugin_id,
                    str(destination),
                    plan.plugin.local_state.loaded,
                )
                if loaded:
                    message = "插件已安装并加载完成"
                    restart_required = False
                else:
                    message = (
                        f"插件包已写入，热加载失败：{load_message}，请重启 Neo-MoFox 后生效"
                    )
                    restart_required = True
                self._update_operation(
                    operation_id,
                    status="succeeded",
                    stage="completed",
                    progress=100,
                    message=message,
                    result=MarketOperationResult(
                        plugin_id=plan.plugin.plugin_id,
                        version=plan.version.version,
                        restart_required=restart_required,
                    ),
                )
                logger.warning(
                    f"市场插件已写入: plugin={plan.plugin.plugin_id}, "
                    f"version={plan.version.version}, path={destination}, "
                    f"hot_loaded={loaded}"
                )
            except Exception as error:
                logger.error(f"市场安装失败: {error}", exc_info=True)
                self._fail_operation(operation_id, error)

    async def _hot_load_plugin(
        self,
        plugin_id: str,
        plugin_path: str,
        was_loaded: bool,
    ) -> tuple[bool, str]:
        """下载写入完成后尝试热加载或重载插件，避免必须重启。

        Args:
            plugin_id: 插件唯一标识。
            plugin_path: 已写入的插件包绝对路径。
            was_loaded: 安装前插件是否处于已加载状态。

        Returns:
            (是否成功热加载, 失败时的说明)。
        """
        try:
            if was_loaded:
                success = await reload_plugin(plugin_id)
                action = "reload"
            else:
                success = await load_plugin(plugin_path)
                action = "load"
            if not success:
                return False, f"{action} 操作返回失败"
            return True, ""
        except Exception as error:
            logger.warning(
                f"热加载插件失败，仍需重启生效: plugin={plugin_id}, error={error}",
                exc_info=True,
            )
            return False, str(error)

    async def _get_market_plugins(self, *, refresh: bool) -> list[MarketPlugin]:
        """按配置的有效期读取或刷新完整市场列表缓存。"""
        cache_seconds = max(0, _CACHE_SECONDS)
        if (
            not refresh
            and self._cache is not None
            and time.monotonic() - self._cache_at < cache_seconds
        ):
            return list(self._cache)
        async with self._cache_lock:
            if (
                not refresh
                and self._cache is not None
                and time.monotonic() - self._cache_at < cache_seconds
            ):
                return list(self._cache)
            plugins = await self._fetch_all_plugins()
            self._cache = plugins
            self._cache_at = time.monotonic()
            return list(plugins)

    async def _fetch_all_plugins(self) -> list[MarketPlugin]:
        """分页读取上游市场，并按插件标识去重。"""
        page_size = _PAGE_SIZE
        offset = 0
        total: int | None = None
        plugins: list[MarketPlugin] = []
        seen: set[str] = set()
        while total is None or offset < total:
            payload = await self._get_json(
                "/api/v1/plugins",
                query={"limit": str(page_size), "offset": str(offset)},
            )
            page = UpstreamPluginList.model_validate(payload)
            if total is None:
                total = page.total
            if not page.items:
                break
            added = 0
            for plugin in page.items:
                if plugin.plugin_id in seen:
                    continue
                seen.add(plugin.plugin_id)
                plugins.append(plugin)
                added += 1
            if added == 0:
                break
            offset += len(page.items)
        return plugins

    async def _select_version(
        self,
        detail: MarketPluginDetail,
        requested_version: str | None,
    ) -> MarketVersion:
        """选择显式版本、详情推荐版本或上游推荐安装版本。"""
        if requested_version:
            selected = next(
                (item for item in detail.versions if item.version == requested_version),
                None,
            )
            if selected is None:
                raise PluginMarketError(f"市场中不存在版本 {requested_version}")
            return selected
        if detail.recommended_version is not None:
            return detail.recommended_version

        payload = await self._get_json(
            f"/api/v1/plugins/{detail.plugin.plugin_id}/install",
        )
        install_info = UpstreamInstallInfo.model_validate(payload)
        return self._with_compatibility(install_info.version)

    async def _load_local_plugins(self) -> dict[str, LocalPluginRecord]:
        """通过主程序加载器发现本地插件并补全当前运行态记录。"""
        root = self._plugins_root()
        loader = PluginLoader()
        records: dict[str, LocalPluginRecord] = {}
        loaded = set(list_loaded_plugins())
        discovered = await loader.discover_plugins(str(root))
        for plugin_path in discovered:
            manifest = await load_manifest(plugin_path)
            if manifest is None:
                continue
            path = Path(plugin_path).resolve()
            records[manifest.name] = LocalPluginRecord(
                manifest=manifest,
                path=path,
                loaded=manifest.name in loaded,
                has_config=get_config(manifest.name) is not None if manifest.name in loaded else False,
            )
        for plugin_id in loaded:
            if plugin_id in records:
                continue
            manifest = get_manifest(plugin_id)
            plugin_path = get_plugin_path(plugin_id)
            if manifest is not None and plugin_path:
                records[plugin_id] = LocalPluginRecord(
                    manifest=manifest,
                    path=Path(plugin_path).resolve(),
                    loaded=True,
                    has_config=get_config(plugin_id) is not None,
                )
        return records

    def _local_state(
        self,
        plugin_id: str,
        latest_version: str | None,
        records: dict[str, LocalPluginRecord],
        dependents: dict[str, list[str]],
    ) -> MarketLocalState:
        """根据本地清单、加载状态和依赖方生成市场展示状态。"""
        record = records.get(plugin_id)
        if record is None:
            return MarketLocalState()
        dependent_plugins = dependents.get(plugin_id, [])
        can_uninstall, reason = self._can_manage_local(plugin_id, record, dependent_plugins)
        return MarketLocalState(
            installed=True,
            loaded=record.loaded,
            installed_version=record.manifest.version,
            plugin_path=str(record.path),
            has_config=record.has_config,
            update_available=self._is_newer(latest_version, record.manifest.version),
            can_uninstall=can_uninstall,
            uninstall_reason=reason,
            dependent_plugins=dependent_plugins,
        )

    def _can_manage_local(
        self,
        plugin_id: str,
        record: LocalPluginRecord,
        dependents: list[str],
    ) -> tuple[bool, str | None]:
        """判断本地插件是否满足市场覆盖白名单。"""
        if plugin_id == "neo-mofox-webui":
            return False, "WebUI 插件不能从其自身市场中覆盖"
        root = self._plugins_root()
        if record.path.parent != root:
            return False, "插件路径不在配置的插件目录根级"
        if record.path.is_dir():
            return False, "目录版插件必须由管理员手动管理"
        if record.path.suffix.lower() not in {".mfp", ".zip"}:
            return False, "仅支持管理插件目录根级的 .mfp 或 .zip 包"
        if dependents:
            return False, "存在已安装的依赖方: " + ", ".join(dependents)
        return True, None

    def _build_dependents(
        self,
        records: dict[str, LocalPluginRecord],
    ) -> dict[str, list[str]]:
        """从本地清单反向构建插件依赖方索引。"""
        result: dict[str, list[str]] = {}
        for plugin_id, record in records.items():
            for dependency in record.manifest.dependencies.get("plugins", []):
                dependency_id, _ = self._split_dependency(dependency)
                if dependency_id:
                    result.setdefault(dependency_id, []).append(plugin_id)
        return {key: sorted(set(value)) for key, value in result.items()}

    def _with_dependency_state(
        self,
        dependencies: list[MarketDependency],
        records: dict[str, LocalPluginRecord],
    ) -> list[MarketDependency]:
        """将本机安装版本和约束满足情况合并到市场依赖。"""
        result: list[MarketDependency] = []
        for dependency in dependencies:
            record = records.get(dependency.plugin_id)
            constraint = dependency.version_constraint or dependency.required_version
            satisfied = bool(
                record
                and self._version_satisfies(record.manifest.version, constraint)
            )
            result.append(
                dependency.model_copy(
                    update={
                        "installed": record is not None,
                        "installed_version": record.manifest.version if record else None,
                        "satisfied": satisfied,
                    }
                )
            )
        return result

    def _with_compatibility(self, version: MarketVersion) -> MarketVersion:
        """根据宿主版本和当前平台计算插件版本兼容性。"""
        reasons: list[str] = []
        unknown: list[str] = []
        try:
            host = Version(CORE_VERSION)
            if version.min_host_version and host < Version(version.min_host_version):
                reasons.append(f"需要 Neo-MoFox >= {version.min_host_version}")
            if version.max_host_version and host > Version(version.max_host_version):
                reasons.append(f"仅支持 Neo-MoFox <= {version.max_host_version}")
        except InvalidVersion:
            unknown.append("宿主版本约束格式无效")

        platforms = {item.lower() for item in version.supported_platforms}
        current_platform = self._platform_names()
        if platforms and "all" not in platforms and not platforms.intersection(current_platform):
            reasons.append("当前操作系统不在支持平台列表中")
        if not version.min_host_version and not version.max_host_version:
            unknown.append("未声明宿主版本范围")
        if not version.plugin_api_version:
            unknown.append("未声明插件 API 版本")

        if reasons:
            compatibility = CompatibilityInfo(
                status="incompatible",
                summary="与当前 Neo-MoFox 不兼容",
                reasons=reasons,
            )
        elif unknown:
            compatibility = CompatibilityInfo(
                status="unknown",
                summary="；".join(unknown),
                reasons=unknown,
            )
        else:
            compatibility = CompatibilityInfo(
                status="compatible",
                summary="兼容当前版本",
            )
        return version.model_copy(update={"compatibility": compatibility})

    async def _download_and_store(
        self,
        operation_id: str,
        plugin_id: str,
        version: MarketVersion,
        existing_plugin_path: str | None,
    ) -> Path:
        """下载并验证插件包，然后原子写入插件目录。

        Args:
            operation_id: 用于报告下载和校验进度的操作标识。
            plugin_id: 期望写入的插件唯一标识。
            version: 包含下载地址、大小和哈希的市场版本记录。
            existing_plugin_path: 更新时允许被替换的现有插件包路径。

        Returns:
            原子写入后的插件包绝对路径。

        Raises:
            PluginMarketError: 下载、哈希、包结构、清单或目标路径校验失败。
        """
        self._validate_plugin_id(plugin_id)
        package_url = version.asset_download_url.lower().split("?", 1)[0]
        if not package_url.endswith((".mfp", ".zip")):
            raise PluginMarketError("安装器只接受 .mfp 或 .zip 插件包")
        root = self._plugins_root()
        root.mkdir(parents=True, exist_ok=True)
        max_bytes = _MAX_PACKAGE_SIZE_MB * 1024 * 1024
        temporary = await self._download_file(
            version.asset_download_url,
            root,
            max_bytes,
            version.file_size,
            version.checksum_sha256,
            lambda progress: self._update_operation(
                operation_id,
                progress=min(60, 5 + int(progress * 0.55)),
            ),
        )
        try:
            self._update_operation(
                operation_id,
                stage="validating",
                progress=65,
                message="正在校验插件结构与清单",
            )
            manifest = await asyncio.to_thread(self._validate_package, temporary, max_bytes)
            if str(manifest.get("name") or "") != plugin_id:
                raise PluginMarketError("安装包插件 ID 与市场记录不一致")
            if str(manifest.get("version") or "") != version.version:
                raise PluginMarketError("安装包版本与市场记录不一致")

            existing_path = Path(existing_plugin_path).resolve() if existing_plugin_path else None
            if existing_path is not None and (
                existing_path.parent != root
                or existing_path.suffix.lower() not in {".mfp", ".zip"}
                or not existing_path.is_file()
            ):
                raise PluginMarketError("现有插件路径未通过更新白名单校验")

            self._update_operation(
                operation_id,
                stage="storing",
                progress=85,
                message="正在原子写入插件目录",
            )
            destination = (root / f"{plugin_id}.mfp").resolve()
            if destination.parent != root:
                raise PluginMarketError("插件安装路径无效")
            os.replace(temporary, destination)
            if existing_path is not None and existing_path != destination:
                existing_path.unlink(missing_ok=True)
            return destination
        finally:
            temporary.unlink(missing_ok=True)

    async def _download_file(
        self,
        url: str,
        target_dir: Path,
        max_bytes: int,
        expected_size: int | None,
        expected_sha256: str,
        progress_callback: Callable[[int], None],
    ) -> Path:
        """受大小限制地下载原始字节，同时校验长度和 SHA-256。

        Args:
            url: 经过逐跳安全校验的插件包 HTTPS 地址。
            target_dir: 临时文件所在目录。
            max_bytes: 允许读取的最大字节数。
            expected_size: 市场声明的精确大小，可为 ``None``。
            expected_sha256: 市场声明的 SHA-256 十六进制摘要。
            progress_callback: 接收下载百分比的同步回调。

        Returns:
            校验成功的临时文件路径。

        Raises:
            PluginMarketError: 地址、体积、长度或哈希校验失败。
        """
        if len(expected_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in expected_sha256.lower()
        ):
            raise PluginMarketError("市场提供的 SHA-256 无效")
        async with self._open_url(url, max_bytes) as response:
            temporary_handle = tempfile.NamedTemporaryFile(
                prefix=".plugin-market-",
                suffix=".download",
                dir=target_dir,
                delete=False,
            )
            temporary = Path(temporary_handle.name)
            digest = hashlib.sha256()
            total = 0
            try:
                with temporary_handle:
                    length = response.content_length
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        total += len(chunk)
                        if total > max_bytes:
                            raise PluginMarketError("插件包超过配置的大小限制")
                        digest.update(chunk)
                        temporary_handle.write(chunk)
                        denominator = expected_size or length or max_bytes
                        progress_callback(min(100, int(total * 100 / max(denominator, 1))))
                if expected_size is not None and total != expected_size:
                    raise PluginMarketError("插件包大小与市场记录不一致")
                if digest.hexdigest() != expected_sha256.lower():
                    raise PluginMarketError("插件包 SHA-256 校验失败")
                return temporary
            except Exception:
                temporary.unlink(missing_ok=True)
                raise

    @staticmethod
    def _validate_package(path: Path, max_uncompressed_bytes: int) -> dict[str, Any]:
        """验证 ZIP 安全边界、唯一清单和入口文件后返回清单对象。

        Args:
            path: 已通过下载哈希校验的插件包路径。
            max_uncompressed_bytes: 允许的 ZIP 条目累计解压大小。

        Returns:
            从唯一根级或一级 ``manifest.json`` 读取的清单对象。

        Raises:
            PluginMarketError: 压缩包路径、符号链接、体积、清单或入口校验失败。
        """
        try:
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if not entries:
                    raise PluginMarketError("插件压缩包为空")
                total = 0
                manifest_paths: list[str] = []
                normalized_names: set[str] = set()
                for entry in entries:
                    # 只检查包结构，不解压文件；路径、符号链接和累计体积均在写入前拒绝。
                    normalized = entry.filename.replace("\\", "/").rstrip("/")
                    entry_path = Path(normalized)
                    if entry_path.is_absolute() or ".." in entry_path.parts:
                        raise PluginMarketError("插件压缩包包含非法路径")
                    if not normalized:
                        continue
                    normalized_names.add(normalized)
                    if not entry.is_dir():
                        total += entry.file_size
                        if total > max_uncompressed_bytes:
                            raise PluginMarketError("插件包解压后超过大小限制")
                        mode = entry.external_attr >> 16
                        if mode and (mode & 0o170000) == 0o120000:
                            raise PluginMarketError("插件压缩包不能包含符号链接")
                        if normalized.endswith("manifest.json") and len(entry_path.parts) <= 2:
                            manifest_paths.append(normalized)
                if len(manifest_paths) != 1:
                    raise PluginMarketError("插件包必须包含唯一的根级或一级 manifest.json")
                manifest = json.loads(archive.read(manifest_paths[0]).decode("utf-8"))
                if not isinstance(manifest, dict):
                    raise PluginMarketError("manifest.json 必须是 JSON 对象")
                entry_point = str(manifest.get("entry_point") or "plugin.py")
                parent = manifest_paths[0].rsplit("/", 1)[0] if "/" in manifest_paths[0] else ""
                entry_path = f"{parent}/{entry_point}".lstrip("/")
                if entry_path not in normalized_names:
                    raise PluginMarketError("插件入口文件不存在")
                return manifest
        except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PluginMarketError(f"插件包格式无效: {error}") from error

    async def _get_json(
        self,
        path: str,
        query: dict[str, str] | None = None,
    ) -> Any:
        """从市场 API 读取受大小限制的 UTF-8 JSON。

        Args:
            path: 相对于市场基础地址的 API 路径。
            query: 可选查询参数。

        Returns:
            解析后的 JSON 值，由调用方使用 Pydantic 模型校验。

        Raises:
            PluginMarketError: 网络、安全、大小、编码或 JSON 解析失败。
        """
        base = (await self._get_market_settings()).base_url.rstrip("/")
        url = f"{base}/{path.lstrip('/')}"
        try:
            async with self._open_url(url, _JSON_LIMIT_BYTES, query=query) as response:
                data = await self._read_limited(
                    response,
                    _JSON_LIMIT_BYTES,
                    "市场响应超过允许大小",
                )
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PluginMarketError(f"市场返回的 JSON 无效: {error}") from error

    @asynccontextmanager
    async def _open_url(
        self,
        url: str,
        max_bytes: int,
        *,
        query: dict[str, str] | None = None,
    ) -> AsyncIterator[aiohttp.ClientResponse]:
        """打开经过逐跳公网 HTTPS 校验且响应体受限的请求。

        Args:
            url: 初始请求地址。
            max_bytes: ``Content-Length`` 和后续读取允许的最大字节数。
            query: 仅附加到初始请求地址的查询参数。

        Yields:
            状态码成功且通过响应头大小检查的 aiohttp 响应。

        Raises:
            PluginMarketError: URL、DNS、重定向、状态码、大小或网络请求无效。
        """
        timeout = aiohttp.ClientTimeout(
            total=float(_REQUEST_TIMEOUT_SECONDS)
        )
        try:
            current_url = URL(url)
            if query is not None:
                current_url = current_url.with_query(query)
        except ValueError as error:
            raise PluginMarketError("市场地址格式无效") from error
        try:
            # 禁止透明解压，确保大小限制和下载哈希基于服务器返回的原始字节。
            async with aiohttp.ClientSession(
                timeout=timeout,
                trust_env=_TRUST_ENV,
                auto_decompress=False,
                headers={
                    "Accept-Encoding": "identity",
                    "User-Agent": "Neo-MoFox-WebUI-Plugin-Market/1.0.18-dev",
                },
            ) as session:
                for redirect_count in range(_MAX_REDIRECTS + 1):
                    # 每次重定向后重新解析 DNS，避免跳转到本机、局域网或保留网络。
                    await asyncio.to_thread(self._validate_remote_url, str(current_url))
                    response = await session.get(current_url, allow_redirects=False)
                    if response.status in _REDIRECT_STATUSES:
                        location = response.headers.get("Location")
                        response.release()
                        if not location:
                            raise PluginMarketError(
                                f"市场请求失败（HTTP {response.status}，缺少重定向地址）"
                            )
                        if redirect_count >= _MAX_REDIRECTS:
                            raise PluginMarketError("市场请求重定向次数过多")
                        try:
                            current_url = response.url.join(URL(location))
                        except ValueError as error:
                            raise PluginMarketError("市场返回了无效的重定向地址") from error
                        continue
                    if response.status == 404:
                        response.release()
                        raise PluginMarketError("市场中未找到请求的插件或版本")
                    if not 200 <= response.status < 300:
                        status = response.status
                        response.release()
                        raise PluginMarketError(f"市场请求失败（HTTP {status}）")
                    length = response.content_length
                    if length is not None and length > max_bytes:
                        response.release()
                        raise PluginMarketError("远程响应超过允许大小")
                    try:
                        yield response
                    finally:
                        response.release()
                    return
        except PluginMarketError:
            raise
        except asyncio.TimeoutError as error:
            raise PluginMarketError("无法访问插件市场: 请求超时") from error
        except aiohttp.ClientError as error:
            raise PluginMarketError(f"无法访问插件市场: {error}") from error

    @staticmethod
    async def _read_limited(
        response: aiohttp.ClientResponse,
        max_bytes: int,
        error_message: str,
    ) -> bytes:
        """分块读取响应，并在超过限制时立即终止。"""
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.content.iter_chunked(64 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise PluginMarketError(error_message)
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _validate_remote_url(url: str) -> None:
        """要求 URL 使用 HTTPS，且所有 DNS 结果均为公网地址。"""
        try:
            parsed = URL(url)
            hostname = parsed.host
            port = parsed.port or 443
        except ValueError as error:
            raise PluginMarketError("市场地址格式无效") from error
        if parsed.scheme.lower() != "https" or not hostname:
            raise PluginMarketError("市场只允许访问 HTTPS 公网地址")
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(
                    hostname,
                    port,
                    type=socket.SOCK_STREAM,
                )
            }
        except OSError as error:
            raise PluginMarketError(f"无法解析市场地址: {error}") from error
        if not addresses:
            raise PluginMarketError("市场地址未解析到有效 IP")
        for address in addresses:
            try:
                if not ipaddress.ip_address(address).is_global:
                    raise PluginMarketError("市场地址不能指向本机、局域网或保留网络")
            except ValueError as error:
                raise PluginMarketError("市场地址解析结果无效") from error

    def _new_operation(
        self,
        plugin_id: str,
        kind: OperationKind,
        stage: str,
        message: str,
    ) -> MarketOperation:
        """创建操作状态，并限制内存中保留的已完成记录数量。"""
        now = self._now()
        operation = MarketOperation(
            operation_id=str(uuid4()),
            plugin_id=plugin_id,
            kind=kind,
            status="queued",
            stage=stage,
            progress=0,
            message=message,
            created_at=now,
            updated_at=now,
        )
        with self._operation_state_lock:
            self._operations[operation.operation_id] = operation
            if len(self._operations) > 100:
                finished = [
                    key
                    for key, value in self._operations.items()
                    if value.status in {"succeeded", "failed"}
                ]
                for key in finished[: len(self._operations) - 100]:
                    self._operations.pop(key, None)
        return operation.model_copy(deep=True)

    def _update_operation(self, operation_id: str, **updates: Any) -> None:
        """原子更新操作状态并刷新更新时间。"""
        with self._operation_state_lock:
            current = self._operations[operation_id]
            updates["updated_at"] = self._now()
            self._operations[operation_id] = current.model_copy(update=updates)

    def _fail_operation(self, operation_id: str, error: Exception) -> None:
        """将后台任务异常转换为前端可轮询的失败状态。"""
        self._update_operation(
            operation_id,
            status="failed",
            stage="failed",
            message="操作失败",
            error_message=str(error),
        )

    def _ensure_no_active_operation(self, plugin_id: str) -> None:
        """拒绝为同一插件并发创建多个写操作。"""
        with self._operation_state_lock:
            if any(
                item.plugin_id == plugin_id and item.status in {"queued", "running"}
                for item in self._operations.values()
            ):
                raise PluginMarketError(f"插件 {plugin_id} 已有操作正在执行")

    def _plugins_root(self) -> Path:
        """返回主程序配置的插件目录规范化绝对路径。"""
        return Path(get_core_config().bot.plugins_dir).resolve()

    @staticmethod
    def _split_dependency(value: str) -> tuple[str, str | None]:
        """将清单依赖拆分为插件标识和可选版本约束。"""
        raw = str(value or "").strip()
        name, separator, remainder = raw.partition(":")
        if separator and remainder.lstrip().startswith(("===", "==", "!=", "~=", ">=", "<=", ">", "<")):
            return name.strip(), remainder.strip() or None
        match = _DEPENDENCY_PATTERN.match(raw)
        if match:
            return match.group("name"), (match.group("spec") or "").strip() or None
        return raw, None

    @staticmethod
    def _version_satisfies(version: str, constraint: str | None) -> bool:
        """判断版本是否满足 PEP 440 约束；无效输入按不满足处理。"""
        if not constraint:
            return True
        from packaging.specifiers import InvalidSpecifier, SpecifierSet

        try:
            return Version(version) in SpecifierSet(constraint)
        except (InvalidSpecifier, InvalidVersion):
            return False

    @staticmethod
    def _is_newer(candidate: str | None, installed: str) -> bool:
        """判断候选市场版本是否高于本机版本。"""
        if not candidate:
            return False
        try:
            return Version(candidate) > Version(installed)
        except InvalidVersion:
            return candidate != installed

    @staticmethod
    def _platform_names() -> set[str]:
        """返回当前平台及市场常用别名。"""
        names = {sys.platform.lower()}
        if sys.platform.startswith("win"):
            names.update({"windows", "win", "win32"})
        elif sys.platform.startswith("linux"):
            names.update({"linux", "linux2"})
        elif sys.platform == "darwin":
            names.update({"macos", "mac", "darwin"})
        return names

    @staticmethod
    def _validate_plugin_id(plugin_id: str) -> None:
        """拒绝不符合市场路径安全字符集的插件标识。"""
        if not _PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            raise PluginMarketError(f"插件 ID 格式无效: {plugin_id}")

    @staticmethod
    def _now() -> str:
        """返回秒级 UTC ISO 8601 时间。"""
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


_plugin_market_manager: PluginMarketManager | None = None


def get_plugin_market_manager(settings_storage: SettingsStorage) -> PluginMarketManager:
    """获取使用 WebUI 设置存储的市场 Manager 单例。

    Args:
        settings_storage: WebUI 设置存储实例，用于读取市场地址。

    Returns:
        与设置存储绑定的进程内 Manager；存储实例变化时重新创建。
    """
    global _plugin_market_manager
    if _plugin_market_manager is None or _plugin_market_manager._settings_storage is not settings_storage:
        _plugin_market_manager = PluginMarketManager(settings_storage)
    return _plugin_market_manager


__all__ = [
    "PluginMarketError",
    "PluginMarketManager",
    "get_plugin_market_manager",
]
