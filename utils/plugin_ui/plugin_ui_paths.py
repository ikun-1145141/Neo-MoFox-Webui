"""插件 UI 路径工具。

提供安全的路径解析功能，防止路径穿越攻击。
HTML 模式下所有相对路径以「插件根目录」为基准——
插件根目录由插件名通过插件系统 API（get_plugin_path）查询得到，
解析后再做路径穿越校验，确保资源路径不会跳出插件根目录树。
"""

from __future__ import annotations

from pathlib import Path

from .plugin_ui_constants import ALLOWED_ASSET_EXTENSIONS, MAX_ASSET_SIZE_BYTES


def resolve_safe(rel_path: str, base_dir: Path) -> Path:
    """安全解析资源路径（相对于 base_dir）。

    确保解析后的路径仍在 base_dir 目录树内，防止路径穿越。
    base_dir 通常为「插件根目录」（HTML 模式由插件名查得）。

    Args:
        rel_path: 相对于 base_dir 的路径字符串
        base_dir: 基准目录（插件根目录）的绝对路径

    Returns:
        解析后的绝对路径

    Raises:
        PermissionError: 路径穿越被阻止
        FileNotFoundError: 文件不存在
    """
    base = base_dir.resolve()
    candidate = (base / rel_path).resolve()

    if not candidate.is_relative_to(base):
        raise PermissionError(f"path traversal blocked: {rel_path}")
    if not candidate.is_file():
        raise FileNotFoundError(f"asset not found: {rel_path}")
    return candidate


def resolve_safe_dir(rel_path: str, base_dir: Path) -> Path:
    """安全解析目录路径（相对于 base_dir）。

    与 resolve_safe 类似，但校验目标为目录而非文件。

    Args:
        rel_path: 相对于 base_dir 的目录路径字符串
        base_dir: 基准目录（插件根目录）的绝对路径

    Returns:
        解析后的绝对路径

    Raises:
        PermissionError: 路径穿越被阻止
        FileNotFoundError: 目录不存在
    """
    base = base_dir.resolve()
    candidate = (base / rel_path).resolve()

    if not candidate.is_relative_to(base):
        raise PermissionError(f"path traversal blocked: {rel_path}")
    if not candidate.is_dir():
        raise FileNotFoundError(f"directory not found: {rel_path}")
    return candidate


def resolve_asset_in_dir(
    assets_dir: Path, rel_path: str, base_dir: Path
) -> Path:
    """在 assets_dir 内安全解析子路径。

    确保解析后的路径仍在 assets_dir 内（不允许跳出），
    且在 base_dir（插件根目录）内（双重保护）。

    Args:
        assets_dir: 资源目录的绝对路径（应在 base_dir 内）
        rel_path: 相对于 assets_dir 的子路径
        base_dir: 基准目录（插件根目录）的绝对路径

    Returns:
        解析后的绝对路径

    Raises:
        PermissionError: 路径穿越被阻止
        FileNotFoundError: 文件不存在
    """
    base = base_dir.resolve()
    assets_resolved = assets_dir.resolve()

    # assets_dir 自身必须位于插件根目录内
    if not assets_resolved.is_relative_to(base):
        raise PermissionError(
            f"path traversal blocked (assets_dir out of base_dir): {assets_dir}"
        )

    candidate = (assets_resolved / rel_path).resolve()

    # 双重校验：必须在 assets_dir 内，且在 base_dir 内
    if not candidate.is_relative_to(assets_resolved):
        raise PermissionError(f"path traversal blocked (out of assets_dir): {rel_path}")
    if not candidate.is_relative_to(base):
        raise PermissionError(f"path traversal blocked (out of base_dir): {rel_path}")
    if not candidate.is_file():
        raise FileNotFoundError(f"asset not found: {rel_path}")
    return candidate


def validate_asset_extension(file_path: Path) -> None:
    """校验文件扩展名是否在白名单中。

    Args:
        file_path: 待校验的文件路径

    Raises:
        PermissionError: 扩展名不在白名单中
    """
    ext = file_path.suffix.lower()
    if ext not in ALLOWED_ASSET_EXTENSIONS:
        raise PermissionError(
            f"extension not allowed: {ext} (file: {file_path.name})"
        )


def validate_asset_size(file_path: Path) -> None:
    """校验文件大小是否超出限制。

    Args:
        file_path: 待校验的文件路径

    Raises:
        PermissionError: 文件大小超出限制
    """
    size = file_path.stat().st_size
    if size > MAX_ASSET_SIZE_BYTES:
        raise PermissionError(
            f"file too large: {file_path.name} "
            f"({size} bytes > {MAX_ASSET_SIZE_BYTES} bytes limit)"
        )
