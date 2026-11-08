"""插件包（.zip / .mfp）安全校验工具。

主程序加载压缩包插件时直接整体解压，不做任何结构校验，
因此所有写入插件目录的包都必须先经过这里的检查。
插件市场安装与本地导入共用同一套规则。
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

# 插件包技术性边界常量（不暴露到插件配置或 UI 设置）
MAX_PACKAGE_SIZE_MB = 50
PACKAGE_SUFFIXES = frozenset({".zip", ".mfp"})

_PLUGIN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class PluginPackageError(RuntimeError):
    """插件包结构、清单或标识未通过安全校验。"""


class PluginPackageTooLargeError(PluginPackageError):
    """上传的插件包超过体积上限。"""


def validate_plugin_id(plugin_id: str) -> None:
    """拒绝不符合路径安全字符集的插件标识。

    Args:
        plugin_id: 待校验的插件唯一标识，会被用于拼接插件包文件名。

    Raises:
        PluginPackageError: 标识为空、过长或包含路径分隔符等非法字符。
    """
    if not _PLUGIN_ID_PATTERN.fullmatch(plugin_id):
        raise PluginPackageError(f"插件 ID 格式无效: {plugin_id}")


def validate_plugin_package(path: Path, max_uncompressed_bytes: int) -> dict[str, Any]:
    """验证 ZIP 安全边界、唯一清单和入口文件后返回清单对象。

    Args:
        path: 待校验的插件包路径。
        max_uncompressed_bytes: 允许的 ZIP 条目累计解压大小。

    Returns:
        从唯一根级或一级 ``manifest.json`` 读取的清单对象。

    Raises:
        PluginPackageError: 压缩包路径、符号链接、体积、清单或入口校验失败。
    """
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if not entries:
                raise PluginPackageError("插件压缩包为空")
            total = 0
            manifest_paths: list[str] = []
            normalized_names: set[str] = set()
            for entry in entries:
                # 只检查包结构，不解压文件；路径、符号链接和累计体积均在写入前拒绝。
                normalized = entry.filename.replace("\\", "/").rstrip("/")
                entry_path = Path(normalized)
                if entry_path.is_absolute() or ".." in entry_path.parts:
                    raise PluginPackageError("插件压缩包包含非法路径")
                if not normalized:
                    continue
                normalized_names.add(normalized)
                if not entry.is_dir():
                    total += entry.file_size
                    if total > max_uncompressed_bytes:
                        raise PluginPackageError("插件包解压后超过大小限制")
                    mode = entry.external_attr >> 16
                    if mode and (mode & 0o170000) == 0o120000:
                        raise PluginPackageError("插件压缩包不能包含符号链接")
                    if normalized.endswith("manifest.json") and len(entry_path.parts) <= 2:
                        manifest_paths.append(normalized)
            if len(manifest_paths) != 1:
                raise PluginPackageError("插件包必须包含唯一的根级或一级 manifest.json")
            manifest = json.loads(archive.read(manifest_paths[0]).decode("utf-8"))
            if not isinstance(manifest, dict):
                raise PluginPackageError("manifest.json 必须是 JSON 对象")
            entry_point = str(manifest.get("entry_point") or "plugin.py")
            parent = manifest_paths[0].rsplit("/", 1)[0] if "/" in manifest_paths[0] else ""
            entry_path = f"{parent}/{entry_point}".lstrip("/")
            if entry_path not in normalized_names:
                raise PluginPackageError("插件入口文件不存在")
            return manifest
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PluginPackageError(f"插件包格式无效: {error}") from error


__all__ = [
    "MAX_PACKAGE_SIZE_MB",
    "PACKAGE_SUFFIXES",
    "PluginPackageError",
    "PluginPackageTooLargeError",
    "validate_plugin_id",
    "validate_plugin_package",
]
