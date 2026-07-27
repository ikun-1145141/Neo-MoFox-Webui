"""Router 组件模块。"""

from .auth_router import AuthRouter
from .chat_router import ChatRouter
from .dashboard_router import DashboardRouter
from .llm_metrics_router import LLMMetricsRouter
from .request_inspector_router import RequestInspectorRouter
from .plugin_market_router import PluginMarketRouter
from .wallpaper_router import WallpaperRouter
from .webui_router import WebuiSettingsRouter


__all__ = [
    "AuthRouter",
    "ChatRouter",
    "DashboardRouter",
    "LLMMetricsRouter",
    "RequestInspectorRouter",
    "PluginMarketRouter",
    "WebuiSettingsRouter",
]
