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
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from packaging.version import InvalidVersion, Version

from src.app.plugin_system.api.config_api import get_config
from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.plugin_api import (
    get_manifest,
    get_plugin_path,
    is_plugin_loaded,
    list_loaded_plugins,
    unload_plugin,
)
from src.core.components.loader import PluginLoader, PluginManifest, load_manifest
from src.core.config import CORE_VERSION
from src.core.config.core_config import get_core_config
from src.kernel.concurrency import get_task_manager

from ..plugin_market_config import WebUIConfig
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
_RATE_WINDOW_SECONDS = 600.0
_JSON_LIMIT_BYTES = 8 * 1024 * 1024


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
    """聚合市场索引、本地状态和插件包写操作。"""

    def __init__(self, config: WebUIConfig) -> None:
        self._config = config
        self._cache: list[MarketPlugin] | None = None
        self._cache_at = 0.0
        self._cache_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        self._operation_state_lock = Lock()
        self._operations: dict[str, MarketOperation] = {}
        self._install_attempts: deque[float] = deque()

    def capabilities(self) -> MarketCapabilities:
        """返回当前配置允许的市场能力。"""
        return MarketCapabilities(
            market_enabled=self._config.plugin_market.enabled,
            install_enabled=self._config.plugin_market_operations.install_enabled,
            uninstall_enabled=self._config.plugin_market_operations.uninstall_enabled,
            supports_streaming_progress=False,
        )

    async def list_plugins(self, *, refresh: bool = False) -> MarketPluginList:
        """读取全部市场插件并合并本地安装状态。"""
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
        """读取插件详情、版本、依赖和本地状态。"""
        self._validate_plugin_id(plugin_id)
        plugin_payload, versions_payload, dependencies_payload = await asyncio.gather(
            asyncio.to_thread(self._get_json, f"/api/v1/plugins/{self._quote(plugin_id)}"),
            asyncio.to_thread(
                self._get_json,
                f"/api/v1/plugins/{self._quote(plugin_id)}/versions",
            ),
            asyncio.to_thread(
                self._get_json,
                f"/api/v1/plugins/{self._quote(plugin_id)}/dependencies",
            ),
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

    async def create_install_plan(
        self,
        plugin_id: str,
        version: str | None,
    ) -> InstallPlan:
        """生成安装或更新前必须展示的真实计划。"""
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
        """创建受任务管理器追踪的安装或更新任务。"""
        if not self._config.plugin_market_operations.install_enabled:
            raise PluginMarketError("WebUI 插件市场安装功能已关闭")
        self._check_rate_limit()
        plan = await self.create_install_plan(plugin_id, version)
        if not plan.can_install:
            raise PluginMarketError("；".join(plan.blocking_reasons))
        self._ensure_no_active_operation(plugin_id)

        operation = self._new_operation(plugin_id, "install", "等待安装", "任务已进入队列")
        self._install_attempts.append(time.monotonic())
        get_task_manager().create_task(
            self._run_install(operation.operation_id, plan),
            name=f"plugin-market-install-{plugin_id}",
            timeout=float(self._config.plugin_market.request_timeout_seconds) + 180.0,
            metadata={"plugin_id": plugin_id, "operation_id": operation.operation_id},
        )
        return operation

    async def start_uninstall(self, plugin_id: str) -> MarketOperation:
        """创建受任务管理器追踪的卸载任务。"""
        if not self._config.plugin_market_operations.uninstall_enabled:
            raise PluginMarketError("WebUI 插件市场卸载功能已关闭")
        self._validate_plugin_id(plugin_id)
        records = await self._load_local_plugins()
        record = records.get(plugin_id)
        if record is None:
            raise PluginMarketError(f"插件 {plugin_id} 未安装")
        dependents = self._build_dependents(records).get(plugin_id, [])
        allowed, reason = self._can_manage_local(plugin_id, record, dependents)
        if not allowed:
            raise PluginMarketError(reason or "当前插件不能由市场卸载")
        self._ensure_no_active_operation(plugin_id)

        operation = self._new_operation(plugin_id, "uninstall", "等待卸载", "任务已进入队列")
        get_task_manager().create_task(
            self._run_uninstall(operation.operation_id, record),
            name=f"plugin-market-uninstall-{plugin_id}",
            timeout=120.0,
            metadata={"plugin_id": plugin_id, "operation_id": operation.operation_id},
        )
        return operation

    def get_operation(self, operation_id: str) -> MarketOperation:
        """读取可轮询的操作状态。"""
        with self._operation_state_lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                raise PluginMarketError("操作记录不存在或已过期")
            return operation.model_copy(deep=True)

    async def _run_install(self, operation_id: str, plan: InstallPlan) -> None:
        async with self._operation_lock:
            try:
                self._update_operation(
                    operation_id,
                    status="running",
                    stage="downloading",
                    progress=5,
                    message="正在下载插件包",
                )
                destination = await asyncio.to_thread(
                self._download_and_store,
                operation_id,
                plan.plugin.plugin_id,
                plan.version,
                plan.plugin.local_state.plugin_path,
                )
                self._cache = None
                self._update_operation(
                    operation_id,
                    status="succeeded",
                    stage="completed",
                    progress=100,
                    message="插件包已写入，请重启 Neo-MoFox 后生效",
                    result=MarketOperationResult(
                        plugin_id=plan.plugin.plugin_id,
                        version=plan.version.version,
                        restart_required=True,
                    ),
                )
                logger.warning(
                    f"市场插件已写入: plugin={plan.plugin.plugin_id}, "
                    f"version={plan.version.version}, path={destination}"
                )
            except Exception as error:
                logger.error(f"市场安装失败: {error}", exc_info=True)
                self._fail_operation(operation_id, error)

    async def _run_uninstall(
        self,
        operation_id: str,
        record: LocalPluginRecord,
    ) -> None:
        async with self._operation_lock:
            plugin_id = record.manifest.name
            try:
                self._update_operation(
                    operation_id,
                    status="running",
                    stage="unloading",
                    progress=20,
                    message="正在停止插件运行态",
                )
                if is_plugin_loaded(plugin_id) and not await unload_plugin(plugin_id):
                    raise PluginMarketError("核心运行时拒绝卸载该插件")
                self._update_operation(
                    operation_id,
                    stage="removing",
                    progress=70,
                    message="正在删除插件包",
                )
                await asyncio.to_thread(self._delete_archive, record.path)
                self._cache = None
                self._update_operation(
                    operation_id,
                    status="succeeded",
                    stage="completed",
                    progress=100,
                    message="插件已卸载",
                    result=MarketOperationResult(
                        plugin_id=plugin_id,
                        version=record.manifest.version,
                        restart_required=False,
                    ),
                )
                logger.warning(f"市场插件已卸载: plugin={plugin_id}, path={record.path}")
            except Exception as error:
                logger.error(f"市场卸载失败: {error}", exc_info=True)
                self._fail_operation(operation_id, error)

    async def _get_market_plugins(self, *, refresh: bool) -> list[MarketPlugin]:
        cache_seconds = max(0, self._config.plugin_market.cache_seconds)
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
            plugins = await asyncio.to_thread(self._fetch_all_plugins)
            self._cache = plugins
            self._cache_at = time.monotonic()
            return list(plugins)

    def _fetch_all_plugins(self) -> list[MarketPlugin]:
        page_size = self._config.plugin_market.page_size
        offset = 0
        total: int | None = None
        plugins: list[MarketPlugin] = []
        seen: set[str] = set()
        while total is None or offset < total:
            payload = self._get_json(
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

        payload = await asyncio.to_thread(
            self._get_json,
            f"/api/v1/plugins/{self._quote(detail.plugin.plugin_id)}/install",
        )
        install_info = UpstreamInstallInfo.model_validate(payload)
        return self._with_compatibility(install_info.version)

    async def _load_local_plugins(self) -> dict[str, LocalPluginRecord]:
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
        if plugin_id == "neo-mofox-webui":
            return False, "WebUI 插件不能从其自身市场中卸载或覆盖"
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
                summary=f"兼容 Neo-MoFox {CORE_VERSION}",
            )
        return version.model_copy(update={"compatibility": compatibility})

    def _download_and_store(
        self,
        operation_id: str,
        plugin_id: str,
        version: MarketVersion,
        existing_plugin_path: str | None,
    ) -> Path:
        self._validate_plugin_id(plugin_id)
        package_url = version.asset_download_url.lower().split("?", 1)[0]
        if not package_url.endswith((".mfp", ".zip")):
            raise PluginMarketError("安装器只接受 .mfp 或 .zip 插件包")
        root = self._plugins_root()
        root.mkdir(parents=True, exist_ok=True)
        max_bytes = self._config.plugin_market.max_package_size_mb * 1024 * 1024
        temporary = self._download_file(
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
            manifest = self._validate_package(temporary, max_bytes)
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

    def _download_file(
        self,
        url: str,
        target_dir: Path,
        max_bytes: int,
        expected_size: int | None,
        expected_sha256: str,
        progress_callback: Callable[[int], None],
    ) -> Path:
        if len(expected_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in expected_sha256.lower()
        ):
            raise PluginMarketError("市场提供的 SHA-256 无效")
        response = self._open_url(url, max_bytes)
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
            with response, temporary_handle:
                length = response.headers.get("Content-Length")
                if length and int(length) > max_bytes:
                    raise PluginMarketError("插件包超过配置的大小限制")
                while chunk := response.read(64 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise PluginMarketError("插件包超过配置的大小限制")
                    digest.update(chunk)
                    temporary_handle.write(chunk)
                    denominator = expected_size or (int(length) if length else max_bytes)
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
        try:
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if not entries:
                    raise PluginMarketError("插件压缩包为空")
                total = 0
                manifest_paths: list[str] = []
                normalized_names: set[str] = set()
                for entry in entries:
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

    def _get_json(
        self,
        path: str,
        query: dict[str, str] | None = None,
    ) -> Any:
        base = self._config.plugin_market.base_url.rstrip("/")
        url = f"{base}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        response = self._open_url(url, _JSON_LIMIT_BYTES)
        try:
            with response:
                data = response.read(_JSON_LIMIT_BYTES + 1)
            if len(data) > _JSON_LIMIT_BYTES:
                raise PluginMarketError("市场响应超过允许大小")
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PluginMarketError(f"市场返回的 JSON 无效: {error}") from error

    def _open_url(self, url: str, max_bytes: int) -> Any:
        self._validate_remote_url(url)
        handlers: list[Any] = [_SafeRedirectHandler(self._validate_remote_url)]
        if not self._config.plugin_market.trust_env:
            handlers.insert(0, urllib.request.ProxyHandler({}))
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Neo-MoFox-WebUI-Plugin-Market/1.0.18"},
        )
        try:
            response = urllib.request.build_opener(*handlers).open(
                request,
                timeout=self._config.plugin_market.request_timeout_seconds,
            )
            self._validate_remote_url(response.geturl())
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                response.close()
                raise PluginMarketError("远程响应超过允许大小")
            return response
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise PluginMarketError("市场中未找到请求的插件或版本") from error
            raise PluginMarketError(f"市场请求失败（HTTP {error.code}）") from error
        except urllib.error.URLError as error:
            raise PluginMarketError(f"无法访问插件市场: {error.reason}") from error

    @staticmethod
    def _validate_remote_url(url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise PluginMarketError("市场只允许访问 HTTPS 公网地址")
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(
                    parsed.hostname,
                    parsed.port or 443,
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
        with self._operation_state_lock:
            current = self._operations[operation_id]
            updates["updated_at"] = self._now()
            self._operations[operation_id] = current.model_copy(update=updates)

    def _fail_operation(self, operation_id: str, error: Exception) -> None:
        self._update_operation(
            operation_id,
            status="failed",
            stage="failed",
            message="操作失败",
            error_message=str(error),
        )

    def _ensure_no_active_operation(self, plugin_id: str) -> None:
        with self._operation_state_lock:
            if any(
                item.plugin_id == plugin_id and item.status in {"queued", "running"}
                for item in self._operations.values()
            ):
                raise PluginMarketError(f"插件 {plugin_id} 已有操作正在执行")

    def _check_rate_limit(self) -> None:
        now = time.monotonic()
        while self._install_attempts and now - self._install_attempts[0] >= _RATE_WINDOW_SECONDS:
            self._install_attempts.popleft()
        if (
            len(self._install_attempts)
            >= self._config.plugin_market_operations.max_installs_per_10_minutes
        ):
            raise PluginMarketError("安装操作过于频繁，请稍后再试")

    def _plugins_root(self) -> Path:
        return Path(get_core_config().bot.plugins_dir).resolve()

    def _delete_archive(self, path: Path) -> None:
        root = self._plugins_root()
        resolved = path.resolve()
        if resolved.parent != root or resolved.suffix.lower() not in {".mfp", ".zip"}:
            raise PluginMarketError("插件路径未通过删除白名单校验")
        if not resolved.is_file():
            raise PluginMarketError("插件包不存在或不是普通文件")
        resolved.unlink()

    @staticmethod
    def _split_dependency(value: str) -> tuple[str, str | None]:
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
        if not constraint:
            return True
        from packaging.specifiers import InvalidSpecifier, SpecifierSet

        try:
            return Version(version) in SpecifierSet(constraint)
        except (InvalidSpecifier, InvalidVersion):
            return False

    @staticmethod
    def _is_newer(candidate: str | None, installed: str) -> bool:
        if not candidate:
            return False
        try:
            return Version(candidate) > Version(installed)
        except InvalidVersion:
            return candidate != installed

    @staticmethod
    def _platform_names() -> set[str]:
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
        if not _PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            raise PluginMarketError(f"插件 ID 格式无效: {plugin_id}")

    @staticmethod
    def _quote(value: str) -> str:
        return urllib.parse.quote(value, safe="")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """在跟随每一次重定向前重新校验目标。"""

    def __init__(self, validator: Callable[[str], None]) -> None:
        super().__init__()
        self._validator = validator

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        self._validator(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_plugin_market_manager: PluginMarketManager | None = None


def get_plugin_market_manager(config: WebUIConfig) -> PluginMarketManager:
    """获取使用当前 WebUI 配置的市场 Manager 单例。"""
    global _plugin_market_manager
    if _plugin_market_manager is None or _plugin_market_manager._config is not config:
        _plugin_market_manager = PluginMarketManager(config)
    return _plugin_market_manager


__all__ = [
    "PluginMarketError",
    "PluginMarketManager",
    "get_plugin_market_manager",
]
