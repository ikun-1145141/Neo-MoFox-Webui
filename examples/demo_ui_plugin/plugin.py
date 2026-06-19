"""Demo UI Plugin - XML 前端 UI 演示插件。

展示如何注册自定义 API 路由，并通过 XML 声明式 UI 与之交互。
"""

from src.app.plugin_system.base import BasePlugin, register_plugin

from .router import DemoUIRouter


@register_plugin
class DemoUIPlugin(BasePlugin):
    """XML 前端 UI 演示插件。"""

    plugin_name = "demo_ui_plugin"
    plugin_description = "展示 XML 前端 UI 系统各组件和 API 交互"
    plugin_version = "1.0.0"

    configs: list[type] = []
    dependent_components: list[str] = ["neo-mofox-webui:service:plugin_ui"]

    def get_components(self) -> list[type]:
        """返回插件组件类。"""
        return [DemoUIRouter]

    async def on_plugin_loaded(self) -> None:
        """插件加载后注册 UI 页面。"""
        from src.app.plugin_system.api.service_api import get_service  # type: ignore

        service = get_service("neo-mofox-webui:service:plugin_ui")

        # 注册 XML 页面（纯关键字参数，无需导入 WebUI 内部类型）
        await service.register_ui_page(
            plugin_name="demo_ui_plugin",
            page_id="dashboard",
            title="Demo 仪表板",
            icon="dashboard",
            description="展示 XML UI 组件和 API 交互的示例页面",
            order=10,
            mode="xml",
            xml=_DASHBOARD_XML,
        )


# === XML 页面内容 ===

_DASHBOARD_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<page version="3.1" xmlns:bind="urn:neo-mofox:bind">
  <definitions>
    <var name="greeting" default="'Hello, World!'" />
    <var name="counter" default="0" />
    <var name="username" default="''" />
    <var name="items" default="[]" />
    <var name="featureEnabled" default="false" />
    <var name="volume" default="60" />
    <api id="getItems" method="GET" url="/router/demo_ui_router/demo-ui/items" response-to="items" auto-fetch="true" />
    <api id="addItem" method="POST" url="router/demo_ui_router/demo-ui/items" body='{"name": "{username}"}' response-to="items" />
  </definitions>

  <layout>
    <vbox gap="1.5rem">
      <!-- 标题区域 -->
      <card title="XML UI 演示" variant="elevated" padding="1.5rem">
        <vbox gap="0.75rem">
          <sys-text variant="title">欢迎使用插件 UI 系统</sys-text>
          <sys-text variant="body">这个页面展示了 XML 声明式 UI 的各种组件和 API 交互能力。</sys-text>
          <sys-text variant="caption">当前问候语: {greeting}</sys-text>
        </vbox>
      </card>

      <!-- 计数器演示 -->
      <card title="计数器" variant="outlined">
        <hbox gap="1rem" align="center">
          <sys-button variant="outlined" on-click="set: counter={counter - 1}">
            -1
          </sys-button>
          <sys-text variant="subtitle" bold="true">{counter}</sys-text>
          <sys-button variant="filled" on-click="set: counter={counter + 1}">
            +1
          </sys-button>
          <sys-button variant="tonal" on-click="set: counter=0">
            重置
          </sys-button>
        </hbox>
      </card>

      <!-- 表单 + API 交互 -->
      <card title="添加条目" variant="outlined">
        <vbox gap="0.75rem">
          <sys-input label="名称" placeholder="输入条目名称..." bind:value="username" />
          <hbox gap="0.5rem">
            <sys-button variant="filled" icon="add" on-click="api: addItem | notify: '添加成功', 'success'">
              添加
            </sys-button>
            <sys-button variant="text" on-click="set: username=''">
              清空
            </sys-button>
          </hbox>
        </vbox>
      </card>

      <!-- 数据展示 -->
      <card title="数据列表" variant="elevated">
        <vbox gap="0.75rem">
          <hbox gap="0.5rem" align="center">
            <sys-text variant="body">共 {len(items)} 条数据</sys-text>
            <spacer />
            <sys-icon-button icon="refresh" on-click="api: getItems" />
          </hbox>
          <sys-table data="{items}" striped="true" />
        </vbox>
      </card>

      <!-- 各种组件展示 -->
      <card title="组件画廊" variant="outlined">
        <grid columns="2" gap="1rem">
          <vbox gap="0.5rem">
            <sys-text variant="subtitle">标签</sys-text>
            <hbox gap="0.25rem" wrap="true">
              <sys-tag variant="default">默认</sys-tag>
              <sys-tag variant="primary">主要</sys-tag>
              <sys-tag variant="success">成功</sys-tag>
              <sys-tag variant="error">错误</sys-tag>
            </hbox>
          </vbox>
          <vbox gap="0.5rem">
            <sys-text variant="subtitle">徽章</sys-text>
            <hbox gap="0.5rem">
              <sys-badge value="3" />
              <sys-badge value="99+" />
            </hbox>
          </vbox>
          <vbox gap="0.5rem">
            <sys-text variant="subtitle">开关</sys-text>
            <sys-switch label="启用功能" bind:value="featureEnabled" />
          </vbox>
          <vbox gap="0.5rem">
            <sys-text variant="subtitle">滑块</sys-text>
            <sys-slider label="音量" bind:value="volume" min="0" max="100" />
          </vbox>
        </grid>
      </card>

      <!-- 条件渲染演示 -->
      <card title="条件渲染" variant="outlined">
        <vbox gap="0.5rem">
          <sys-text variant="body">计数器 &gt; 5 时显示下方内容：</sys-text>
          <sys-text variant="body" hidden="{counter &lt;= 5}">
            🎉 计数器已超过 5！当前值: {counter}
          </sys-text>
          <sys-text variant="caption" hidden="{counter &gt; 5}">
            （继续点击 +1 直到超过 5）
          </sys-text>
        </vbox>
      </card>

      <!-- 分割线和间距演示 -->
      <card title="布局辅助" variant="outlined">
        <vbox gap="0.5rem">
          <sys-text variant="body">分割线：</sys-text>
          <divider />
          <sys-text variant="body">上方有水平分割线</sys-text>
          <hbox gap="0.5rem" align="center">
            <sys-text variant="body">左</sys-text>
            <divider direction="vertical" />
            <sys-text variant="body">右</sys-text>
          </hbox>
        </vbox>
      </card>
    </vbox>
  </layout>
</page>
"""
