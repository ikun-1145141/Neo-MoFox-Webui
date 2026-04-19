"""Neo-MoFox-Webui 插件入口。

提供 WebUI 后端支持。
"""

from __future__ import annotations

from src.core.components.base.plugin import BasePlugin
from src.core.components.loader import register_plugin
from src.app.plugin_system.api.log_api import get_logger

from .components.router.webui_router import WebuiSettingsRouter

logger = get_logger("webui_plugin")


@register_plugin
class WebuiPlugin(BasePlugin):
    """WebUI 插件。

    提供 WebUI 的后端支持，包括：
    - 设置管理 API
    - 静态文件服务（未来）
    - Git 更新管理（未来）
    """

    plugin_name: str = "webui"
    plugin_description: str = "Neo-MoFox WebUI 后端插件"
    plugin_version: str = "1.0.0"

    configs: list[type] = []
    dependent_components: list[str] = []

    def get_components(self) -> list[type]:
        """获取插件内所有组件类。

        Returns:
            组件类列表
        """
        components: list[type] = [
            WebuiSettingsRouter,
        ]
        return components

    async def on_plugin_loaded(self) -> None:
        """插件加载钩子。"""
        logger.info(f"WebUI 插件 v{self.plugin_version} 已加载")
        logger.info("API 路径: /api/webui")

    async def on_plugin_unloaded(self) -> None:
        """插件卸载钩子。"""
        logger.info("WebUI 插件即将卸载")
