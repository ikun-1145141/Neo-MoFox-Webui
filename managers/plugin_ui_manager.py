"""插件 UI 注册表管理器。

提供内存态注册表，管理所有插件页面的注册/查询/卸载。
进程重启即清空（设计文档 §3.5 硬要求）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Literal

from src.app.plugin_system.api.log_api import get_logger  # type: ignore

from ..utils.plugin_ui.plugin_ui_types import (
    HTMLAssets,
    PageDetail,
    PageMode,
    PageRegistration,
    PageSchemaResponse,
    PageSummary,
    RegisteredPage,
)

logger = get_logger("plugin_ui_manager")


class PluginUIManager:
    """插件 UI 注册表。内存态，进程重启清空。

    负责注册元数据的存储、查询和路径/URL 生成。
    不做校验——校验由 PluginUIValidators 在 Service 层处理。
    """

    def __init__(self) -> None:
        """初始化注册表。"""
        # key: (plugin_name, page_id) -> RegisteredPage
        self._registry: dict[tuple[str, str], RegisteredPage] = {}
        # 反向索引：plugin_name -> set[page_id]
        self._by_plugin: dict[str, set[str]] = {}
        # 写操作锁
        self._lock = asyncio.Lock()

    async def register(
        self, reg: PageRegistration, plugin_root: Path
    ) -> RegisteredPage:
        """注册或更新一个插件页面。

        Args:
            reg: 页面注册元数据（已通过校验）
            plugin_root: 插件根目录绝对路径

        Returns:
            加工后的 RegisteredPage 实例
        """
        route_path = self._build_route_path(reg.plugin_name, reg.page_id)
        desktop_assets_urls = self._build_assets_urls(
            reg.plugin_name, reg.page_id, "desktop", reg.assets
        )
        mobile_assets_urls = None
        if reg.mode == PageMode.HTML and reg.mobile_assets:
            mobile_assets_urls = self._build_assets_urls(
                reg.plugin_name, reg.page_id, "mobile", reg.mobile_assets
            )

        page = RegisteredPage(
            plugin_name=reg.plugin_name,
            page_id=reg.page_id,
            title=reg.title,
            icon=reg.icon,
            description=reg.description,
            order=reg.order,
            mode=reg.mode,
            xml=reg.xml,
            assets=reg.assets,
            mobile_xml=reg.mobile_xml,
            mobile_assets=reg.mobile_assets,
            route_path=route_path,
            desktop_assets_urls=desktop_assets_urls,
            mobile_assets_urls=mobile_assets_urls,
            registered_at=datetime.now(),
            plugin_root=plugin_root,
        )

        async with self._lock:
            key = (reg.plugin_name, reg.page_id)
            is_update = key in self._registry
            self._registry[key] = page

            if reg.plugin_name not in self._by_plugin:
                self._by_plugin[reg.plugin_name] = set()
            self._by_plugin[reg.plugin_name].add(reg.page_id)

        action = "updated" if is_update else "registered"
        logger.info(
            f"Plugin UI page {action}: {reg.plugin_name}/{reg.page_id} "
            f"(mode={reg.mode.value})"
        )
        return page

    async def unregister(self, plugin_name: str, page_id: str) -> bool:
        """卸载单个页面注册。

        幂等操作：key 不存在时返回 False，不抛异常。

        Args:
            plugin_name: 插件名称
            page_id: 页面标识

        Returns:
            是否真的存在并被移除
        """
        async with self._lock:
            key = (plugin_name, page_id)
            if key not in self._registry:
                return False
            del self._registry[key]
            if plugin_name in self._by_plugin:
                self._by_plugin[plugin_name].discard(page_id)
                if not self._by_plugin[plugin_name]:
                    del self._by_plugin[plugin_name]

        logger.info(f"Plugin UI page unregistered: {plugin_name}/{page_id}")
        return True

    async def unregister_all(self, plugin_name: str) -> int:
        """批量卸载指定插件的所有页面。

        Args:
            plugin_name: 插件名称

        Returns:
            被清理的页面数量
        """
        async with self._lock:
            page_ids = self._by_plugin.pop(plugin_name, set())
            count = 0
            for page_id in page_ids:
                key = (plugin_name, page_id)
                if key in self._registry:
                    del self._registry[key]
                    count += 1

        if count > 0:
            logger.info(
                f"Plugin UI pages bulk unregistered: {plugin_name} ({count} pages)"
            )
        return count

    def list_pages(self, filter_plugin: str | None = None) -> list[PageSummary]:
        """获取页面摘要列表。

        Args:
            filter_plugin: 可选的插件名过滤

        Returns:
            按 order 升序排列的 PageSummary 列表
        """
        pages: list[PageSummary] = []
        for page in self._registry.values():
            if filter_plugin and page.plugin_name != filter_plugin:
                continue
            pages.append(
                PageSummary(
                    plugin_name=page.plugin_name,
                    page_id=page.page_id,
                    title=page.title,
                    icon=page.icon,
                    description=page.description,
                    order=page.order,
                    mode=page.mode,
                    route_path=page.route_path,
                    has_mobile=page.has_mobile,
                )
            )
        pages.sort(key=lambda p: p.order)
        return pages

    def get_detail(self, plugin_name: str, page_id: str) -> PageDetail | None:
        """获取页面详情。

        Args:
            plugin_name: 插件名称
            page_id: 页面标识

        Returns:
            PageDetail 或 None（不存在时）
        """
        key = (plugin_name, page_id)
        page = self._registry.get(key)
        if page is None:
            return None

        return PageDetail(
            plugin_name=page.plugin_name,
            page_id=page.page_id,
            title=page.title,
            icon=page.icon,
            description=page.description,
            order=page.order,
            mode=page.mode,
            route_path=page.route_path,
            has_mobile=page.has_mobile,
            desktop_assets_urls=page.desktop_assets_urls,
            mobile_assets_urls=page.mobile_assets_urls,
        )

    def get_schema(
        self,
        plugin_name: str,
        page_id: str,
        variant: Literal["desktop", "mobile"] = "desktop",
    ) -> PageSchemaResponse | None:
        """获取页面渲染 schema。

        Args:
            plugin_name: 插件名称
            page_id: 页面标识
            variant: 变体类型（desktop 或 mobile）

        Returns:
            PageSchemaResponse 或 None（不存在/mobile 缺失时）
        """
        key = (plugin_name, page_id)
        page = self._registry.get(key)
        if page is None:
            return None

        if variant == "desktop":
            return PageSchemaResponse(
                plugin_name=page.plugin_name,
                page_id=page.page_id,
                mode=page.mode,
                xml=page.xml if page.mode == PageMode.XML else None,
                assets_urls=page.desktop_assets_urls
                if page.mode == PageMode.HTML
                else None,
            )
        elif variant == "mobile":
            if not page.has_mobile:
                return None
            return PageSchemaResponse(
                plugin_name=page.plugin_name,
                page_id=page.page_id,
                mode=page.mode,
                xml=page.mobile_xml
                if page.mode == PageMode.XML
                else None,
                assets_urls=page.mobile_assets_urls
                if page.mode == PageMode.HTML
                else None,
            )
        return None

    def get_registered_page(
        self, plugin_name: str, page_id: str
    ) -> RegisteredPage | None:
        """获取完整的 RegisteredPage 对象（内部用）。

        Args:
            plugin_name: 插件名称
            page_id: 页面标识

        Returns:
            RegisteredPage 或 None
        """
        return self._registry.get((plugin_name, page_id))

    # --- 私有方法 ---

    @staticmethod
    def _build_route_path(plugin_name: str, page_id: str) -> str:
        """生成系统路由路径。

        Args:
            plugin_name: 插件名称
            page_id: 页面标识

        Returns:
            系统路由路径字符串
        """
        return f"/plugins/{plugin_name}/{page_id}"

    @staticmethod
    def _build_assets_urls(
        plugin_name: str,
        page_id: str,
        variant: str,
        assets: HTMLAssets | None,
    ) -> dict[str, list[str]] | None:
        """生成 HTML 资源的绝对 URL 映射。

        Args:
            plugin_name: 插件名称
            page_id: 页面标识
            variant: 变体类型（desktop/mobile）
            assets: HTML 资源声明

        Returns:
            URL 映射字典或 None（非 HTML 模式时）
        """
        if assets is None:
            return None

        base = f"/webui/static/plugin-ui/{plugin_name}/{page_id}/{variant}"
        urls: dict[str, list[str]] = {
            "entry_html": [f"{base}/entry"],
            "styles": [f"{base}/style/{i}" for i in range(len(assets.styles))],
            "scripts": [f"{base}/script/{i}" for i in range(len(assets.scripts))],
        }
        return urls


# --- 单例工厂 ---

_plugin_ui_manager_instance: PluginUIManager | None = None


def get_plugin_ui_manager() -> PluginUIManager:
    """获取 PluginUIManager 全局单例。

    Returns:
        PluginUIManager 实例
    """
    global _plugin_ui_manager_instance
    if _plugin_ui_manager_instance is None:
        _plugin_ui_manager_instance = PluginUIManager()
        logger.info("PluginUIManager 单例已初始化")
    return _plugin_ui_manager_instance
