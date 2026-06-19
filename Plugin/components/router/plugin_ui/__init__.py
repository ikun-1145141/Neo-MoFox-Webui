"""插件 UI 扩展 Router 子目录。

提供 Discovery、Schema 和 Asset 三个 HTTP Router。
"""

from .plugin_ui_discovery_router import PluginUIDiscoveryRouter
from .plugin_ui_schema_router import PluginUISchemaRouter
from .plugin_ui_asset_router import PluginUIAssetRouter

__all__ = [
    "PluginUIDiscoveryRouter",
    "PluginUISchemaRouter",
    "PluginUIAssetRouter",
]
