"""插件 UI 校验器。

提供 XML 三层校验（XSD + 白名单 + 占位符表达式）和 HTML 资源校验。
这是注册流程中的安全关口。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

from .plugin_ui_constants import (
    ALLOWED_ASSET_EXTENSIONS,
    EXPRESSION_ALLOWED_HELPERS,
    EXPRESSION_FORBIDDEN_KEYWORDS,
    HTML_FORBIDDEN_TAGS,
    MAX_ASSET_SIZE_BYTES,
    XML_ALLOWED_TAGS,
    XML_FORBIDDEN_TAGS,
)
from .plugin_ui_paths import resolve_safe, resolve_safe_dir

if TYPE_CHECKING:
    from .plugin_ui_types import HTMLAssets, MobileVariant, PageRegistration


# --- 自定义异常 ---


class XMLValidationError(Exception):
    """XML 校验失败（XSD / 白名单 / 占位符语法错误）。"""

    pass


class AssetPathError(Exception):
    """资源路径不合法或穿越。"""

    pass


class AssetMissingError(Exception):
    """资源文件不存在。"""

    pass


class AssetSizeError(Exception):
    """资源文件超出大小限制。"""

    pass


# --- lark 占位符表达式语法 ---

# 占位符表达式的 lark 语法定义
EXPRESSION_GRAMMAR = r"""
    ?start: expr

    ?expr: or_expr

    ?or_expr: and_expr ("||" and_expr)*

    ?and_expr: not_expr ("&&" not_expr)*

    ?not_expr: "!" not_expr -> negate
             | comparison

    ?comparison: addition (COMP_OP addition)?

    ?addition: multiplication (("+"|"-") multiplication)*

    ?multiplication: atom (("*"|"/"|"%") atom)*

    ?atom: "(" expr ")"
         | function_call
         | identifier
         | literal

    function_call: NAME "(" arguments? ")"
    arguments: expr ("," expr)*

    identifier: NAME ("." NAME)*

    ?literal: NUMBER -> number
            | ESCAPED_STRING -> string
            | "true" -> true
            | "false" -> false
            | "null" -> null

    COMP_OP: ">=" | "<=" | "!=" | "==" | ">" | "<"

    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/

    %import common.NUMBER
    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS
"""

# 占位符提取正则
_PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")

# style 属性中禁止的模式
_STYLE_DANGEROUS_PATTERNS = [
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"url\s*\(\s*javascript:", re.IGNORECASE),
    re.compile(r"url\s*\(\s*data:", re.IGNORECASE),
    re.compile(r"-moz-binding", re.IGNORECASE),
    re.compile(r"behavior\s*:", re.IGNORECASE),
]

# XSD schema 缓存
_xsd_schema: etree.XMLSchema | None = None


def _get_xsd_schema() -> etree.XMLSchema:
    """获取缓存的 XSD schema 对象。

    Returns:
        加载后的 XMLSchema 实例
    """
    global _xsd_schema
    if _xsd_schema is None:
        xsd_path = Path(__file__).parent / "schemas" / "plugin_ui_v3_1.xsd"
        xsd_doc = etree.parse(str(xsd_path))
        _xsd_schema = etree.XMLSchema(xsd_doc)
    return _xsd_schema


# lark parser 缓存
_lark_parser = None


def _get_lark_parser():
    """获取缓存的 lark 解析器。

    Returns:
        Lark 解析器实例
    """
    global _lark_parser
    if _lark_parser is None:
        from lark import Lark  # type: ignore

        _lark_parser = Lark(
            EXPRESSION_GRAMMAR,
            parser="earley",
            ambiguity="resolve",
        )
    return _lark_parser


# --- 主入口 ---


class PluginUIValidators:
    """插件 UI 校验器集合。

    提供统一的 validate 入口，内部按 mode 分发到 XML 或 HTML 校验。
    """

    @classmethod
    def validate(cls, metadata: "PageRegistration") -> None:
        """校验页面注册元数据。

        根据 mode 分发到对应的校验流程。同时校验移动端 variant（如有）。

        Args:
            metadata: 页面注册入参

        Raises:
            XMLValidationError: XML 校验失败
            AssetPathError: 路径不合法
            AssetMissingError: 文件不存在
            AssetSizeError: 文件过大
        """
        from .plugin_ui_types import PageMode

        # 桌面版校验
        if metadata.mode == PageMode.XML:
            if metadata.xml:
                cls._validate_xml(metadata.xml)
        elif metadata.mode == PageMode.HTML:
            if metadata.assets:
                cls._validate_html_assets(metadata.assets)

        # 移动版校验
        if metadata.mobile:
            cls._validate_mobile(metadata.mobile)

    @classmethod
    def _validate_mobile(cls, mobile: "MobileVariant") -> None:
        """校验移动端 variant。

        Args:
            mobile: 移动端变体声明

        Raises:
            XMLValidationError: XML 校验失败
            AssetPathError: 路径不合法
            AssetMissingError: 文件不存在
            AssetSizeError: 文件过大
        """
        from .plugin_ui_types import PageMode

        if mobile.mode == PageMode.XML and mobile.xml:
            cls._validate_xml(mobile.xml)
        elif mobile.mode == PageMode.HTML and mobile.assets:
            cls._validate_html_assets(mobile.assets)

    # --- XML 校验 ---

    @classmethod
    def _validate_xml(cls, xml_content: str) -> None:
        """XML 三层校验：XSD + 白名单 + 占位符表达式。

        Args:
            xml_content: XML 字符串

        Raises:
            XMLValidationError: 任意层校验失败
        """
        # 第一层：XSD schema 校验
        cls._validate_xml_xsd(xml_content)

        # 第二层：标签 / 属性白名单
        cls._validate_xml_whitelist(xml_content)

        # 第三层：占位符表达式校验
        cls._validate_xml_expressions(xml_content)

    @classmethod
    def _validate_xml_xsd(cls, xml_content: str) -> None:
        """第一层：XSD schema 校验。

        Args:
            xml_content: XML 字符串

        Raises:
            XMLValidationError: XSD 校验失败
        """
        try:
            doc = etree.fromstring(xml_content.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            raise XMLValidationError(f"XML 语法错误: {e}") from e

        schema = _get_xsd_schema()
        if not schema.validate(doc):
            errors = "; ".join(str(e) for e in schema.error_log)
            raise XMLValidationError(f"XSD 校验失败: {errors}")

    @classmethod
    def _validate_xml_whitelist(cls, xml_content: str) -> None:
        """第二层：标签 / 属性白名单校验。

        Args:
            xml_content: XML 字符串

        Raises:
            XMLValidationError: 白名单校验失败
        """
        try:
            doc = etree.fromstring(xml_content.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            raise XMLValidationError(f"XML 语法错误: {e}") from e

        cls._check_element_recursive(doc)

    @classmethod
    def _check_element_recursive(cls, element: etree._Element) -> None:
        """递归检查 XML 元素的标签和属性。

        Args:
            element: lxml Element 节点

        Raises:
            XMLValidationError: 发现禁止的标签或属性
        """
        # 获取不带命名空间的本地标签名
        tag = etree.QName(element.tag).localname if isinstance(element.tag, str) else str(element.tag)

        # 检查禁止标签
        if tag in XML_FORBIDDEN_TAGS:
            raise XMLValidationError(f"禁止使用标签: <{tag}>")

        # 检查是否在允许标签列表中
        if tag not in XML_ALLOWED_TAGS:
            raise XMLValidationError(
                f"未知标签: <{tag}>，不在白名单中"
            )

        # 检查属性
        for attr_name, attr_value in element.attrib.items():
            # 去除命名空间前缀
            local_attr = etree.QName(attr_name).localname if "{" in attr_name else attr_name

            # 拒绝原生 DOM 事件属性（以 'on' 开头但不含连字符的）
            if local_attr.startswith("on") and "-" not in local_attr:
                raise XMLValidationError(
                    f"禁止使用原生 DOM 事件属性: {local_attr} (在 <{tag}> 中)"
                )

            # style 属性安全过滤
            if local_attr == "style":
                cls._validate_style_attribute(attr_value, tag)

        # 检查文本内容中的占位符（在第三层单独处理）
        # 递归处理子元素
        for child in element:
            if isinstance(child.tag, str):  # 跳过注释节点
                cls._check_element_recursive(child)

    @classmethod
    def _validate_style_attribute(cls, style_value: str, tag: str) -> None:
        """校验 style 属性值安全性。

        Args:
            style_value: style 属性值
            tag: 所在标签名

        Raises:
            XMLValidationError: 发现危险样式模式
        """
        for pattern in _STYLE_DANGEROUS_PATTERNS:
            if pattern.search(style_value):
                raise XMLValidationError(
                    f"style 属性中包含危险模式: '{pattern.pattern}' (在 <{tag}> 中)"
                )

    @classmethod
    def _validate_xml_expressions(cls, xml_content: str) -> None:
        """第三层：占位符表达式校验。

        提取 XML 中所有 {expression} 占位符并校验其语法安全性。

        Args:
            xml_content: XML 字符串

        Raises:
            XMLValidationError: 表达式校验失败
        """
        # 提取所有占位符
        placeholders = _PLACEHOLDER_RE.findall(xml_content)
        for expr in placeholders:
            cls._validate_single_expression(expr.strip())

    @classmethod
    def _validate_single_expression(cls, expr: str) -> None:
        """校验单个占位符表达式。

        使用 lark 解析器校验语法，并检查函数调用白名单。

        Args:
            expr: 表达式字符串（不含花括号）

        Raises:
            XMLValidationError: 表达式不合法
        """
        if not expr:
            return

        # 处理取反前缀
        check_expr = expr.lstrip("!")

        if not check_expr:
            return

        # 快速拒绝：检查禁止关键字
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", check_expr)
        for token in tokens:
            if token in EXPRESSION_FORBIDDEN_KEYWORDS:
                raise XMLValidationError(
                    f"占位符表达式中包含禁止的关键字: '{token}' (在 '{{{expr}}}' 中)"
                )

        # 检查是否包含箭头函数
        if "=>" in check_expr:
            raise XMLValidationError(
                f"占位符表达式中禁止使用箭头函数 '=>' (在 '{{{expr}}}' 中)"
            )

        # 使用 lark 解析器校验语法
        parser = _get_lark_parser()
        try:
            tree = parser.parse(check_expr)
        except Exception as e:
            raise XMLValidationError(
                f"占位符表达式语法错误: '{{{expr}}}' — {e}"
            ) from e

        # 检查函数调用白名单
        cls._check_function_calls(tree, expr)

    @classmethod
    def _check_function_calls(cls, tree, original_expr: str) -> None:
        """递归检查语法树中的函数调用是否在白名单中。

        Args:
            tree: lark 解析树
            original_expr: 原始表达式（用于错误消息）

        Raises:
            XMLValidationError: 发现非白名单函数调用
        """
        from lark import Tree, Token  # type: ignore

        if isinstance(tree, Tree):
            if tree.data == "function_call":
                # 函数名是第一个 Token 子节点
                func_name = None
                for child in tree.children:
                    if isinstance(child, Token) and child.type == "NAME":
                        func_name = str(child)
                        break
                if func_name and func_name not in EXPRESSION_ALLOWED_HELPERS:
                    raise XMLValidationError(
                        f"占位符表达式中调用了非白名单函数: '{func_name}' "
                        f"(在 '{{{original_expr}}}' 中)"
                    )
            # 递归子树
            for child in tree.children:
                cls._check_function_calls(child, original_expr)

    # --- HTML 校验 ---

    @classmethod
    def _validate_html_assets(cls, assets: "HTMLAssets") -> None:
        """校验 HTML 模式的资源声明。

        包含：路径穿越校验、文件存在性、文件大小、扩展名白名单、
        以及 entry_html 中禁止标签扫描。

        Args:
            assets: HTML 资源声明

        Raises:
            AssetPathError: 路径不合法
            AssetMissingError: 文件不存在
            AssetSizeError: 文件过大
        """
        # 校验 entry_html
        cls._validate_single_asset(assets.entry_html, "entry_html")
        cls._scan_html_forbidden_tags(assets.entry_html)

        # 校验 styles
        for i, style_path in enumerate(assets.styles):
            cls._validate_single_asset(style_path, f"styles[{i}]")

        # 校验 scripts
        for i, script_path in enumerate(assets.scripts):
            cls._validate_single_asset(script_path, f"scripts[{i}]")

        # 校验 assets_dir
        if assets.assets_dir:
            try:
                resolve_safe_dir(assets.assets_dir)
            except PermissionError as e:
                raise AssetPathError(
                    f"assets_dir 路径穿越: {assets.assets_dir}"
                ) from e
            except FileNotFoundError as e:
                raise AssetMissingError(
                    f"assets_dir 目录不存在: {assets.assets_dir}"
                ) from e

    @classmethod
    def _validate_single_asset(cls, rel_path: str, field_name: str) -> None:
        """校验单个资源文件。

        Args:
            rel_path: 相对路径
            field_name: 字段名（用于错误消息）

        Raises:
            AssetPathError: 路径不合法
            AssetMissingError: 文件不存在
            AssetSizeError: 文件过大
        """
        try:
            abs_path = resolve_safe(rel_path)
        except PermissionError as e:
            raise AssetPathError(f"{field_name} 路径穿越: {rel_path}") from e
        except FileNotFoundError as e:
            raise AssetMissingError(f"{field_name} 文件不存在: {rel_path}") from e

        # 文件大小校验
        size = abs_path.stat().st_size
        if size > MAX_ASSET_SIZE_BYTES:
            raise AssetSizeError(
                f"{field_name} 文件过大: {rel_path} "
                f"({size} bytes > {MAX_ASSET_SIZE_BYTES} bytes)"
            )

        # 扩展名校验
        ext = abs_path.suffix.lower()
        if ext not in ALLOWED_ASSET_EXTENSIONS:
            raise AssetPathError(
                f"{field_name} 扩展名不允许: {ext} (file: {rel_path})"
            )

    @classmethod
    def _scan_html_forbidden_tags(cls, entry_html_path: str) -> None:
        """扫描 entry HTML 文件中是否包含禁止的标签。

        使用简单的正则扫描而非完整 HTML 解析，足以检测明显违规。

        Args:
            entry_html_path: entry HTML 的相对路径

        Raises:
            XMLValidationError: 发现禁止标签
        """
        try:
            abs_path = resolve_safe(entry_html_path)
        except (PermissionError, FileNotFoundError):
            # 路径问题已在 _validate_single_asset 中处理
            return

        content = abs_path.read_text(encoding="utf-8", errors="ignore")
        content_lower = content.lower()

        for tag in HTML_FORBIDDEN_TAGS:
            # 匹配 <tag 或 <tag> 或 <tag/> 模式
            pattern = f"<{tag}[\\s>/]"
            if re.search(pattern, content_lower):
                raise XMLValidationError(
                    f"entry_html 中禁止使用 <{tag}> 标签 (file: {entry_html_path})"
                )
