"""管理器层模块。

提供业务逻辑的转发和处理。
"""

from .config_manager import ConfigManager
from .wallpaper_manager import WallpaperManager
from .dashboard_manager import DashboardManager, get_dashboard_manager

__all__ = [
	"ConfigManager",
	"WallpaperManager",
	"DashboardManager",
	"get_dashboard_manager",
]
