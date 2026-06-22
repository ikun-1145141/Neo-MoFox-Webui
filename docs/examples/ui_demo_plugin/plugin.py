"""WebUI 扩展示例插件入口。

演示如何在插件加载后，通过 WebUI 暴露的 webui_ui Service 动态注册一个
XML 描述的前端页面（留言板）。对应设计文档 Phase 5。

关键点：
- manifest.json 中声明 dependencies.plugins=["neo-mofox-webui"]，
  保证本插件在 WebUI 插件之后加载，注册时 Service 已就绪。
- Service 签名为 "{webui_plugin_name}:service:webui_ui"，
  即 "neo-mofox-webui:service:webui_ui"。
"""

from __future__ import annotations

from src.core.components.base.plugin import BasePlugin  # type: ignore
from src.core.components.loader import register_plugin  # type: ignore
from src.app.plugin_system.api.log_api import get_logger  # type: ignore

from .demo_router import UiDemoRouter

logger = get_logger("ui_demo_plugin")

# WebUI 前端扩展页面 XML（留言板）。
# 按钮端点使用绝对路径直达后端，故无需 <api-base>。
_PAGE_XML = """
<ui-page schema-version="1.0" xmlns="https://mofox.studio/ui-schema/v1">
  <metadata>
    <title>留言板 Demo</title>
    <description>演示 WebUI 插件前端扩展：表单校验 + POST 提交 + 表格自动加载</description>
    <icon>material-symbols:forum-outline-rounded</icon>
  </metadata>
  <layout>
    <container layout="vertical" spacing="24" padding="24">
      <card title="写留言" elevation="1">
        <container layout="vertical" spacing="16">
          <input-field
            id="name"
            label="昵称"
            type="text"
            placeholder="2-20 个字符"
            required="true"
            min-length="2"
            max-length="20"
            error-message="昵称需为 2-20 个字符"
            data-bind="form.name"
          />
          <textarea
            id="message"
            label="留言内容"
            rows="4"
            placeholder="说点什么..."
            required="true"
            min-length="1"
            max-length="200"
            error-message="留言内容不能为空，且不超过 200 字"
            data-bind="form.message"
          />
          <container layout="horizontal" justify="end">
            <button
              type="primary"
              api-endpoint="/webui/api/ui-demo/greet"
              api-method="POST"
              api-data-from="form"
              on-success="show-toast:留言成功;refresh-table:msgTable"
            >
              提交
            </button>
          </container>
        </container>
      </card>

      <card title="全部留言" elevation="1">
        <data-table
          id="msgTable"
          api-endpoint="/webui/api/ui-demo/list"
          api-method="GET"
          auto-refresh="true"
        >
          <column key="name" label="昵称" width="160" />
          <column key="message" label="留言" />
          <column key="time" label="时间" width="200" />
        </data-table>
      </card>
    </container>
  </layout>
</ui-page>
"""

# 占位：下方追加插件类定义


@register_plugin
class UiDemoPlugin(BasePlugin):
    """WebUI 扩展示例插件。"""

    plugin_name: str = "ui_demo_plugin"
    plugin_description: str = "WebUI 插件前端扩展系统的最小可运行示例"
    plugin_version: str = "1.0.0"

    configs: list[type] = []
    dependent_components: list[str] = []

    # WebUI 暴露的页面注册服务签名
    _WEBUI_SERVICE_SIG = "neo-mofox-webui:service:webui_ui"

    def get_components(self) -> list[type]:
        """返回插件组件列表。"""
        return [UiDemoRouter]

    async def on_plugin_loaded(self) -> None:
        """插件加载后注册前端页面。"""
        from src.core.managers import get_service_manager  # type: ignore

        service = get_service_manager().get_service(self._WEBUI_SERVICE_SIG)
        if service is None:
            logger.warning(
                "未找到 WebUI 页面注册服务 (%s)，跳过前端页面注册。"
                "请确认 neo-mofox-webui 插件已加载。",
                self._WEBUI_SERVICE_SIG,
            )
            return

        ok = await service.register_ui_page(
            plugin_name=self.plugin_name,
            page_id="message-board",
            page_xml=_PAGE_XML,
            order=100,
        )
        if ok:
            logger.info("留言板页面注册成功")
        else:
            logger.error("留言板页面注册失败")

    async def on_plugin_unloaded(self) -> None:
        """插件卸载时清理已注册页面。"""
        from src.core.managers import get_service_manager  # type: ignore

        service = get_service_manager().get_service(self._WEBUI_SERVICE_SIG)
        if service is not None:
            service.unregister_plugin_pages(self.plugin_name)
            logger.info("已清理留言板页面")
