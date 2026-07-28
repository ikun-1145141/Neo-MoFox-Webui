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
        # i18n_path 指向本插件自带的 i18n JSON bundle；前端拿到后会自动注册，
        # XML 中的 {t('welcome')} / {t('form.add')} 等会命中本插件命名空间下的 key。
        await service.register_ui_page(
            plugin_name="demo_ui_plugin",
            page_id="dashboard",
            title="Demo 仪表板",
            icon="dashboard",
            description="展示 XML UI 组件和 API 交互的示例页面",
            order=10,
            mode="xml",
            xml=_DASHBOARD_XML,
            i18n_path="i18n/i18n.json",
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
    <var name="chartData" default="null" />
    <var name="lineChartData" default='{"xAxis":["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],"series":[{"name":"邮件","data":[120,132,101,134,90,230,210]},{"name":"访问","data":[220,182,191,234,290,330,310]}],"title":"周访问量统计"}' />
    <var name="barChartData" default='{"xAxis":["产品A","产品B","产品C","产品D"],"series":[{"name":"销量","data":[150,230,180,320]}],"title":"产品销量对比"}' />
    <var name="pieChartData" default='{"series":[{"name":"搜索引擎","value":1048},{"name":"直接访问","value":735},{"name":"邮件营销","value":580},{"name":"联盟广告","value":484},{"name":"视频广告","value":300}],"title":"访问来源分布"}' />
    <var name="radarChartData" default='{"indicator":[{"name":"销售","max":6500},{"name":"管理","max":16000},{"name":"技术","max":30000},{"name":"客服","max":38000},{"name":"研发","max":52000}],"series":[{"name":"预算","data":[4200,3000,20000,35000,50000]},{"name":"实际","data":[5000,14000,28000,26000,42000]}],"title":"部门能力评估"}' />
    <api id="getItems" method="GET" url="/router/demo_ui_router/demo-ui/items" response-to="items" auto-fetch="true" />
    <api id="addItem" method="POST" url="/router/demo_ui_router/demo-ui/items" body='{"name": "{username}"}' response-to="items" />
    <api id="getChartData" method="GET" url="/router/demo_ui_router/demo-ui/chart-data" response-to="chartData" raw-response="true" auto-fetch="true" />
  </definitions>

  <layout>
    <vbox gap="1.5rem">
      <!-- 标题区域 -->
      <card title="{t('title')}" variant="elevated" padding="1.5rem">
        <vbox gap="0.75rem">
          <sys-text variant="title">{t('welcome')}</sys-text>
          <sys-text variant="body">{t('welcomeBody')}</sys-text>
          <sys-text variant="caption">{t('currentGreeting', {'greeting': greeting})}</sys-text>
        </vbox>
      </card>

      <!-- 计数器演示 -->
      <card title="{t('counter.title')}" variant="outlined">
        <hbox gap="1rem" align="center">
          <sys-button variant="outlined" on-click="set: counter={counter - 1}">
            {t('counter.decrement')}
          </sys-button>
          <sys-text variant="subtitle" bold="true">{counter}</sys-text>
          <sys-button variant="filled" on-click="set: counter={counter + 1}">
            {t('counter.increment')}
          </sys-button>
          <sys-button variant="tonal" on-click="set: counter=0">
            {t('counter.reset')}
          </sys-button>
        </hbox>
      </card>

      <!-- 表单 + API 交互 -->
      <card title="{t('form.title')}" variant="outlined">
        <vbox gap="0.75rem">
          <sys-input label="{t('form.nameLabel')}" placeholder="{t('form.namePlaceholder')}" bind:value="username" />
          <hbox gap="0.5rem">
            <sys-button variant="filled" icon="add" on-click="api: addItem | notify: {t('form.addSuccess')}, 'success'" disabled="{!username}">
              {t('form.add')}
            </sys-button>
            <sys-button variant="text" on-click="set: username=''">
              {t('form.clear')}
            </sys-button>
          </hbox>
        </vbox>
      </card>

      <!-- 数据展示 -->
      <card title="{t('dataList.title')}" variant="elevated">
        <vbox gap="0.75rem">
          <hbox gap="0.5rem" align="center">
            <sys-text variant="body">{t('dataList.count', {'count': str(len(items))})}</sys-text>
            <spacer />
            <sys-icon-button icon="refresh" on-click="api: getItems" />
          </hbox>
          <sys-table data="{items}" striped="true" />
        </vbox>
      </card>

      <!-- 各种组件展示 -->
      <card title="{t('gallery.title')}" variant="outlined">
        <grid columns="2" gap="1rem">
          <vbox gap="0.5rem">
            <sys-text variant="subtitle">{t('gallery.tags')}</sys-text>
            <hbox gap="0.25rem" wrap="true">
              <sys-tag variant="default">{t('gallery.tagDefault')}</sys-tag>
              <sys-tag variant="primary">{t('gallery.tagPrimary')}</sys-tag>
              <sys-tag variant="success">{t('gallery.tagSuccess')}</sys-tag>
              <sys-tag variant="error">{t('gallery.tagError')}</sys-tag>
            </hbox>
          </vbox>
          <vbox gap="0.5rem">
            <sys-text variant="subtitle">{t('gallery.badges')}</sys-text>
            <hbox gap="0.5rem">
              <sys-badge value="3" />
              <sys-badge value="99+" />
            </hbox>
          </vbox>
          <vbox gap="0.5rem">
            <sys-text variant="subtitle">{t('gallery.switch')}</sys-text>
            <sys-switch label="{t('gallery.switchLabel')}" bind:value="featureEnabled" />
          </vbox>
          <vbox gap="0.5rem">
            <sys-text variant="subtitle">{t('gallery.slider')}</sys-text>
            <sys-slider label="{t('gallery.sliderLabel')}" bind:value="volume" min="0" max="100" />
          </vbox>
        </grid>
      </card>

      <!-- 条件渲染演示 -->
      <card title="{t('conditional.title')}" variant="outlined">
        <vbox gap="0.5rem">
          <sys-text variant="body">{t('conditional.hint')}</sys-text>
          <sys-text variant="body" hidden="{counter &lt;= 5}">
            {t('conditional.exceeded', {'value': str(counter)})}
          </sys-text>
          <sys-text variant="caption" hidden="{counter &gt; 5}">
            {t('conditional.continueHint')}
          </sys-text>
        </vbox>
      </card>

      <!-- 动态图表（raw-response API 演示） -->
      <card title="{t('dynamicChart.title')}" variant="elevated">
        <vbox gap="0.75rem">
          <sys-text variant="body">{t('dynamicChart.body')}</sys-text>
          <sys-text variant="caption">{t('dynamicChart.caption')}</sys-text>
          <hbox gap="0.5rem" align="center">
            <sys-button variant="tonal" icon="refresh" on-click="api: getChartData | notify: {t('dynamicChart.refreshed')}, 'success'">
              {t('dynamicChart.refresh')}
            </sys-button>
          </hbox>
          <sys-chart type="line" height="300px" data="{chartData}" />
        </vbox>
      </card>

      <!-- 图表演示 -->
      <card title="{t('staticChart.title')}" variant="elevated">
        <vbox gap="1.5rem">
          <sys-text variant="body">{t('staticChart.body')}</sys-text>

          <!-- 折线图 -->
          <sys-text variant="subtitle">{t('staticChart.line')}</sys-text>
          <sys-chart type="line" height="280px" data="{lineChartData}" />

          <divider />

          <!-- 柱状图 -->
          <sys-text variant="subtitle">{t('staticChart.bar')}</sys-text>
          <sys-chart type="bar" height="260px" data="{barChartData}" />

          <divider />

          <!-- 饼图 -->
          <sys-text variant="subtitle">{t('staticChart.pie')}</sys-text>
          <sys-chart type="pie" height="300px" data="{pieChartData}" />

          <divider />

          <!-- 雷达图 -->
          <sys-text variant="subtitle">{t('staticChart.radar')}</sys-text>
          <sys-chart type="radar" height="320px" data="{radarChartData}" />
        </vbox>
      </card>

      <!-- 分割线和间距演示 -->
      <card title="{t('layout.title')}" variant="outlined">
        <vbox gap="0.5rem">
          <sys-text variant="body">{t('layout.dividerHint')}</sys-text>
          <divider />
          <sys-text variant="body">{t('layout.aboveDivider')}</sys-text>
          <hbox gap="0.5rem" align="center">
            <sys-text variant="body">{t('layout.left')}</sys-text>
            <divider direction="vertical" />
            <sys-text variant="body">{t('layout.right')}</sys-text>
          </hbox>
        </vbox>
      </card>
    </vbox>
  </layout>
</page>
"""
