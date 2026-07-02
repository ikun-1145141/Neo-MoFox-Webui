"""XML Schema 校验器（XSD 强校验）。

对插件注册的 XML 页面描述进行合法性校验，并提取元数据。

校验策略（对应设计文档 8.1 XML 注入防护 - Schema 强校验）：
- 使用 lxml 加载 ``ui_schema.xsd`` 对 XML 做 XSD 强校验。
- XSD 带 targetNamespace ``https://mofox.studio/ui-schema/v1``，
  因此所有 ``<ui-page>`` 文档必须声明该默认命名空间
  （``xmlns="https://mofox.studio/ui-schema/v1"``）。
- XSD 默认拒绝未声明的元素 / 属性，因此 ``<script>``、``<iframe>``、
  ``onclick`` 等非法标签与事件属性天然被拒绝。
- ``<template>`` 子树含 Vue 模板语法（如 ``:color``、``{{ row.x }}``），
  在 XSD 中以 ``<xs:any processContents="skip"/>`` 放行，不参与校验，
  由前端在隔离上下文中渲染并做二次清理。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree

# 目标命名空间（须与 ui_schema.xsd 的 targetNamespace 一致）
_UI_NS = "https://mofox.studio/ui-schema/v1"
_NS_MAP = {"ui": _UI_NS}

# XSD 文件路径（与本模块同目录）
_XSD_PATH = Path(__file__).parent / "ui_schema.xsd"

# 模块加载时编译 XSD（失败则在首次校验时报错）
_schema: etree.XMLSchema | None = None


def _get_schema() -> etree.XMLSchema:
    """惰性加载并缓存编译后的 XSD Schema。"""
    global _schema
    if _schema is None:
        _schema = etree.XMLSchema(etree.parse(str(_XSD_PATH)))
    return _schema


class XmlSchemaValidator:
    """XML 页面描述校验器（基于 lxml XSD）。

    对插件注册的 XML 字符串执行 XSD 强校验，
    并提取 ``<metadata>`` 中的标题、描述、图标和 API 前缀。
    """

    def validate_and_extract(self, page_xml: str) -> dict[str, Any]:
        """校验 XML 并提取元数据。

        Args:
            page_xml: 待校验的 XML 字符串

        Returns:
            包含 ``title``/``description``/``icon``/``api_base`` 的元数据字典。

        Raises:
            ValueError: XML 不合法（解析失败、XSD 校验失败、缺少必需的
                schema-version 或 title）。
        """
        if not page_xml or not page_xml.strip():
            raise ValueError("XML 内容为空")

        # 1. 解析 XML
        try:
            doc = etree.fromstring(page_xml.encode("utf-8"))
        except etree.XMLSyntaxError as exc:
            raise ValueError(f"XML 语法错误: {exc}") from exc

        # 2. 根节点必须为 ui-page（命名空间限定）
        if doc.tag != f"{{{_UI_NS}}}ui-page":
            local = etree.QName(doc).localname if doc.tag else "?"
            raise ValueError(
                f"根节点必须为命名空间 {_UI_NS} 下的 <ui-page>，实际为 <{local}>。"
                f"请确保根元素声明 xmlns=\"{_UI_NS}\""
            )

        # 3. XSD 强校验
        schema = _get_schema()
        if not schema.validate(doc):
            errors = "\n".join(str(e) for e in schema.error_log)
            raise ValueError(f"XSD 校验失败:\n{errors}")

        # 4. schema-version 必需（XSD 已要求，此处兜底明确报错）
        if not doc.get("schema-version"):
            raise ValueError("根节点 <ui-page> 缺少必需属性 schema-version")

        # 5. 提取元数据
        metadata = self._extract_metadata(doc)
        if not metadata.get("title"):
            raise ValueError("<metadata> 缺少必需的 <title>")

        return metadata

    def _extract_metadata(self, root: etree._Element) -> dict[str, Any]:
        """从根节点下的 <metadata> 提取元数据。"""
        result: dict[str, Any] = {
            "title": None,
            "description": None,
            "icon": None,
            "api_base": None,
        }

        metadata = root.find("ui:metadata", _NS_MAP)
        if metadata is None:
            return result

        field_map = {
            "title": "title",
            "description": "description",
            "icon": "icon",
            "api-base": "api_base",
        }
        for child in metadata:
            local = etree.QName(child).localname
            key = field_map.get(local)
            if key is None:
                continue
            text = (child.text or "").strip()
            result[key] = text or None

        return result
