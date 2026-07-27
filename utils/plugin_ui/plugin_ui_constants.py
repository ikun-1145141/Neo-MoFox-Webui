"""插件 UI 扩展子系统常量定义。

安全和运行时边界常量，不暴露到用户设置中。
"""

# 单文件大小上限（字节）
MAX_ASSET_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

# 允许的资源扩展名
ALLOWED_ASSET_EXTENSIONS: frozenset[str] = frozenset([
    ".html", ".css", ".js",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".otf",
])

# 静态资源 Cache-Control max-age（秒）
ASSET_CACHE_MAX_AGE: int = 300

# page_id 正则校验
PAGE_ID_PATTERN: str = r"^[a-z][a-z0-9_-]{0,63}$"

# 标题最大长度
MAX_TITLE_LENGTH: int = 64

# 描述最大长度
MAX_DESCRIPTION_LENGTH: int = 256

# HTML entry 中禁止出现的标签
HTML_FORBIDDEN_TAGS: frozenset[str] = frozenset([
    "iframe", "object", "embed",
])

# XML 布局标签白名单
XML_LAYOUT_TAGS: frozenset[str] = frozenset([
    "vbox", "hbox", "grid", "card", "tabs", "tab",
    "dialog", "divider", "spacer",
])

# XML 基础组件标签白名单
XML_BASIC_COMPONENT_TAGS: frozenset[str] = frozenset([
    "sys-text", "sys-input", "sys-textarea", "sys-select",
    "sys-switch", "sys-slider", "sys-date-picker",
    "sys-button", "sys-icon-button", "sys-tag",
    "sys-badge", "sys-icon",
])

# XML 高级组件标签白名单
XML_ADVANCED_COMPONENT_TAGS: frozenset[str] = frozenset([
    "sys-table", "sys-chart", "sys-form", "sys-list",
])

# XML 表格子元素标签
XML_TABLE_CHILD_TAGS: frozenset[str] = frozenset([
    "column", "map", "format", "progress", "actions",
])

# XML 定义节标签
XML_DEFINITION_TAGS: frozenset[str] = frozenset([
    "var", "api", "template",
])

# XML 结构标签（definitions, layout）
XML_STRUCTURE_TAGS: frozenset[str] = frozenset([
    "page", "definitions", "layout",
])

# 全部允许的 XML 标签合集
XML_ALLOWED_TAGS: frozenset[str] = (
    XML_LAYOUT_TAGS
    | XML_BASIC_COMPONENT_TAGS
    | XML_ADVANCED_COMPONENT_TAGS
    | XML_TABLE_CHILD_TAGS
    | XML_DEFINITION_TAGS
    | XML_STRUCTURE_TAGS
)

# XML 中禁止的标签
XML_FORBIDDEN_TAGS: frozenset[str] = frozenset([
    "plugin-page-picker", "sys-include", "sys-bind",
    "sys-toast-anchor", "script", "style",
    "iframe", "object", "embed",
])

# 占位符表达式中允许的内置 helper 函数
EXPRESSION_ALLOWED_HELPERS: frozenset[str] = frozenset([
    "empty", "len", "keys", "values",
    # 文档定义的格式化函数
    "format_date", "format_number", "format_bytes",
    "format_duration", "format_percent",
    "uppercase", "lowercase", "capitalize", "truncate",
])

# 占位符表达式中禁止的关键字
EXPRESSION_FORBIDDEN_KEYWORDS: frozenset[str] = frozenset([
    "new", "function", "class", "import", "from",
    "eval", "exec", "compile", "globals", "locals",
    "__", "lambda",
])
