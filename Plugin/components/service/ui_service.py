"""WebUI UI Service 组件。

按设计文档 3.1 暴露给其他插件调用的框架级 Service。
外部插件通过 Service Manager 获取本服务，动态注册前端扩展页面：

    from src.core.managers import get_service_manager

    service = get_service_manager().get_service("neo-mofox-webui:service:webui_ui")
    await service.register_ui_page(plugin_name, page_id, page_xml, order=100)

实现说明：
- 框架的 ServiceManager.get_service() 每次创建新的 Service 实例（非单例），
  因此本类不持有任何状态，所有方法转发到模块级单例
  WebuiServiceManager（get_webui_service_manager()），
  保证页面注册表在不同调用方之间共享、且与发现/Schema 端点读写同一份数据。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.app.plugin_system.api.log_api import get_logger  # type: ignore
from src.core.components.base.service import BaseService  # type: ignore

from ...managers.webui_service_manager import get_webui_service_manager

if TYPE_CHECKING:
    from src.core.components.base.plugin import BasePlugin  # type: ignore

logger = get_logger("webui_ui_service")


class WebuiUiService(BaseService):
    """WebUI 前端扩展页面注册服务。

    供其他插件在 on_plugin_loaded() 中调用，动态注册 XML 描述的前端页面。
    所有方法转发到 WebuiServiceManager 单例。
    """

    service_name: str = "webui_ui"
    service_description: str = "WebUI 前端扩展页面动态注册服务"
    version: str = "1.0.0"

    dependencies: list[str] = []

    def __init__(self, plugin: "BasePlugin") -> None:
        """初始化服务组件。

        Args:
            plugin: 所属插件实例（由框架注入）
        """
        super().__init__(plugin)
        self._manager = get_webui_service_manager()

    async def register_ui_page(
        self,
        plugin_name: str,
        page_id: str,
        page_xml: str,
        order: int = 0,
    ) -> bool:
        """注册插件前端页面（转发到 WebuiServiceManager）。

        Args:
            plugin_name: 调用方插件名称（必须已加载）
            page_id: 页面唯一标识符
            page_xml: XML Schema 页面描述字符串
            order: 排序权重（越小越靠前）

        Returns:
            是否注册成功
        """
        return await self._manager.register_ui_page(
            plugin_name=plugin_name,
            page_id=page_id,
            page_xml=page_xml,
            order=order,
        )

    def unregister_ui_page(self, plugin_name: str, page_id: str) -> bool:
        """注销指定插件的单个页面（转发）。"""
        return self._manager.unregister_ui_page(plugin_name, page_id)

    def unregister_plugin_pages(self, plugin_name: str) -> int:
        """注销指定插件的全部页面（转发）。"""
        return self._manager.unregister_plugin_pages(plugin_name)

    def get_all_pages(self) -> list[dict[str, Any]]:
        """获取所有已注册页面的元数据列表（转发）。"""
        return self._manager.get_all_pages()

    def get_page_xml(self, plugin_name: str, page_id: str) -> str | None:
        """获取指定页面的 XML 描述字符串（转发）。"""
        return self._manager.get_page_xml(plugin_name, page_id)

    async def notify_page_updated(self, plugin_name: str, page_id: str) -> None:
        """通知前端指定页面已更新，触发热更新（转发）。

        插件重新注册页面后调用本方法，前端将刷新页面列表，
        并在当前正查看该页面时自动重载其 Schema（设计文档 3.2）。

        Args:
            plugin_name: 页面所属插件名
            page_id: 页面唯一标识符
        """
        await self._manager.notify_page_updated(plugin_name, page_id)
