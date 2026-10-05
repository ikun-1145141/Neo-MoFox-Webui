"""插件 UI 扩展子系统工具层。

提供数据模型、路径工具、常量和校验器。
"""

from .plugin_ui_constants import (
    ALLOWED_ASSET_EXTENSIONS,
    ASSET_CACHE_MAX_AGE,
    MAX_ASSET_SIZE_BYTES,
)
from .plugin_ui_paths import resolve_safe
from .plugin_ui_types import (
    HTMLAssets,
    PageDetail,
    PageMode,
    PageRegistration,
    PageSchemaResponse,
    PageSummary,
    RegisteredPage,
)

__all__ = [
    "ALLOWED_ASSET_EXTENSIONS",
    "ASSET_CACHE_MAX_AGE",
    "MAX_ASSET_SIZE_BYTES",
    "HTMLAssets",
    "PageDetail",
    "PageMode",
    "PageRegistration",
    "PageSchemaResponse",
    "PageSummary",
    "RegisteredPage",
    "resolve_safe",
]
