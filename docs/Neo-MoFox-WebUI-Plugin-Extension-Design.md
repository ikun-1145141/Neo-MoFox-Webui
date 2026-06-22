# Neo-MoFox WebUI 插件前端扩展系统设计文档

**版本**: 3.1.0
**作者**: MoFox Team
**日期**: 2026-06-19
**状态**: 设计稿 — 双轨响应式 UI 框架（v3.1：去用户权限 / 禁用零感知 / HTML 轨 fetch 重写 / 管道仅 XML / Web Components 命令式 API）

---

## 📋 目录

1. [系统概述](#1-系统概述)
2. [核心架构：响应式变量池 + 双轨 UI](#2-核心架构响应式变量池--双轨-ui)
3. [插件注册与生命周期](#3-插件注册与生命周期)
4. [双轨之一：XML 声明式 UI](#4-双轨之一xml-声明式-ui)
5. [双轨之二：HTML/Web Components 自定义 UI](#5-双轨之二htmlweb-components-自定义-ui)
6. [脚本与 DSL（管道指令，仅 XML）](#6-脚本与-dsl管道指令仅-xml)
7. [API 模板与请求处理](#7-api-模板与请求处理)
8. [移动端适配策略](#8-移动端适配策略)
9. [安全边界与卸载](#9-安全边界与卸载)
10. [组件清单速查表](#10-组件清单速查表)

---

## 1. 系统概述

### 1.1 设计目标

为 Neo-MoFox 插件提供 **低代码 + 高自由度并行** 的前端扩展能力：

- ✅ **数据驱动**：UI 不直接生产数据，而是订阅一个全局响应式变量池
- ✅ **占位符即绑定**：XML 轨的所有组件属性、文字、显隐、API 参数都可写 `{var_name}`，变量变 → UI 全场联动
- ✅ **双轨并行**：低代码用户写 XML，专业前端写 HTML 三件套；**page 维度二选一**，不在同一 page 内混用
- ✅ **路径系统自管理**：插件不关心也无法控制路由路径，所有路由由系统按 `plugin_name:page_id` 规则自动生成
- ✅ **禁用零感知**：系统无法可靠探测插件是否被禁用 / 重载 / 卸载，因此**默认完全不感知，不动 Registry**；只有插件主动调用 `unregister_*` 才会清理
- ✅ **移动端友好**：插件可选提交移动端三件套，未提交则降级为横向滚动 fallback

### 1.2 适用场景判定

| 场景 | 复杂度 | 推荐 |
|---|---|---|
| 简单配置表单（一两个开关/输入） | ⭐ | 用 ConfigBase（不在本方案范围）|
| CRUD 列表 + 表格 + 图表 | ⭐⭐ | XML 声明式 UI |
| 仪表盘 / 多视图切换 / 中等交互 | ⭐⭐⭐ | XML 单 page；如需多页协同则注册多个 XML page |
| 强自定义视觉、动画、画布、第三方 SDK | ⭐⭐⭐⭐ | HTML 三件套（整个 page 走 HTML） |

### 1.3 架构分层

```
┌─────────────────────────────────────────────────────────┐
│ 插件后端（Python，Neo-MoFox 插件）                       │
│  - 定义 page 元数据（标题、图标、order、移动端支持）     │
│  - 提交 XML 字符串 / HTML+CSS+JS 文件路径                │
│  - 通过 Service API 注册 / 卸载                          │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│ WebUI 后端 Service 层                                    │
│  - PluginUIRegistry：登记表（plugin_name → 多 page）     │
│  - 资源服务：以本地静态映射方式暴露 HTML/CSS/JS          │
│  - Discovery API：返回所有 page 元数据 + 系统生成路径    │
│  - Schema/Asset API：按需返回某个 page 的 XML 或文件     │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│ WebUI 前端运行时（Vue 3 + Pinia + Web Components）       │
│  - 响应式变量池 Store（每页一个 scope，全局一个 share）  │
│  - 占位符解析器（{ var.path } / {! var } / 表达式）      │
│  - XML 渲染器：解析 → Vue 组件树                          │
│  - HTML 沙箱渲染器：iframe-less，Web Components + 桥接   │
│  - 统一 Bridge：sys.request / sys.api / sys.vars / sys.ui│
│  - fetch 代理：window.fetch / XHR 被改写到 sys.request   │
└─────────────────────────────────────────────────────────┘
```

> **`<plugin-page-picker>` 是 WebUI 主程序自身的官方导航组件**（用于"插件中心"等宿主页面浏览/选择插件 page），**不在插件可用组件清单内**，插件作者既不能也不需要在自己的 XML/HTML 中写出它。

---

## 2. 核心架构：响应式变量池 + 双轨 UI

### 2.1 变量池（Reactive Store）

**核心定位**：UI 不直接持有数据，UI 只是变量池的"皮"。

变量池分为三个作用域：

| 作用域 | 生命周期 | 可见范围 | 用途示例 |
|---|---|---|---|
| `page` | 进入页面创建 / 离开页面销毁 | 当前 page 内所有组件 | 表单值、列表数据、loading、对话框开关 |
| `plugin` | 插件页面被首次访问起 / 显式 unregister 销毁 | 同一插件的所有 page | 跨页面会话状态、插件本地缓存、向导中间结果 |
| `global` | 与 WebUI 同寿命 | 全部插件页面（**只读**） | 当前主题、当前语言、WebUI 版本、feature flags |

> 不允许插件直接读写其他插件的 `plugin` scope；这是 9.x 节描述的隔离边界。
> `global` 仅由 WebUI 主程序写入；插件对其只读，写操作会被静默忽略。

### 2.2 占位符语法

占位符是变量池在 UI 上的"引线"，**XML 轨原生支持**；HTML 轨可选使用，但通常用 JS 直接读写 `sys.vars` 更直接。

| 写法 | 含义 |
|---|---|
| `{user.name}` | 取 `page.user.name`（默认 page 优先，找不到回退 plugin/global）|
| `{global.theme.mode}` | 显式指定 global scope |
| `{plugin.session.token}` | 显式指定 plugin scope |
| `{!list}` | 取反；常用于 `disabled="{!form_valid}"` |
| `{list.length}` | 内置访问器（length / keys / values）|
| `{empty(list)}` | 内置 helper：判断空 |
| `{len(list) > 5}` | 简单表达式（仅支持 `> < >= <= == != && || !` 与字面量）|
| `{api.saveUser.pending}` | 系统保留命名空间，反映 API 状态（loading）|

> **强约束**：不支持任意 JS 表达式。这是安全和稳定性的硬边界。
> **强约束**：内置 helper 名单封闭（`empty`、`len`、`keys`、`values`、格式化函数），不含任何用户权限相关 helper。

### 2.3 双轨 UI 是什么

| 轨道 | 输入物 | 渲染方式 | 受众 |
|---|---|---|---|
| **XML 轨** | 一段 XML 字符串 | 解析 → Vue 组件树 | 插件作者、低代码用户 |
| **HTML 轨** | 一组 `index.html` + `style.css` + `script.js` 文件路径 | Web Components + Shadow DOM 沙箱桥接 | 专业前端开发者 |

**两条轨道共享**：注册流程 / 路径系统 / API 模板 / Toast 通知 / 主题变量 / 沙箱内的 `sys.*` 桥接。
**两条轨道不共享**：组件标签的实现细节（XML 走 Vue 组件，HTML 走 Web Components）。

> **page 维度二选一**：每个 page 注册时只能声明一个 `mode`（`xml` 或 `html`），不允许在同一 page 内混用。同一插件可以同时注册多个 page，每个 page 各自选择自己的 mode。

---

## 3. 插件注册与生命周期

### 3.1 设计原则（与上一版的关键差异）

1. **路由路径系统自动生成**：插件不传 `route`、不传 `path`，系统按 `plugin_name:page_id` 生成 `/plugins/{plugin_name}/{page_id}`，避免冲突与篡改。
2. **禁用 / 重载零感知**：系统无法可靠区分"插件被禁用"、"插件热重载"、"插件被卸载但未来还会回来"这几种状态。因此**系统对这些事件一律不感知、不动 Registry**。要清理 UI 必须由插件主动调用 `unregister_*`。
3. **没有 inactive 标记**：Registry 中只有"存在"与"不存在"两种状态，不再有"暂时不可达"这种中间态。
4. **`<plugin-page-picker>` 是 WebUI 官方组件**：宿主前端用它做插件 UI 的导航视图，但它本身不属于"插件可写的标签集合"。

### 3.2 注册数据结构（PageRegistration）

每个 page 注册时携带的元数据字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `plugin_name` | ✅ | 插件名（与 manifest 一致，由后端校验） |
| `page_id` | ✅ | 同插件内唯一的页面 ID |
| `title` | ✅ | 显示名 |
| `icon` | ❌ | Material Symbols 图标名 |
| `description` | ❌ | 简介 |
| `order` | ❌ | 排序权重 |
| `mode` | ✅ | `xml` 或 `html`（**page 维度二选一**） |
| `xml` | 条件必填 | 当 mode=xml 时提供（字符串） |
| `assets` | 条件必填 | 当 mode=html 时提供（见 3.3） |
| `mobile` | ❌ | 移动端三件套（见第 8 节） |

> 不再有 `permissions` 字段。API 调用边界由"插件身份注入 + 后端校验"接管（见 9.3）。

### 3.3 HTML 模式资源声明（assets）

HTML 轨不让插件作者写一团字符串，而是 **指文件路径**：

| 字段 | 说明 |
|---|---|
| `entry_html` | 主入口 HTML 文件路径（相对插件目录） |
| `styles[]` | 0..N 个 CSS 文件路径 |
| `scripts[]` | 0..N 个 JS 文件路径 |
| `assets_dir` | 静态资源根目录（图片/字体），系统会以只读静态映射暴露 |

> 系统在注册时把这些路径解析成 WebUI 可访问的 URL（仍由系统生成）。插件无权决定外部 URL。

### 3.4 注册接口（语义层面）

WebUI 提供以下 Service 接口（具体实现由插件 Service 暴露给其他插件调用，不在此文档中给代码）：

| 接口 | 行为 |
|---|---|
| `register_ui_page(metadata)` | 新建或覆盖一个 page 注册（同 `plugin_name:page_id` 视为更新） |
| `unregister_ui_page(plugin_name, page_id)` | 显式卸载单个 page |
| `unregister_plugin_pages(plugin_name)` | 显式卸载该插件下全部 page |
| `list_pages(filter)` | 枚举可见 page，前端 Discovery 用 |
| `get_page_schema(plugin_name, page_id, variant)` | 拉取详细 schema；variant 取 `desktop` 或 `mobile` |

> 注意：上述接口都是**显式调用**。插件"被禁用"或"热重载"不会触发任何 unregister——系统对这些事件零感知。

### 3.5 生命周期时序

```
插件加载（on_plugin_loaded）
    └─ 插件主动调用 register_ui_page(metadata)
         └─ WebUI Service 校验 → 入 Registry → 生成系统路径
              └─ 前端 Discovery 下次拉取时见到这条 page

插件运行中
    └─ 插件可随时再次调用 register_ui_page 覆盖（热更新 XML / 文件路径）

插件被禁用 / 重载 / 静默崩溃
    └─ 系统无法可靠探测，因此什么都不做
       Registry 完全不动，UI 仍然可达
       （这是有意为之——避免热重载/调试期反复加载误清用户工作）

插件主动调用 unregister_ui_page / unregister_plugin_pages
    └─ Registry 移除条目；前端在下一次 Discovery 中失去该 page

WebUI 主程序重启
    └─ Registry 全清空（设计为内存态，不做硬持久）
       这是"陈旧 Registry"的兜底机制
```

> **设计取舍说明（必须写进开发者守则）**：
> - 插件作者负责在"真正想清理"的场景调用 unregister，例如：用户在管理面板点击"清理插件 UI 缓存"时
> - 插件 disable 时不调 unregister——因为系统根本不知道你 disable 了，没人会替你触发
> - 由于 Registry 是内存态，WebUI 重启天然就清空了；这是兜底机制

---

## 4. 双轨之一：XML 声明式 UI

### 4.1 文档结构

每个 XML page 由三段组成：

- `<metadata>`：标题、图标、描述（**注意：不写 route/path，由系统生成**）
- `<definitions>` 可选：API 模板、初始变量、子模板
- `<layout>`：桌面版组件树

### 4.2 通用属性（所有 sys-* 组件都支持）

这些是"全场通用语法"，不再每个组件单列：

| 属性 | 作用 | 示例 |
|---|---|---|
| `id` | 组件 ID（用于跨组件引用与刷新） | `id="usersTable"` |
| `value` | 渲染/绑定文本，支持占位符 | `value="欢迎，{user.name}"` |
| `bind` | 双向绑定到变量池路径 | `bind="form.username"` |
| `disabled` | 禁用交互（占位符可计算） | `disabled="{!form.username}"` |
| `hidden` | 不渲染（占位符可计算） | `hidden="{empty(user_list)}"` |
| `readonly` | 只读（适用于输入类） | `readonly="{is_locked}"` |
| `loading` | 显示加载态（按钮转圈、表格遮罩） | `loading="{api.saveUser.pending}"` |
| `class` / `style` | 透传样式（受白名单过滤） | — |
| `mobile-only` / `desktop-only` | 仅在某种视口出现 | — |

> v3.1 起：移除 `permission` 通用属性（用户权限不再纳入框架）。如需差异化展示，请用 `hidden` + 业务变量池中的状态字段表达。

### 4.3 布局组件

| 标签 | 作用 |
|---|---|
| `<vbox>` / `<hbox>` | 纵向 / 横向排列；属性：`gap`、`align`、`justify` |
| `<grid>` | 网格；属性：`columns`、`row-gap`、`col-gap`，子元素可写 `span` |
| `<card>` | MD3 卡片；属性：`title`、`elevation` |
| `<tabs>` / `<tab>` | 标签页 |
| `<dialog>` | 对话框；属性：`open`（绑变量池布尔）、`title` |
| `<divider>` | 分割线 |
| `<spacer>` | 弹性空白 |

### 4.4 基础组件

| 标签 | 作用 | 关键属性 |
|---|---|---|
| `<sys-text>` | 文本（含占位符） | `value`、`variant`（display/headline/body/caption） |
| `<sys-input>` | 输入框 | `bind`、`type`、`placeholder`、`min-length`、`max-length`、`pattern`、`error-message` |
| `<sys-textarea>` | 多行 | `bind`、`rows`、`max-length` |
| `<sys-select>` | 下拉 | `bind`、`options`（静态）/ `options-from`（变量池路径，配合 API） |
| `<sys-switch>` | 开关 | `bind` |
| `<sys-slider>` | 滑块 | `bind`、`min`、`max`、`step` |
| `<sys-date-picker>` | 日期 | `bind`、`format`、`min-date`、`max-date` |
| `<sys-button>` | 按钮 | `text`、`variant`（primary/secondary/text/danger）、`on-click`（管道指令） |
| `<sys-icon-button>` | 图标按钮 | `icon`、`on-click` |
| `<sys-tag>` / `<sys-badge>` | 标签 / 徽章 | `value`、`color` |
| `<sys-icon>` | Material Symbols 图标 | `name` |

### 4.5 高级数据组件（核心）

#### `<sys-table>` 数据表格

| 属性 | 说明 |
|---|---|
| `data` | 绑数组的占位符，如 `data="{user_list}"` |
| `data-path` | 提取路径（如后端返回 `{ data: { items: [...] } }`，写 `data-path="data.items"`） |
| `pagination` | `true` / `false` |
| `page-size` | 每页条数 |
| `selectable` | 行选中模式（`single` / `multi`） |
| `selected-bind` | 选中行写入哪个变量 |
| `row-key` | 唯一键字段名 |

子元素：

- `<column field="name" title="姓名" width="120" sortable="true" />`
- `<column>` 内可嵌套：
  - `<map from="1" to="在线" color="green" />`（值映射，0/1 → 文案）
  - `<format type="date" pattern="YYYY-MM-DD" />`（日期/货币/百分比）
  - `<progress min="0" max="100" />`（进度条）
  - `<actions>`（行操作槽，内部放 `<sys-button>`）

#### `<sys-chart>` 图表

| 属性 | 说明 |
|---|---|
| `type` | `line` / `bar` / `pie` / `area` |
| `data` | 数据来源占位符 |
| `data-path` | 数据路径提取 |
| `x-field` / `y-field` / `name-field` / `value-field` | 字段映射 |
| `height` | 高度（px） |
| `legend` / `tooltip` | 是否显示 |

#### `<sys-form>` 表单容器

可选包装。提供：

- 子元素提交时统一校验
- `valid-bind="form_valid"` 把校验结果写入变量池
- `on-submit="api: ... | ..."` 简化按钮逻辑

#### `<sys-list>` 简单列表（替代轻量场景下的表格）

| 属性 | 说明 |
|---|---|
| `data`、`data-path` | 同表格 |
| `item-template` | 子模板的 ID（在 `<definitions>` 中预先声明） |

### 4.6 条件交互的标准写法（重点）

| 需求 | 写法 |
|---|---|
| 输入为空时禁用按钮 | `<sys-button disabled="{!search_q}" ... />` |
| 没数据时隐藏提示文本 | `<sys-text hidden="{!user_list.length}" value="共 {user_list.length} 条" />` |
| 请求中按钮禁用 + 转圈 | `<sys-button loading="{api.saveUser.pending}" disabled="{api.saveUser.pending}" />` |
| 表单整体校验通过才允许提交 | `<sys-form valid-bind="form_valid">…</sys-form>` 配合 `<sys-button disabled="{!form_valid}" />` |
| 危险操作二次确认 | `<sys-button on-click="confirm: '确认删除?' \| api: deleteUser(id={row.id})" />` |

### 4.7 变量初始化与 `<definitions>`

为避免"访问未定义变量导致 UI 闪烁"，鼓励在 `<definitions>` 段声明初始变量与默认值；同时该段也存放 API 模板（见第 7 节）与可复用子模板。

| 子元素 | 作用 |
|---|---|
| `<var name="user_list" default="[]" />` | 声明 page scope 变量（初始值为数组） |
| `<var name="form" default="{}" />` | 对象类型 |
| `<var name="form.username" default="''" />` | 也支持点路径声明嵌套字段 |
| `<api id="...">…</api>` | API 模板（第 7 节） |
| `<template id="...">…</template>` | 可被 `sys-list` 等引用的子模板 |

> v3.1 起：删除原 `<sys-bind>` 标签——变量声明的唯一入口就是 `<definitions>` 中的 `<var>`。

---

## 5. 双轨之二：HTML/Web Components 自定义 UI

### 5.1 设计意图

XML 轨服务的是 **"快速搭好用的页面"**；HTML 轨服务的是 **"需要自定义视觉的高级前端用户"**。两类受众诉求不同：

- HTML 用户不想被 `<sys-table data-path>` 限制；他们想自己写 div 和 canvas
- 但他们仍然希望复用响应式变量池、主题变量、系统通知/对话框等内部前端 API、统一请求拦截
- 所以 HTML 轨提供的是 **Web Components + Bridge**，不是"XML 转 Vue"那一套

> **page 维度二选一**：声明 `mode=html` 的 page 整页都走 HTML 三件套，**不能在 HTML 中嵌入 XML 片段，反之亦然**。如果一个插件既需要低代码页面又需要高度自定义页面，请注册多个 page 各自选择 mode。

> **管道指令不在 HTML 轨可用**（v3.1 起）：第 6 节描述的 `指令: 参数 | ...` 属性 DSL 仅适用于 XML 轨。HTML 轨的事件、请求、组件控制一律用 JS 通过 `sys.*` 编排——这是 HTML 轨的核心心智模型。

### 5.2 Web Components（系统注入）

WebUI 运行时会把以下自定义元素注入到 HTML 沙箱中。**它们底层与 XML 轨的同名组件共享内核，但作为 Web Components 暴露**，并提供完整的命令式 JS API（详见 10.7 节）：

| 元素 | 等价 XML 组件 | HTML 轨常用控制方式 |
|---|---|---|
| `<sys-text>` | `<sys-text>` | `el.textContent = '...'` 或 `el.setValue('...')` |
| `<sys-input>` | `<sys-input>` | `el.setValue(v)` / `el.getValue()` / 监听 `change` |
| `<sys-textarea>` | `<sys-textarea>` | 同 input |
| `<sys-select>` | `<sys-select>` | `el.setOptions([...])` / `el.setValue(v)` / 监听 `change` |
| `<sys-switch>` / `<sys-slider>` / `<sys-date-picker>` | 同名 | `setValue` / `getValue` / `change` |
| `<sys-button>` | `<sys-button>` | 监听标准 DOM `click`；`el.setLoading(true)`、`el.disable()` 等 |
| `<sys-icon-button>` / `<sys-icon>` | 同名 | `el.setIcon(name)` |
| `<sys-tag>` / `<sys-badge>` | 同名 | 简单展示型，常通过 `textContent` 改文 |
| `<sys-table>` | `<sys-table>` | `el.setData(arr)` / `el.getSelected()` / 监听 `row-click`、`selection-change`、`action` |
| `<sys-chart>` | `<sys-chart>` | `el.setData(arr)` / `el.setType(t)` |
| `<sys-form>` | `<sys-form>` | `el.validate()`、监听 `submit` |
| `<sys-list>` | `<sys-list>` | `el.setData(arr)`，`item-template` 仍来自 `<definitions>` 中的模板 |
| `<sys-dialog>` | `<dialog>` | `el.open()` / `el.close()` / 监听 `open`/`close`/`confirm`/`cancel` |
| `<sys-toast>` | — | `el.show(msg, level)`，等价 `sys.ui.toast(...)` |

> **关键差异**：HTML 轨**不要求**作者通过占位符使用所有功能。占位符（`data-bind` 等）仍可使用以方便简单场景，但**主推 JS 命令式控制**——读写 `sys.vars` / 调用 `sys.api(...)` / 直接对 Web Components 调方法。

### 5.3 沙箱边界

HTML 模式 **不是 iframe**，是同窗口下的隔离区域：

- 渲染容器是一个挂载到 WebUI 主页面里的 `<div class="plugin-html-host">`，使用 Shadow DOM 隔离样式（避免插件样式污染主界面）
- 插件 JS 通过模块化注入方式执行，**不会暴露 WebUI 的内部模块**（Pinia store / Vue 实例 / 路由器对象等）
- 插件 JS 可访问的全局对象 = `sys`（见 5.4）+ 标准浏览器 API + 系统注入的 Web Components
- **`window.fetch` 与 `XMLHttpRequest` 不被禁用，而是被系统代理重写**：所有出站请求都被透明导向 `sys.request` 的同一条拦截链（Token 注入、`X-Plugin-Name` 注入、`BaseResponse` 解包、错误 Toast）。这意味着第三方库（默认调用 `fetch`）能直接工作，但你**不能假设 `fetch` 绕过了任何拦截**

### 5.4 系统全局对象 `sys`

文档级别约定：HTML 沙箱里有且只有一个系统注入对象 `sys`。它分为**核心桥接**和**系统内部前端 API 快捷入口**两部分。

#### 5.4.1 核心桥接

| 命名空间 | 作用 | 形态 |
|---|---|---|
| `sys.vars` | 响应式变量池（page scope） | 读写都触发响应式更新 |
| `sys.plugin` | 插件 scope 变量池 | 同上，仅当前插件可见 |
| `sys.global` | 全局 scope（只读） | 主题、语言、WebUI 版本、feature flags 等系统状态 |
| `sys.api(id, params)` | 调用预定义 API 模板，返回 Promise | 自动套 BaseResponse |
| `sys.request(url, options)` | 统一请求方法 | 带 Token、统一拦截、错误 toast |
| `sys.bus.on / off / emit` | 跨组件事件总线（仅当前 page） | — |
| `sys.theme` | 当前主题信息（mode/primary 等，只读，跟随 global 变化） | — |
| `sys.route.back() / current` | 路由（路径仍由系统管理，不可手写绝对路径） | — |
| `sys.format.date / number / currency` | 格式化辅助 | 与 XML 中 `<format>` 同源 |
| `sys.i18n.t(key, params)` | 文案翻译（只读使用） | — |

#### 5.4.2 系统内部前端 API 快捷入口（`sys.ui.*`）

这一组是 v3.1 重点新增——把"通知、对话框、确认"这些 WebUI 已有的内部前端能力**直接暴露给插件 JS 一键调用**，不必再绕道管道指令或自己实现。

| 入口 | 作用 |
|---|---|
| `sys.ui.notify(msg, level)` | 弹 Toast（level: `success` / `info` / `warn` / `error`）|
| `sys.ui.toast(msg, level)` | `notify` 的别名 |
| `sys.ui.notice(msg, opts)` | 写入 WebUI 通知中心（持久通知，与一次性 Toast 区分）|
| `sys.ui.confirm(msg, opts)` | 确认对话框，返回 `Promise<boolean>` |
| `sys.ui.alert(msg, opts)` | 提示对话框，返回 `Promise<void>` |
| `sys.ui.dialog.open(id)` / `sys.ui.dialog.close(id)` | 控制声明式 `<sys-dialog>` 的开关 |

#### 5.4.3 移除项（v3.1 起不再提供）

| 旧接口 | 状态 |
|---|---|
| `sys.permissions.has(code)` | **删除**（用户权限不再纳入框架） |
| `sys.global.user.*` | **删除**（无多用户登录场景） |

> **fetch 重写约定**：HTML 沙箱中的 `window.fetch` 与 `XMLHttpRequest` **不会被禁用**，而是被系统改写为指向 `sys.request` 的同一条链路。无论插件代码是 `fetch('/api/users')` 还是 `sys.request('/api/users')`，最终都会经过同一条 Token 注入、错误拦截、`X-Plugin-Name` 标注、`BaseResponse` 解包链。这是为了兼容第三方库（它们通常默认调用 `fetch`），同时仍然保证全站统一拦截。

### 5.5 CSS 变量与主题接入

HTML 模式的 CSS 可以直接读 WebUI 暴露的 MD3 变量：

| 变量类（节选） | 用途 |
|---|---|
| `--md-sys-color-primary` 等 MD3 标准色卡 | 主题色 |
| `--md-sys-color-surface` / `--md-sys-color-on-surface` | 背景与前景 |
| `--md-sys-shape-corner-medium` 等 | 圆角 |
| `--mf-spacing-1` ~ `--mf-spacing-8` | 间距阶梯 |
| `--mf-z-toast` / `--mf-z-dialog` | 层级 |

> 主题切换时，这些变量由 WebUI 主程序自动更新，插件 HTML 视觉无须额外处理就跟着变。

### 5.6 HTML 模式的最小契约（开发者守则）

1. 入口 HTML 只用 `body` 一级以下的内容（不写 `<html>` `<head>` `<body>` 包裹，由系统拼装）
2. JS 不能假设 `window` 是干净的；需要的所有外部能力都要从 `sys` 拿
3. 全局选择器、`<style>` 标签会被自动 scope 到该插件的 Shadow DOM，不污染主站
4. 禁止动态 `import()` 外部脚本（需要的库由插件作者打包进自己的 scripts）
5. 提交资源时 `entry_html` 必须存在；`styles[]` `scripts[]` 顺序即加载顺序
6. **不要写属性式管道指令**（如 `data-on-click="api: ... | ..."`）：HTML 轨已不识别此语法。事件处理、请求编排、组件控制一律用 JS 调用 `sys.*` 与 Web Components 的命令式 API 完成
7. **`window.fetch` / `XMLHttpRequest` 已被系统重写**：使用它们与使用 `sys.request` 在拦截链上等价，但请优先使用 `sys.api` / `sys.request`，因为它们的类型与错误语义更清晰

---

## 6. 脚本与 DSL（管道指令，仅 XML）

### 6.1 基本形态

**管道指令仅在 XML 轨可用**。HTML 轨已废弃属性式管道写法，请改用 JS + `sys.*` 编排（详见第 5 节）。

XML 中事件处理写在属性里，遵循 **管道指令** 风格，形式：

```
指令名: 参数 | 指令名: 参数 | ...
```

例如：

```xml
<sys-button text="保存"
            on-click="api: saveUser(name={form.name}) | notify: '保存成功' | refresh: usersTable" />
```

### 6.2 指令清单

| 指令 | 作用 | 示例 |
|---|---|---|
| `set` | 写变量池 | `set: form.username = ''` |
| `set`（管道形态） | 把上一段管道结果写入变量 | `api: getUsers \| set: user_list` |
| `api` | 调用预定义 API 模板 | `api: saveUser(name={form.name})` |
| `notify` | 弹 Toast | `notify: '保存成功'` 或 `notify: '错误' level=error` |
| `confirm` | 二次确认；用户取消则中断管道 | `confirm: '确认删除?' \| api: deleteUser(id={row.id})` |
| `navigate` | 跳转到系统生成的路径（按 plugin/page 名） | `navigate: my_plugin:user-form` |
| `open-dialog` / `close-dialog` | 对话框开关 | `open-dialog: createUserDialog` |
| `refresh` | 刷新指定组件 | `refresh: usersTable` |
| `reset` | 清空表单或某个变量 | `reset: form` |
| `emit` | 通过事件总线广播 | `emit: user.created` |

### 6.3 错误传播

任何一个管道节点抛错（含 API 失败、`confirm` 取消）都会中断后续指令；`api` 节点的错误会被请求拦截层吸收并触发全局 toast，无需作者写 `on-error`。

### 6.4 状态变量（系统保留命名空间）

变量池的 `api.<id>.*` 是系统保留：

| 字段 | 含义 |
|---|---|
| `api.<id>.pending` | bool，请求是否进行中 |
| `api.<id>.error` | 最近一次错误的 message（成功后清空） |
| `api.<id>.last_response` | 最近一次成功响应的 data |

这一块就是"点击按钮 → 自动转圈 → 自动还原"的底层支撑。

---

## 7. API 模板与请求处理

### 7.1 设计动机

不让用户在事件属性里手写 JSON / 复杂查询字符串。所有真实请求都由 **预定义 API 模板** 完成。

### 7.2 模板声明（在 `<definitions>` 中）

每个 `<api>` 节点的字段：

| 字段 | 说明 |
|---|---|
| `id` | API 模板 ID，事件中通过 `api: <id>(...)` 调用 |
| `url` | URL，可含路径参数 `{:id}` |
| `method` | HTTP 方法 |
| `body-template` | 请求体模板，可写 `{{ var_or_param }}` |
| `query-template` | URL Query 模板 |
| `headers` | 额外请求头（默认会自动加 token / X-Plugin-Name） |
| `timeout` | 超时（毫秒） |
| `data-path` | 默认提取路径，调用方可覆盖 |
| `silent` | 失败时不弹 toast（默认 false） |

> v3.1 起：模板**不再含**任何"用户权限白名单"字段。API 调用边界的实施方式见 9.3。

### 7.3 调用语法与执行规则

调用形式：`api: saveUser(name={form.name}, role='admin')`

执行规则：

1. 取实参（含占位符），与 `body-template` / `query-template` 中的 `{{ ... }}` 占位符做填充
2. 通过 `sys.request` 发起请求
3. 期间自动写 `api.saveUser.pending = true`
4. 成功响应：`code === 200` → 把 `data` 暴露给管道下一节（如 `\| set: target_var`）；同时更新 `api.saveUser.last_response`
5. 失败：`api.saveUser.error` 更新；触发全局 toast（除非声明 `silent=true`）；管道中断

### 7.4 请求拦截统一约定

所有走 `sys.request`（包括被重写的 `fetch` / `XHR`）的调用都会被统一拦截：

- 自动附加身份令牌
- 自动附加 `X-Plugin-Name`（来自当前 page 的注册元数据，前端无法伪造）
- 响应统一按照项目 `BaseResponse` 协议解包
- 网络层错误 → 全局 Dialog；业务错误（code != 200）→ 全局 Toast
- **严禁静默失败**（与项目设计文档一致）

> v3.1：原 7.5 节"权限校验"整节删除（用户权限不再纳入框架）。其中"X-Plugin-Name 注入 / 注册身份校验"这部分**插件身份边界**内容已并入 9.3 节。

---

## 8. 移动端适配策略

### 8.1 总策略

**插件可选提交移动端三件套**。文档以"是否提交"作为分支：

| 是否提交 | 移动端表现 |
|---|---|
| ✅ 提交了 | 用插件提交的移动端 XML 或 HTML 三件套渲染 |
| ❌ 未提交 | 用桌面版渲染，外层套一个**横向滚动 fallback**（保证不卡死，但视觉妥协） |

### 8.2 移动端三件套字段

PageRegistration 中 `mobile` 是可选对象，结构与桌面版同构：

| 字段 | 说明 |
|---|---|
| `mode` | `xml` / `html`，可与桌面版不同（例如桌面 XML、移动 HTML） |
| `xml` | 当 mode=xml 时必填 |
| `assets` | 当 mode=html 时必填，三件套：`entry_html` / `styles[]` / `scripts[]` / `assets_dir` |

### 8.3 视口判定

WebUI 主程序通过 viewport 宽度阈值判断当前是 desktop 还是 mobile：

- `>= 768px`：使用桌面版 schema
- `< 768px`：优先使用 `mobile.*`，若不存在则走 fallback 模式
- 用户在桌面手动切"移动模拟"模式时同样走移动版

### 8.4 fallback 行为细节

未提供 mobile 版本时，系统对桌面版进行如下包装：

- 整页渲染在一个固定最小宽度（例如 1024px）容器中
- 容器外层添加水平滚动条
- 顶部加一条提示条：「该插件页面未适配移动端，已启用兼容显示」
- 不尝试自动"响应式重排"，避免组件破图

### 8.5 通用属性 `mobile-only` / `desktop-only` 的使用

即便插件提交了完整三件套，仍可在某一份 schema 内部用这两个属性做局部差异：

- 例如桌面 XML 中保留 `<sys-button mobile-only ... />`，渲染桌面版时不出现，但被宿主直接把这份 XML 当作移动版用时也能存在
- 这两个属性是"纯前端视口标记"，不影响注册元数据

---

## 9. 安全边界与卸载

### 9.1 注册侧校验

注册请求经过：

1. **结构校验**：XML 走 XSD；HTML 三件套校验路径存在、扩展名白名单（.html/.css/.js）
2. **标签白名单**：XML 仅允许已登记的 `<sys-*>` 与布局标签，未知标签报错
3. **事件属性约束**：
   - **XML 侧**：所有 `on*` DOM 原生事件属性被拒；只允许 `on-click` 等管道指令属性
   - **HTML 侧**：因 Shadow DOM + 沙箱注入隔离，作者只能通过自己的 JS 调 `sys.*` 与组件方法；HTML 内联 `onclick="..."` 等仍会被解析器与 CSP 双重拦截
4. **资源大小限制**：单个 HTML/CSS/JS 文件 ≤ N MB（具体数值由实现确定）

### 9.2 运行时隔离

- 不同插件的 `plugin` scope 互不可见
- HTML 沙箱 Shadow DOM 隔离样式
- 插件无法访问 WebUI 主程序内部模块、Pinia Store、Vue 实例
- 唯一交互通道是 `sys.*`

### 9.3 API 调用边界

> v3.1 起，本节不再涉及"用户权限白名单"。仅保留**插件身份边界**：

- 实际请求时 `X-Plugin-Name` 在前端由系统注入（来自当前 page 的注册元数据），插件无法伪造
- 后端可基于此做二次校验（例如对插件 ID 做 IP 速率限制、API 调用审计）
- 注册时元数据中的 `plugin_name` 必须与发起注册的插件身份一致；不一致直接拒绝注册

### 9.4 卸载流程（重要）

**核心原则：系统对插件禁用 / 重载零感知，不主动动 Registry。**

| 触发场景 | 系统行为 |
|---|---|
| 插件被禁用 | **不动**——系统无法可靠探测，Registry 保留，UI 仍可达 |
| 插件主程序重载 | **不动**——同上 |
| 插件静默崩溃 | **不动**——同上 |
| 插件主动调用 `unregister_ui_page` | 立即从 Registry 移除 |
| 插件主动调用 `unregister_plugin_pages` | 移除该插件所有 page |
| WebUI 主程序重启 | Registry 全清空（设计为内存态，不做硬持久） |

> **设计取舍说明**（必须写进开发者守则）：
>
> - 插件作者负责在"真正想清理"的场景调用 unregister，例如：用户在管理面板点击"清理插件 UI 缓存"时
> - 插件 disable 时不调 unregister——因为系统根本不知道你 disable 了，没人会替你触发；这是有意为之的零感知设计，避免热重载/调试期反复加载丢失用户工作
> - 由于 Registry 是内存态，WebUI 重启天然就清空了"陈旧 Registry"；这是兜底机制

### 9.5 安全审计点（实现 checklist）

- [ ] XML 解析后过一遍标签白名单
- [ ] 属性过滤包含 `on*` 原生事件
- [ ] 占位符表达式禁止 `()` 函数调用（除内置 helper 名单：`empty` / `len` / `keys` / `values` / 格式化函数）
- [ ] HTML 静态资源仅以只读 GET 暴露
- [ ] 静态资源路径必须落在插件目录内（防路径穿越）
- [ ] sys.request 内置 `X-Plugin-Name` 是后端确认而非前端宣称
- [ ] 注册时元数据中的 `plugin_name` 必须与发起注册的插件身份一致
- [ ] HTML 沙箱中 `window.fetch` / `XMLHttpRequest` 必须被代理重写到 `sys.request` 同一拦截链

---

## 10. 组件清单速查表

> 本表用于实现侧 / 文档侧的快速对照。XML 列与 HTML 列同名表示底层共享内核。
> v3.1 起：原"系统级 / 嵌入组件"清单整体移出——`<plugin-page-picker>` 是 WebUI 主程序自身的官方组件；`<sys-include>` / `<sys-bind>` / `<sys-toast-anchor>` 不再作为插件可写标签存在。

### 10.1 布局类（仅 XML 提供，HTML 用户用原生 div / CSS）

| XML 标签 | 作用 |
|---|---|
| `<vbox>` / `<hbox>` | 纵 / 横排列 |
| `<grid>` | 网格 |
| `<card>` | MD3 卡片 |
| `<tabs>` / `<tab>` | 标签页 |
| `<dialog>` | 对话框（HTML 用 `<sys-dialog>`） |
| `<divider>` / `<spacer>` | 分割线 / 弹性空白 |

### 10.2 基础输入与展示（双轨同名）

| 名称 | XML | HTML | 备注 |
|---|---|---|---|
| 文本 | `<sys-text>` | `<sys-text>` | 占位符渲染 |
| 输入框 | `<sys-input>` | `<sys-input>` | 双向绑定 / 命令式 setValue |
| 文本域 | `<sys-textarea>` | `<sys-textarea>` | — |
| 下拉 | `<sys-select>` | `<sys-select>` | HTML 轨可 `setOptions(arr)` 动态注入 |
| 开关 | `<sys-switch>` | `<sys-switch>` | — |
| 滑块 | `<sys-slider>` | `<sys-slider>` | — |
| 日期 | `<sys-date-picker>` | `<sys-date-picker>` | — |
| 按钮 | `<sys-button>` | `<sys-button>` | XML 用 `on-click` 管道；HTML 监听 `click` + 调 `sys.*` |
| 图标按钮 | `<sys-icon-button>` | `<sys-icon-button>` | — |
| 图标 | `<sys-icon>` | `<sys-icon>` | Material Symbols |
| 标签 / 徽章 | `<sys-tag>` / `<sys-badge>` | `<sys-tag>` / `<sys-badge>` | — |

### 10.3 高级数据组件（双轨同名）

| 名称 | XML | HTML | 备注 |
|---|---|---|---|
| 数据表格 | `<sys-table>` | `<sys-table>` | 含 `<column>` `<map>` `<format>` `<progress>` `<actions>` 子元素；HTML 轨可 `setData(arr)` 直接喂数据 |
| 图表 | `<sys-chart>` | `<sys-chart>` | type=line/bar/pie/area |
| 表单容器 | `<sys-form>` | `<sys-form>` | XML 偏声明式；HTML 轨直接 `el.validate()` |
| 列表 | `<sys-list>` | `<sys-list>` | 配 `item-template` |
| 对话框 | `<dialog>` (XML) | `<sys-dialog>` (HTML) | — |
| Toast | 通过 `notify:` 指令 | `sys.ui.notify(...)` 或 `<sys-toast>` 元素 | — |

### 10.4 通用属性速查

不是组件，但全部 sys-* 都支持，回顾一遍：

| 属性 | 作用 |
|---|---|
| `id` | 组件 ID |
| `value` | 渲染值（占位符） |
| `bind` / `data-bind` | 双向绑定 |
| `disabled` | 禁用 |
| `hidden` | 隐藏 |
| `readonly` | 只读 |
| `loading` | 加载态 |
| `mobile-only` / `desktop-only` | 视口可见性 |
| `class` / `style` | 样式透传（受白名单过滤） |

### 10.5 给宿主用的预定义入口（非插件提供）

这些是 WebUI 自身渲染时用，不属于插件作者编写范畴，但与本设计强相关：

- 插件页面装载入口：根据系统生成路径 `/plugins/{plugin}/{page}` 渲染对应 schema
- "插件中心"页面：基于 WebUI 官方组件 `<plugin-page-picker>` 的导航视图（**该组件不属于插件可用清单**）
- 移动端 fallback 包装：参见 8.4 节

### 10.6 HTML 轨 Web Component 命令式 JS API 速查

> 在 HTML 轨中，所有 `<sys-*>` 组件除了支持 `data-bind` 等属性绑定外，**还提供命令式 JS 方法和自定义事件**，开发者可完全脱离属性绑定、用 JS 控制组件状态。

#### 10.6.1 通用方法（所有 sys-* 组件都有）

| 方法 | 作用 |
|---|---|
| `el.disable()` / `el.enable()` | 禁用 / 启用 |
| `el.setReadonly(bool)` | 设只读 |
| `el.setHidden(bool)` | 显示 / 隐藏 |
| `el.setLoading(bool)` | 加载态切换 |
| `el.refresh()` | 强制刷新（数据组件常用） |
| `el.focus()` / `el.blur()` | 焦点控制 |

#### 10.6.2 输入类（input / textarea / select / switch / slider / date-picker）

| 方法 / 事件 | 作用 |
|---|---|
| `el.setValue(v)` / `el.getValue()` | 读写值 |
| `el.setOptions(arr)` | 仅 select：动态设置选项 |
| `el.setError(msg)` / `el.clearError()` | 设 / 清错误提示 |
| `el.validate()` | 触发校验，返回 boolean |
| 事件 `change` | 值变化 |
| 事件 `input` | 输入中（仅 input / textarea） |

#### 10.6.3 按钮类（`<sys-button>` / `<sys-icon-button>`）

| 方法 / 事件 | 作用 |
|---|---|
| `el.setText(s)` / `el.setIcon(name)` | 改文案 / 图标 |
| `el.setVariant(v)` | primary / secondary / text / danger |
| 事件 `click` | 点击（标准 DOM 事件） |

#### 10.6.4 表格（`<sys-table>`）

| 方法 / 事件 | 作用 |
|---|---|
| `el.setData(arr)` | 直接喂数据（不走 data-bind） |
| `el.getSelected()` / `el.setSelected(rows)` | 选中读写 |
| `el.gotoPage(n)` / `el.setPageSize(n)` | 分页控制 |
| `el.sortBy(field, order)` | 排序 |
| 事件 `row-click` / `selection-change` / `action`（行操作） | — |

#### 10.6.5 图表（`<sys-chart>`）

| 方法 | 作用 |
|---|---|
| `el.setData(arr)` / `el.setType(t)` | 重设数据 / 图表类型 |
| `el.exportImage()` | 导出图片 |

#### 10.6.6 对话框（`<sys-dialog>`）

| 方法 / 事件 | 作用 |
|---|---|
| `el.open()` / `el.close()` | 开 / 关 |
| 事件 `open` / `close` / `confirm` / `cancel` | 对应生命周期 |

#### 10.6.7 表单（`<sys-form>`）

| 方法 / 事件 | 作用 |
|---|---|
| `el.validate()` | 全表单校验，返回 boolean |
| `el.reset()` | 清空所有子输入 |
| 事件 `submit` | 用户提交（点击 `<sys-button type="submit">` 时触发） |

---

## 附录 A：与上一版的差异

### A.1 v2.0 → v3.0

| 维度 | v2.0 | v3.0 |
|---|---|---|
| UI 模型 | 单轨 XML | 双轨 XML + HTML/Web Components |
| 数据流 | dataStore + data-bind | 全局响应式变量池 + 占位符 |
| 路由 | 文档隐含但插件可猜 | 明确：系统生成，不暴露给插件 |
| 卸载 | 暗示自动 | 必须显式调用 |
| 移动端 | 无 | 三件套 + fallback 横滚 |
| 错误处理 | 由插件作者写 on-error | 系统拦截层统一 toast；管道自动中断 |
| API | 写完整 endpoint | 预定义 API 模板，调用时填参 |
| 沙箱 | XSD + 白名单 | 同 + Shadow DOM + 强制 sys.* |

### A.2 v3.0 → v3.1（本稿）

| 维度 | v3.0 | v3.1 |
|---|---|---|
| 用户权限 | `permission` 属性 / `permissions` 白名单 / `sys.permissions.has` / 9.4 节 | **全部移除**（框架不再涉及用户权限） |
| 全局用户身份 | `sys.global.user.*` | 移除（无多用户登录） |
| 插件禁用 / 重载 | 标记 inactive，从导航隐藏 | **零感知**：系统不动 Registry，UI 仍可达；仅显式 unregister 才清理 |
| HTML 出站请求 | `window.fetch` / `XHR` 被禁用 | **被代理重写**到 `sys.request` 同一拦截链（兼容第三方库） |
| HTML 事件 / 编排 | 可用属性管道 `data-on-click` | **属性管道废止**：HTML 轨一律用 JS + `sys.*` |
| HTML 轨组件控制 | 主推占位符 + 部分 JS 读写 | **命令式 JS API 主推**：每个 sys-* 组件提供 setValue/setOptions/setData/setLoading/disable/enable 等方法（见 10.6）|
| `sys.ui.*` 快捷入口 | 散落在 `sys.notify` / `sys.confirm` 等 | **统一在 `sys.ui.*`**：notify / toast / notice / confirm / alert / dialog.open / dialog.close |
| 双轨混用 | 文档暗示可同 page 跨轨道共享变量 | **page 维度二选一**：同一 page 内不能混用 XML 与 HTML |
| 系统级 / 嵌入组件 | `<plugin-page-picker>` / `<sys-include>` / `<sys-bind>` / `<sys-toast-anchor>` 在插件可用清单里 | **全部移出**插件清单。`<plugin-page-picker>` 改为 WebUI 官方组件；变量声明改为只用 `<definitions>` 中的 `<var>` |
| 条件交互 | disabled / hidden / readonly / loading / **permission** | 同上五个，**permission 已删** |

---

## 附录 B：开发者守则（精简版）

1. **不要写路由**：系统按 `plugin_name:page_id` 自动生成路径
2. **不要假定自动卸载**：要清就显式 `unregister_*`；插件被禁用 / 重载 / 静默崩溃时**系统零感知**，UI 仍在
3. **不要绕过统一请求链路**：`window.fetch` / `XHR` 已被代理重写到 `sys.request`；优先使用 `sys.api` / `sys.request`，第三方库直接调 `fetch` 也会走统一拦截，但**不要假设它绕过了任何拦截**
4. **不要在 XML 事件处理里写 JSON**：API 用模板，事件里写 `api: <id>(...)`
5. **不要在 HTML 轨里写管道指令**：`data-on-click="api: ... | ..."` 已被废弃；事件、请求、组件控制一律用 JS + `sys.*` + Web Components 命令式 API
6. **不要静默失败**：错误一定走全局 toast / dialog，符合项目规范
7. **不要用 `localStorage` 存"配置类"状态**：跟着 WebUI 主程序的 `settings` 走（项目已有约定）
8. **不要跨插件 import**：双轨之间共享只能通过公开组件签名 / 公共 page，不能伸手要别家的私有变量
9. **不要在同一 page 内混用 XML 与 HTML**：page 维度二选一；需要兼有两种风格请注册多个 page
10. **不要尝试在 XML/HTML 中写 `<plugin-page-picker>`**：它是 WebUI 官方导航组件，不在插件可用清单内
11. **要给移动端一份**：哪怕只是 XML 的简化版；不给的话，用户在手机上只能横向滚
12. **要尽量用占位符 + 通用属性**：XML 轨的 `disabled` / `hidden` / `loading` 这些足够覆盖 80% 交互；HTML 轨同样有等价命令式 API
13. **要做危险操作二次确认**：XML 用 `confirm:` 管道；HTML 用 `await sys.ui.confirm(...)`

---

## 总结

本设计给出 Neo-MoFox WebUI 的 v3.1 双轨响应式 UI 框架方案：

- **数据驱动**的运行时（响应式变量池 + 占位符 + 命令式 JS API）
- **XML 与 HTML/Web Components 双轨并存**，但 **page 维度二选一**，不在同一 page 内混用
- **路径系统自管理 + 显式卸载**，对插件禁用 / 重载 **零感知**，避免热重载误清
- **移动端可选三件套，fallback 横向滚动**，平衡完成度与可用性
- **HTML 沙箱通过 `sys.*` 桥接 + Shadow DOM**，`window.fetch` / `XHR` 被代理重写到统一拦截链，新增 `sys.ui.*` 系统内部前端 API 快捷入口（notify / notice / confirm / dialog 等）
- **HTML 轨用 JS + `sys.*` 编排**，废弃属性管道；Web Components 提供完整命令式 JS API（setValue / setOptions / setData / setLoading / disable / enable …）
- **去除用户权限验证**：`permission` 属性 / `permissions` 白名单 / `sys.permissions.has` / `sys.global.user.*` 全部移除
- **CSS 变量与 MD3 主题接入**，主题切换零成本
- **系统级 / 嵌入组件全部移出插件清单**：`<plugin-page-picker>` 是 WebUI 官方组件，不属于插件可写标签
- **完整组件清单见第 10 章**，是实现方与文档方的对照表

下一步建议：

1. 评审本稿设计边界（特别是"对禁用零感知"、"HTML fetch 改为代理重写"、"page 维度二选一"三条强约束）
2. 确认 `sys.ui.*` 快捷入口与现有 WebUI 内部前端 API 的能力对齐情况（notify / notice / dialog 等是否已有现成实现可桥接）
3. 再分模块拆 Phase（Registry / 占位符运行时 / XML 渲染器 / HTML 沙箱 / fetch 代理 / 内置组件库 / sys.ui 桥接）

---

**版本历史**：

- **v3.1.0 (2026-06-19)** — 双轨响应式 UI 框架（v3.1 调整版）：
  - 移除全部用户权限相关设计（`permission` 属性 / `permissions` 白名单 / `sys.permissions.has` / `sys.global.user.*`）
  - 系统对插件禁用 / 重载 **零感知**，Registry 不动，仅显式 unregister 才清理
  - HTML 沙箱中 `window.fetch` / `XHR` 由"禁用"改为"代理重写到 `sys.request` 同一拦截链"
  - HTML 轨**废弃属性式管道指令**，事件 / 请求 / 组件控制一律用 JS + `sys.*`
  - HTML 轨 Web Components 提供完整命令式 JS API（10.6 节）
  - 新增 `sys.ui.*` 系统内部前端 API 快捷入口
  - 明确 page 维度 **XML / HTML 二选一**，不在同一 page 内混用
  - 移除"系统级 / 嵌入组件"清单：`<plugin-page-picker>` 改为 WebUI 官方组件、`<sys-include>` / `<sys-bind>` / `<sys-toast-anchor>` 不再可写
- v3.0.0 (2026-06-18) — 双轨响应式 UI 框架（方案 C），引入响应式变量池、HTML/Web Components 轨道、移动端三件套、显式卸载与系统生成路径
- v2.0.0 (2026-05-04) — 单轨 XML 动态注册（已被 v3 取代）
- v1.0.0 (2026-05-03) — 初始静态 XML（已废弃）

