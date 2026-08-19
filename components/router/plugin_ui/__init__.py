"""插件 UI 扩展 Router 子目录。

提供统一的 Plugin UI Router 和 Asset Router。
"""

from .plugin_ui_router import PluginUIRouter
from .plugin_ui_asset_router import PluginUIAssetRouter

__all__ = [
    "PluginUIRouter",
    "PluginUIAssetRouter",
]
