"""Router 组件模块。"""

from .auth_router import AuthRouter
from .dashboard_router import DashboardRouter
from .wallpaper_router import WallpaperRouter
from .webui_router import WebuiSettingsRouter


__all__ = ["AuthRouter", "DashboardRouter", "WebuiSettingsRouter", "WallpaperRouter"]
