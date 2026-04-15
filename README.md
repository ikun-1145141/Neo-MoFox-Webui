# Neo-MoFox-WebUI 技术设计文档

> Neo-MoFox-WebUI 是对旧版 MoFox-Core-WebUI 的彻底重构，旨在通过**强类型约束**、**统一配置管理**和**标准化的通讯协议**，解决旧版本配置散乱、组件不统一、错误处理混乱、插件市场支持缺失等核心痛点。

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 后端架构](#2-后端架构)
- [3. 前端架构](#3-前端架构)
- [4. 前后端通讯协议](#4-前后端通讯协议)
- [5. 设置与持久化流程](#5-设置与持久化流程)
- [6. 设计系统规范](#6-设计系统规范)
- [7. 开发约束与规范汇总](#7-开发约束与规范汇总)

---

## 1. 项目概述

| 项目 | 说明 |
|---|---|
| **技术栈（后端）** | Python，与 Neo-MoFox 插件系统集成 |
| **技术栈（前端）** | Vite + Vue 3 + TypeScript |
| **设计语言** | Material Design 3（MD3） |
| **持久化路径** | `data/WebUI_data`（所有数据的统一根目录） |

Neo-MoFox-WebUI 以插件的形式接入 Neo-MoFox 框架。目前仅有一个后端插件，暂不支持多插件扩展。

---

## 2. 后端架构

### 2.1 目录结构

```
Plugin/
├── manifest.json               # 插件元数据
├── components/                 # 组件层：定义直接用于 UI 注册的元数据
├── handlers/                   # 事件处理层：处理来自 Adapter 的事件
├── managers/                   # 转发层：前端请求的业务逻辑中转
│   ├── git_updater.py          # Git 更新管理器
│   └── config_manager.py       # 配置分发与校验管理器
├── storage/                    # 存储层
│   ├── base.py                 # 基于 Neo 框架 json_storage 的统一封装（base_storage）
│   ├── settings.py             # WebUI 全局设置对象（继承 base.py）
│   └── <feature>_storage/      # 各功能的独立存储子文件夹（均继承 base.py）
├── utils/                      # 工具层：可复用的工具类与常量
└── plugin.py                   # 插件入口
```

### 2.2 各层职责说明

#### 组件层（`components/`）

存放直接用于向框架注册的 UI 组件元数据。不包含业务逻辑。

#### 事件处理层（`handlers/`）

接收来自 Neo-MoFox Adapter 的事件并进行适配处理，不直接操作存储。

#### 转发层（`managers/`）

前端 API 请求的实际处理核心。负责：

- 接收并校验前端数据
- 调用 Storage 层进行读写
- 封装响应并返回

> **所有 Manager 的核心函数必须标注完整的输入/输出类型及业务说明。**

#### 存储层（`storage/`）

| 文件/目录 | 说明 |
|---|---|
| `base.py` | 对 Neo 框架 `json_storage` 的二次封装，所有 Storage 类均继承此类 |
| `settings.py` | 存储 WebUI 全局设置，数据写入 `data/WebUI_data/config.json` |
| `<feature>_storage/` | 各功能模块独立的存储子目录，所有类均**继承 `base.py`** |

所有持久化数据（JSON 配置、壁纸、缓存等）路径**硬性规定**为 `data/WebUI_data` 下。

#### 工具层（`utils/`）

存放可跨层复用的工具函数、枚举值和常量。

### 2.3 后端开发规范

- **强制使用 Pydantic**：所有 Router 返回值、请求体的数据模型必须使用 Pydantic 定义，**严禁手写 `dict`**。
- **统一基础响应**：所有接口响应必须继承统一的 `BaseResponse` 模型（见第 4 节）。
- **配置管理继承规范**：Config Manager 在读写配置时必须通过继承自 `base.py` 的 Storage 类操作，不得绕过。
- **路径规范**：壁纸等静态资源同样必须存入 `data/WebUI_data`，后端返回其本地映射路径。

---

## 3. 前端架构

### 3.1 目录结构

```
src/
├── api/
│   ├── base.ts                 # Axios/Fetch 实例封装，含全局请求/响应拦截器
│   ├── config.ts               # API 配置（BaseURL、超时等）
│   ├── types/                  # 与后端 Pydantic 模型严格对应的 TypeScript 类型
│   └── modules/                # 按功能模块划分的 API 请求函数
├── views/                      # 页面层：组合组件与调用 API 的顶层容器
│   └── config-view.vue         # 设置页面（示例）
├── components/
│   ├── common/                 # 通用组件：可在多个 View 中复用的 MD3 组件
│   └── features/               # 各 View 独立使用的业务组件（按 View 划分子文件夹）
├── router/                     # Vue Router 路由配置
└── utils/                      # 可复用工具类（含 MD3U 取色逻辑封装）
```

### 3.2 各层职责说明

#### Api 层（`api/`）

所有与后端的通讯**只能**在此层发生。

- **`base.ts`**：封装 HTTP 客户端实例，配置全局请求头、超时和**统一的响应/错误拦截器**。其他所有 `modules/` 中的 API 函数必须通过 `base.ts` 暴露的方法调用，不得自行创建实例。
- **`types/`**：TypeScript 类型定义。类型必须与后端 Pydantic 模型**1:1 对应**，可通过后端暴露的 `openapi.json` 自动生成，也可手动维护。
- **`modules/`**：按功能拆分的 API 模块（如 `settings.ts`、`git.ts`），每个函数对应一个接口。

#### View 层（`views/`）

页面的顶层容器，负责：

- 调用 Api 层获取/提交数据
- 将数据分发给下层组件
- 不包含细粒度业务逻辑（由 Manager 层或 utils 层承接）

#### 组件层（`components/`）

| 目录 | 说明 |
|---|---|
| `common/` | 全局通用 MD3 组件，如统一的日志查看器、错误提示等 |
| `features/` | 仅某一 View 使用的业务组件，以 View 名称为子目录划分 |

#### 路由层（`router/`）

维护 Vue Router 路由表。路由与 View 一一对应，不在组件内动态注册路由。

#### 工具层（`utils/`）

存放与业务无关的纯工具函数。MD3U 取色逻辑的调用封装放于此处。

### 3.3 前端开发规范

- **类型一致性**：`api/types/` 中的所有类型定义必须与后端 Pydantic 模型严格一致。类型不得在组件内临时定义。
- **100% 响应式覆盖**：所有来自后端的数据必须使用 `ref` 或 `reactive` 包装，严禁使用普通变量承载 UI 状态。
- **禁止直接操作 DOM**：所有 UI 变更通过数据驱动，通过 Vue 的响应式系统更新视图。
- **图标规范**：图标统一使用本地化的 **Material Design 3 Icons**，禁止外链 CDN。

---

## 4. 前后端通讯协议

### 4.1 标准响应结构

所有后端接口必须返回以下统一 JSON 结构：

```json
{
  "code": 200,
  "data": {},
  "message": "success"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | `int` | 业务状态码，`200` 为成功，其余为各类错误 |
| `data` | `Any` | 实际业务数据，失败时可为 `null` |
| `message` | `str` | 可读的状态描述 |

**Pydantic 模型示例（后端）：**

```python
from pydantic import BaseModel
from typing import Any, Optional

class BaseResponse(BaseModel):
    code: int = 200
    data: Optional[Any] = None
    message: str = "success"

    @classmethod
    def ok(cls, data: Any = None, message: str = "success") -> "BaseResponse":
        return cls(code=200, data=data, message=message)

    @classmethod
    def error(cls, code: int, message: str) -> "BaseResponse":
        return cls(code=code, data=None, message=message)
```

**TypeScript 类型（前端 `api/types/base.ts`）：**

```typescript
export interface BaseResponse<T = unknown> {
  code: number;
  data: T | null;
  message: string;
}
```

### 4.2 错误处理机制

#### 后端

- 通过自定义全局异常处理器捕获所有业务错误。
- 业务错误统一返回非 `200` 的 `code`，HTTP 状态码视情况使用 `400` / `500` 等。
- 返回格式始终遵循 `BaseResponse` 结构。

#### 前端

- 在 `api/base.ts` 的**响应拦截器**中统一捕获所有错误（HTTP 错误 + 业务 `code` 非 200）。
- 请求失败时**必须**触发全局 Toast 或 Dialog 提示，**严禁静默失败**。
- 各 View/组件无需单独处理网络错误，仅需处理成功态的数据渲染。

```typescript
// api/base.ts 拦截器示例结构
instance.interceptors.response.use(
  (response) => {
    const res = response.data as BaseResponse;
    if (res.code !== 200) {
      // 触发全局 Toast 提示
      showErrorToast(res.message);
      return Promise.reject(res);
    }
    return res.data;
  },
  (error) => {
    // 网络层错误，触发全局错误 Dialog
    showErrorDialog(error.message ?? '网络请求失败');
    return Promise.reject(error);
  }
);
```

### 4.3 长耗时任务（WebSocket）

对于 Git 更新等无法立即完成的任务：

- **后端**：通过 WebSocket 连接向前端实时推送任务进度和日志流。
- **前端**：在 `components/common/` 中提供**统一的日志查看器组件**，所有长耗时任务复用同一个组件展示日志，不得各自实现。

---

## 5. 设置与持久化流程

```
用户进入设置页
      │
      ▼
GET /api/settings  ──→  settings.py 读取 data/WebUI_data/config.json
      │
      ▼
响应式数据绑定至 UI（100% ref/reactive 覆盖）
      │
      ▼
用户修改设置项
      │
      ▼
点击「保存」按钮 / 手动刷新按钮重新获取
      │
      ▼
POST /api/settings  ──→  Config_Manager 接收
      │
      ▼
Pydantic 校验 → settings.py 写入 data/WebUI_data/config.json
```

**关键约定：**

- 每次**进入设置页面**均主动调用 `GET /api/settings` 获取最新配置，不使用本地缓存。
- 页面提供**手动刷新按钮**以支持用户主动同步。
- 壁纸等静态文件上传后，后端存入 `data/WebUI_data/`，返回本地静态映射路径，前端使用路径渲染。
- 主题设置同样通过 `settings.py` 持久化，**禁止将主题存储在 `localStorage` 或其他前端存储**。

---

## 6. 设计系统规范

> 设计主旨：**"The Curated Canvas"（策展画布）**  
> 以高端编辑出版物的设计语言呈现界面，强调留白、层次与克制的用色。

### 6.1 颜色

**主色板：**

| Token | 色值 | 用途 |
|---|---|---|
| `primary` | `#0058BD` | 主行动色、聚焦态 |
| `primary_container` | `#2771DF` | 渐变结束色 |
| `surface` | `#F7F9FF` | 页面底层背景 |
| `surface-container-lowest` | `#FFFFFF` | 卡片/内容块最高层 |
| `surface-container-high` | `#E5E8EE` | 卡片背景底色 |
| `outline-variant` | `#C2C6D5` | 极端无障碍需求下的幽灵边框（15% 不透明度）|
| `tertiary` | `#B51B15` | 破坏性操作、高危警告按钮文字色 |

**"无边框"强制规范：**

- **严禁**使用 `1px solid` 的边框来划分区域。
- 区域边界通过**相邻背景色的差异**来呈现（如 `surface-container-low` 毗邻 `surface` 背景）。
- 若无障碍需求必须使用边框，允许使用 `outline-variant` 色 **15% 不透明度**的幽灵边框。

### 6.2 字体

| 字体 | 用途 |
|---|---|
| **Plus Jakarta Sans** | 所有展示级标题（`display`、`headline`），体现品牌调性 |
| **Inter** | 正文、副标题（`body`、`title`）|

**排版规范：**

- `display-lg`（3.5rem）、`headline-lg`（2rem）使用 `-0.02em` 字间距。
- 鼓励大标题（`display-md`）与小标签（`body-sm`）直接搭配，形成非对称的高级感排版。

### 6.3 主题系统（MD3U）

- 使用 **MD3U**（npm 包）实现 MD3 动态取色。
- 用户可选择以下两种方式设置主题色：
  1. **手动选择**：从预设的 MD3 主题色中选取。
  2. **壁纸自动取色**：上传静态/动态壁纸，前端通过 MD3U 实时计算色板并更新全局 CSS 变量。
- 壁纸由**前端**负责渲染，不得在单个页面中大范围平铺壁纸（避免旧版 UI 的"壁纸一大片"问题）。
- 所有主题色更新后，必须通过 `POST /api/settings` 写入后端持久化，**不得仅存于 `localStorage`**。

### 6.4 阴影与层次

- **禁止**使用标准 `box-shadow: 0px 2px 4px` 等"书盒"阴影。
- 使用**环境光阴影（Ambient Shadow）**：`0px 20px 40px rgba(24, 28, 32, 0.06)`。
- 首选**层叠背景色差异**替代阴影：将 `surface-container-lowest` 元素放置于 `surface-container` 背景上，自然产生层次感。
- 浮层（弹窗、导航栏）使用 **Glassmorphism**：`surface-variant` 70% 不透明度 + `backdrop-blur(20px)`。

### 6.5 圆角

- 按钮、容器优先使用 `xl`（`3rem`）和 `full`（`9999px`）圆角 Token，保持现代感与亲和力。

### 6.6 组件规范

#### 按钮

| 类型 | 样式 |
|---|---|
| **Primary** | 全圆角，`primary` → `primary_container` 135° 渐变背景，白色文字 |
| **Secondary** | `surface-container-highest` 背景，`on-surface` 文字，无边框 |
| **Tertiary (危险)** | 透明背景，`tertiary`（`#B51B15`）文字，仅用于破坏性/高危操作 |

#### 卡片

- **零边框，零分割线。**
- 卡片间距通过 `1.5rem` 内边距 + 垂直 Whitespace 分隔。
- Hover 态：背景从 `surface-container-low` 过渡到 `surface-container-highest`，叠加环境光阴影。

#### 输入框

- 极简底线样式或 `surface-container-low` 软填充容器。
- 聚焦时 Label 变为 `primary` 色，幽灵边框过渡为 100% 不透明的 `primary` 色边框。

#### 列表

- **禁止使用 `<hr>` 分割线。**
- 通过垂直间距（4px gap）分组，必要时以 2% 透明度斑马纹区分行。

---

## 7. 开发约束与规范汇总

### 后端

| 规范 | 详情 |
|---|---|
| **Pydantic 强制** | 所有 Router 返回值与请求体**必须**使用 Pydantic 模型，禁止手写 `dict` |
| **统一响应结构** | 所有接口继承 `BaseResponse`，包含 `code`、`data`、`message` |
| **存储路径** | 所有持久化数据（含静态文件）路径固定为 `data/WebUI_data` |
| **Storage 继承** | 所有 Storage 类必须继承 `base.py`（`base_storage`）|
| **Config 管理** | 配置的读写操作只能通过继承 `base.py` 的 Storage 类进行，不得绕过 |
| **函数注释** | Manager 层和 API 层的核心函数必须注明输入/输出类型及业务说明 |

### 前端

| 规范 | 详情 |
|---|---|
| **类型一致性** | `api/types/` 中的类型必须与后端 Pydantic 模型 1:1 对应，不得在组件内临时定义 |
| **100% 响应式** | 所有后端数据必须用 `ref` / `reactive` 包装，禁止普通变量承载 UI 状态 |
| **错误不静默** | 所有请求失败必须触发全局 Toast 或 Dialog，不得静默失败 |
| **禁止直接操作 DOM** | 所有 UI 状态变更通过 Vue 响应式系统驱动 |
| **图标本地化** | 只使用本地 MD3 Icons，禁止外链 CDN |
| **主题持久化** | 主题等设置不得存于 `localStorage`，必须通过后端 `settings.py` 持久化 |
| **API 集中管理** | 所有后端通讯只在 `api/` 层发生，所有模块通过 `base.ts` 实例调用 |

### 设计

| 规范 | 详情 |
|---|---|
| **禁止实线边框** | 不得使用 `1px solid` 颜色边框，用背景色差替代 |
| **禁止标准阴影** | 不得使用 `0px 2px 4px` 等传统 `box-shadow` |
| **禁止大范围壁纸铺设** | 壁纸渲染由前端统一处理，不得在单页面大范围平铺 |
| **字体规范** | 标题使用 Plus Jakarta Sans，正文使用 Inter |
| **MD3U 取色** | 所有主题色提取必须通过 MD3U 包进行 |
