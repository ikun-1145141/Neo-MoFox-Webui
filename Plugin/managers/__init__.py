"""管理器层模块。

提供业务逻辑的转发和处理。
"""

from .config_manager import ConfigManager
from .dashboard_manager import DashboardManager, get_dashboard_manager
from .plugin_market_manager import PluginMarketManager, get_plugin_market_manager
from .wallpaper_manager import WallpaperManager

__all__ = [
    "ConfigManager",
    "DashboardManager",
    "PluginMarketManager",
    "WallpaperManager",
    "get_dashboard_manager",
    "get_plugin_market_manager",
]
