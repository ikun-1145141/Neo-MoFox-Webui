"""Local ZIP/MFP import: preview without execution, confirmed atomic commit, activation."""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from fastapi import UploadFile
from packaging.version import InvalidVersion, Version

from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.plugin_api import (
    get_manifest, get_plugin_path, list_loaded_plugins, list_unloaded_plugins,
    load_plugin, reload_plugin,
)
from src.core.components.loader import PluginLoader, PluginManifest, load_manifest
from src.core.components.registry import get_global_registry
from src.core.config.core_config import get_core_config
from src.kernel.concurrency import get_task_manager

from ..utils.plugin_import_types import (
    PluginImportCommit, PluginImportOperation, PluginImportPreview, PluginImportResult,
)
from ..utils.plugin_package import MAX_PACKAGE_BYTES, PackageError, atomic_store, validate_package
from ..utils.plugin_write_lock import plugin_write_lock

logger = get_logger("plugin_import_manager")
UPLOAD_TTL = 15 * 60
OPERATION_TTL = 24 * 60 * 60
MAX_PENDING_UPLOADS = 8
MAX_OPERATION_RECORDS = 256
_ID = re.compile(r"^[a-f0-9]{32}$")


def _iso(timestamp: float | None = None) -> str:
    return datetime.fromtimestamp(timestamp if timestamp is not None else time.time(), timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class PluginImportError(ValueError):
    """An expected import failure with a consistent HTTP/business status."""
    def __init__(self, message: str, code: int = 400) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class LocalRecord:
    manifest: PluginManifest
    path: Path


@dataclass
class StagedUpload:
    path: Path
    preview: PluginImportPreview
    manifest: PluginManifest
    destination: Path
    fingerprint: tuple[Any, ...]
    digest: str
    expires: float
    operation_id: str | None = None


class PluginImportManager:
    """Manage authenticated uploads; all official plugin changes use the shared lock."""

    def __init__(self, self_plugin_name: str = "neo-mofox-webui") -> None:
        self.self_plugin_name = self_plugin_name
        self.upload_dir = Path("data/json_storage/WebUI_data/plugin_imports").absolute()
        self._state_lock = RLock()
        self._uploads: dict[str, StagedUpload] = {}
        self._operations: dict[str, PluginImportOperation] = {}
        self._submitted: dict[str, str] = {}
        self._preparing = 0
        self._orphan_paths: set[Path] = set()
        self._initialized = False
        self._startup_cleaned = False
        self._cleanup_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Initialize scratch space and start expiry cleanup through the host task manager."""
        with self._state_lock:
            if self._initialized:
                return
            # Only remove our own random-named files. Never recursively delete a directory.
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            if self.upload_dir.is_symlink():
                raise PluginImportError("上传暂存目录不能是符号链接")
            if not self._startup_cleaned:
                for candidate in self.upload_dir.iterdir():
                    if candidate.suffix in {".mfp", ".part"} and _ID.fullmatch(candidate.stem):
                        candidate.unlink(missing_ok=True)
                self._startup_cleaned = True
            self._initialized = True
        coroutine = self._cleanup_loop()
        try:
            task_info = get_task_manager().create_task(coroutine, name="webui-plugin-import-cleanup", daemon=True)
            self._cleanup_task = task_info.task
        except BaseException:
            coroutine.close()
            self._initialized = False
            raise

    async def shutdown(self) -> None:
        """Stop idle-upload cleanup on router shutdown, without cancelling accepted installs."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        self._cleanup(expire_all_idle=True)
        # A router reload may reuse this manager. Its live operation state must survive.
        self._initialized = False

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            try:
                self._cleanup()
            except Exception:
                logger.error("清理过期插件上传失败", exc_info=True)

    def _cleanup(self, *, expire_all_idle: bool = False) -> None:
        now = time.time()
        with self._state_lock:
            for path in list(self._orphan_paths):
                self._remove_scratch(path)
            for upload_id, upload in list(self._uploads.items()):
                operation = self._operations.get(upload.operation_id or "")
                finished = operation is not None and operation.status in {"succeeded", "failed"}
                if finished or (upload.operation_id is None and (expire_all_idle or upload.expires <= now)):
                    self._discard(upload_id)
            for operation_id, operation in list(self._operations.items()):
                if operation.status in {"succeeded", "failed"} and (
                    now - datetime.fromisoformat(operation.updated_at).timestamp() > OPERATION_TTL
                ):
                    del self._operations[operation_id]
                    self._submitted = {key: value for key, value in self._submitted.items() if value != operation_id}

    def _remove_scratch(self, path: Path) -> None:
        """Retry Windows worker-held files during cleanup instead of masking the real result."""
        with self._state_lock:
            try:
                path.unlink(missing_ok=True)
                self._orphan_paths.discard(path)
            except OSError:
                self._orphan_paths.add(path)
                logger.warning(f"插件暂存文件仍被占用，将稍后清理: {path.name}")

    def _discard(self, upload_id: str) -> None:
        upload = self._uploads.get(upload_id)
        if upload is not None:
            try:
                upload.path.unlink(missing_ok=True)
            except OSError:
                logger.error(f"无法删除插件暂存包 {upload_id}", exc_info=True)
                return
            del self._uploads[upload_id]

    def _root(self) -> Path:
        return Path(get_core_config().bot.plugins_dir).resolve()

    async def _local_records(self) -> list[LocalRecord]:
        """Scan each source separately: a name-keyed dict would conceal duplicate packages."""
        records: list[LocalRecord] = []
        root = self._root()
        if root.exists():
            for candidate in sorted(root.iterdir()):
                if candidate.is_dir() or candidate.suffix in {".zip", ".mfp"}:
                    manifest = await load_manifest(str(candidate))
                    if manifest is not None:
                        records.append(LocalRecord(manifest, candidate.absolute()))
        for name in list_loaded_plugins():
            manifest, source = get_manifest(name), get_plugin_path(name)
            if manifest is not None and source:
                candidate = Path(source).absolute()
                if not any(record.path == candidate and record.manifest.name == name for record in records):
                    records.append(LocalRecord(manifest, candidate))
        return records

    def _compatibility(self, manifest: PluginManifest, records: list[LocalRecord]) -> tuple[list[str], list[str]]:
        """Use a private, isolated host loader for its version/dependency semantics only.

        The host exposes no public single-manifest planning API; keep this adapter
        isolated rather than reimplementing API-version AND/core-version rules.
        No load/import/dependency-install method is called here.
        """
        blocked: list[str] = []
        warnings: list[str] = []
        loader = PluginLoader()
        manifests = {record.manifest.name: record.manifest for record in records}
        before = loader._prune_unloadable_plugins(manifests)
        manifests[manifest.name] = manifest
        after = loader._prune_unloadable_plugins(manifests)
        if manifest.name not in after:
            blocked.append(loader.get_failed_plugins().get(manifest.name, "插件与当前宿主或依赖不兼容"))
        affected = sorted(set(before) - set(after) - {manifest.name})
        if affected:
            blocked.append("更新会使已有插件的依赖不满足: " + ", ".join(affected))
        if not manifest.api_version and not manifest.min_core_version:
            warnings.append("插件未声明 API/核心版本要求，无法保证兼容性")
        # Only cycles reachable from the new plugin are relevant to this import.
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(name: str) -> bool:
            if name in visiting:
                return True
            if name in visited or name not in manifests:
                return False
            visiting.add(name)
            for ref in manifests[name].dependencies.get("plugins", []):
                if visit(loader._parse_plugin_ref(ref)):
                    return True
            visiting.remove(name)
            visited.add(name)
            return False
        if visit(manifest.name):
            blocked.append("插件声明存在循环依赖")
        registry = get_global_registry()
        own_components = {f"{manifest.name}:{item.component_type}:{item.component_name}"
                          for item in manifest.include if item.enabled}
        required_components = list(manifest.dependencies.get("components", []))
        for item in manifest.include:
            if item.enabled:
                required_components.extend(item.dependencies)
        missing_components = sorted({ref for ref in required_components
                                     if ref not in own_components and registry.get(ref) is None})
        if missing_components:
            blocked.append("需要先加载依赖组件: " + ", ".join(missing_components))
        loaded = set(list_loaded_plugins())
        unloaded = sorted({loader._parse_plugin_ref(ref) for ref in manifest.dependencies.get("plugins", [])} - loaded)
        if unloaded:
            warnings.append("依赖插件尚未加载，热加载可能失败: " + ", ".join(unloaded))
        if manifest.python_dependencies:
            warnings.append("本操作不会自动安装 Python 依赖: " + ", ".join(manifest.python_dependencies))
        return blocked, warnings

    async def _inspect_target(self, manifest: PluginManifest) -> tuple[Path, tuple[Any, ...], str | None, list[str], list[str]]:
        records = await self._local_records()
        matches = [record for record in records if record.manifest.name.casefold() == manifest.name.casefold()]
        blocked, warnings = self._compatibility(manifest, records)
        root = self._root()
        destination = root / f"{manifest.name}.mfp"
        installed_version: str | None = None
        fingerprint: tuple[Any, ...] = (str(root), None)
        if len(matches) > 1:
            blocked.append("发现多份同名插件，请先手工处理重复安装")
        elif matches:
            record = matches[0]
            destination = record.path
            installed_version = record.manifest.version
            if record.manifest.name != manifest.name:
                blocked.append("插件名称与已有插件仅大小写不同，拒绝覆盖")
            if (destination.parent != root or destination.resolve().parent != root or destination.is_symlink()
                    or not destination.is_file() or destination.suffix not in {".zip", ".mfp"}):
                blocked.append("只能覆盖插件根目录中的普通 ZIP/MFP 包；目录版及外部路径需手工管理")
            else:
                stat = destination.stat()
                fingerprint = (str(root), str(destination), stat.st_size, stat.st_mtime_ns,
                               stat.st_ino, await asyncio.to_thread(_sha256, destination))
            try:
                old, new = Version(installed_version), Version(manifest.version)
                if old == new:
                    warnings.append("将覆盖相同版本的插件")
                elif new < old:
                    warnings.append("正在降级插件，请确认配置和数据兼容性")
            except InvalidVersion:
                warnings.append("版本号无法比较，请自行确认新旧版本兼容性")
        elif destination.exists() or destination.is_symlink():
            blocked.append("目标文件已存在但无法识别为同名插件，拒绝覆盖")
        if not matches and root.exists():
            for candidate in root.iterdir():
                if candidate.name.casefold() == manifest.name.casefold() and (candidate.is_dir() or candidate.is_symlink()):
                    blocked.append("存在同名目录版插件，需手工管理")
        if manifest.name == self.self_plugin_name:
            warnings.append("WebUI 自身更新仅写入插件包，请手动重启 Neo-MoFox；不会热重载自身")
        # Catch casing/path collisions, even for broken packages and directories.
        if root.exists():
            for candidate in root.iterdir():
                if candidate != destination and candidate.name.casefold() == destination.name.casefold():
                    blocked.append("目标文件名与现有路径冲突")
        return destination, fingerprint, installed_version, blocked, warnings

    async def prepare(self, file: UploadFile) -> PluginImportPreview:
        """Stream one bounded upload, validate it, and return a 15-minute non-executing preview."""
        await self.initialize()
        self._cleanup()
        filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1][:255]
        if Path(filename).suffix.lower() not in {".zip", ".mfp"}:
            raise PluginImportError("仅支持 .zip 或 .mfp 标准插件包")
        upload_id = uuid4().hex
        temporary = self.upload_dir / f"{upload_id}.part"
        package = self.upload_dir / f"{upload_id}.mfp"
        with self._state_lock:
            if len(self._uploads) + self._preparing >= MAX_PENDING_UPLOADS:
                raise PluginImportError("待处理上传过多，请先完成或取消已有上传", 429)
            self._preparing += 1
        retained = False
        try:
            size = 0
            with temporary.open("xb") as target:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_PACKAGE_BYTES:
                        raise PluginImportError("插件包不能超过 50 MiB", 413)
                    target.write(chunk)
            if size == 0:
                raise PluginImportError("上传文件不能为空")
            os.replace(temporary, package)
            await asyncio.to_thread(validate_package, package)
            manifest = await load_manifest(str(package))
            if manifest is None:
                raise PluginImportError("主程序无法识别该插件清单")
            async with plugin_write_lock:
                destination, fingerprint, installed_version, blocked, warnings = await self._inspect_target(manifest)
            expires = time.time() + UPLOAD_TTL
            preview = PluginImportPreview(
                upload_id=upload_id, expires_at=_iso(expires), filename=filename, size_bytes=size,
                plugin_name=manifest.name, version=manifest.version, description=manifest.description,
                installed_version=installed_version, overwrite_required=installed_version is not None,
                self_update=manifest.name == self.self_plugin_name, can_import=not blocked,
                warnings=warnings, blocking_reasons=blocked,
            )
            digest = await asyncio.to_thread(_sha256, package)
            with self._state_lock:
                self._uploads[upload_id] = StagedUpload(package, preview, manifest, destination, fingerprint, digest, expires)
            retained = True
            return preview
        except PackageError as error:
            raise PluginImportError(str(error)) from error
        finally:
            with self._state_lock:
                self._preparing -= 1
            self._remove_scratch(temporary)
            if not retained:
                self._remove_scratch(package)

    async def commit(self, request: PluginImportCommit) -> PluginImportOperation:
        """Claim a preview once and enqueue a tracked task; repeat submissions return its status."""
        self._cleanup()
        with self._state_lock:
            previous = self._submitted.get(request.upload_id)
            if previous is not None:
                return self.get_operation(previous)
            upload = self._uploads.get(request.upload_id)
            if upload is None or upload.expires <= time.time():
                raise PluginImportError("上传已过期或不存在，请重新选择文件", 410)
            if not upload.preview.can_import:
                raise PluginImportError("；".join(upload.preview.blocking_reasons))
            if upload.preview.overwrite_required and not request.confirm_overwrite:
                raise PluginImportError("需要明确确认覆盖已有插件", 409)
            if any(op.plugin_name == upload.manifest.name and op.status in {"queued", "running"}
                   for op in self._operations.values()):
                raise PluginImportError("该插件已有导入任务，请等待完成", 409)
            if len(self._operations) >= MAX_OPERATION_RECORDS:
                raise PluginImportError("导入任务记录已达上限，请稍后再试", 429)
            operation = PluginImportOperation(operation_id=uuid4().hex, plugin_name=upload.manifest.name,
                                              created_at=_iso(), updated_at=_iso())
            upload.operation_id = operation.operation_id
            self._operations[operation.operation_id] = operation
            self._submitted[request.upload_id] = operation.operation_id
        coroutine = self._run(request.upload_id, upload)
        try:
            get_task_manager().create_task(coroutine, name=f"webui-plugin-import-{operation.operation_id}",
                                          metadata={"plugin_id": operation.plugin_name}, timeout=None)
        except BaseException:
            coroutine.close()
            with self._state_lock:
                upload.operation_id = None
                self._operations.pop(operation.operation_id, None)
                self._submitted.pop(request.upload_id, None)
            raise
        return operation.model_copy(deep=True)

    def get_operation(self, operation_id: str) -> PluginImportOperation:
        """Return an immutable snapshot; no file paths are accepted from the caller."""
        with self._state_lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                raise PluginImportError("导入任务不存在或已过期", 404)
            return operation.model_copy(deep=True)

    def discard(self, upload_id: str) -> None:
        """Idempotently cancel an uncommitted upload, never an accepted installation."""
        with self._state_lock:
            if upload_id in self._submitted:
                raise PluginImportError("导入已提交，不能取消；请查询任务结果", 409)
            self._discard(upload_id)

    def _update(self, operation_id: str, **updates: Any) -> None:
        with self._state_lock:
            self._operations[operation_id] = self._operations[operation_id].model_copy(
                update={**updates, "updated_at": _iso()}, deep=True)

    async def _run(self, upload_id: str, upload: StagedUpload) -> None:
        operation_id = upload.operation_id
        assert operation_id is not None
        result = PluginImportResult(plugin_name=upload.manifest.name, version=upload.manifest.version)
        try:
            async with plugin_write_lock:
                self._update(operation_id, status="running", stage="validating", progress=10, message="正在重新校验插件包与本地状态")
                await asyncio.to_thread(validate_package, upload.path)
                if await asyncio.to_thread(_sha256, upload.path) != upload.digest:
                    raise PluginImportError("上传包在确认后发生变化，请重新上传", 409)
                destination, fingerprint, _, blocked, _ = await self._inspect_target(upload.manifest)
                if destination != upload.destination or fingerprint != upload.fingerprint:
                    raise PluginImportError("本地插件在预览后发生变化，请重新上传并确认", 409)
                if blocked:
                    raise PluginImportError("；".join(blocked), 409)
                was_loaded = upload.manifest.name in list_loaded_plugins()
                self._update(operation_id, stage="storing", progress=55, message="正在原子写入插件包")
                # Keep replace and written-state update in one cancellation-free section.
                atomic_store(upload.path, destination, self._root(), overwrite=upload.preview.overwrite_required)
                result.written = True
                if upload.preview.self_update:
                    result.restart_required = True
                    message = "WebUI 插件包已更新，请手动重启 Neo-MoFox 后生效"
                else:
                    self._update(operation_id, stage="loading", progress=80, message="正在加载插件", result=result)
                    try:
                        async with asyncio.timeout(120):
                            result.loaded = bool(await reload_plugin(upload.manifest.name) if was_loaded
                                                 else await load_plugin(str(destination)))
                        if not result.loaded:
                            result.load_error = "主程序加载返回失败，请查看插件日志"
                            try:
                                info = (await list_unloaded_plugins()).get(upload.manifest.name, {})
                                result.load_error = info.get("reason") or result.load_error
                            except Exception:
                                logger.error("读取插件加载失败原因失败", exc_info=True)
                    except TimeoutError:
                        result.load_error = "插件加载超过 120 秒，运行状态可能不完整，请检查日志并手动重启"
                    except Exception as error:
                        result.load_error = str(error)
                    if result.loaded:
                        message = "插件已导入并加载成功"
                    else:
                        message = "插件包已导入，但加载失败；请处理日志中的错误或依赖后重试，必要时手动重启"
                self._update(operation_id, status="succeeded", stage="completed", progress=100, message=message, result=result)
                logger.info(f"本地插件导入完成: plugin={result.plugin_name} version={result.version} "
                            f"loaded={result.loaded} restart_required={result.restart_required}")
        except asyncio.CancelledError:
            self._update(operation_id, status="failed", stage="failed", message="导入任务被中断，请核对插件状态",
                         error_message="任务被中断", result=result)
            raise
        except Exception as error:
            logger.error("本地插件导入失败", exc_info=True)
            self._update(operation_id, status="failed", stage="failed", message="插件导入失败", error_message=str(error), result=result)
        finally:
            with self._state_lock:
                self._discard(upload_id)


_manager: PluginImportManager | None = None


def get_plugin_import_manager(self_plugin_name: str = "neo-mofox-webui") -> PluginImportManager:
    """Share uploads/operations across requests and router instances."""
    global _manager
    if _manager is None:
        _manager = PluginImportManager(self_plugin_name)
    return _manager
