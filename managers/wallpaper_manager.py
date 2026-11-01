"""壁纸管理器。

负责单张壁纸文件的保存、删除和查询。
"""

from __future__ import annotations

import asyncio
from pathlib import Path


class WallpaperManager:
    """壁纸管理器。

    管理 WebUI 的单张壁纸文件，固定目录为
    data/json_storage/WebUI_data/wallpaper。

    Attributes:
        wallpaper_dir: 壁纸目录路径
    """

    SUPPORTED_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm")

    def __init__(self) -> None:
        """初始化壁纸管理器。"""
        self.wallpaper_dir = Path("data/json_storage/WebUI_data/wallpaper")

    async def initialize(self) -> None:
        """初始化壁纸目录。"""
        await asyncio.to_thread(self.wallpaper_dir.mkdir, parents=True, exist_ok=True)

    def is_video_wallpaper(self, path: Path) -> bool:
        """判断壁纸是否为视频。
        
        Args:
            path: 壁纸文件路径
            
        Returns:
            是否为视频壁纸
        """
        return path.suffix.lower() in (".mp4", ".webm")

    async def get_wallpaper_path(self) -> Path | None:
        """获取当前壁纸路径。

        Returns:
            当前壁纸路径；不存在时返回 None
        """

        def _find_current() -> Path | None:
            if not self.wallpaper_dir.exists():
                return None
            for candidate in sorted(self.wallpaper_dir.glob("current.*")):
                if candidate.suffix.lower() in self.SUPPORTED_EXTENSIONS and candidate.is_file():
                    return candidate
            return None

        return await asyncio.to_thread(_find_current)

    async def has_wallpaper(self) -> bool:
        """检查是否存在当前壁纸。"""
        return (await self.get_wallpaper_path()) is not None

    async def save_wallpaper(self, content: bytes, extension: str) -> Path:
        """保存壁纸文件。

        Args:
            content: 壁纸二进制内容
            extension: 文件扩展名（含或不含点）

        Returns:
            保存后的文件路径
        """

        normalized_extension = extension.lower().strip()
        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"
        if normalized_extension == ".jpeg":
            normalized_extension = ".jpg"

        if normalized_extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError("不支持的壁纸格式")

        await self.initialize()
        await self.delete_wallpaper()

        target_path = self.wallpaper_dir / f"current{normalized_extension}"
        await asyncio.to_thread(target_path.write_bytes, content)
        return target_path

    async def delete_wallpaper(self) -> None:
        """删除当前壁纸文件。"""

        current = await self.get_wallpaper_path()
        if current is None:
            return
        await asyncio.to_thread(current.unlink, True)


_wallpaper_manager: WallpaperManager | None = None


def get_wallpaper_manager() -> WallpaperManager:
    """获取壁纸管理器单例。"""
    global _wallpaper_manager
    if _wallpaper_manager is None:
        _wallpaper_manager = WallpaperManager()
    return _wallpaper_manager
