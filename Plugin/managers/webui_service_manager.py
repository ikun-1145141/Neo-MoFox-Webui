"""WebUI Service 管理器 - 插件前端扩展页面动态注册系统。

提供 register_ui_page() 注册 API、页面发现和 Schema 查询。
按 Neo-MoFox-WebUI-Plugin-Extension-Design.md v2.0.0 设计实现。
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.plugin_api import is_plugin_loaded
from ..utils.xml_schema_validator import XmlSchemaValidator

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = get_logger("webui_service_manager")


@dataclass
class PageRegistration:
    """已注册页面信息。存储 XML 页面描述及其元数据。"""
    plugin_name: str
    page_id: str
    page_xml: str
    title: str
    description: str | None = None
    icon: str | None = None
    api_base: str | None = None
    order: int = 0
    registered_at: float = field(default_factory=time.time)

    def to_discovery_dict(self) -> dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "page_id": self.page_id,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "api_base": self.api_base,
            "order": self.order,
            "registered_at": self.registered_at,
        }


# ============================================================
# WebUI Service Manager 单例
# ============================================================

class WebuiServiceManager:
    """WebUI Service 管理器。

    提供页面注册、发现和 Schema 查询的核心逻辑。
    在内存中维护所有已注册页面的字典。

    存储结构：
        _registered_pages: dict[str, dict[str, PageRegistration]]
        第一层 key = plugin_name，第二层 key = page_id
    """

    def __init__(self) -> None:
        self._registered_pages: dict[str, dict[str, PageRegistration]] = {}
        self._validator = XmlSchemaValidator()
        # 已建立的 WebSocket 连接集合（用于页面热更新通知，设计文档 3.2）
        self._ws_connections: set["WebSocket"] = set()
        logger.info("WebUI Service Manager 已初始化，等待页面注册...")

    # ============================================================
    # 页面注册
    # ============================================================

    async def register_ui_page(
        self,
        plugin_name: str,
        page_id: str,
        page_xml: str,
        order: int = 0,
    ) -> bool:
        """注册插件前端页面。

        插件在 on_plugin_loaded() 中调用此方法，
        传入 XML 字符串动态注册自定义页面。

        Args:
            plugin_name: 插件名称（必须已加载）
            page_id: 页面唯一标识符
            page_xml: XML Schema 页面描述字符串
            order: 排序权重（越小越靠前）

        Returns:
            是否注册成功
        """
        # 注册时不校验 is_plugin_loaded：按设计文档 3.1，插件在 on_plugin_loaded()
        # 钩子中调用本方法，而框架此时尚未将插件标记为 loaded，校验必然误伤。
        # 已加载状态的过滤在 get_all_pages()（discovery）层做运行时兜底。

        # XML 校验和元数据提取
        try:
            validated = self._validator.validate_and_extract(page_xml)
        except ValueError as e:
            logger.error(f"XML 校验失败 [{plugin_name}/{page_id}]: {e}")
            return False

        # 3. 创建注册记录
        registration = PageRegistration(
            plugin_name=plugin_name,
            page_id=page_id,
            page_xml=page_xml,
            title=validated["title"],
            description=validated.get("description"),
            icon=validated.get("icon"),
            api_base=validated.get("api_base"),
            order=order,
        )

        # 4. 存储到内存字典（按 plugin_name -> page_id 两层索引）
        if plugin_name not in self._registered_pages:
            self._registered_pages[plugin_name] = {}
        is_update = page_id in self._registered_pages[plugin_name]
        self._registered_pages[plugin_name][page_id] = registration

        if is_update:
            logger.info(f"页面已更新: {plugin_name}/{page_id} -> {registration.title}")
        else:
            logger.info(f"页面已注册: {plugin_name}/{page_id} -> {registration.title}")
        return True

    # ============================================================
    # 页面注销
    # ============================================================

    def unregister_ui_page(self, plugin_name: str, page_id: str) -> bool:
        """注销指定插件的单个页面。

        Args:
            plugin_name: 插件名称
            page_id: 页面唯一标识符

        Returns:
            是否成功注销（页面不存在时返回 False）
        """
        pages = self._registered_pages.get(plugin_name)
        if not pages or page_id not in pages:
            return False
        del pages[page_id]
        if not pages:
            del self._registered_pages[plugin_name]
        logger.info(f"页面已注销: {plugin_name}/{page_id}")
        return True

    def unregister_plugin_pages(self, plugin_name: str) -> int:
        """注销指定插件的全部页面（用于插件卸载清理）。

        Args:
            plugin_name: 插件名称

        Returns:
            被注销的页面数量
        """
        pages = self._registered_pages.pop(plugin_name, None)
        if not pages:
            return 0
        count = len(pages)
        logger.info(f"已注销插件 {plugin_name} 的 {count} 个页面")
        return count

    # ============================================================
    # 页面发现与查询
    # ============================================================

    def get_all_pages(self) -> list[dict[str, Any]]:
        """获取所有已注册页面的元数据列表。

        只返回当前仍处于已加载状态的插件页面（设计文档 8.3）。
        结果按 order 升序、page_id 升序排序。

        Returns:
            页面元数据字典列表
        """
        pages: list[dict[str, Any]] = []
        for plugin_name, registrations in self._registered_pages.items():
            if not is_plugin_loaded(plugin_name):
                continue
            for registration in registrations.values():
                pages.append(registration.to_discovery_dict())
        pages.sort(key=lambda item: (item["order"], item["page_id"]))
        return pages

    def get_page(self, plugin_name: str, page_id: str) -> PageRegistration | None:
        """获取指定页面的完整注册信息。

        Args:
            plugin_name: 插件名称
            page_id: 页面唯一标识符

        Returns:
            PageRegistration 实例，不存在时返回 None
        """
        return self._registered_pages.get(plugin_name, {}).get(page_id)

    def get_page_xml(self, plugin_name: str, page_id: str) -> str | None:
        """获取指定页面的 XML 描述字符串。

        Args:
            plugin_name: 插件名称
            page_id: 页面唯一标识符

        Returns:
            XML 字符串，不存在时返回 None
        """
        registration = self.get_page(plugin_name, page_id)
        return registration.page_xml if registration else None

    # ============================================================
    # WebSocket 页面热更新通知（设计文档 3.2 / 10.3）
    # ============================================================

    def add_ws_connection(self, ws: "WebSocket") -> None:
        """注册一个 WebSocket 连接（由 UI Router 的 WS 端点调用）。"""
        self._ws_connections.add(ws)

    def remove_ws_connection(self, ws: "WebSocket") -> None:
        """移除一个 WebSocket 连接。"""
        self._ws_connections.discard(ws)

    async def notify_page_updated(self, plugin_name: str, page_id: str) -> None:
        """通过 WebSocket 通知所有前端：指定页面已更新。

        插件在运行时调用 register_ui_page 覆盖旧页面后，可调用本方法
        （经由 WebuiUiService 转发）触发前端刷新页面列表 / 重载当前 Schema，
        实现热更新。

        Args:
            plugin_name: 页面所属插件名
            page_id: 页面唯一标识符
        """
        message = {
            "type": "page_updated",
            "plugin_name": plugin_name,
            "page_id": page_id,
        }
        disconnected: list["WebSocket"] = []
        for ws in self._ws_connections:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.debug(f"WS 发送失败（连接可能已断开）: {exc}")
                disconnected.append(ws)
        for ws in disconnected:
            self._ws_connections.discard(ws)
        if self._ws_connections:
            logger.info(
                f"已推送页面更新通知: {plugin_name}/{page_id} "
                f"(连接数={len(self._ws_connections)})"
            )


# ============================================================
# 单例工厂
# ============================================================

_webui_service_manager: WebuiServiceManager | None = None


def get_webui_service_manager() -> WebuiServiceManager:
    """获取 WebuiServiceManager 单例。"""
    global _webui_service_manager
    if _webui_service_manager is None:
        _webui_service_manager = WebuiServiceManager()
    return _webui_service_manager