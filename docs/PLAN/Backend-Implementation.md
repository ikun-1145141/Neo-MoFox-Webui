# Neo-MoFox WebUI 插件前端扩展系统 — 后端实现方案

**关联设计文档**: [`Neo-MoFox-WebUI-Plugin-Extension-Design.md`](../Neo-MoFox-WebUI-Plugin-Extension-Design.md:1)
**目标版本**: v3.1.0
**适用项目**: [`Neo-MoFox-Webui/Plugin/`](../../Plugin:1)（neo-mofox-webui 后端插件）
**作者**: MoFox Team
**状态**: 实现方案稿

---

## 0. 文档目的与读者

本文档面向 **WebUI 后端实现者**，给出"如何把设计文档里的能力在 [`Neo-MoFox-Webui/Plugin/`](../../Plugin:1) 这个 Neo-MoFox 插件里落地"的工程方案。读者预设：

- 已读 [`Neo-MoFox-WebUI-Plugin-Extension-Design.md`](../Neo-MoFox-WebUI-Plugin-Extension-Design.md:1) 全文
- 熟悉 Neo-MoFox 插件系统（`BasePlugin` / `BaseRouter` / `BaseService` / Service API）
- 熟悉本仓库分层规范（[`.kilocode/rules/设计文档.md`](../../../.kilocode/rules/设计文档.md:1)）：组件层 → 转发层（Manager）→ 存储层 → 工具层

> 文档只描述**实现策略与边界约束**，不直接贴可运行源码。代码量大的部分（XML 校验器、资源服务、Service 接口）以接口签名 + Pydantic 模型 + 关键流程图描述。

---

## 📋 目录

1. [整体落地策略](#1-整体落地策略)
2. [插件目录结构变更](#2-插件目录结构变更)
3. [数据模型（Pydantic）](#3-数据模型pydantic)
4. [Registry 转发层（PluginUIManager）](#4-registry-转发层pluginuimanager)
5. [对外 Service 接口（PluginUIService）](#5-对外-service-接口pluginuiservice)
6. [Discovery / Schema / Asset 三类 Router](#6-discovery--schema--asset-三类-router)
7. [HTML 静态资源服务与路径穿越防御](#7-html-静态资源服务与路径穿越防御)
8. [插件身份注入与请求拦截契约](#8-插件身份注入与请求拦截契约)
9. [校验器与白名单（XML/HTML）](#9-校验器与白名单xmlhtml)
10. [生命周期与"零感知卸载"实现](#10-生命周期与零感知卸载实现)
11. [配置项与启动顺序](#11-配置项与启动顺序)
12. [里程碑（Phase 划分）](#12-里程碑phase-划分)

---

## 1. 整体落地策略

### 1.1 一句话总结

在现有 [`Neo-MoFox-Webui/Plugin/`](../../Plugin:1) 内**新增一个"插件 UI 扩展子系统"**，由如下五块拼成：

| 模块 | 作用 | 落点 |
|---|---|---|
| `PluginUIService` | 暴露给其他 Neo-MoFox 插件的 Service 接口 | `Plugin/components/services/plugin_ui_service.py` |
| `PluginUIManager` | 注册表 + 校验 + 路径生成（Registry 内核） | `Plugin/managers/plugin_ui_manager.py` |
| `PluginUIRegistry` | 注册元数据的内存态登记（不持久化） | `PluginUIManager` 内部类 |
| `PluginUIDiscoveryRouter` / `PluginUISchemaRouter` / `PluginUIAssetRouter` | 给前端用的三个 HTTP Router | `Plugin/components/router/plugin_ui_*.py` |
| `plugin_ui_types.py` | Pydantic 数据模型集合 | `Plugin/utils/plugin_ui_types.py` |

> **不需要碰** [`storage/base.py`](../../Plugin/storage/base.py:1)：UI 注册表是**内存态**（设计第 3.5 节明文要求），WebUI 重启即清空。

### 1.2 与设计文档的对应关系

| 设计文档章节 | 对应实现模块 |
|---|---|
| §3 注册接口语义 | [`PluginUIService`](#5-对外-service-接口pluginuiservice) |
| §3.5 生命周期 | [`PluginUIManager`](#4-registry-转发层pluginuimanager) + 不订阅任何 plugin lifecycle |
| §4 XML 轨 schema | §9.1 XML XSD + 标签白名单 |
| §5 HTML 轨 assets | §6 [`AssetRouter`](#6-discovery--schema--asset-三类-router) + §7 路径穿越防御 |
| §7 API 模板 | 后端不实现执行逻辑，仅在 schema 中**透传** |
| §8 移动端三件套 | `PageRegistration.mobile` 子结构（§3） |
| §9.1 注册侧校验 | §9 校验器 |
| §9.3 插件身份边界 | §8 身份注入与拦截契约 |
| §9.4 卸载流程 | §10 零感知实现 |

### 1.3 强约束清单（实现时必须遵守）

1. **不订阅任何插件加载/卸载事件**——这是设计文档 §9.4 的"零感知"硬要求，实现侧不能"自作聪明"挂 EventHandler。
2. **不做后端插件间身份校验**——`plugin_name` 由调用方自行声明，不做 cross-check（同进程互信前提，见 §7.1.3）。
3. **静态资源只读 GET**——禁用 POST/PUT/DELETE 等任何写操作。
4. **路径穿越防御**——所有相对路径（相对于 CWD）resolve 后必须仍在 CWD 目录树内。
5. **Registry 不持久化**——内存态 dict，进程重启即丢失（这是兜底机制）。
6. **接口全部 Pydantic**——返回值与请求体不允许手写 `dict`（项目规范）。

---

## 2. 插件目录结构变更

在现有 [`Plugin/`](../../Plugin:1) 下增加以下文件（**不动**现有 router/manager）：

```
Plugin/
├── components/
│   ├── router/
|       ├── plugin_ui
│   │   ├── plugin_ui_discovery_router.py   # 新增：GET /webui/api/plugin-ui/list, /detail
│   │   ├── plugin_ui_schema_router.py      # 新增：GET /webui/api/plugin-ui/schema
│   │   └── plugin_ui_asset_router.py       # 新增：GET /webui/static/plugin-ui/{...}
│   └── services/                           # 新增子目录
│       ├── __init__.py
│       └── plugin_ui_service.py            # 新增：BaseService 实现
├── managers/
│   └── plugin_ui_manager.py                # 新增：Registry 内核 + 校验入口
└── utils/
├───  plugin_ui
    ├── plugin_ui_types.py                  # 新增：Pydantic 模型集合
    ├── plugin_ui_validators.py             # 新增：XML/HTML 校验器
    └── plugin_ui_paths.py                  # 新增：插件目录定位 + 路径穿越防御
```

[`Plugin/plugin.py`](../../Plugin/plugin.py:1) 主插件入口的 `get_components()` 需追加新增的三个 Router 与一个 Service：

```python
# Plugin/plugin.py（仅展示新增 import 与组件追加，原有项保留）
from .components.router.plugin_ui_discovery_router import PluginUIDiscoveryRouter
from .components.router.plugin_ui_schema_router import PluginUISchemaRouter
from .components.router.plugin_ui_asset_router import PluginUIAssetRouter
from .components.services.plugin_ui_service import PluginUIService

def get_components(self) -> list[type]:
    return [
        # ... 原有 13 个组件保留 ...
        PluginUIService,
        PluginUIDiscoveryRouter,
        PluginUISchemaRouter,
        PluginUIAssetRouter,
    ]
```

> 当前 [`components/`](../../Plugin/components:1) 没有 `services/` 子目录，需要新建（参照 Neo-MoFox 主仓库其他插件用法）。

---

## 3. 数据模型（Pydantic）

全部位于 [`Plugin/utils/plugin_ui_types.py`](../../Plugin/utils/plugin_ui_types.py:1)。这些模型是**唯一权威 schema**：Service 入参、Router 返回、内部 Registry 存的对象都用同一套。

### 3.1 PageMode 枚举

```python
from enum import Enum

class PageMode(str, Enum):
    XML = "xml"
    HTML = "html"
```

### 3.2 HTMLAssets

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `entry_html` | `str` | ✅ | 相对插件根目录的 HTML 入口路径 |
| `styles` | `list[str]` | ❌ | CSS 文件相对路径，按数组顺序加载 |
| `scripts` | `list[str]` | ❌ | JS 文件相对路径，按数组顺序加载 |
| `assets_dir` | `str \| None` | ❌ | 静态资源根目录；为空时不暴露任何静态资源 |

**字段级 validator**：
- 所有路径不得以 `/`、`\` 开头（必须相对路径）
- 不得包含 `..` 段
- 扩展名白名单：`entry_html` 必须 `.html`；`styles[*]` 必须 `.css`；`scripts[*]` 必须 `.js`

### 3.3 MobileVariant

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `mode` | `PageMode` | ✅ | 移动版的 mode（可与桌面不同） |
| `xml` | `str \| None` | 条件 | 当 mode=xml 时必填 |
| `assets` | `HTMLAssets \| None` | 条件 | 当 mode=html 时必填 |

### 3.4 PageRegistration（核心入参）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `plugin_name` | `str` | ✅ | 必须与调用方插件身份一致（§8 校验） |
| `page_id` | `str` | ✅ | 同插件内唯一；正则 `^[a-z][a-z0-9_-]{0,63}$` |
| `title` | `str` | ✅ | 显示名（最长 64） |
| `icon` | `str \| None` | ❌ | Material Symbols 图标名 |
| `description` | `str \| None` | ❌ | 简介（最长 256） |
| `order` | `int` | ❌ | 排序权重，默认 100 |
| `mode` | `PageMode` | ✅ | 桌面版 mode（page 维度二选一） |
| `xml` | `str \| None` | 条件 | 当 mode=xml 时必填，整段 XML 字符串 |
| `assets` | `HTMLAssets \| None` | 条件 | 当 mode=html 时必填 |
| `mobile` | `MobileVariant \| None` | ❌ | 移动端三件套，可空（空则走 fallback） |

**模型级 validator**（@model_validator）：
- `mode == XML` 时 `xml` 非空、`assets` 必须 None；反之亦然
- `mobile.mode == XML` 时 `mobile.xml` 非空、`mobile.assets` 必须 None；反之亦然
- 不允许在桌面版 `xml` 和 `assets` 同时存在（page 维度二选一约束）

### 3.5 RegisteredPage（Registry 内部存储）

`PageRegistration` 是入参；Registry 真正持有的是它的"加工版"：

| 字段 | 类型 | 来源 | 说明 |
|---|---|---|---|
| 全部 PageRegistration 字段 | — | 入参 | 透传 |
| `route_path` | `str` | 系统生成 | `/plugins/{plugin_name}/{page_id}` |
| `desktop_assets_urls` | `dict[str, list[str]]` | 系统生成 | HTML 模式下 entry_html / styles / scripts 的绝对 URL |
| `mobile_assets_urls` | `dict[str, list[str]] \| None` | 系统生成 | 移动 HTML 模式下同上 |
| `registered_at` | `datetime` | 系统填 | 注册/更新时间戳 |
| `plugin_root` | `Path` | 系统填 | 插件根目录绝对路径，校验时用 |

### 3.6 Discovery 用的对外简化模型

| 模型 | 字段 | 备注 |
|---|---|---|
| `PageSummary` | `plugin_name`、`page_id`、`title`、`icon`、`description`、`order`、`mode`、`route_path`、`has_mobile` | 列表用，不含 schema |
| `PageDetail` | `PageSummary` 全部 + `mobile_mode` + `desktop_assets_urls` + `mobile_assets_urls` | 详情用，仍不含 XML 内容 |
| `PageSchemaResponse` | `mode`、`xml \| None`、`assets_urls \| None` | 渲染时按 variant 拉取 |

> **为什么 Schema 单独拉**：避免列表 API 把所有 page 的全部 XML/JS 路径在首屏就发给前端，控制网络体积；同时让 `XML / HTML` 混合分发更顺：列表只展示元信息，进页时再请求 schema。

---

## 4. Registry 转发层（PluginUIManager）

落点：[`Plugin/managers/plugin_ui_manager.py`](../../Plugin/managers/plugin_ui_manager.py:1)。

### 4.1 内部数据结构

```python
class PluginUIManager:
    """插件 UI 注册表。内存态，进程重启清空。"""

    def __init__(self) -> None:
        # key: (plugin_name, page_id) -> RegisteredPage
        self._registry: dict[tuple[str, str], RegisteredPage] = {}
        # 反向索引：plugin_name -> set[page_id]
        self._by_plugin: dict[str, set[str]] = {}
        # 写操作锁
        self._lock = asyncio.Lock()
```

### 4.2 公开方法

| 方法 | 输入 | 输出 | 行为 |
|---|---|---|---|
| `register(reg: PageRegistration, plugin_root: Path) -> RegisteredPage` | 注册元数据 + 校验过的插件根目录 | 加工后的 RegisteredPage | 校验 → 路径解析 → 写入 dict |
| `unregister(plugin_name: str, page_id: str) -> bool` | — | 是否真的存在并被移除 | 删除 dict 与反向索引项 |
| `unregister_all(plugin_name: str) -> int` | — | 被清掉的 page 数 | 批量删除该插件所有 page |
| `list_pages(filter_plugin: str \| None = None) -> list[PageSummary]` | 可选过滤插件名 | 按 order 升序排序的列表 | 仅元信息 |
| `get_detail(plugin_name: str, page_id: str) -> PageDetail \| None` | — | 详情或 None | — |
| `get_schema(plugin_name: str, page_id: str, variant: Literal["desktop","mobile"]) -> PageSchemaResponse \| None` | — | 拉取桌面 / 移动 schema | mobile 不存在时返回 None；上层据此决定走 fallback |

### 4.3 路径生成（系统自管理）

```python
def _build_route_path(plugin_name: str, page_id: str) -> str:
    return f"/plugins/{plugin_name}/{page_id}"
```

> 设计文档明文要求：插件不传 path/route，系统按上述规则生成；不允许覆盖。

### 4.4 资源 URL 生成

HTML 三件套提交后，Manager 在 `register` 阶段把每个相对路径转成系统暴露的绝对 URL：

| 资源 | URL 规则 |
|---|---|
| `entry_html` | `/webui/static/plugin-ui/{plugin_name}/{page_id}/desktop/entry` |
| `styles[i]` | `/webui/static/plugin-ui/{plugin_name}/{page_id}/desktop/style/{i}` |
| `scripts[i]` | `/webui/static/plugin-ui/{plugin_name}/{page_id}/desktop/script/{i}` |
| `assets_dir/*` | `/webui/static/plugin-ui/{plugin_name}/{page_id}/desktop/asset/{rel}` |
| 移动版镜像 | 把 `desktop` 改成 `mobile` |

> URL 不直接暴露插件本地文件系统路径——而是走 `AssetRouter`（§7）以索引形式定位，避免泄露插件作者的目录布局。

### 4.5 单例获取

参照 [`managers/__init__.py`](../../Plugin/managers/__init__.py:1) 既有写法（`get_dashboard_manager / get_log_manager` 等），暴露 `get_plugin_ui_manager()` 全局单例工厂。

---

## 5. 对外 Service 接口（PluginUIService）

落点：[`Plugin/components/services/plugin_ui_service.py`](../../Plugin/components/services/plugin_ui_service.py:1)。

`BaseService` 子类，签名固定为 `neo-mofox-webui:service:plugin_ui`。其他 Neo-MoFox 插件通过 `get_service("neo-mofox-webui:service:plugin_ui")` 拿到实例并调用。

### 5.1 类骨架

```python
class PluginUIService(BaseService):
    service_name: str = "plugin_ui"
    service_description: str = "Neo-MoFox WebUI 插件页面注册服务"
    version: str = "1.0.0"

    def __init__(self, plugin: BasePlugin) -> None:
        super().__init__(plugin)
        self._manager = get_plugin_ui_manager()
```

### 5.2 公开方法（与设计文档 §3.4 对齐）

| 方法 | 输入 | 行为 | 失败模式 |
|---|---|---|---|
| `async register_ui_page(metadata: PageRegistration) -> RegisteredPage` | 注册元数据 | 见 §5.3 | `ValueError` / `FileNotFoundError` / `PermissionError` |
| `async unregister_ui_page(plugin_name: str, page_id: str) -> bool` | — | 显式卸载 | — |
| `async unregister_plugin_pages(plugin_name: str) -> int` | — | 批量卸载该插件所有 page | — |
| `async list_pages(*, plugin_filter: str \| None = None) -> list[PageSummary]` | 可选过滤 | Discovery 用 | — |
| `async get_page_schema(plugin_name: str, page_id: str, variant: str = "desktop") -> PageSchemaResponse \| None` | — | 拉 schema | `ValueError` variant 非法 |

> 注意：不再有 `_calling_plugin` 参数。插件 plugin_name 由调用方自行在 metadata 中声明，不做身份交叉校验（见 §7.1.3 的设计决定）。

### 5.3 注册流程（核心）

```
register_ui_page(metadata)
  │
  ├─ 1. 调用 PluginUIValidators.validate(metadata)
  │     - XML 模式：XSD 校验 + 标签白名单 + 占位符表达式校验
  │     - HTML 模式：路径穿越校验（相对于 CWD）+ 文件存在性 + 扩展名白名单
  │     - 移动 variant：同上
  │
  ├─ 2. PluginUIManager.register(metadata)
  │     - 生成 route_path
  │     - 把所有相对路径转成 AssetRouter URL
  │     - 写入内存 Registry（同 key 视为更新）
  │
  └─ 3. 返回 RegisteredPage
```

### 5.4 卸载流程

`unregister_*` 系列不做身份校验——任何插件都可以卸载任何 page。这与"不校验 plugin_name"的设计一致：同进程内互信，防误不防恶。

### 5.5 错误处理（与项目 BaseResponse 协议结合）

Service 抛出的 `ValueError / PermissionError / FileNotFoundError` 由调用方（其他插件）的代码自己处理；本 Service 不直接面向 HTTP，因此不返回 `BaseResponse`。但当 [`PluginUISchemaRouter`](#6-discovery--schema--asset-三类-router) 等 Router 调它时，Router 会把异常翻译为 `BaseResponse.error(code, msg)`。

---

## 6. Discovery / Schema / Asset 三类 Router

### 6.1 路径规划（与现有 router 风格一致）

参考 [`plugin_router.py`](../../Plugin/components/router/plugin_router.py:38) 的 `custom_route_path = "/webui/api/plugin"` 写法，新 Router 路径如下：

| Router | `custom_route_path` | 说明 |
|---|---|---|
| `PluginUIDiscoveryRouter` | `/webui/api/plugin-ui` | 列表与详情 |
| `PluginUISchemaRouter` | `/webui/api/plugin-ui` | 拉取 XML / assets URL bundle（同前缀，不同子路径） |
| `PluginUIAssetRouter` | `/webui/static/plugin-ui` | 静态资源服务（不带 /api） |

> Discovery 与 Schema 共享前缀，可以合并为单 Router；分两个文件主要为了模块边界清晰、便于审计与替换。

### 6.2 PluginUIDiscoveryRouter

| 端点 | 方法 | 鉴权 | 返回 |
|---|---|---|---|
| `/list` | GET | `VerifiedDep` | `BaseResponse[list[PageSummary]]` |
| `/list/{plugin_name}` | GET | `VerifiedDep` | `BaseResponse[list[PageSummary]]`（按插件过滤） |
| `/detail/{plugin_name}/{page_id}` | GET | `VerifiedDep` | `BaseResponse[PageDetail]` |

行为：
- `/list` 内部调 `PluginUIService.list_pages()`，按 `order` 升序排序
- 找不到 detail 时返回 `BaseResponse.error(code=404, message=...)`，HTTP 状态仍 200（与项目 BaseResponse 约定一致）

### 6.3 PluginUISchemaRouter

| 端点 | 方法 | 鉴权 | 查询参数 | 返回 |
|---|---|---|---|---|
| `/schema/{plugin_name}/{page_id}` | GET | `VerifiedDep` | `variant=desktop\|mobile`，默认 desktop | `BaseResponse[PageSchemaResponse]` |

行为：
- variant=mobile 但插件未提交 `mobile` 字段时，返回 `BaseResponse.error(code=204, message="no_mobile_variant")`，前端据此走 fallback 横向滚动模式
- 返回的 `PageSchemaResponse` 在 HTML 模式下只含 `assets_urls`，不含文件原文（前端拿 URL 自行 fetch CSS/JS）

### 6.4 PluginUIAssetRouter

设计要点见 §7，路径形式：

| 路径 | 内容 |
|---|---|
| `/{plugin_name}/{page_id}/desktop/entry` | 桌面 entry HTML |
| `/{plugin_name}/{page_id}/desktop/style/{i}` | 桌面 CSS（按 styles 索引） |
| `/{plugin_name}/{page_id}/desktop/script/{i}` | 桌面 JS（按 scripts 索引） |
| `/{plugin_name}/{page_id}/desktop/asset/{rel:path}` | 桌面 assets_dir 下任意文件（GET） |
| `/{plugin_name}/{page_id}/mobile/...` | 移动版镜像 |

- 仅 `GET`；其他方法返回 405
- 返回 `FileResponse`，根据扩展名设置 `Content-Type` 与 `Cache-Control: max-age=300`（小幅缓存，避免首屏炸网）
- 文件不存在 → 404；路径穿越检测失败 → 403

### 6.5 鉴权策略

- Discovery / Schema 用现有 [`VerifiedDep`](../../../Neo-MoFox/src/core/utils/security.py:1)（与现有 `plugin_router.py` 保持一致），对应"已登录用户"
- Asset 默认也加 `VerifiedDep`，避免未登录用户直接刷出插件 JS/CSS（虽然这些资源体并非敏感数据，但一致性优先）

---

## 7. HTML 静态资源服务与路径穿越防御

### 7.1 插件根目录定位与相对路径基准

落点：[`Plugin/utils/plugin_ui_paths.py`](../../Plugin/utils/plugin_ui_paths.py:1)。

#### 7.1.1 相对路径基准：主程序根目录（CWD）

> **`HTMLAssets` 中的 `entry_html / styles / scripts / assets_dir` 的相对路径，以 Neo-MoFox 主程序的工作目录（CWD）为基准。**

与 `PluginManager._plugin_paths` 体系一致——那里存的也是相对于 CWD 的路径（如 `plugins/my_plugin`）。

解析流程：
```
插件提交: entry_html = "plugins/my_plugin/ui/index.html"
  → Path("plugins/my_plugin/ui/index.html").resolve()
  → /opt/mofox/plugins/my_plugin/ui/index.html
  → 校验 is_file() ✓
  → 返回绝对路径
```

#### 7.1.2 路径穿越防御

路径穿越防御仍然保留——但 jail 不是"该插件的目录"，而是确保路径不跑到系统敏感位置：

```python
def resolve_safe(rel_path: str) -> Path:
    """安全解析资源路径（相对于 CWD）。"""
    candidate = Path(rel_path).resolve()
    cwd = Path.cwd().resolve()

    # 至少要在 CWD 或其子目录内（不能跳出主程序目录树）
    if not candidate.is_relative_to(cwd):
        raise PermissionError(f"path traversal blocked: {rel_path}")
    if not candidate.is_file():
        raise FileNotFoundError(f"asset not found: {rel_path}")
    return candidate
```

> 更严格的做法（可选）是限制在 `plugins/` 目录树内，但基础版只要不跳出 CWD 就够了。

#### 7.1.3 关于 `plugin_name` 身份校验：不做

> **设计决定：不校验 `_calling_plugin` 与 `metadata.plugin_name` 的一致性。插件爱起什么名字起什么名字。**

理由：
- 同进程 Python 代码层面无法真正阻止调用方传任意字符串
- 一个插件注册的 page 名字叫什么，本质上只影响它自己（Registry key 是 `(plugin_name, page_id)` 组合唯一）
- 如果 A 插件非要用 B 的名字注册 page，那只是覆盖了 B 的条目——这是它自找的
- 恶意插件已经在主进程里了，防不了也没必要在这层防

**因此**：
- `PluginUIService.register_ui_page` 的签名简化为 `register_ui_page(metadata: PageRegistration)`，去掉 `_calling_plugin` 参数
- 不做 `metadata.plugin_name` 与调用方身份的 cross-check
- 仅保留路径穿越防御（§7.1.2）和结构校验（§9）

### 7.2 路径穿越防御（与 §7.1.2 一致）

§7.1.2 已给出 `resolve_safe(rel_path)` 的实现。`AssetRouter` 运行时读取文件时也走同一个函数——注册时校验一次，运行时再校验一次（双保险，因为注册后文件系统可能被修改）。

### 7.3 资源 URL → 文件路径的映射

`AssetRouter` 处理 GET 请求时：

| URL 段 | 解析 |
|---|---|
| `{plugin_name}/{page_id}` | 查 Registry 拿到 `RegisteredPage` |
| `desktop/mobile` | 选择对应 variant（mobile 缺失返回 404） |
| `entry` / `style/{i}` / `script/{i}` | 按 variant 内 list 索引取相对路径 |
| `asset/{rel:path}` | 在 `assets_dir` 内按 `rel` 解析（必须 `assets_dir` 已声明） |

随后调用 `resolve_safe(plugin_root, 上一步得到的 rel)` 拿到磁盘绝对路径，最后 `FileResponse(path)`。

### 7.4 资源大小与扩展名再校验

虽然注册时已校验扩展名，运行时仍做最后一道防御：
- 单文件 ≤ 5 MB（默认上限，写在 [`§11 配置项`](#11-配置项与启动顺序)）
- 扩展名白名单：`.html .css .js .png .jpg .jpeg .gif .webp .svg .woff .woff2 .ttf .otf .ico`
- 不在白名单 → 返回 403，并记 warn 日志（用于审计）

---

## 8. 插件身份注入与请求拦截契约

### 8.1 后端契约：`X-Plugin-Name` 由后端确认

设计文档 §9.3 与 §9.5 涉及 `X-Plugin-Name` 的前后端边界。本插件的实际职责是：

1. **Schema 下发时**：`PageSchemaResponse` 中携带 `plugin_name` 字段，前端用它作为后续业务请求 header 的值。
2. **前端请求拦截**：前端 fetch 代理自动注入 `X-Plugin-Name`（来自当前渲染 page 的注册元数据），这样后端业务 Router 可以据此做审计。
3. **后端业务 Router 侧的校验**：不在本插件范围内——那属于具体业务插件自己的职责。

> **注册时的 `plugin_name`**：如 §7.1.3 所述，不做身份校验。插件自行声明，爱叫什么叫什么。

### 8.2 前端 `X-Plugin-Name` 的可信度

前端 fetch 代理注入的 `X-Plugin-Name` 来自当前页面的 `PageSchemaResponse.plugin_name`（后端下发的），不是用户可编辑的输入。但要注意：

- 这个值的"可信"边界是：**后端曾经注册过这个名字的 page**
- 并不代表"当前请求真的来自这个插件的合法业务逻辑"——因为用户可以手动 curl 带任意 header
- 所以 `X-Plugin-Name` 的用途是**审计 / 限速 / 日志追踪**，而不是安全鉴权

---

## 9. 校验器与白名单（XML/HTML）

落点：[`Plugin/utils/plugin_ui_validators.py`](../../Plugin/utils/plugin_ui_validators.py:1)。

### 9.1 XML 校验

实现按"两层校验"：

#### 第一层：XSD schema 校验

- XSD 文件位置：`Plugin/utils/schemas/plugin_ui_v3_1.xsd`（新增）
- 用 `lxml.etree.XMLSchema` 加载，文档结构必须符合：
  - 根元素 `<page>`
  - 子元素 `<metadata>`、`<definitions>`（可选）、`<layout>`
  - layout 下所有子元素必须出现在标签白名单里

#### 第二层：标签 / 属性白名单

XSD 之上做更严的检查：

| 类别 | 白名单 |
|---|---|
| 布局标签 | `vbox`、`hbox`、`grid`、`card`、`tabs`、`tab`、`dialog`、`divider`、`spacer` |
| 基础组件 | `sys-text`、`sys-input`、`sys-textarea`、`sys-select`、`sys-switch`、`sys-slider`、`sys-date-picker`、`sys-button`、`sys-icon-button`、`sys-tag`、`sys-badge`、`sys-icon` |
| 高级组件 | `sys-table`（含子元素 `column / map / format / progress / actions`）、`sys-chart`、`sys-form`、`sys-list` |
| 定义节 | `var`、`api`、`template` |

**禁止的标签**：`<plugin-page-picker>` / `<sys-include>` / `<sys-bind>` / `<sys-toast-anchor>` / 任何 `<script>` / `<style>` / `<iframe>` / `<object>` / `<embed>`。

**属性级**：
- 拒绝任何以 `on` 开头的原生 DOM 事件属性（`onclick / onload / onerror / ...`）——只允许 `on-click`、`on-change` 等设计文档定义的"管道指令属性"
- `class` 与 `style` 透传，但 `style` 走简单白名单过滤（剔除 `expression()`、`url(javascript:...)` 等）
- 占位符字符串 `{...}` 走 §9.3 表达式校验

#### 第三层：占位符表达式校验

`{...}` 内允许的语法（与设计 §2.2 完全对齐）：

| 允许 | 说明 |
|---|---|
| 标识符 / 点路径 | `user.name`、`form.username` |
| 取反前缀 `!` | `{!form_valid}` |
| 内置 helper 函数 | 仅 `empty`、`len`、`keys`、`values` 与文档列出的格式化函数 |
| 简单比较与逻辑 | `>` `<` `>=` `<=` `==` `!=` `&&` `||` `!` |
| 字面量 | 数字、字符串（单/双引号）、true、false、null |

**禁止**：任意函数调用（除内置 helper）、属性赋值、链式 `()`、`new`、`function`、`=>`。

实现建议：用 `lark` 或 `pyparsing` 写一个小型语法解析器，遇到非白名单 token 立即抛错。

### 9.2 HTML 校验

HTML 模式的 entry / styles / scripts 内容**不做 XSD 校验**——HTML 轨设计上就允许自由写。校验集中在：

| 校验项 | 说明 |
|---|---|
| 路径合法 | §3.2 + §7.2 |
| 文件存在 | `resolve_safe` 时顺带 `is_file` |
| 文件大小 | ≤ 5 MB（可配置，见 §11） |
| 扩展名白名单 | §3.2 字段级 + §7.4 运行时再校验 |
| 不允许 `entry_html` 内含 `<iframe>` / `<object>` / `<embed>` | 用 `BeautifulSoup` 简单扫描；命中拒绝注册 |

### 9.3 校验失败的统一异常

`PluginUIValidators.validate(metadata, plugin_root)` 抛出的统一异常：

| 异常 | 含义 |
|---|---|
| `XMLValidationError` | XSD / 白名单 / 占位符语法错 |
| `AssetPathError` | 路径不合法 / 穿越 |
| `AssetMissingError` | 文件不存在 |
| `AssetSizeError` | 文件超大 |

Router 层再统一翻译为 `BaseResponse.error(code, message)`。

---

## 10. 生命周期与"零感知卸载"实现

### 10.1 不订阅插件 lifecycle 事件

设计 §9.4 的"零感知"要求落到代码层就是一句话：

> **不要在 `Plugin/components/handlers/` 里加任何 `BaseEventHandler` 去订阅 `on_plugin_unloaded` / `on_plugin_disabled` 之类事件。**

### 10.2 WebUI 主插件自身的卸载

[`Plugin/plugin.py`](../../Plugin/plugin.py:89) 的 `on_plugin_unloaded()` 中：

```python
async def on_plugin_unloaded(self) -> None:
    logger.info("WebUI 插件即将卸载")
    # 不做：get_plugin_ui_manager().clear_all()
    # Registry 内存态生死跟进程走，进程退出天然清空
```

### 10.3 显式 unregister 的幂等性

`PluginUIManager.unregister` 应该是幂等的：
- key 不存在时返回 `False`，**不抛异常**
- 调用方根据返回值判断是否真的清理了一条，但不应因返回 False 而 panic

---

## 11. 常量与启动顺序

### 11.1 硬编码常量（不放进用户设置）

这些值**不暴露到 `data/json_storage/WebUI_data/` 的设置中**——它们是安全 / 运行时边界，用户没有理由去改，放成代码常量即可。

落点：`Plugin/utils/plugin_ui_constants.py`

```python
# 单文件大小上限（字节）
MAX_ASSET_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

# 允许的资源扩展名
ALLOWED_ASSET_EXTENSIONS: frozenset[str] = frozenset([
    ".html", ".css", ".js",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".otf",
])

# 静态资源 Cache-Control max-age（秒）
ASSET_CACHE_MAX_AGE: int = 300
```

> 如果将来有充分理由需要运行时可调（比如运维需要临时放大文件限制），再迁移到 settings——但不是现在。

### 11.2 启动顺序

WebUI 插件 `on_plugin_loaded`：
1. `PluginUIManager` 单例懒加载（由 `get_plugin_ui_manager()` 触发）
2. 三个 Router 在 `BaseRouter.__init__` 时已 `register_endpoints()`
3. `PluginUIService` 在 `BaseService.__init__` 时已就绪
4. **不预注册任何 page**——所有 page 都由调用方插件在自己的 `on_plugin_loaded` 中显式注册

> **依赖声明**：调用方插件在 `manifest.json` 的 `dependencies.plugins` 里声明 `["neo-mofox-webui:>=1.0.0"]`，让插件加载器先加载 WebUI 插件，避免 `get_service` 找不到 `plugin_ui`。

---

---

## 12. 里程碑（Phase 划分）

### Phase B-1：数据模型与 Manager 内核（1 周）

- [`plugin_ui_types.py`](../../Plugin/utils/plugin_ui_types.py:1)：全部 Pydantic 模型 + validator
- [`plugin_ui_paths.py`](../../Plugin/utils/plugin_ui_paths.py:1)：`locate_plugin_root` + `resolve_safe`
- [`plugin_ui_manager.py`](../../Plugin/managers/plugin_ui_manager.py:1)：纯内存 Registry（无校验）
- 单元测试：模型与 Manager 的快乐路径 + 边界值

### Phase B-2：校验器（1 周）

- XSD 文件 + [`plugin_ui_validators.py`](../../Plugin/utils/plugin_ui_validators.py:1)
- XML 三层校验（XSD / 白名单 / 占位符表达式）
- HTML 资源校验
- 单元测试：覆盖白名单和黑名单两侧

### Phase B-3：Service 与三个 Router（1 周）

- [`plugin_ui_service.py`](../../Plugin/components/services/plugin_ui_service.py:1)
- [`plugin_ui_discovery_router.py`](../../Plugin/components/router/plugin_ui_discovery_router.py:1)
- [`plugin_ui_schema_router.py`](../../Plugin/components/router/plugin_ui_schema_router.py:1)
- [`plugin_ui_asset_router.py`](../../Plugin/components/router/plugin_ui_asset_router.py:1)
- [`plugin.py`](../../Plugin/plugin.py:1) 追加四个组件
- 集成测试（FastAPI TestClient 全场景覆盖）

### Phase B-4：联调与安全审计（1 周）

- 与前端联调（配合前端 Phase F-3 Discovery + Renderer）
- 按设计文档 §9.5 安全审计 checklist 逐项验证
- 补齐边缘用例测试
- `enable_admin_dump` 接口（可选，按需交付）

---

**版本历史**

- **v1.0.0 (2026-06-19)** — 初版实现方案，对应设计文档 v3.1.0

**禁止的标签**：`<plugin-page-picker>` / `<sys-include>` / `<sys-bind>` / `<sys-toast-anchor>` / 任何 `<script>` / `<style>` / `<iframe