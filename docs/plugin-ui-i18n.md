# 插件 UI 国际化 (i18n) 指南

> 自 v3.1 起，插件 UI 系统支持插件自定义翻译 bundle。XML 轨和 HTML 轨都能引用本插件注册的 key，自动加 `pluginName` 命名空间前缀，与 WebUI 内置 messages 平级查找、互不冲突。

## 1. 总览

### 1.1 设计目标

- **零侵入**：插件作者无需导入 WebUI 内部 i18n 模块，无需在 manifest 声明 i18n 依赖。
- **懒加载**：bundle 随页面 `/schema` 接口一起返回，无独立请求；不打开页面不加载。
- **命名空间隔离**：插件 key 自动落入 `<pluginName>.<key>`，不会与 WebUI 或其他插件冲突。
- **统一回退链**：plugin locale → plugin DEFAULT_LOCALE → 静态 messages → DEFAULT_LOCALE → key 字面量。
- **双轨一致**：XML `{t('key')}` 与 HTML `sys.i18n.t('key')` 行为一致，都自动加前缀。

### 1.2 数据流

```
插件 on_plugin_loaded
    │
    │  await service.register_ui_page(..., i18n_path='i18n/i18n.json')
    ▼
后端 PluginUIService
    │  _resolve_plugin_root(plugin_name)  # 复用 HTML 轨的根目录解析
    │  PluginUIValidators.validate_i18n(metadata, plugin_root)
    │      ├─ 路径穿越校验（resolve_safe）
    │      ├─ 文件大小 ≤ 256 KB（MAX_I18N_FILE_SIZE_BYTES）
    │      └─ JSON 解析 + 顶层结构校验（dict[str, dict | null]）
    ▼
PluginUIManager.register(metadata, plugin_root, i18n_bundle)
    │  存入 RegisteredPage.i18n（内存态，进程重启清空）
    ▼
GET /webui/api/plugin-ui/schema/{plugin_name}/{page_id}?variant=desktop|mobile
    │  PageSchemaResponse.i18n = RegisteredPage.i18n
    ▼
前端 PluginUIView.loadPage
    │  registerPluginI18n(pluginName, pageId, schema.i18n)
    │  → 把 bundle 在每个 locale 下包一层 {pluginName: ...} 后深合并
    │  → 写入响应式 pluginMessages store
    ▼
渲染层
    │  XML 轨: {t('welcome')}        → expression-evaluator 的 t() 内置函数
    │                                  → resolver.tFn('welcome')  ← 由 PluginUIVarStore 提供
    │                                  → i18nT('demo_plugin.welcome')
    │  HTML 轨: sys.i18n.t('welcome') → sys-bridge 的 sysI18n.t
    │                                  → i18nT('demo_plugin.welcome')
    ▼
resolveMessage  →  pluginMessages[locale]  →  messages[locale]  →  DEFAULT_LOCALE  →  key 字面量
```

## 2. 后端：注册 i18n bundle

### 2.1 文件格式

JSON，单一文件包含所有 locale。结构与 WebUI 内置 `messages` 一致：

```json
{
  "zh-CN": {
    "title": "XML UI 演示",
    "welcome": "欢迎使用插件 UI 系统",
    "counter": {
      "title": "计数器",
      "increment": "+1"
    },
    "greeting": "你好，{name}"
  },
  "en-US": {
    "title": "XML UI Demo",
    "welcome": "Welcome to the Plugin UI System",
    "counter": {
      "title": "Counter",
      "increment": "+1"
    },
    "greeting": "Hello, {name}"
  }
}
```

**约定**：

| 项 | 规则 |
|---|---|
| 顶层键 | locale 名（`zh-CN` / `en-US`，与 `UISettings.language` 严格匹配） |
| locale 值 | 嵌套 dict（支持任意深度点路径）或 `null`（表示该 locale 无翻译，走 fallback） |
| 占位符 | `{name}` 语法，运行时由前端 `t()` 替换 |
| 文件大小 | ≤ 256 KB（`MAX_I18N_FILE_SIZE_BYTES`） |
| 路径 | 相对插件根目录，必须以 `.json` 结尾，禁含 `..` 跨目录 |

### 2.2 在 `register_ui_page` 中声明

```python
async def on_plugin_loaded(self) -> None:
    from src.app.plugin_system.api.service_api import get_service
    service = get_service("neo-mofox-webui:service:plugin_ui")

    await service.register_ui_page(
        plugin_name="my_plugin",
        page_id="dashboard",
        title="My Dashboard",  # 注意：title 不参与 i18n，列表展示用
        mode="xml",
        xml=_XML_CONTENT,
        i18n_path="i18n/i18n.json",  # ← 新增：相对插件根目录
    )
```

### 2.3 校验规则

`PluginUIValidators.validate_i18n(metadata, plugin_root)` 在注册时执行：

1. **路径格式**：`.json` 后缀（model 层 `_validate_i18n_path`）。
2. **路径穿越**：`resolve_safe(i18n_path, plugin_root)` 复用 HTML 轨的 `_validate_relative_path` + `is_relative_to` 检查。
3. **文件存在**：`resolve_safe` 自带 `FileNotFoundError` → `AssetMissingError`。
4. **大小校验**：超过 `MAX_I18N_FILE_SIZE_BYTES` (256 KB) 抛 `AssetSizeError`。
5. **JSON 解析**：`json.JSONDecodeError` → `ValueError`。
6. **结构校验**：顶层必须是 `dict`；每个 locale 键必须是字符串；每个 locale 值必须是 `dict` 或 `null`。

> **XML 模式 + i18n_path**：原本 XML 模式不读取本地资源，`plugin_root` 用 `Path.cwd()` 占位。引入 `i18n_path` 后，service 层会**强制**调用 `_resolve_plugin_root(plugin_name)` 拿到真实根目录，确保路径穿越校验有意义（见 `plugin_ui_service.py:154-167`）。

### 2.4 bundle 存储位置

- `RegisteredPage.i18n`（已解析的 dict）—— 内存态，进程重启清空，与现有 Registry 一致。
- `PageSchemaResponse.i18n`（HTTP 响应字段）—— 由 `manager.get_schema()` 注入，桌面/移动 variant 共用同一份 bundle。

## 3. 前端：使用翻译 key

### 3.1 XML 轨：占位符表达式中的 `t()` 内置函数

在 XML 文本节点或属性值中，用 `{t('key')}` 或 `{t('key', {'param': expr})}` 引用本插件注册的翻译。

```xml
<!-- 文本节点 -->
<sys-text variant="title">{t('welcome')}</sys-text>

<!-- 属性值 -->
<card title="{t('counter.title')}">
  <sys-button on-click="set: counter=0">{t('counter.reset')}</sys-button>
</card>

<!-- 带参数（{name} 占位符会被替换） -->
<sys-text>{t('greeting', {'name': username})}</sys-text>

<!-- 在管道指令中（notify 等） -->
<sys-button on-click="api: save | notify: {t('form.addSuccess')}, 'success'">
  {t('form.add')}
</sys-button>
```

**`t()` 函数签名**：

```ts
t(key: string, params?: Record<string, string>): string
```

- `key`：字符串字面量（单引号或双引号都支持）。**不需要**写 `pluginName.` 前缀，框架会自动加。
- `params`（可选）：对象字面量 `{'name': value}`，键必须是字符串字面量，值可以是任意表达式（变量、函数调用、嵌套对象等）。每个 `{paramKey}` 占位符会被 `params.paramKey` 的求值字符串替换。

**实现位置**：

| 文件 | 作用 |
|---|---|
| `frontend/src/utils/plugin-ui/expression-evaluator.ts` | `BUILTIN_FUNCTIONS` 白名单加入 `t`；`evaluateBuiltin('t', args, resolver)` 调用 `resolver.tFn(key, params)` |
| `frontend/src/utils/plugin-ui/plugin-ui-vars.ts` | `createPluginUIVarStore(pluginName)` 创建 `tFn` 闭包，自动把 key 拼成 `${pluginName}.${key}` 后转给全局 `i18nT()` |
| `frontend/src/utils/plugin-ui/xml/xml-renderer.ts` | `safeEvaluate` 调用时把 `store`（实现 `VariableResolver`）作为 resolver 传入 |
| `frontend/src/utils/plugin-ui/xml/pipe-executor.ts` | 管道指令中的占位符解析同样使用 `store`，复用同一套 `t()` 求值 |

### 3.2 HTML 轨：`sys.i18n.t`

HTML 轨通过 `sys` 桥接对象访问 i18n。`sys.i18n.t(key, params?)` 与 XML 的 `t()` 行为完全一致：自动加 `pluginName.` 前缀。

```html
<script>
  // 命中本插件 bundle 中的 greeting key
  const greeting = sys.i18n.t('greeting', { name: 'Alice' })
  document.querySelector('#greeting').textContent = greeting

  // 命中 WebUI 内置 key（无前缀注入，但需要知道完整路径）
  const homeTitle = sys.i18n.t('app.nav.home')  // 会查找 demo_plugin.app.nav.home，找不到回退到 app.nav.home
</script>
```

> 注意：HTML 轨的 `sys.i18n.t` 总是会自动加 `pluginName.` 前缀。如果想访问 WebUI 内置 key，框架会先在 `pluginMessages[locale]['demo_plugin.app.nav.home']` 查找（找不到），再回退到 `messages[locale]['app.nav.home']`（找到）—— 因此间接也能命中内置 key。

**实现位置**：`frontend/src/utils/plugin-ui/html/sys-bridge.ts:331-338`

```ts
const sysI18n = {
  t: (key, params) => t(`${pluginName}.${key}`, params),
}
```

### 3.3 WebUI 自身前端代码

WebUI 自己的 Vue 组件（不在插件上下文里）可以直接用 `useI18n()` 返回的 `t()`，传入完整 key：

```ts
import { useI18n, registerPluginI18n } from '@/utils/i18n'

const { t } = useI18n()
t('app.nav.home')             // 内置 key
t('demo_plugin.greeting', { name: 'Alice' })  // 插件 key（需带 pluginName 前缀）
```

> 一般情况下 WebUI 自身代码不需要访问插件 key。这里仅说明解析路径。

## 4. 命名空间与回退链

### 4.1 自动前缀

bundle 注册时，框架会在每个 locale 的内容外包一层 `{pluginName: bundle[locale]}`，深合并到全局 `pluginMessages[locale]`：

```ts
// 输入 bundle
{
  'zh-CN': { greeting: '你好', counter: { title: '计数器' } },
  'en-US': { greeting: 'Hello', counter: { title: 'Counter' } },
}

// 注册到 pluginMessages（pluginName='demo_plugin'）
{
  'zh-CN': {
    demo_plugin: { greeting: '你好', counter: { title: '计数器' } }
  },
  'en-US': {
    demo_plugin: { greeting: 'Hello', counter: { title: 'Counter' } }
  },
}
```

XML/HTML 调用 `t('greeting')` → 求值器拼成 `tFn('greeting')` → 全局 `t('demo_plugin.greeting')` → 命中 `pluginMessages['zh-CN'].demo_plugin.greeting` = `你好`。

### 4.2 回退链

`resolveMessage` 查询顺序（参见 `frontend/src/utils/i18n.ts:1856-1873`）：

```
pluginMessages[currentLocale]            ← 插件 bundle（含 pluginName 前缀）
  ↓ 未命中
messages[currentLocale]                  ← WebUI 内置静态 messages
  ↓ 未命中
pluginMessages[DEFAULT_LOCALE='zh-CN']   ← 插件 bundle 默认 locale
  ↓ 未命中
messages[DEFAULT_LOCALE]                 ← WebUI 默认 locale
  ↓ 未命中
返回 key 字面量
```

### 4.3 多页面同名 key 冲突

同一插件的多个页面各自注册 bundle 时，`<pluginName>.<key>` 命名空间共享：

- 不同 key → 自然不冲突。
- 同 key → 后注册覆盖先注册（`deepMerge` 行为：对象递归合并，叶子值后者覆盖前者）。

切页时 `PluginUIView.loadPage` 会先 `unregisterPluginI18n(prevPlugin, prevPage)` 再 `registerPluginI18n(newPlugin, newPage)`，避免上一页 key 残留污染当前页。

## 5. 占位符表达式语法扩展

为支持 `t('key', {'param': value})` 语法，对占位符表达式语言做了两处扩展（前后端一致）：

### 5.1 新增 `t` 内置函数

加入 `EXPRESSION_ALLOWED_HELPERS` 白名单（后端 lark）和 `BUILTIN_FUNCTIONS` 集合（前端 evaluator），允许在 `{...}` 占位符中调用 `t()`。

### 5.2 新增对象字面量

支持 `{'key': value, 'key2': value2}` 语法：

- 键必须是字符串字面量（单引号或双引号）—— 与 JSON 一致，避免 identifier-as-key 的歧义。
- 值可以是任意表达式（变量、函数调用、嵌套对象等）。
- 支持尾随逗号。
- 求值结果是一个普通 JS/TS 对象，可直接传给 `t()` 的第二参数。

### 5.3 单引号字符串字面量

后端 lark 语法原本只支持双引号字符串（`common.ESCAPED_STRING`）。考虑到 XML 属性常用双引号包裹、表达式内部需用单引号（如 `on-click="notify: '添加成功'"`），新增自定义 `STRING` 终结符，同时接受单/双引号。前端 evaluator 的 tokenizer 早已支持两种引号，本次保持一致。

### 5.4 语法示例

```xml
<!-- 简单 key -->
<sys-text>{t('welcome')}</sys-text>

<!-- 嵌套 key（点路径） -->
<sys-text>{t('counter.title')}</sys-text>

<!-- 带变量参数 -->
<sys-text>{t('greeting', {'name': username})}</sys-text>

<!-- 带字面量参数 -->
<sys-text>{t('greeting', {'name': 'Bob'})}</sys-text>

<!-- 带函数调用参数 -->
<sys-text>{t('dataList.count', {'count': str(len(items))})}</sys-text>

<!-- 多参数 -->
<sys-text>{t('welcome', {'name': username, 'count': str(counter)})}</sys-text>

<!-- 与其他表达式组合 -->
<sys-text>{t('counter.title')}: {counter}</sys-text>
<sys-text hidden="{counter &lt;= 5}">{t('conditional.exceeded', {'value': str(counter)})}</sys-text>
```

## 6. 完整示例

参见 `examples/demo_ui_plugin/`：

- `i18n/i18n.json` —— 双 locale bundle（zh-CN + en-US）
- `plugin.py` —— `register_ui_page(..., i18n_path='i18n/i18n.json')`，XML 全部硬编码中文改为 `{t('...')}` 形式

关键代码片段：

```python
# examples/demo_ui_plugin/plugin.py
await service.register_ui_page(
    plugin_name="demo_ui_plugin",
    page_id="dashboard",
    title="Demo 仪表板",
    mode="xml",
    xml=_DASHBOARD_XML,
    i18n_path="i18n/i18n.json",
)
```

```xml
<!-- _DASHBOARD_XML -->
<card title="{t('title')}">
  <sys-text variant="title">{t('welcome')}</sys-text>
  <sys-text variant="caption">{t('currentGreeting', {'greeting': greeting})}</sys-text>
  <sys-button on-click="api: addItem | notify: {t('form.addSuccess')}, 'success'">
    {t('form.add')}
  </sys-button>
</card>
```

切换 WebUI 语言（设置页 → 语言 → English）即可看到全部文本切换为 en-US bundle 的内容。

## 7. 生命周期与清理

| 事件 | 行为 |
|---|---|
| 插件加载（`on_plugin_loaded`） | 插件调 `register_ui_page(i18n_path=...)` → 后端校验 + 解析 + 缓存到 `RegisteredPage.i18n` |
| 用户打开插件页面 | 前端 `PluginUIView.loadPage` 拉取 schema → `registerPluginI18n(pluginName, pageId, schema.i18n)` |
| 用户切换页面 | `loadPage` 先 `unregisterPluginI18n(prevPlugin, prevPage)` 再注册新页 |
| 用户离开 `/plugin-ui` 路由 | `onBeforeUnmount` 调 `unregisterPluginI18n` |
| 后端 `unregister_ui_page` | 内存 Registry 删除条目；前端不主动感知，下次 `/list` 拉取时自然消失 |
| 进程重启 | Registry 全部清空（设计文档 §3.5 硬要求） |

> ** eventual consistency**：后端 `unregister_ui_page` 不会推送给前端。如果用户已打开页面、插件被卸载，前端仍会缓存 bundle 直到下次切页或离开路由。v1 接受此行为；后续可加 SSE/WebSocket 推送。

## 8. API 速查

### 8.1 后端

```python
# 注册时传 i18n_path
await service.register_ui_page(
    plugin_name=...,
    page_id=...,
    mode="xml" | "html",
    xml=... | assets=...,
    i18n_path="i18n/i18n.json",  # 可选，相对插件根目录
)
```

### 8.2 前端 XML

```xml
{t('key')}
{t('nested.key')}
{t('key', {'param': variableExpr})}
{t('key', {'param': 'literal'})}
```

### 8.3 前端 HTML

```js
sys.i18n.t('key')
sys.i18n.t('key', { name: 'Alice' })
```

### 8.4 前端 TypeScript（WebUI 自身）

```ts
import { useI18n, registerPluginI18n, unregisterPluginI18n } from '@/utils/i18n'

const { t, setLocale, locale } = useI18n()

// 通常由 PluginUIView 调用，业务代码不直接用
registerPluginI18n(pluginName, pageId, bundle)
unregisterPluginI18n(pluginName, pageId)
```

## 9. 限制与边界

| 项 | 当前限制 | 后续可扩展 |
|---|---|---|
| 文件大小 | 256 KB | 大 bundle 可拆 `/i18n/{plugin}/{page}` 独立端点按需拉取 |
| 文件格式 | JSON | YAML（需在 manifest 加 PyYAML 依赖） |
| bundle 结构 | 单文件多 locale | 多文件（`i18n_dir`） |
| 命名空间 | 强制 `pluginName.` 前缀 | 可选自定义前缀 |
| 卸载推送 | 前端不感知后端卸载 | SSE/WebSocket 推送 |
| 占位符参数 | 对象字面量仅支持字符串键 | 可扩展计算属性（`{[expr]: value}`） |

## 10. 相关文件索引

| 层 | 文件 | 改动摘要 |
|---|---|---|
| 后端类型 | `Plugin/utils/plugin_ui/plugin_ui_types.py` | `PageRegistration.i18n_path`、`RegisteredPage.i18n`、`PageSchemaResponse.i18n` |
| 后端常量 | `Plugin/utils/plugin_ui/plugin_ui_constants.py` | `MAX_I18N_FILE_SIZE_BYTES`；`EXPRESSION_ALLOWED_HELPERS` 加 `t` |
| 后端校验 | `Plugin/utils/plugin_ui/plugin_ui_validators.py` | `PluginUIValidators.validate_i18n`；lark 语法加 `object_literal` + 单引号 `STRING` |
| 后端服务 | `Plugin/components/services/plugin_ui_service.py` | `register_ui_page` 加 `i18n_path` 参数；XML 模式也调 `_resolve_plugin_root` |
| 后端管理 | `Plugin/managers/plugin_ui_manager.py` | `register()` 加 `i18n_bundle` 参数；`get_schema()` 注入 `i18n` |
| 前端 i18n 核心 | `frontend/src/utils/i18n.ts` | `pluginBundles` Map + `pluginMessages` ref；`registerPluginI18n` / `unregisterPluginI18n` 导出；`resolveMessage` 合并查询 |
| 前端类型 | `frontend/src/api/types/plugin-ui.ts` | `PageSchemaResponse.i18n` 字段 |
| 前端变量池 | `frontend/src/utils/plugin-ui/plugin-ui-vars.ts` | `PluginUIVarStore` 加 `pluginName` + `tFn` 字段 |
| 前端求值器 | `frontend/src/utils/plugin-ui/expression-evaluator.ts` | `t` 加入 `BUILTIN_FUNCTIONS`；`ObjectLiteral` AST 节点；`{` `}` `:` token |
| 前端 sys 桥 | `frontend/src/utils/plugin-ui/html/sys-bridge.ts` | `sysI18n.t` 自动加 `pluginName` 前缀 |
| 前端视图 | `frontend/src/views/PluginUIView.vue` | `loadPage` 调 `registerPluginI18n`；卸载/切页调 `unregisterPluginI18n` |
| 示例 | `examples/demo_ui_plugin/i18n/i18n.json` | 双 locale bundle |
| 示例 | `examples/demo_ui_plugin/plugin.py` | `i18n_path='i18n/i18n.json'`；XML 改用 `{t(...)}` |
