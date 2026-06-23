"""插件 UI 路径工具。

提供安全的路径解析功能，防止路径穿越攻击。
所有相对路径以 Neo-MoFox 主程序的工作目录（CWD）为基准。
"""

from __future__ import annotations

from pathlib import Path

from .plugin_ui_constants import ALLOWED_ASSET_EXTENSIONS, MAX_ASSET_SIZE_BYTES


def resolve_safe(rel_path: str) -> Path:
    """安全解析资源路径（相对于 CWD）。

    确保解析后的路径仍在 CWD 目录树内，防止路径穿越。

    Args:
        rel_path: 相对于 CWD 的路径字符串

    Returns:
        解析后的绝对路径

    Raises:
        PermissionError: 路径穿越被阻止
        FileNotFoundError: 文件不存在
    """
    candidate = Path(rel_path).resolve()
    cwd = Path.cwd().resolve()

    # 至少要在 CWD 或其子目录内（不能跳出主程序目录树）
    if not candidate.is_relative_to(cwd):
        raise PermissionError(f"path traversal blocked: {rel_path}")
    if not candidate.is_file():
        raise FileNotFoundError(f"asset not found: {rel_path}")
    return candidate


def resolve_safe_dir(rel_path: str) -> Path:
    """安全解析目录路径（相对于 CWD）。

    与 resolve_safe 类似，但校验目标为目录而非文件。

    Args:
        rel_path: 相对于 CWD 的目录路径字符串

    Returns:
        解析后的绝对路径

    Raises:
        PermissionError: 路径穿越被阻止
        FileNotFoundError: 目录不存在
    """
    candidate = Path(rel_path).resolve()
    cwd = Path.cwd().resolve()

    if not candidate.is_relative_to(cwd):
        raise PermissionError(f"path traversal blocked: {rel_path}")
    if not candidate.is_dir():
        raise FileNotFoundError(f"directory not found: {rel_path}")
    return candidate


def resolve_asset_in_dir(assets_dir: Path, rel_path: str) -> Path:
    """在 assets_dir 内安全解析子路径。

    确保解析后的路径仍在 assets_dir 内（不允许跳出），
    且在 CWD 内（双重保护）。

    Args:
        assets_dir: 资源目录的绝对路径
        rel_path: 相对于 assets_dir 的子路径

    Returns:
        解析后的绝对路径

    Raises:
        PermissionError: 路径穿越被阻止
        FileNotFoundError: 文件不存在
    """
    candidate = (assets_dir / rel_path).resolve()
    cwd = Path.cwd().resolve()

    # 双重校验：必须在 assets_dir 内，且在 CWD 内
    if not candidate.is_relative_to(assets_dir):
        raise PermissionError(f"path traversal blocked (out of assets_dir): {rel_path}")
    if not candidate.is_relative_to(cwd):
        raise PermissionError(f"path traversal blocked (out of CWD): {rel_path}")
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
