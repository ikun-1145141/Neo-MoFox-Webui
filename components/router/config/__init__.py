"""配置路由模块。

导出所有配置路由组件。
"""

from .main_config_router import MainConfigRouter
from .bot_config_router import BotConfigRouter
from .model_config_router import ModelConfigRouter
from .mcp_config_router import McpConfigRouter
from .plugin_config_router import PluginConfigRouter

__all__ = [
    "MainConfigRouter",
    "BotConfigRouter",
    "ModelConfigRouter",
    "McpConfigRouter",
    "PluginConfigRouter",
]
