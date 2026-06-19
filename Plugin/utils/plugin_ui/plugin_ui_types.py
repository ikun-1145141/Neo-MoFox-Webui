"""插件 UI 扩展子系统数据模型。

定义注册表使用的所有 Pydantic 模型，是唯一权威 schema。
Service 入参、Router 返回、内部 Registry 存储的对象都用同一套。
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from .plugin_ui_constants import (
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
    PAGE_ID_PATTERN,
)


class PageMode(str, Enum):
    """页面渲染模式枚举。"""

    XML = "xml"
    HTML = "html"


class HTMLAssets(BaseModel):
    """HTML 轨资源声明。

    所有路径相对于主程序工作目录（CWD）。

    Attributes:
        entry_html: HTML 入口文件相对路径
        styles: CSS 文件相对路径列表，按数组顺序加载
        scripts: JS 文件相对路径列表，按数组顺序加载
        assets_dir: 静态资源根目录；为空时不暴露任何静态资源
    """

    entry_html: str = Field(..., description="相对于 CWD 的 HTML 入口路径")
    styles: list[str] = Field(default_factory=list, description="CSS 文件相对路径")
    scripts: list[str] = Field(default_factory=list, description="JS 文件相对路径")
    assets_dir: str | None = Field(default=None, description="静态资源根目录")

    @field_validator("entry_html")
    @classmethod
    def validate_entry_html(cls, v: str) -> str:
        """校验 entry_html 路径合法性。"""
        _validate_relative_path(v)
        if not v.endswith(".html"):
            raise ValueError("entry_html 必须以 .html 结尾")
        return v

    @field_validator("styles")
    @classmethod
    def validate_styles(cls, v: list[str]) -> list[str]:
        """校验 styles 路径合法性。"""
        for path in v:
            _validate_relative_path(path)
            if not path.endswith(".css"):
                raise ValueError(f"styles 中的路径必须以 .css 结尾: {path}")
        return v

    @field_validator("scripts")
    @classmethod
    def validate_scripts(cls, v: list[str]) -> list[str]:
        """校验 scripts 路径合法性。"""
        for path in v:
            _validate_relative_path(path)
            if not path.endswith(".js"):
                raise ValueError(f"scripts 中的路径必须以 .js 结尾: {path}")
        return v

    @field_validator("assets_dir")
    @classmethod
    def validate_assets_dir(cls, v: str | None) -> str | None:
        """校验 assets_dir 路径合法性。"""
        if v is not None:
            _validate_relative_path(v)
        return v


class PageRegistration(BaseModel):
    """页面注册入参（核心入参模型）。

    Attributes:
        plugin_name: 调用方声明的插件名称
        page_id: 同插件内唯一标识
        title: 页面显示名
        icon: Material Symbols 图标名
        description: 页面简介
        order: 排序权重（升序），默认 100
        mode: 渲染模式（桌面端和移动端共用）
        xml: XML 模式下的 XML 字符串（桌面端）
        assets: HTML 模式下的资源声明（桌面端）
        mobile_xml: XML 模式下的移动端 XML 字符串（可空，空则移动端 fallback 到桌面端）
        mobile_assets: HTML 模式下的移动端资源声明（可空，空则移动端 fallback 到桌面端）
    """

    plugin_name: str = Field(..., description="插件名称")
    page_id: str = Field(..., description="页面唯一标识")
    title: str = Field(..., description="页面显示名", max_length=MAX_TITLE_LENGTH)
    icon: str | None = Field(default=None, description="Material Symbols 图标名")
    description: str | None = Field(
        default=None, description="页面简介", max_length=MAX_DESCRIPTION_LENGTH
    )
    order: int = Field(default=100, description="排序权重，升序")
    mode: PageMode = Field(..., description="渲染模式（桌面端和移动端共用）")
    xml: str | None = Field(default=None, description="XML 模式下的 XML 字符串（桌面端）")
    assets: HTMLAssets | None = Field(
        default=None, description="HTML 模式下的资源声明（桌面端）"
    )
    mobile_xml: str | None = Field(
        default=None, description="XML 模式下的移动端 XML 字符串"
    )
    mobile_assets: HTMLAssets | None = Field(
        default=None, description="HTML 模式下的移动端资源声明"
    )

    @field_validator("page_id")
    @classmethod
    def validate_page_id(cls, v: str) -> str:
        """校验 page_id 格式。"""
        if not re.match(PAGE_ID_PATTERN, v):
            raise ValueError(
                f"page_id 不合法: '{v}'，必须匹配 {PAGE_ID_PATTERN}"
            )
        return v

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "PageRegistration":
        """校验 mode 与内容字段的一致性。

        规则：
        - mode=xml 时：xml 必填，assets 必须为 None，mobile_assets 必须为 None
        - mode=html 时：assets 必填，xml 必须为 None，mobile_xml 必须为 None
        """
        if self.mode == PageMode.XML:
            if not self.xml:
                raise ValueError("mode 为 xml 时，xml 字段不得为空")
            if self.assets is not None:
                raise ValueError("mode 为 xml 时，assets 必须为 None")
            if self.mobile_assets is not None:
                raise ValueError("mode 为 xml 时，mobile_assets 必须为 None")
        elif self.mode == PageMode.HTML:
            if self.xml is not None:
                raise ValueError("mode 为 html 时，xml 字段必须为 None")
            if not self.assets:
                raise ValueError("mode 为 html 时，assets 不得为空")
            if self.mobile_xml is not None:
                raise ValueError("mode 为 html 时，mobile_xml 必须为 None")
        return self


class RegisteredPage(BaseModel):
    """注册表内部存储的加工后页面数据。

    包含 PageRegistration 所有字段 + 系统生成的派生字段。

    Attributes:
        plugin_name: 插件名称
        page_id: 页面唯一标识
        title: 页面显示名
        icon: 图标名
        description: 页面简介
        order: 排序权重
        mode: 渲染模式（桌面端和移动端共用）
        xml: XML 字符串（桌面端，XML 模式）
        assets: 资源声明（桌面端，HTML 模式）
        mobile_xml: 移动端 XML 字符串（XML 模式）
        mobile_assets: 移动端资源声明（HTML 模式）
        route_path: 系统生成的路由路径
        desktop_assets_urls: HTML 模式下桌面端资源绝对 URL
        mobile_assets_urls: HTML 模式下移动端资源绝对 URL
        registered_at: 注册/更新时间戳
        plugin_root: 插件根目录绝对路径
    """

    plugin_name: str
    page_id: str
    title: str
    icon: str | None = None
    description: str | None = None
    order: int = 100
    mode: PageMode
    xml: str | None = None
    assets: HTMLAssets | None = None
    mobile_xml: str | None = None
    mobile_assets: HTMLAssets | None = None
    route_path: str
    desktop_assets_urls: dict[str, list[str]] | None = None
    mobile_assets_urls: dict[str, list[str]] | None = None
    registered_at: datetime = Field(default_factory=datetime.now)
    plugin_root: Path

    model_config = {"arbitrary_types_allowed": True}

    @property
    def has_mobile(self) -> bool:
        """是否存在移动端变体内容。"""
        return self.mobile_xml is not None or self.mobile_assets is not None


class PageSummary(BaseModel):
    """页面摘要信息（列表展示用，不含 schema）。

    Attributes:
        plugin_name: 插件名称
        page_id: 页面唯一标识
        title: 页面显示名
        icon: 图标名
        description: 页面简介
        order: 排序权重
        mode: 渲染模式
        route_path: 系统生成的路由路径
        has_mobile: 是否有移动端 variant
    """

    plugin_name: str
    page_id: str
    title: str
    icon: str | None = None
    description: str | None = None
    order: int = 100
    mode: PageMode
    route_path: str
    has_mobile: bool = False


class PageDetail(BaseModel):
    """页面详情信息（含 assets URL，不含 XML 内容）。

    Attributes:
        plugin_name: 插件名称
        page_id: 页面唯一标识
        title: 页面显示名
        icon: 图标名
        description: 页面简介
        order: 排序权重
        mode: 渲染模式（桌面端和移动端共用）
        route_path: 系统生成的路由路径
        has_mobile: 是否有移动端 variant
        desktop_assets_urls: 桌面端资源 URL
        mobile_assets_urls: 移动端资源 URL
    """

    plugin_name: str
    page_id: str
    title: str
    icon: str | None = None
    description: str | None = None
    order: int = 100
    mode: PageMode
    route_path: str
    has_mobile: bool = False
    desktop_assets_urls: dict[str, list[str]] | None = None
    mobile_assets_urls: dict[str, list[str]] | None = None


class PageSchemaResponse(BaseModel):
    """页面渲染 schema 响应（按 variant 返回 XML 或 assets URL）。

    Attributes:
        plugin_name: 插件名称
        page_id: 页面唯一标识
        mode: 渲染模式
        xml: XML 字符串（XML 模式）
        assets_urls: 资源 URL 集合（HTML 模式）
    """

    plugin_name: str
    page_id: str
    mode: PageMode
    xml: str | None = None
    assets_urls: dict[str, list[str]] | None = None


# --- 内部工具函数 ---


def _validate_relative_path(path: str) -> None:
    """校验路径必须为合法的相对路径。

    Args:
        path: 待校验路径字符串

    Raises:
        ValueError: 路径不合法时抛出
    """
    if not path:
        raise ValueError("路径不得为空")
    if path.startswith("/") or path.startswith("\\"):
        raise ValueError(f"路径必须为相对路径，不得以 / 或 \\ 开头: {path}")
    if ".." in Path(path).parts:
        raise ValueError(f"路径中不得包含 '..' 段: {path}")
