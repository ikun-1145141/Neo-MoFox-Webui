"""Shared, non-executing ZIP/MFP validation and atomic package storage."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import stat
import tempfile
import unicodedata
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_PACKAGE_BYTES = 50 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ENTRIES = 20000
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


class PackageError(ValueError):
    """The package cannot be safely stored or loaded."""


class PackageComponent(BaseModel):
    model_config = ConfigDict(strict=True, extra="allow")
    component_type: str = Field(min_length=1)
    component_name: str = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    enabled: bool = True


class PackageManifest(BaseModel):
    """Validate loader-consumed fields without importing any plugin code."""
    model_config = ConfigDict(strict=True, extra="allow")
    name: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=128)
    description: str
    author: str
    entry_point: str
    dependencies: dict[str, list[str]]
    include: list[PackageComponent] = Field(default_factory=list)
    api_version: str | dict[str, str] = ""
    min_core_version: str = ""
    python_dependencies: list[str] = Field(default_factory=list)
    dependencies_required: bool = True


def validate_plugin_id(name: str) -> None:
    """Validate a portable filename derived from manifest.name, never the upload name."""
    if not _ID.fullmatch(name) or name.endswith(".") or _RESERVED.match(name):
        raise PackageError("插件名称不能安全地用作文件名")


def _safe_parts(name: str) -> tuple[str, ...]:
    if not name or "\\" in name or name.startswith("/"):
        raise PackageError("插件压缩包包含非法路径")
    parts = tuple(name.split("/"))
    for part in parts:
        if (not part or part in {".", ".."} or part.endswith((".", " "))
                or any(ord(c) < 32 or c in ':<>"|?*' for c in part)
                or _RESERVED.match(part)):
            raise PackageError("插件压缩包包含非法或不跨平台的路径")
    return parts


def validate_package(package: Path, max_uncompressed_bytes: int = MAX_PACKAGE_BYTES) -> dict[str, Any]:
    """Read bounded entries, check CRC/path/manifest/entrypoint; never extract or execute."""
    try:
        if package.stat().st_size > MAX_PACKAGE_BYTES:
            raise PackageError("插件包不能超过 50 MiB")
        with zipfile.ZipFile(package) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > MAX_ENTRIES:
                raise PackageError("插件压缩包为空或文件条目过多")
            seen: set[str] = set()
            spellings: dict[str, str] = {}
            files: set[str] = set()
            parents: set[str] = set()
            manifest_entries: list[zipfile.ZipInfo] = []
            total = 0
            for entry in entries:
                if entry.orig_filename != entry.filename or entry.flag_bits & 1:
                    raise PackageError("插件包含有非法文件名或加密文件")
                name = entry.filename.rstrip("/") if entry.is_dir() else entry.filename
                parts = _safe_parts(name)
                key = unicodedata.normalize("NFC", name).casefold()
                if key in seen:
                    raise PackageError("插件包含有重复或大小写冲突的路径")
                seen.add(key)
                for index in range(1, len(parts) + 1):
                    prefix = "/".join(parts[:index])
                    canonical = unicodedata.normalize("NFC", prefix).casefold()
                    if canonical in spellings and spellings[canonical] != prefix:
                        raise PackageError("插件包包含规范化后冲突的目录或文件")
                    spellings[canonical] = prefix
                mode = stat.S_IFMT(entry.external_attr >> 16)
                if mode not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise PackageError("插件包不能包含符号链接或特殊文件")
                if (mode == stat.S_IFDIR and not entry.is_dir()) or (mode == stat.S_IFREG and entry.is_dir()):
                    raise PackageError("插件包文件类型与路径不一致")
                parents.update(unicodedata.normalize("NFC", "/".join(parts[:i])).casefold()
                               for i in range(1, len(parts)))
                if not entry.is_dir():
                    files.add(key)
                    total += entry.file_size
                    if total > max_uncompressed_bytes:
                        raise PackageError("插件包解压后超过 50 MiB 限制")
                    if parts[-1] == "manifest.json" and len(parts) <= 2:
                        manifest_entries.append(entry)
            if files & parents:
                raise PackageError("插件包包含文件与目录冲突")
            if len(manifest_entries) != 1:
                raise PackageError("需要唯一的根级或一级目录 manifest.json；不支持任意源码仓库 ZIP")
            manifest_entry = manifest_entries[0]
            parent = str(PurePosixPath(manifest_entry.filename).parent)
            if parent != "." and any(not e.is_dir() and not e.filename.startswith(parent + "/") for e in entries):
                raise PackageError("一级目录插件包的所有文件必须位于同一个插件目录，避免入口歧义")
            if manifest_entry.file_size > MAX_MANIFEST_BYTES:
                raise PackageError("manifest.json 过大")
            raw = json.loads(archive.read(manifest_entry).decode("utf-8-sig"))
            manifest = PackageManifest.model_validate(raw)
            validate_plugin_id(manifest.name)
            if not manifest.version.strip():
                raise PackageError("插件版本不能为空")
            _safe_parts(manifest.entry_point)
            entry_name = str(PurePosixPath(manifest_entry.filename).parent / manifest.entry_point)
            # Require the exact path the host loader will use, not a casefold-only match.
            if entry_name not in {e.filename for e in entries if not e.is_dir()}:
                raise PackageError("manifest.json 声明的入口文件不存在")
            if not manifest.entry_point.endswith(".py"):
                raise PackageError("插件入口必须是 Python 文件")
            actual_total = 0
            for entry in entries:
                if entry.is_dir():
                    continue
                with archive.open(entry) as source:
                    while chunk := source.read(1024 * 1024):
                        actual_total += len(chunk)
                        if actual_total > max_uncompressed_bytes:
                            raise PackageError("插件包实际解压大小超出限制")
            return raw
    except PackageError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError, NotImplementedError,
            zipfile.BadZipFile, ValidationError, EOFError, zlib.error) as error:
        raise PackageError(f"插件包格式或清单无效: {error}") from error


def atomic_store(source: Path, destination: Path, root: Path, *, overwrite: bool) -> None:
    """Copy to a same-filesystem temporary file and replace only a root-level package.

    Called in the short, serialized commit section; no await may split the replace
    from recording the written result. Failure before replace preserves the old file.
    """
    if destination.parent != root or destination.is_symlink() or destination.resolve().parent != root:
        raise PackageError("插件目标路径不在允许的插件根目录")
    if destination.exists() and not destination.is_file():
        raise PackageError("插件目标不是普通文件")
    if not overwrite and destination.exists():
        raise PackageError("插件目标已存在，请重新预览后确认覆盖")
    previous = destination.stat() if destination.exists() else None
    root.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    published = False
    try:
        with tempfile.NamedTemporaryFile(dir=root, prefix=".webui-import-", suffix=".tmp", delete=False) as target:
            temporary = Path(target.name)
            with source.open("rb") as origin:
                shutil.copyfileobj(origin, target, length=1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        if destination.is_symlink() or destination.resolve().parent != root:
            raise PackageError("插件目标路径在写入前发生变化")
        if overwrite:
            current = destination.stat()
            if previous is None or (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                previous.st_dev, previous.st_ino, previous.st_size, previous.st_mtime_ns
            ):
                raise PackageError("插件目标文件在写入前发生变化，请重新预览")
            os.replace(temporary, destination)
        else:
            # Publish complete bytes without clobbering a concurrently created file.
            # Hard links are supported on the normal NTFS/ext4 plugin filesystems.
            if os.name == "nt":
                os.rename(temporary, destination)
            else:
                os.link(temporary, destination)
        published = True
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                if not published:
                    raise
                logging.getLogger(__name__).warning("已写入插件，但临时文件清理失败: %s", temporary, exc_info=True)
