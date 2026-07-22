"""Demo HTML UI Plugin - HTML 前端 UI 演示插件。

展示 HTML 轨的完整能力：sys.* 桥接对象、Web Components 命令式 API、
fetch 代理（自动 Token + BaseResponse 解包）、事件总线、对话框、
Toast 通知、主题读取、格式化工具等。

与 demo_ui_plugin（XML 轨）形成对照：
- XML 轨：声明式，通过 <api> 模板 + 管道指令编排交互
- HTML 轨：命令式，通过 sys.* + Web Components 方法调用编排交互
"""

from __future__ import annotations

from src.app.plugin_system.base import BasePlugin, register_plugin  # type: ignore

from .router import DemoHTMLRouter


@register_plugin
class DemoHTMLPlugin(BasePlugin):
    """HTML 前端 UI 演示插件。"""

    plugin_name = "demo_html_plugin"
    plugin_description = "展示 HTML 轨 sys.* 桥接对象与 Web Components 命令式用法"
    plugin_version = "1.0.0"

    configs: list[type] = []
    dependent_components: list[str] = ["neo-mofox-webui:service:plugin_ui"]

    def get_components(self) -> list[type]:
        """返回插件组件类。"""
        return [DemoHTMLRouter]

    async def on_plugin_loaded(self) -> None:
        """插件加载后注册 HTML UI 页面。

        HTML 模式通过 assets 字段声明资源文件路径。
        路径以「插件根目录」为基准（系统通过 plugin_name 自动解析）。
        系统会自动为 entry_html / styles / scripts 生成可访问的 URL。
        """
        from src.app.plugin_system.api.service_api import get_service  # type: ignore

        service = get_service("neo-mofox-webui:service:plugin_ui")

        # 注册 HTML 页面
        # assets 中的路径相对于插件根目录
        await service.register_ui_page(
            plugin_name="demo_html_plugin",
            page_id="dashboard",
            title="HTML Demo 仪表板",
            icon="code_blocks",
            description="展示 HTML 轨 sys.* 桥接与 Web Components 的命令式用法",
            order=20,
            mode="html",
            assets={
                "entry_html": "assets/index.html",
                "styles": ["assets/styles.css"],
                "scripts": ["assets/script.js"],
                "assets_dir": "assets",
            },
        )
