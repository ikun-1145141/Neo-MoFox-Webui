# Neo-MoFox WebUI 插件前端扩展系统 — 前端实现方案

**关联设计文档**: [`Neo-MoFox-WebUI-Plugin-Extension-Design.md`](../Neo-MoFox-WebUI-Plugin-Extension-Design.md:1)
**关联后端方案**: [`Backend-Implementation.md`](./Backend-Implementation.md:1)
**目标版本**: v3.1.0
**适用项目**: [`Neo-MoFox-Webui/frontend/`](../../frontend:1)（Vue 3 + TypeScript 前端）
**作者**: MoFox Team
**状态**: 实现方案稿

---

## 0. 文档目的与读者

本文档面向 **WebUI 前端实现者**，给出"如何把设计文档里的双轨 UI 能力在 [`frontend/src/`](../../frontend/src:1) 里落地"的工程方案。读者预设：

- 已读 [`Neo-MoFox-WebUI-Plugin-Extension-Design.md`](../Neo-MoFox-WebUI-Plugin-Extension-Design.md:1) 全文
- 已读 [`Backend-Implementation.md`](./Backend-Implementation.md:1)（了解后端 API 端点与数据结构）
- 熟悉本仓库前端分层规范（[`.kilocode/rules/设计文档.md`](../../../.kilocode/rules/设计文档.md:1)）：API 层 → View 层 → 组件层 → 工具层
- 熟悉技术栈：Vue 3 Composition API + TypeScript + Vue Router + Axios + ECharts

---

## 📋 目录

1. [整体落地策略](#1-整体落地策略)
2. [前端目录结构变更](#2-前端目录结构变更)
3. [TypeScript 类型定义](#3-typescript-类型定义)
4. [API 模块（plugin-ui.ts）](#4-api-模块plugin-uits)
5. [动态路由注册](#5-动态路由注册)
6. [响应式变量池 Store](#6-响应式变量池-store)
7. [占位符解析器](#7-占位符解析器)
8. [XML 渲染器](#8-xml-渲染器)
9. [HTML 沙箱渲染器](#9-html-沙箱渲染器)
10. [sys 桥接对象](#10-sys-桥接对象)
11. [Web Components 组件库](#11-web-components-组件库)
12. [fetch 代理与请求拦截](#12-fetch-代理与请求拦截)
13. [移动端适配与 fallback](#13-移动端适配与-fallback)
14. [插件页面导航（plugin-page-picker）](#14-插件页面导航plugin-page-picker)
15. [测试策略](#15-测试策略)
16. [里程碑（Phase 划分）](#16-里程碑phase-划分)

---

## 1. 整体落地策略

### 1.1 一句话总结

在现有 [`frontend/src/`](../../frontend/src:1) 内**新增一个"插件 UI 运行时子系统"**，按设计文档的架构分层图实现以下核心模块：

| 模块 | 作用 | 落点 |
|---|---|---|
| API 模块 | 与后端 Discovery / Schema / Asset Router 通信 | `src/api/modules/plugin-ui.ts` + `src/api/types/plugin-ui.ts` |
| 动态路由 | 按 Discovery 结果注册 `/plugins/{name}/{page}` 路由 | `src/router/plugin-ui-routes.ts` |
| 变量池 Store | 响应式 page / plugin / global 三级 scope | `src/stores/plugin-ui-vars.ts` |
| 占位符解析器 | `{var.path}` / `{!x}` / `{len(list) > 5}` 解析与响应式绑定 | `src/utils/plugin-ui/placeholder-parser.ts` |
| XML 渲染器 | XML 字符串 → Vue 组件树 | `src/utils/plugin-ui/xml-renderer.ts` |
| HTML 沙箱渲染器 | Shadow DOM + sys 注入 + fetch 代理 | `src/utils/plugin-ui/html-sandbox.ts` |
| sys 桥接对象 | HTML 轨唯一交互通道 | `src/utils/plugin-ui/sys-bridge.ts` |
| Web Components 库 | `<sys-*>` 自定义元素（命令式 API） | `src/components/plugin-ui/web-components/` |
| 内置 Vue 组件 | XML 轨用的 Vue 组件映射 | `src/components/plugin-ui/xml-components/` |
| 插件页面容器 | 承载 XML / HTML 渲染结果的 View | `src/views/PluginPageView.vue` |
| 导航组件 | `<plugin-page-picker>`（WebUI 官方组件） | `src/components/plugin-ui/PluginPagePicker.vue` |

### 1.2 与设计文档的对应关系

| 设计文档章节 | 对应前端模块 |
|---|---|
| §2.1 变量池 | [§6 响应式变量池 Store](#6-响应式变量池-store) |
| §2.2 占位符语法 | [§7 占位符解析器](#7-占位符解析器) |
| §2.3 双轨 UI | §8 XML 渲染器 + §9 HTML 沙箱 |
| §3 注册与 Discovery | §4 API 模块 + §5 动态路由 |
| §4 XML 声明式 UI | §8 XML 渲染器 + §11 Web Components |
| §5 HTML/Web Components | §9 HTML 沙箱 + §10 sys 桥接 + §11 Web Components |
| §6 管道指令（仅 XML） | §8.4 管道指令执行引擎 |
| §7 API 模板 | §6.3 API 模板 Store + §8.4 `api:` 指令 |
| §8 移动端适配 | [§13 移动端适配](#13-移动端适配与-fallback) |
| §10 组件清单 | §11 Web Components 组件库 |

### 1.3 强约束清单

1. **`api/types/` 中的类型必须与后端 Pydantic 模型 1:1 对应**
2. **所有后端数据必须用 `ref` / `reactive` 包装**
3. **错误不静默**——全局 Toast / Dialog
4. **图标本地化**——只使用 `frontend/public/material-symbols`
5. **主题不存 localStorage**——通过后端 settings 持久化
6. **API 集中管理**——所有通信只在 `api/` 层发生
7. **page 维度二选一**——同一页面容器内不混用 XML 与 HTML 渲染
8. **HTML 轨不识别管道指令**——纯 JS + sys.* 编排
9. **window.fetch / XHR 被代理重写**——HTML 沙箱内统一走拦截链

---

## 2. 前端目录结构变更

在现有 [`frontend/src/`](../../frontend/src:1) 下增加：

```
src/
├── api/
│   ├── modules/
│   │   └── plugin-ui.ts                    # 新增：Discovery + Schema API 调用
│   └── types/
│       └── plugin-ui.ts                    # 新增：与后端模型 1:1 对应的 TS 类型
├── components/
│   └── plugin-ui/                          # 新增子目录
│       ├── PluginPagePicker.vue            # 新增：WebUI 官方导航组件
│       ├── PluginPageContainer.vue         # 新增：页面渲染容器（双轨分发）
│       ├── XmlRenderer.vue                 # 新增：XML → Vue 组件树
│       ├── HtmlSandbox.vue                 # 新增：Shadow DOM + sys 注入
│       ├── MobileFallback.vue              # 新增：横向滚动 fallback 壳
│       ├── xml-components/                 # 新增：XML 轨内置 Vue 组件
│       │   ├── SysText.vue
│       │   ├── SysInput.vue
│       │   ├── SysButton.vue
│       │   ├── SysTable.vue
│       │   ├── SysChart.vue
│       │   ├── SysForm.vue
│       │   ├── SysList.vue
│       │   ├── SysDialog.vue
│       │   ├── ... (完整列表见 §11)
│       │   └── index.ts                    # 组件注册表
│       └── web-components/                 # 新增：HTML 轨 Web Components
│           ├── sys-text.ts
│           ├── sys-input.ts
│           ├── sys-button.ts
│           ├── sys-table.ts
│           ├── sys-chart.ts
│           ├── sys-dialog.ts
│           ├── ... (完整列表见 §11)
│           └── register-all.ts             # 统一 customElements.define
├── router/
│   └── plugin-ui-routes.ts                 # 新增：动态路由注册逻辑
├── stores/
│   └── plugin-ui-vars.ts                   # 新增：响应式变量池（无 Pinia，用 reactive）
├── utils/
│   └── plugin-ui/                          # 新增子目录
│       ├── placeholder-parser.ts           # 占位符解析 + 响应式绑定
│       ├── xml-renderer.ts                 # XML 解析 → 虚拟 DOM 树
│       ├── html-sandbox.ts                 # HTML 沙箱创建 + 生命周期
│       ├── sys-bridge.ts                   # sys 对象构建
│       ├── fetch-proxy.ts                  # window.fetch / XHR 重写
│       ├── pipe-executor.ts                # 管道指令执行引擎（仅 XML）
│       ├── api-template-engine.ts          # API 模板解析与执行
│       └── expression-evaluator.ts         # 安全表达式求值器
└── views/
    └── PluginPageView.vue                  # 新增：/plugins/:name/:page 路由对应 View
```

> 现有文件**不动**（AppShell.vue 后续可能要在侧边栏添加"插件中心"入口，但这是 UI 层变化，不影响架构）。

---

## 3. TypeScript 类型定义

落点：[`src/api/types/plugin-ui.ts`](../../frontend/src/api/types/plugin-ui.ts:1)

与后端 [`Plugin/utils/plugin_ui_types.py`](../../Plugin/utils/plugin_ui_types.py:1) 严格 1:1 对应：

```typescript
// === 枚举 ===
export type PageMode = 'xml' | 'html'

// === HTML 资源声明 ===
export interface HTMLAssets {
  entry_html: string
  styles: string[]
  scripts: string[]
  assets_dir: string | null
}

// === 移动端 variant ===
export interface MobileVariant {
  mode: PageMode
  xml: string | null
  assets: HTMLAssets | null
}

// === Discovery 列表项 ===
export interface PageSummary {
  plugin_name: string
  page_id: string
  title: string
  icon: string | null
  description: string | null
  order: number
  mode: PageMode
  route_path: string
  has_mobile: boolean
}

// === 详情 ===
export interface PageDetail extends PageSummary {
  mobile_mode: PageMode | null
  desktop_assets_urls: Record<string, string[]> | null
  mobile_assets_urls: Record<string, string[]> | null
}

// === Schema 响应 ===
export interface PageSchemaResponse {
  mode: PageMode
  xml: string | null
  assets_urls: Record<string, string[]> | null
}
```

---

## 4. API 模块（plugin-ui.ts）

落点：[`src/api/modules/plugin-ui.ts`](../../frontend/src/api/modules/plugin-ui.ts:1)

所有请求通过 [`src/api/base.ts`](../../frontend/src/api/base.ts:1) 的 axios 实例发出（统一 Token 注入 + 错误 Toast）。

```typescript
import instance from '../base'
import type { PageSummary, PageDetail, PageSchemaResponse } from '../types/plugin-ui'

/** 获取所有插件页面列表 */
export function listPluginPages(): Promise<PageSummary[]> {
  return instance.get('/webui/api/plugin-ui/list')
}

/** 获取指定插件的页面列表 */
export function listPluginPagesByPlugin(pluginName: string): Promise<PageSummary[]> {
  return instance.get(`/webui/api/plugin-ui/list/${pluginName}`)
}

/** 获取页面详情 */
export function getPageDetail(pluginName: string, pageId: string): Promise<PageDetail> {
  return instance.get(`/webui/api/plugin-ui/detail/${pluginName}/${pageId}`)
}

/** 获取页面 schema（XML 内容或 HTML 资源 URL） */
export function getPageSchema(
  pluginName: string,
  pageId: string,
  variant: 'desktop' | 'mobile' = 'desktop'
): Promise<PageSchemaResponse> {
  return instance.get(`/webui/api/plugin-ui/schema/${pluginName}/${pageId}`, {
    params: { variant }
  })
}
```

---

## 5. 动态路由注册

落点：[`src/router/plugin-ui-routes.ts`](../../frontend/src/router/plugin-ui-routes.ts:1)

### 5.1 设计思路

设计文档要求"路径系统自管理"——前端不硬编码每个插件 page 的路由，而是：

1. 在 [`src/router/index.ts`](../../frontend/src/router/index.ts:1) 中注册一条**通配路由**：`/plugins/:pluginName/:pageId`
2. 该路由对应的 View（`PluginPageView.vue`）在 `onMounted` 时调 Discovery API 验证有效性
3. 无效的 `pluginName:pageId` 组合重定向到 404 或插件中心

### 5.2 路由配置变更

在现有 [`router/index.ts`](../../frontend/src/router/index.ts:1) 的 routes 数组中，**在 catch-all `/:pathMatch(.*)*` 之前**插入：

```typescript
{
  path: '/plugins/:pluginName/:pageId',
  name: 'plugin-page',
  component: () => import('../views/PluginPageView.vue'),
  meta: { requiresAuth: true, title: '插件页面' },
  props: true
}
```

### 5.3 PluginPageView.vue 行为

```
props: { pluginName: string, pageId: string }

onMounted:
  1. 调 getPageDetail(pluginName, pageId)
  2. 判断 viewport 是否 < 768px（移动端）
  3. 调 getPageSchema(pluginName, pageId, variant)
     - variant=mobile 返回 204/null → 进入 fallback 模式
  4. 根据 schema.mode 选择 <XmlRenderer> 或 <HtmlSandbox>
  5. 创建 page scope 变量池
  6. 渲染

onUnmounted:
  7. 销毁 page scope 变量池
  8. HTML 沙箱清理（移除 Shadow DOM、解绑 fetch 代理）
```

---

## 6. 响应式变量池 Store

落点：[`src/stores/plugin-ui-vars.ts`](../../frontend/src/stores/plugin-ui-vars.ts:1)

### 6.1 设计原则

- **不用 Pinia**——变量池是动态的、按页面实例化/销毁的；Pinia store 更适合全局单例
- 直接用 Vue 3 的 `reactive` + `computed` 构建
- 三级 scope 用三个独立 `reactive` 对象表示

### 6.2 核心接口

```typescript
export interface PluginUIVarStore {
  /** page scope：进入页面创建 / 离开销毁 */
  page: Record<string, any>

  /** plugin scope：同插件的所有 page 共享 */
  plugin: Record<string, any>

  /** global scope：只读，WebUI 主程序写入 */
  readonly global: Readonly<Record<string, any>>

  /** 取值（自动按 page → plugin → global 优先级解析） */
  get(path: string): any

  /** 写值（仅 page / plugin 可写；global 写操作静默忽略） */
  set(path: string, value: any): void

  /** 销毁 page scope */
  destroyPageScope(): void
}
```

### 6.3 API 模板状态自动注入

设计文档 §6.4 的 `api.<id>.pending / error / last_response` 是系统保留命名空间。实现策略：

- `api-template-engine.ts` 在执行 API 请求前/后自动写入 `store.set('api.<id>.pending', true/false)`
- 这些值在 page scope 下，组件通过占位符 `{api.saveUser.pending}` 自动响应

### 6.4 global scope 写入

`global` 由 WebUI 主程序在应用启动时填入：

```typescript
const globalVars = reactive({
  theme: { mode: 'auto', primary_color: '#0058bd' },
  language: 'zh-CN',
  webui_version: '1.0.0'
})
```

任何插件页面对 global 的写操作被 `set()` 拦截并静默忽略（设计 §2.1 要求）。

---

## 7. 占位符解析器

落点：[`src/utils/plugin-ui/placeholder-parser.ts`](../../frontend/src/utils/plugin-ui/placeholder-parser.ts:1)

### 7.1 解析流程

输入：含占位符的字符串，如 `"欢迎，{user.name}！共 {len(list)} 条"`

输出：一个 Vue `computed` 或 `watchEffect` 可绑定的响应式值

### 7.2 语法解析（与设计 §2.2 完全对齐）

解析器将字符串拆分为 **静态文本段** 与 **表达式段**：

```
"欢迎，{user.name}！共 {len(list)} 条"
 ↓
 [
   { type: 'text', value: '欢迎，' },
   { type: 'expr', expr: 'user.name' },
   { type: 'text', value: '！共 ' },
   { type: 'expr', expr: 'len(list)' },
   { type: 'text', value: ' 条' }
 ]
```

### 7.3 表达式求值器

落点：[`src/utils/plugin-ui/expression-evaluator.ts`](../../frontend/src/utils/plugin-ui/expression-evaluator.ts:1)

**安全沙箱求值**——不用 `eval` / `new Function`，而是实现一个极简 AST 解释器：

| 支持 | 说明 |
|---|---|
| 标识符 / 点路径 | `user.name` → `store.get('user.name')` |
| 取反 `!` | `!form_valid` → `!store.get('form_valid')` |
| 比较运算 | `> < >= <= == !=` |
| 逻辑运算 | `&& \|\| !` |
| 字面量 | 数字、字符串、true/false/null |
| 内置函数 | `empty(x)` / `len(x)` / `keys(x)` / `values(x)` |
| 属性访问器 | `list.length` / `obj.keys` |

**禁止**：任何括号组合的函数调用（除白名单）、赋值、分号等。

实现建议：用递归下降解析器（~200行 TS），不引入外部 parser 库。

### 7.4 响应式绑定

`resolvedPlaceholder(template: string, store: PluginUIVarStore)` 返回 `ComputedRef<string>`：

```typescript
import { computed } from 'vue'

export function resolvedPlaceholder(
  template: string,
  store: PluginUIVarStore
): ComputedRef<string> {
  const segments = parse(template)
  return computed(() => {
    return segments.map(seg => {
      if (seg.type === 'text') return seg.value
      return String(evaluate(seg.expr, store))
    }).join('')
  })
}
```

因为 `store.page` / `store.plugin` 都是 `reactive` 对象，Vue 的响应式追踪会自动在表达式依赖的变量变化时重新计算。

---

## 8. XML 渲染器

落点：[`src/utils/plugin-ui/xml-renderer.ts`](../../frontend/src/utils/plugin-ui/xml-renderer.ts:1) + [`src/components/plugin-ui/XmlRenderer.vue`](../../frontend/src/components/plugin-ui/XmlRenderer.vue:1)

### 8.1 整体流程

```
XML 字符串
  ↓ DOMParser 解析
AST（DOM 树）
  ↓ 遍历转换
Vue VNode 树（h() 函数调用）
  ↓ Vue render 渲染
实际 DOM
```

### 8.2 XML 解析

使用浏览器原生 `DOMParser`：

```typescript
const parser = new DOMParser()
const doc = parser.parseFromString(xmlString, 'application/xml')
```

解析错误（`<parsererror>`）→ 显示错误面板，不渲染。

### 8.3 节点映射

遍历 DOM 树，每个元素节点映射到对应的 Vue 组件：

| XML 标签 | Vue 组件 |
|---|---|
| `<vbox>` | `SysVbox` |
| `<hbox>` | `SysHbox` |
| `<grid>` | `SysGrid` |
| `<card>` | `SysCard` |
| `<sys-text>` | `SysText` |
| `<sys-input>` | `SysInput` |
| `<sys-button>` | `SysButton` |
| `<sys-table>` | `SysTable` |
| ... | 完整映射见 §11 |

未知标签 → 报错（后端已校验，但前端做二次防御）。

### 8.4 管道指令执行引擎

落点：[`src/utils/plugin-ui/pipe-executor.ts`](../../frontend/src/utils/plugin-ui/pipe-executor.ts:1)

**仅 XML 轨可用**。解析 `on-click="api: saveUser(name={form.name}) | notify: '保存成功' | refresh: usersTable"` 这类属性。

#### 解析规则

```
指令字符串 → split by ' | ' → 指令节点列表
每个节点 = { name: string, args: string }
```

#### 指令实现

| 指令 | 实现 |
|---|---|
| `set` | `store.set(path, value)` |
| `api` | 调用 API 模板引擎，await 结果 |
| `notify` | `useToastStore().show(msg, level)` |
| `confirm` | `await useDialogStore().confirm(msg)`；取消则 throw 中断管道 |
| `navigate` | `router.push(resolvePluginRoute(target))` |
| `open-dialog` / `close-dialog` | `store.set('__dialog_<id>_open', true/false)` |
| `refresh` | 找到对应组件实例调 `refresh()` |
| `reset` | `store.set(path, defaultValue)` |
| `emit` | 事件总线 `bus.emit(eventName)` |

#### 错误传播

任何管道节点 throw → 中断后续节点。`api:` 节点的 HTTP 错误已被 axios 拦截器处理（全局 Toast），管道只需 reject。

### 8.5 `<definitions>` 处理

XML 的 `<definitions>` 段在渲染前预处理：

| 子元素 | 行为 |
|---|---|
| `<var name="x" default="[]">` | `store.set('x', JSON.parse(default))` |
| `<api id="..." ...>` | 注册到 API 模板引擎 |
| `<template id="...">` | 存储为子模板，`<sys-list item-template="...">` 引用时取出 |

---

## 9. HTML 沙箱渲染器

落点：[`src/utils/plugin-ui/html-sandbox.ts`](../../frontend/src/utils/plugin-ui/html-sandbox.ts:1) + [`src/components/plugin-ui/HtmlSandbox.vue`](../../frontend/src/components/plugin-ui/HtmlSandbox.vue:1)

### 9.1 渲染流程

```
后端返回 assets_urls: { entry: [url], styles: [url, ...], scripts: [url, ...] }
  ↓
HtmlSandbox.vue onMounted:
  1. 创建容器 div.plugin-html-host
  2. attachShadow({ mode: 'open' })
  3. 加载 styles → <link> 注入 Shadow DOM
  4. fetch entry_html → innerHTML 设置到 Shadow DOM
  5. 注册 Web Components（customElements.define）
  6. 构建 sys 桥接对象（§10）
  7. 重写 Shadow DOM 内的 window.fetch / XMLHttpRequest（§12）
  8. 按顺序加载并执行 scripts
```

### 9.2 Shadow DOM 隔离

- **样式隔离**：插件 CSS 在 Shadow DOM 内生效，不污染主站
- **MD3 CSS 变量穿透**：通过 `:host { }` 或 `@import` 把主站的 `--md-sys-color-*` 等 CSS 变量注入到 Shadow DOM（CSS 变量天然穿透 Shadow DOM）
- **JS 隔离**：插件脚本在一个受限的执行上下文中运行（见 §9.3）

### 9.3 脚本执行策略

不使用 `eval`，而是通过动态 `<script>` 注入到 Shadow DOM 宿主元素中，并在注入前：

1. 创建 `sys` 对象并绑定到脚本可见的作用域
2. 重写 `window.fetch` / `XMLHttpRequest`（§12）
3. 脚本以 ES Module 方式加载（`type="module"`），确保严格模式

```typescript
// 简化示意
const script = document.createElement('script')
script.type = 'module'
script.textContent = `
  const sys = window.__plugin_sys_${pageId};
  ${scriptContent}
`
shadowRoot.host.appendChild(script)
```

### 9.4 生命周期

| 时机 | 行为 |
|---|---|
| 创建 | attachShadow → 注入资源 → 执行脚本 |
| 页面离开 | 移除 Shadow DOM → 清理事件监听 → 销毁 page scope 变量池 |
| 热更新 | 销毁旧 Shadow DOM → 重新执行创建流程（后端 register 覆盖触发前端重拉 schema） |

---

## 10. sys 桥接对象

落点：[`src/utils/plugin-ui/sys-bridge.ts`](../../frontend/src/utils/plugin-ui/sys-bridge.ts:1)

### 10.1 构建

每个 HTML page 实例化时构建唯一的 `sys` 对象：

```typescript
export function createSysBridge(options: {
  store: PluginUIVarStore
  pluginName: string
  pageId: string
  router: Router
  apiTemplates: Map<string, ApiTemplate>
}): SysBridge { ... }
```

### 10.2 接口实现（与设计 §5.4 完全对齐）

#### sys.vars / sys.plugin / sys.global

```typescript
sys.vars = new Proxy(store.page, {
  get(target, prop) { return store.get(String(prop)) },
  set(target, prop, value) { store.set(String(prop), value); return true }
})

sys.plugin = new Proxy(store.plugin, { /* 同上 */ })

sys.global = Object.freeze({ ...store.global })  // 只读
```

#### sys.api(id, params)

```typescript
sys.api = async (id: string, params?: Record<string, any>) => {
  return apiTemplateEngine.execute(id, params, store)
}
```

#### sys.request(url, options)

```typescript
sys.request = async (url: string, options?: RequestInit) => {
  // 走统一拦截链（Token + X-Plugin-Name + BaseResponse 解包）
  return proxiedFetch(url, options, { pluginName })
}
```

#### sys.bus

```typescript
import mitt from 'mitt'  // 或自写 ~30行的 EventEmitter
const emitter = mitt()
sys.bus = { on: emitter.on, off: emitter.off, emit: emitter.emit }
```

> 注意：事件总线**仅当前 page**，页面销毁时 `emitter.all.clear()`。

#### sys.ui.*

```typescript
sys.ui = {
  notify: (msg, level) => useToastStore().show(msg, level),
  toast: (msg, level) => useToastStore().show(msg, level),  // 别名
  notice: (msg, opts) => { /* 写入通知中心（若已实现） */ },
  confirm: (msg, opts) => useDialogStore().confirm(msg, opts),
  alert: (msg, opts) => useDialogStore().alert(msg, opts),
  dialog: {
    open: (id) => store.set(`__dialog_${id}_open`, true),
    close: (id) => store.set(`__dialog_${id}_open`, false),
  }
}
```

#### sys.theme / sys.route / sys.format / sys.i18n

```typescript
sys.theme = Object.freeze({ mode: store.global.theme?.mode, ... })

sys.route = {
  current: router.currentRoute.value.fullPath,
  back: () => router.back()
}

sys.format = {
  date: (val, pattern) => formatDate(val, pattern),
  number: (val, opts) => formatNumber(val, opts),
  currency: (val, opts) => formatCurrency(val, opts),
}

sys.i18n = { t: (key, params) => i18n.t(key, params) }
```

---

## 11. Web Components 组件库

### 11.1 双轨共用内核

每个 `<sys-*>` 组件需要**两个实现**：

| 轨道 | 实现形式 | 落点 |
|---|---|---|
| XML 轨 | Vue SFC（`.vue`） | `src/components/plugin-ui/xml-components/` |
| HTML 轨 | Web Component（`.ts`，`HTMLElement` 子类） | `src/components/plugin-ui/web-components/` |

两者视觉上共享 CSS/MD3 变量，行为上遵循同一套 props/events 契约。

### 11.2 完整组件清单

| 组件 | XML Vue 组件 | HTML Web Component | 命令式 API |
|---|---|---|---|
| 文本 | `SysText.vue` | `sys-text.ts` | `el.setValue(s)` |
| 输入框 | `SysInput.vue` | `sys-input.ts` | `setValue/getValue/setError/clearError/validate` |
| 文本域 | `SysTextarea.vue` | `sys-textarea.ts` | 同 input |
| 下拉 | `SysSelect.vue` | `sys-select.ts` | `setOptions/setValue/getValue` |
| 开关 | `SysSwitch.vue` | `sys-switch.ts` | `setValue/getValue` |
| 滑块 | `SysSlider.vue` | `sys-slider.ts` | `setValue/getValue` |
| 日期 | `SysDatePicker.vue` | `sys-date-picker.ts` | `setValue/getValue` |
| 按钮 | `SysButton.vue` | `sys-button.ts` | `setText/setIcon/setVariant/setLoading/disable/enable` |
| 图标按钮 | `SysIconButton.vue` | `sys-icon-button.ts` | `setIcon/setLoading/disable/enable` |
| 图标 | `SysIcon.vue` | `sys-icon.ts` | `setIcon` |
| 标签 | `SysTag.vue` | `sys-tag.ts` | `setValue` |
| 徽章 | `SysBadge.vue` | `sys-badge.ts` | `setValue` |
| 数据表格 | `SysTable.vue` | `sys-table.ts` | `setData/getSelected/setSelected/gotoPage/setPageSize/sortBy` |
| 图表 | `SysChart.vue` | `sys-chart.ts` | `setData/setType/exportImage` |
| 表单 | `SysForm.vue` | `sys-form.ts` | `validate/reset` |
| 列表 | `SysList.vue` | `sys-list.ts` | `setData` |
| 对话框 | `SysDialog.vue` | `sys-dialog.ts` | `open/close` |
| Toast | —（通过指令/sys.ui） | `sys-toast.ts` | `show(msg, level)` |

### 11.3 通用方法（所有 Web Components）

每个 `sys-*` Web Component 都继承一个 `SysBaseElement` 基类：

```typescript
abstract class SysBaseElement extends HTMLElement {
  disable(): void
  enable(): void
  setReadonly(val: boolean): void
  setHidden(val: boolean): void
  setLoading(val: boolean): void
  refresh(): void
  focus(): void
  blur(): void
}
```

### 11.4 注册时机

Web Components 在 HTML 沙箱创建**之前**统一注册：

```typescript
// src/components/plugin-ui/web-components/register-all.ts
import { SysTextElement } from './sys-text'
import { SysInputElement } from './sys-input'
// ...

export function registerPluginUIWebComponents(): void {
  if (!customElements.get('sys-text')) {
    customElements.define('sys-text', SysTextElement)
  }
  // ... 其他组件
}
```

> `customElements.define` 是全局的（不受 Shadow DOM 限制），所以只需注册一次。在应用启动时调用。

---

## 12. fetch 代理与请求拦截

落点：[`src/utils/plugin-ui/fetch-proxy.ts`](../../frontend/src/utils/plugin-ui/fetch-proxy.ts:1)

### 12.1 设计意图

设计 §5.3 明确："window.fetch 与 XMLHttpRequest 不被禁用，而是被系统代理重写"。这样第三方库（如 axios、chart 库的数据加载）能透明工作，同时保证统一拦截。

### 12.2 实现策略

在 HTML 沙箱的脚本执行上下文中，重写 `window.fetch` 和 `XMLHttpRequest`：

```typescript
export function installFetchProxy(context: {
  pluginName: string
  originalFetch: typeof fetch
  getToken: () => string | null
  onError: (msg: string) => void
}): void {
  // 重写 fetch
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input.url
    const headers = new Headers(init?.headers || {})

    // 注入 Token
    const token = context.getToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
      headers.set('X-API-Key', token)
    }

    // 注入插件身份
    headers.set('X-Plugin-Name', context.pluginName)

    // 调用原始 fetch
    const response = await context.originalFetch(input, { ...init, headers })

    // BaseResponse 解包（如果是 JSON 且符合格式）
    // ...

    return response
  }

  // 类似地重写 XMLHttpRequest.prototype.open / send
}
```

### 12.3 BaseResponse 解包

对于返回 `Content-Type: application/json` 且 body 符合 `{ code, data, message }` 结构的响应：

- `code === 200` → 正常返回（response.json() 解包后仍返回完整 response，但 `sys.request` 会额外解包到 `.data`）
- `code !== 200` → 触发全局 Toast（`context.onError(message)`）

### 12.4 对 XHR 的处理

虽然现代库多用 `fetch`，仍需处理 `XMLHttpRequest` 以确保遗留代码兼容：

- 拦截 `open()` 方法记录 URL
- 拦截 `send()` 方法注入 headers
- 拦截 `onload` / `onerror` 做统一错误处理

---

## 13. 移动端适配与 fallback

### 13.1 视口检测

```typescript
const isMobile = ref(window.innerWidth < 768)
window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth < 768
})
```

### 13.2 schema 拉取策略

`PluginPageView.vue` 根据 `isMobile` 决定 variant：

```typescript
const variant = isMobile.value ? 'mobile' : 'desktop'
const schema = await getPageSchema(pluginName, pageId, variant)

if (schema === null && variant === 'mobile') {
  // 没有 mobile variant → 进入 fallback 模式
  useFallback.value = true
  schema = await getPageSchema(pluginName, pageId, 'desktop')
}
```

### 13.3 Fallback 模式

落点：[`src/components/plugin-ui/MobileFallback.vue`](../../frontend/src/components/plugin-ui/MobileFallback.vue:1)

行为（设计 §8.4）：

- 固定最小宽度容器（1024px）
- 外层水平滚动条
- 顶部提示条："该插件页面未适配移动端，已启用兼容显示"
- 内部正常渲染桌面版 schema

```vue
<template>
  <div class="mobile-fallback">
    <div class="mobile-fallback-notice">
      该插件页面未适配移动端，已启用兼容显示
    </div>
    <div class="mobile-fallback-scroll">
      <div class="mobile-fallback-content" style="min-width: 1024px">
        <slot />
      </div>
    </div>
  </div>
</template>
```

### 13.4 `mobile-only` / `desktop-only` 属性处理

XML 渲染器在映射节点时检查这两个属性：

- `mobile-only`：当 `isMobile === false` 时不渲染（返回 null VNode）
- `desktop-only`：当 `isMobile === true` 时不渲染

---

## 14. 插件页面导航（plugin-page-picker）

落点：[`src/components/plugin-ui/PluginPagePicker.vue`](../../frontend/src/components/plugin-ui/PluginPagePicker.vue:1)

设计文档明确：这是 **WebUI 官方组件**，用于"插件中心"等宿主页面浏览/选择插件 page，**不在插件可用标签清单内**。

### 14.1 功能

- 调用 `listPluginPages()` 获取所有已注册 page
- 按 `plugin_name` 分组展示
- 每个 page 卡片展示 `title / icon / description`
- 点击跳转到 `/plugins/{plugin_name}/{page_id}`
- 支持搜索/过滤

### 14.2 放置位置

可在现有 [`PluginsView.vue`](../../frontend/src/views/PluginsView.vue:1)（插件管理页面）中引入此组件，或新建独立的"插件中心"View。

---

## 15. 测试策略

| 测试目标 | 用例点 |
|---|---|
| `placeholder-parser.ts` | 静态文本、单占位符、多占位符混合、取反 `!`、`empty()/len()`、比较表达式、scope 优先级 |
| `expression-evaluator.ts` | 各运算符、内置函数、深路径访问、拒绝非白名单调用 |
| `xml-renderer.ts` | 基本布局、嵌套组件、未知标签报错、`hidden/disabled` 条件渲染、管道指令执行 |
| `pipe-executor.ts` | 单指令、多指令管道、`confirm` 取消中断、`api:` 失败中断、`set:` 写入变量 |
| `html-sandbox.ts` | Shadow DOM 创建/销毁、CSS 变量穿透、脚本执行顺序 |
| `sys-bridge.ts` | `sys.vars` 读写响应式、`sys.api()` 调通、`sys.ui.confirm` 返回 Promise |
| `fetch-proxy.ts` | Token 注入、X-Plugin-Name 注入、BaseResponse 解包、错误 Toast 触发 |
| `plugin-ui-vars.ts` | page/plugin/global scope 隔离、global 只读、`destroyPageScope` 清理 |
| Web Components | 各组件的 `setValue/getValue`、事件触发、`disable/enable`、响应式更新 |
| `PluginPageView.vue` | 正常渲染、404 跳转、mobile fallback 切换 |
| `PluginPagePicker.vue` | 列表展示、搜索过滤、跳转链接 |

测试框架：Vitest + @vue/test-utils + happy-dom。

---

## 16. 里程碑（Phase 划分）

### Phase F-1：类型 + API + 路由 + 变量池（1 周）

- `src/api/types/plugin-ui.ts`
- `src/api/modules/plugin-ui.ts`
- `src/router/plugin-ui-routes.ts`（通配路由）
- `src/stores/plugin-ui-vars.ts`
- `src/views/PluginPageView.vue`（骨架）
- 单元测试：API mock + 变量池 CRUD

### Phase F-2：占位符 + 表达式引擎 + XML 渲染器骨架（1.5 周）

- `src/utils/plugin-ui/placeholder-parser.ts`
- `src/utils/plugin-ui/expression-evaluator.ts`
- `src/utils/plugin-ui/xml-renderer.ts`
- `src/components/plugin-ui/XmlRenderer.vue`
- `src/utils/plugin-ui/pipe-executor.ts`
- `src/utils/plugin-ui/api-template-engine.ts`
- 单元测试：占位符解析 + 管道执行

### Phase F-3：XML 内置组件库（2 周）

- `src/components/plugin-ui/xml-components/` 全部 Vue 组件
- 布局组件（vbox/hbox/grid/card/tabs/dialog/divider/spacer）
- 基础组件（text/input/textarea/select/switch/slider/date-picker/button/icon/tag/badge）
- 高级组件（table/chart/form/list）
- 视觉调优（MD3 样式对齐）

### Phase F-4：HTML 沙箱 + Web Components + sys 桥接（2 周）

- `src/utils/plugin-ui/html-sandbox.ts`
- `src/utils/plugin-ui/sys-bridge.ts`
- `src/utils/plugin-ui/fetch-proxy.ts`
- `src/components/plugin-ui/HtmlSandbox.vue`
- `src/components/plugin-ui/web-components/` 全部 Web Components
- `register-all.ts`
- 集成测试

### Phase F-5：移动端 + 导航 + 联调（1 周）

- `src/components/plugin-ui/MobileFallback.vue`
- `src/components/plugin-ui/PluginPagePicker.vue`
- 移动端视口检测 + fallback 切换
- 与后端联调（Discovery → Schema → Asset 全链路）
- `mobile-only` / `desktop-only` 属性支持
- E2E 测试

---

**版本历史**

- **v1.0.0 (2026-06-19)** — 初版实现方案，对应设计文档 v3.1.0
