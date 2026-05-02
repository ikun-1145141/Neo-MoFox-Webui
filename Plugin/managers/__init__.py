"""管理器层模块。

提供业务逻辑的转发和处理。
"""

from .config_manager import ConfigManager
from .wallpaper_manager import WallpaperManager

__all__ = ["ConfigManager", "WallpaperManager"]
