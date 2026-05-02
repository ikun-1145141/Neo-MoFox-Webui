"""Router 组件模块。"""

from .auth_router import AuthRouter
from .wallpaper_router import WallpaperRouter
from .webui_router import WebuiSettingsRouter

__all__ = ["AuthRouter", "WebuiSettingsRouter", "WallpaperRouter"]
