# XML 前端编写与注册快速教程

> 5 分钟内为你的 Neo-MoFox 插件添加一个声明式 XML UI 页面。
>
> 本教程聚焦 **前端 XML 编写** 与 **页面注册** 两步。后端 Router/Service/Storage 等组件的开发请先阅读：[**👉 后端组件编写规范**](https://docs.mofox-sama.com/docs/development/plugin_develop/components/router.html)。

---

## 目录

- [1. 它是什么](#1-它是什么)
- [2. 准备工作](#2-准备工作)
- [3. 第一个 XML 页面：3 行就能跑](#3-第一个-xml-页面3-行就能跑)
- [4. 把页面注册到 WebUI](#4-把页面注册到-webui)
- [5. XML 文档骨架](#5-xml-文档骨架)
- [6. 变量、占位符与表达式](#6-变量占位符与表达式)
- [7. 双向绑定 `bind:*`](#7-双向绑定-bind)
- [8. 调用后端 API（`<api>` 模板）](#8-调用后端-apiapi-模板)
- [9. 事件与管道指令](#9-事件与管道指令)
- [10. 条件渲染与响应式断点](#10-条件渲染与响应式断点)
- [11. 常用组件速查表](#11-常用组件速查表)
- [12. 调试技巧](#12-调试技巧)
- [13. 常见坑](#13-常见坑)

---

## 1. 它是什么

Neo-MoFox WebUI 提供一套 **XML 声明式 UI 系统**：你只需写一段 XML，前端就会把它解析成 Vue VNode 树并渲染成 Material Design 3 页面。它支持：

- 变量池 + `{占位符}` 表达式（自动响应式）
- `<api>` 模板：声明即可调用后端，结果自动写回变量池
- 管道指令：`on-click="set: ... | api: ... | notify: ..."` 一条龙
- 桌面端 / 移动端共用一份 XML（也可分别提供）

整套系统由前端三个核心模块协作：

| 模块 | 职责 |
|---|---|
| [`xml-renderer.ts`](../frontend/src/utils/plugin-ui/xml-renderer.ts:1) | 解析 XML → VNode |
| [`api-template-engine.ts`](../frontend/src/utils/plugin-ui/api-template-engine.ts:1) | `<api>` 模板执行 |
| [`pipe-executor.ts`](../frontend/src/utils/plugin-ui/pipe-executor.ts:1) | 管道指令执行 |

XML 文档结构受 [`plugin_ui_v3_1.xsd`](../Plugin/utils/plugin_ui/schemas/plugin_ui_v3_1.xsd:1) 约束。

---

## 2. 准备工作

你需要：

- 一个能在 Neo-MoFox 中正常加载的插件（含 [`manifest.json`](../examples/demo_ui_plugin/manifest.json:1) 和插件类）
- `manifest.json` 里声明对 WebUI 的依赖：

```json
{
  "dependencies": {
    "plugins": ["neo-mofox-webui"],
    "components": ["neo-mofox-webui:service:plugin_ui"]
  }
}
```

- 插件类的 `dependent_components` 同步声明：

```python
dependent_components: list[str] = ["neo-mofox-webui:service:plugin_ui"]
```

> ❗ 不写这两处依赖，`get_service("neo-mofox-webui:service:plugin_ui")` 会拿不到东西。

---

## 3. 第一个 XML 页面：3 行就能跑

最小可运行 XML：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<page version="3.1">
  <layout>
    <card title="Hello">
      <sys-text variant="title">来自 XML 的问候 👋</sys-text>
    </card>
  </layout>
</page>
```

**硬性结构**（来自 XSD）：

- 根元素必须是 `<page>`
- `<layout>` 是必选透传容器，**它本身不渲染**，只渲染子节点
- `<definitions>` 可选，用于声明变量、API、子模板

---

## 4. 把页面注册到 WebUI

在你的插件类的 [`on_plugin_loaded()`](../examples/demo_ui_plugin/plugin.py:26) 钩子里：

```python
from src.app.plugin_system.base import BasePlugin, register_plugin


@register_plugin
class MyPlugin(BasePlugin):
    plugin_name = "my_plugin"
    plugin_description = "示例插件"
    plugin_version = "1.0.0"

    configs: list[type] = []
    dependent_components: list[str] = ["neo-mofox-webui:service:plugin_ui"]

    def get_components(self) -> list[type]:
        return []

    async def on_plugin_loaded(self) -> None:
        from src.app.plugin_system.api.service_api import get_service

        service = get_service("neo-mofox-webui:service:plugin_ui")

        await service.register_ui_page(
            plugin_name="my_plugin",     # 必须与 plugin_name 一致
            page_id="dashboard",         # 同插件内唯一，仅小写、数字、连字符
            title="我的仪表板",
            icon="dashboard",            # Material Symbols 名称
            description="第一次玩 XML UI",
            order=10,
            mode="xml",                  # 固定 "xml"
            xml=_DASHBOARD_XML,          # 上面那段 XML 字符串
            # mobile_xml=_MOBILE_XML,    # 可选，移动端单独一份
        )


_DASHBOARD_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<page version="3.1">
  <layout>
    <card title="Hello">
      <sys-text variant="title">来自 XML 的问候 👋</sys-text>
    </card>
  </layout>
</page>
"""
```

`register_ui_page()` 是 **纯关键字参数 API**，所有参数都是基本类型，不需要 import 任何 WebUI 内部类型。详见服务签名：[`PluginUIService.register_ui_page()`](../Plugin/components/services/plugin_ui_service.py:60)。

注册完成后，刷新 WebUI 侧边栏即可看到你的页面。

---

## 5. XML 文档骨架

完整骨架（推荐起手式）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<page version="3.1" xmlns:bind="urn:neo-mofox:bind">

  <!-- 定义段：变量、API 模板、子模板 -->
  <definitions>
    <var name="counter" default="0" />
    <var name="username" default="''" />
    <var name="items" default="[]" />

    <api id="getItems"
         method="GET"
         url="/router/my_router/api/items"
         response-to="items"
         auto-fetch="true" />
  </definitions>

  <!-- 布局段：UI 树 -->
  <layout>
    <vbox gap="1.5rem">
      <!-- 你的内容 -->
    </vbox>
  </layout>
</page>
```

> `xmlns:bind="urn:neo-mofox:bind"` 命名空间是写 `bind:value="x"` 时让 XML 解析器开心的，**强烈建议加上**。

---

## 6. 变量、占位符与表达式

### 声明变量

```xml
<definitions>
  <var name="counter" default="0" />        <!-- 数字 -->
  <var name="username" default="''" />      <!-- 字符串 -->
  <var name="items" default="[]" />         <!-- 数组 -->
  <var name="enabled" default="false" />    <!-- 布尔 -->
</definitions>
```

`default` 会先尝试 `JSON.parse`，失败则当字符串。`'foo'` 这样带引号写是为了让 `JSON.parse` 失败、回落成字符串字面量。

### 占位符

任何属性值或文本节点中的 `{表达式}` 都会被实时求值并响应式重渲染：

```xml
<sys-text>当前计数：{counter}</sys-text>
<sys-text>共 {len(items)} 条</sys-text>
<sys-text>{user.name || '匿名'}</sys-text>
```

### 内置函数（来自 [`expression-evaluator.ts`](../frontend/src/utils/plugin-ui/expression-evaluator.ts:1)）

`len(x)`、`empty(x)`、`keys(obj)`、`values(obj)`、`str(x)`、`int(x)`、`float(x)`、`bool(x)`

### 转义

文本里想要字面 `{`、`}` 时用 `\{` 和 `\}`。
XML 里 `<` 和 `>` 必须转义为 `<` 和 `>`：

```xml
<sys-text hidden="{counter <= 5}">超过 5 才显示</sys-text>
```

---

## 7. 双向绑定 `bind:*`

把组件的某个属性直接绑到变量池路径，**改一边另一边也变**：

```xml
<sys-input label="名称" bind:value="username" />
<sys-switch label="启用功能" bind:value="enabled" />
<sys-slider bind:value="volume" min="0" max="100" />
```

`bind:value="username"` 等价于：用户输入会自动 `store.set('username', newValue)`，而 `username` 在别处出现 `{username}` 时也会立刻更新。

---

## 8. 调用后端 API（`<api>` 模板）

### 声明

```xml
<api id="getItems"
     method="GET"
     url="/router/my_router/api/items"
     response-to="items"
     auto-fetch="true" />

<api id="addItem"
     method="POST"
     url="/router/my_router/api/items"
     body='{"name": "{username}"}'
     response-to="items" />
```

| 属性 | 说明 |
|---|---|
| `id` | 唯一 ID，管道里用 `api: id` 触发 |
| `method` | `GET` / `POST` / `PUT` / `PATCH` / `DELETE` |
| `url` | 可含 `{占位符}`；通常是后端 Router 暴露的路径 |
| `body` | 请求体 JSON 模板，可含占位符（仅 POST/PUT/PATCH） |
| `response-to` | 把响应数据自动写到变量池的这条路径 |
| `auto-fetch` | `"true"` 时页面加载即触发 |

> URL 里的 `/router/my_router/...` 对应后端 Router 组件中 `self.app.get("...")` 注册的路径。如何写 Router、Service 等后端组件请看：[**👉 后端组件编写规范**](https://docs.mofox-sama.com/docs/development/plugin_develop/components/router.html)。

### 自动状态变量

引擎会为每个 `<api>` 自动维护以下变量，可在 XML 里直接用：

- `api.<id>.pending` — 是否正在请求
- `api.<id>.error` — 错误信息（成功为 `null`）
- `api.<id>.last_response` — 上一次响应数据

举个例子：

```xml
<sys-button loading="{api.getItems.pending}" on-click="api: getItems">
  刷新
</sys-button>

<sys-text variant="caption" color="error" hidden="{!api.getItems.error}">
  请求出错：{api.getItems.error}
</sys-text>
```

---

## 9. 事件与管道指令

任何组件都可以挂 `on-click`、`on-change`、`on-submit`，值是一段 **管道指令字符串**，多个指令用 ` | ` 串起来按顺序执行。

### 完整指令清单（来自 [`pipe-executor.ts`](../frontend/src/utils/plugin-ui/pipe-executor.ts:155)）

| 指令 | 用法 | 含义 |
|---|---|---|
| `set` | `set: counter={counter + 1}` | 写变量池 |
| `api` | `api: addItem` 或 `api: addItem(name='张三')` | 触发 `<api>` 模板 |
| `notify` | `notify: '保存成功', 'success'` | 弹 Toast，level 可选 `info/success/warning/error` |
| `confirm` | `confirm: '确定要删除吗？'` | 弹确认框，取消则中断后续 |
| `navigate` | `navigate: /home` 或 `navigate: plugin:page` | 路由跳转 |
| `open-dialog` | `open-dialog: dialogId` | 打开 `<dialog id="dialogId">` |
| `close-dialog` | `close-dialog: dialogId` | 关闭对话框 |
| `refresh` | `refresh: tableId` | 强制刷新组件 |
| `reset` | `reset: username` 或 `reset: counter=0` | 重置变量 |
| `emit` | `emit: my-event, payload` | 事件总线广播 |

### 经典组合

```xml
<!-- 计数器自增 -->
<sys-button on-click="set: counter={counter + 1}">+1</sys-button>

<!-- 调接口 + 通知 + 清空表单 -->
<sys-button on-click="api: addItem | notify: '添加成功', 'success' | set: username=''">
  提交
</sys-button>

<!-- 危险操作：先确认再调接口 -->
<sys-button on-click="confirm: '确定删除？' | api: deleteItem | notify: '已删除'">
  删除
</sys-button>
```

> ⚠️ 任何一段抛错（包括 `confirm` 取消），后续指令都会被中断。

---

## 10. 条件渲染与响应式断点

XSD 中的 [`GlobalAttrs`](../Plugin/utils/plugin_ui/schemas/plugin_ui_v3_1.xsd:149) 定义了所有组件可用的全局属性：

```xml
<!-- 表达式为真则不渲染 -->
<sys-text hidden="{counter &lt;= 5}">超过 5 才显示</sys-text>

<!-- 表达式为真则禁用 -->
<sys-button disabled="{empty(username)}">提交</sys-button>

<!-- 仅移动端 / 仅桌面端 -->
<sys-text mobile-only="true">只在手机上显示</sys-text>
<sys-text desktop-only="true">只在 PC 上显示</sys-text>
```

`hidden` / `disabled` 可写完整 `{expression}`，也可写裸表达式 `counter > 5`，引擎都吃。

---

## 11. 常用组件速查表

完整组件清单见 [`plugin_ui_v3_1.xsd`](../Plugin/utils/plugin_ui/schemas/plugin_ui_v3_1.xsd:170)。下面是最常用的：

### 布局

| 标签 | 主要属性 | 用途 |
|---|---|---|
| `<vbox>` | `gap` `align` `justify` `padding` | 垂直流式布局 |
| `<hbox>` | `gap` `align` `justify` `wrap` | 水平流式布局 |
| `<grid>` | `columns` `rows` `gap` | 网格布局 |
| `<card>` | `title` `variant` (`elevated`/`outlined`/`filled`) `padding` | 卡片容器 |
| `<tabs>` | `default-tab` | 标签页 |
| `<dialog>` | `id` `title` `message` | 配合 `open-dialog` 用 |
| `<divider>` | `direction` (`horizontal`/`vertical`) | 分割线 |
| `<spacer>` | `height` `width` | 弹性空白 |

### 基础组件

| 标签 | 主要属性 |
|---|---|
| `<sys-text>` | `variant` (`body`/`title`/`subtitle`/`caption`) `color` `align` `bold` |
| `<sys-button>` | `variant` (`filled`/`outlined`/`text`/`tonal`) `icon` `loading` |
| `<sys-icon-button>` | `icon` `variant` `loading` |
| `<sys-icon>` | `name` `size` `color` |
| `<sys-input>` | `label` `placeholder` `type` `value` `error` |
| `<sys-textarea>` | `label` `placeholder` `value` `rows` `error` |
| `<sys-select>` | `label` `options` `value` `placeholder` |
| `<sys-switch>` | `label` `value` |
| `<sys-slider>` | `label` `value` `min` `max` `step` |
| `<sys-date-picker>` | `label` `value` `type` |
| `<sys-tag>` | `variant` (`default`/`primary`/`error`/`success`) `color` |
| `<sys-badge>` | `value` `color` |

### 高级组件

| 标签 | 主要属性 |
|---|---|
| `<sys-table>` | `data` `columns` `striped` `page-size` |
| `<sys-chart>` | `type` (`line`/`bar`/`pie`) `data` `height` |
| `<sys-form>` | `gap` |
| `<sys-list>` | `data` `divider` |

> `icon` 属性的值是 [Material Symbols](../frontend/public/material-symbols) 的图标名（本地图标，不走 CDN）。

---

## 12. 调试技巧

- **打开浏览器控制台**：渲染器会输出大量 `[XmlRenderer]`、`[PipeExecutor]`、`[ApiTemplateEngine]` 调试日志，命中变量初始化、事件触发、管道执行等关键节点。
- **未知组件保护**：写错标签名时页面会显示红色虚线框 `未知组件: <xxx>`，不会整页崩。
- **XML 解析错误**：注册时 [`PluginUIValidators`](../Plugin/utils/plugin_ui/plugin_ui_validators.py) 会先用 XSD 校验你的 XML，错误信息会通过 `XMLValidationError` 抛出，去看插件加载日志。
- **变量没初始化怎么办？**：`<var>` 默认值为空时变量是 `null`，`{name || '缺省'}` 是常见兜底写法。
- **API 路径不对？**：直接看后端 Router 在哪个路径下注册。XML 里的 `url` 默认走前端的 `instance` HTTP 客户端，相对路径会拼到 WebUI 后端基地址下。

---

## 13. 常见坑

1. **`<` 没转义** — XML 里写 `counter < 5` 会让 DOMParser 直接报解析错误。必须写 `counter &lt; 5`。
2. **`default="hello"` 被解析成变量** — 字符串字面量请写 `default="'hello'"`，因为引擎会先尝试 `JSON.parse`。
3. **`<api>` 写在 `<layout>` 里不会执行** — 所有 `<var>` / `<api>` / `<template>` 必须放在 `<definitions>` 段内，外面写了不会被识别。
4. **想自动加载数据但没数据** — 检查 `<api auto-fetch="true">` 里的字符串值，**必须是 `"true"`**，不是 `true`、`1`、`True`。
5. **bind 双向绑定不生效** — XML 命名空间没声明。在 `<page>` 上加 `xmlns:bind="urn:neo-mofox:bind"`。
6. **page_id 注册被拒** — `page_id` 只允许 `[a-z0-9-]+`，不要写下划线、大写或中文。
7. **改了 XML 但页面没变** — 插件没真正卸载重载，重新启动 Neo-MoFox 或卸载该插件后重装。
8. **想从其他插件拿数据** — 别 `import` 对方源码，发请求到对方插件 Router 的 URL 即可（这才是「插件间通过 API 解耦」的正确姿势）。

---

## 写完前端，下一步去哪？

- 前端组件需要后端配合？请阅读：[**👉 后端组件编写规范**](https://docs.mofox-sama.com/docs/development/plugin_develop/components/router.html)
- 想看完整可运行示例：[`examples/demo_ui_plugin/`](../examples/demo_ui_plugin/plugin.py:1)
- 想了解整体架构：[`docs/Neo-MoFox-WebUI-Plugin-Extension-Design.md`](Neo-MoFox-WebUI-Plugin-Extension-Design.md:1)

祝你写得开心 🎉
