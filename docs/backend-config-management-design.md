# 后端配置管理模块设计文档

> 版本：v1.0 | 日期：2026-05-02

---

## 目录

- [1. 设计目标](#1-设计目标)
- [2. 整体架构](#2-整体架构)
- [3. 核心数据结构](#3-核心数据结构)
- [4. 工具类：ConfigParser](#4-工具类configparser)
- [5. Manager 层设计](#5-manager-层设计)
- [6. 路由层设计](#6-路由层设计)
  - [6.1 主配置路由（MainConfigRouter）](#61-主配置路由mainconfigrouter)
  - [6.2 机器人配置路由（BotConfigRouter）](#62-机器人配置路由botconfigrouter)
  - [6.3 模型配置路由（ModelConfigRouter）](#63-模型配置路由modelconfigrouter)
  - [6.4 插件配置路由（PluginConfigRouter）](#64-插件配置路由pluginconfigrouter)
- [7. 完整数据流](#7-完整数据流)
- [8. 接口汇总](#8-接口汇总)
- [9. 插件注册](#9-插件注册)

---

## 1. 设计目标

本模块为 WebUI 提供三类配置文件的可视化管理能力：

| 配置文件 | 路径 | 描述 |
|---|---|---|
| 机器人配置 | `config/core.toml` | Bot 基础行为、人格、聊天等参数 |
| 模型配置 | `config/model.toml` | API 提供商列表与模型列表 |
| 插件配置 | `config/plugins/{plugin_name}/config.toml` | 各插件独立的运行时配置 |

**设计原则：**

1. **主路由统一读写**：所有配置的全量获取（含 Schema）、全量写入、增量写入都收拢在主路由（`/api/config`），子路由不重复实现这些通用接口。
2. **子路由专注领域特化**：子路由只负责各配置类型独有的操作（如模型连通性测试、插件配置列表枚举）。
3. **解析逻辑集中在工具类**：TOML 文件读取、Field 元数据提取、Schema 生成均由 `ConfigParser` 工具类承担，其他层不直接操作文件或解析模型元数据。
4. **前端驱动编辑**：前端拿到带 Schema 的增强配置后，由 UI 组件负责展示与编辑，编辑完成后调用写入 API 回写。

---

## 2. 整体架构

```
Plugin/
├── components/
│   └── router/
│       ├── config/                       # 新增：配置管理路由组
│       │   ├── __init__.py
│       │   ├── main_config_router.py     # 主路由：统一读写
│       │   ├── bot_config_router.py      # 子路由：机器人配置专属操作
│       │   ├── model_config_router.py    # 子路由：模型配置专属操作
│       │   └── plugin_config_router.py   # 子路由：插件配置专属操作
│       └── ...
├── managers/
│   └── config/                           # 新增：配置管理 Manager 组
│       ├── __init__.py
│       ├── main_config_manager.py        # 主 Manager：统一读写业务逻辑
│       ├── bot_config_manager.py         # Bot 配置专属业务逻辑
│       ├── model_config_manager.py       # 模型配置专属业务逻辑
│       └── plugin_config_manager.py      # 插件配置专属业务逻辑
└── utils/
    └── config_parser.py                  # 工具类：Schema 提取与 TOML 解析
```

**调用关系：**

```
Router → Manager → ConfigParser（工具类）
                 → TOML 文件系统
                 → BaseConfig / ConfigBase 类元数据
```

---

## 3. 核心数据结构

所有数据结构均使用 Pydantic 定义，放置于各 Manager/Router 的对应模块，或抽取到 `utils/config_types.py`。

### 3.1 FieldSchema —— 字段 UI 元数据

描述一个配置字段的展示与验证信息，由 `ConfigParser` 从 `Field(...)` 定义中提取。

```python
class FieldSchema(BaseModel):
    """单个配置字段的 Schema 描述。"""
    
    key: str                          # 字段名（Python 属性名）
    label: str                        # 显示标签（来自 Field.label，不填则用 key）
    description: str                  # 字段描述
    type: str                         # 类型字符串，如 "str"、"int"、"bool"、"float"、"list[str]"
    default: Any                      # 默认值
    input_type: str                   # 控件类型："text"|"password"|"number"|"switch"|"slider"|"select"|"list"|"textarea"|"json"|"color"|"file"
    tag: str | None                   # 预设标签（映射图标）
    placeholder: str | None           # 占位符文本
    hint: str | None                  # 帮助提示
    order: int                        # 显示顺序
    hidden: bool                      # 是否隐藏
    disabled: bool                    # 是否只读
    
    # 验证约束（可选）
    ge: float | None = None
    le: float | None = None
    gt: float | None = None
    lt: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    
    # 控件特定
    choices: list[Any] | None = None  # select 选项
    rows: int | None = None           # textarea 行数
    step: float | None = None         # number/slider 步进
    
    # 列表配置
    item_type: str | None = None
    item_fields: dict[str, Any] | None = None
    min_items: int | None = None
    max_items: int | None = None
    
    # 条件显示
    depends_on: str | None = None
    depends_value: Any = None
```

### 3.2 SectionSchema —— 配置节 Schema

```python
class SectionSchema(BaseModel):
    """一个配置节（[section]）的 Schema。"""
    
    name: str                         # 节名称（TOML table key，如 "bot"、"chat"）
    title: str | None                 # 显示标题（来自 config_section(title=...)）
    description: str | None           # 节描述
    tag: str | None                   # 预设标签
    order: int                        # 显示顺序
    fields: list[FieldSchema]         # 本节包含的字段
```

### 3.3 EnhancedConfigResponse —— 前端获取配置的完整响应

这是前端配置编辑器所需的一切信息，由主路由的 GET 接口返回。

```python
class EnhancedConfigResponse(BaseModel):
    """增强配置响应。
    
    包含配置的当前值（data）和渲染编辑器所需的 Schema（schema）。
    前端根据 schema 渲染表单，根据 data 填充初始值，
    编辑完成后将修改后的 data 通过写入接口回写。
    """
    
    config_type: Literal["bot", "model", "plugin"]  # 配置类型
    plugin_name: str | None     # 仅 plugin 类型时有值
    sections: list[SectionSchema]  # 有序的配置节列表（含 Schema）
    data: dict[str, Any]           # 当前配置值（与 TOML 文件内容一致的字典）
```

### 3.4 模型配置专用结构

`model.toml` 使用 TOML 数组表（`[[api_providers]]`、`[[models]]`），结构与 Section 型配置不同，需要独立定义。

```python
class ApiProviderData(BaseModel):
    """单个 API 提供商的数据。"""
    name: str
    base_url: str
    api_key: str | list[str]
    client_type: str
    max_retry: int
    timeout: int
    retry_interval: int

class ModelData(BaseModel):
    """单个模型的数据。"""
    model_identifier: str
    name: str
    api_provider: str
    price_in: float
    price_out: float
    force_stream_mode: bool
    max_context: int
    tool_call_compat: bool
    extra_params: dict[str, Any]
    anti_truncation: bool

class ModelConfigData(BaseModel):
    """model.toml 的完整数据。"""
    api_providers: list[ApiProviderData]
    models: list[ModelData]
```

### 3.5 写入请求体

```python
class FullWriteRequest(BaseModel):
    """全量写入请求（PUT）。
    
    用 data 完全替换配置文件的所有值。
    data 格式与 EnhancedConfigResponse.data 一致。
    """
    data: dict[str, Any]

class PatchWriteRequest(BaseModel):
    """增量写入请求（PATCH）。
    
    仅更新 data 中包含的字段，未出现的字段保持原值不变。
    data 格式与 EnhancedConfigResponse.data 一致，支持嵌套 dict 的深度合并。
    """
    data: dict[str, Any]
```

---

## 4. 工具类：ConfigParser

**文件路径：** `Plugin/utils/config_parser.py`

`ConfigParser` 是一个无状态工具类（或一组纯函数的命名空间），承担以下职责：

- 读取 TOML 文件，返回原始字典
- 从 `ConfigBase` / `BaseConfig` 的子类提取带 UI 属性的 Schema（遍历 `model_fields`，读取 `json_schema_extra` 或 `metadata` 中存储的 Field 增强参数）
- 将原始数据字典与 Schema 合并，构造 `EnhancedConfigResponse`
- 处理 `model.toml` 的数组表结构（`[[api_providers]]`、`[[models]]`），将其解析为 `ModelConfigData`
- 将前端提交的 `dict[str, Any]` 深度合并到当前配置字典（增量写入辅助函数）
- 将配置字典序列化回 TOML 文件，并触发 `ConfigBase.load(..., auto_update=True)` 以保持注释签名

**设计要点（仅描述，不含实现代码）：**

| 函数 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `read_toml(path)` | 文件路径 | `dict[str, Any]` | 读取 TOML 文件，返回原始字典 |
| `write_toml(path, config_class, data)` | 路径 + 配置类 + 数据字典 | `None` | 将数据写入 TOML，并触发签名回写以保留注释 |
| `extract_schema(config_class)` | `type[ConfigBase]` | `list[SectionSchema]` | 遍历配置类的节和字段，提取 Field 增强元数据，构建有序 Schema 列表 |
| `build_enhanced_response(config_type, config_class, data)` | 配置类型 + 配置类 + 数据字典 | `EnhancedConfigResponse` | 组合 schema 与 data，构造完整响应对象 |
| `deep_merge(base, patch)` | 两个嵌套字典 | `dict[str, Any]` | 深度合并，patch 中的叶子值覆盖 base，缺失键保留 base 值 |
| `parse_model_config(path)` | 文件路径 | `ModelConfigData` | 专门解析 model.toml 的数组表结构 |
| `serialize_model_config(path, data)` | 路径 + `ModelConfigData` | `None` | 将 `ModelConfigData` 序列化回 model.toml 格式 |

**关于 Schema 提取机制（原理说明）：**

`Field(...)` 函数（在 `src/kernel/config/core.py` 中定义）通过 Pydantic 的 `json_schema_extra` 或 `metadata` 将 `label`、`tag`、`input_type`、`hint` 等 UI 属性随字段一起存储在模型的 `model_fields` 中。`extract_schema` 只需遍历 `ConfigBase` 子类的 `model_fields`，将各字段的 `FieldInfo` 及其携带的额外属性映射到 `FieldSchema` 即可。`config_section` 装饰器在节类上注入了 `_section_name_`、`_section_title_`、`_section_order_` 等类属性，可直接读取以构建 `SectionSchema`。

---

## 5. Manager 层设计

### 5.1 MainConfigManager

**文件路径：** `Plugin/managers/config/main_config_manager.py`

统一配置读写的业务逻辑层，被主路由调用。

```
职责：
- get_config(config_type, plugin_name?)
    → 调用 ConfigParser 读取对应文件，提取 Schema，返回 EnhancedConfigResponse

- full_write(config_type, data, plugin_name?)
    → 校验 data 符合对应配置类类型约束
    → 调用 ConfigParser.write_toml 全量写入

- patch_write(config_type, patch, plugin_name?)
    → 先读取当前值
    → 调用 ConfigParser.deep_merge 合并
    → 调用 ConfigParser.write_toml 写入合并结果

内部路由分发：根据 config_type 参数选择正确的 ConfigBase 子类和文件路径
    "bot"    → CoreConfig 类，config/core.toml
    "model"  → 走 parse_model_config / serialize_model_config 特殊路径
    "plugin" → 通过 plugin_name 查找对应的 BaseConfig 子类和文件路径
```

### 5.2 BotConfigManager

**文件路径：** `Plugin/managers/config/bot_config_manager.py`

```
职责：
- 目前无独立于主 Manager 之外的专属操作
- 预留扩展点：如未来需要热重载 Bot 配置（apply_config_live），可在此添加
  将修改后的配置通知 Neo-MoFox 核心重新加载 CoreConfig，而无需重启进程
```

### 5.3 ModelConfigManager

**文件路径：** `Plugin/managers/config/model_config_manager.py`

```
职责：
- test_model(provider_name, model_name, test_prompt?)
    → 使用指定提供商和模型的 API Key / base_url 临时构造一个 LLM 请求
    → 发送测试 prompt，返回响应结果与耗时

- list_providers() → list[str]
    → 返回当前 model.toml 中所有 API 提供商的名称列表

- list_models(provider_name?) → list[str]
    → 返回指定提供商（或全部）的模型名称列表

辅助 main_config_manager 的工作：
  get_model_config() / write_model_config() 的实现委托给 main_config_manager，
  ModelConfigManager 只持有模型测试和枚举相关逻辑。
```

### 5.4 PluginConfigManager

**文件路径：** `Plugin/managers/config/plugin_config_manager.py`

```
职责：
- list_plugin_configs() → list[PluginConfigEntry]
    → 扫描 Neo-MoFox 的 ConfigManager（通过 config_api.get_loaded_plugins()）
    → 或直接扫描 config/plugins/ 目录
    → 返回所有已注册/存在配置文件的插件列表，包括插件名、配置文件路径、是否已加载

- get_plugin_config_schema(plugin_name) → list[SectionSchema]
    → 通过 config_api.get_config(plugin_name) 获取对应的 BaseConfig 子类
    → 调用 ConfigParser.extract_schema 提取并返回该插件的 Schema
    → 前端可用来动态渲染插件配置表单

对于读写操作：
  委托给 main_config_manager.get_config("plugin", plugin_name)
  和 main_config_manager.full_write / patch_write
```

---

## 6. 路由层设计

### 6.1 主配置路由（MainConfigRouter）

**文件路径：** `Plugin/components/router/config/main_config_router.py`  
**挂载路径：** `/api/config`

这是配置管理的核心路由，提供统一的读写接口。所有子路由没有这些通用接口。

#### 接口列表

---

**`GET /api/config/{config_type}`** — 获取增强配置

| 项目 | 说明 |
|---|---|
| 路径参数 | `config_type: Literal["bot", "model", "plugin"]` |
| 查询参数 | `plugin_name: str | None`（`config_type=plugin` 时必填） |
| 认证 | `VerifiedDep`（需已登录） |
| 响应 | `BaseResponse[EnhancedConfigResponse]` |

响应的 `data` 字段包含：
- `sections`：按 `order` 排序的 `SectionSchema` 列表，每个节含其下所有字段的完整 Schema
- `data`：当前配置文件的完整值字典

对于 `config_type=model`，`sections` 为空，`data` 直接返回 `ModelConfigData` 序列化结果（数组表结构无法统一为节模型）。前端需要对 model 类型进行独立的渲染处理。

---

**`PUT /api/config/{config_type}`** — 全量写入

| 项目 | 说明 |
|---|---|
| 路径参数 | `config_type: Literal["bot", "model", "plugin"]` |
| 查询参数 | `plugin_name: str | None` |
| 请求体 | `FullWriteRequest` |
| 认证 | `VerifiedDep` |
| 响应 | `BaseResponse[EnhancedConfigResponse]`（写入后返回最新配置） |

全量写入：用请求体中的 `data` 完全替换配置文件的所有值。配置类的约束（类型、范围）在写入前由 Pydantic 校验。

---

**`PATCH /api/config/{config_type}`** — 增量写入

| 项目 | 说明 |
|---|---|
| 路径参数 | `config_type: Literal["bot", "model", "plugin"]` |
| 查询参数 | `plugin_name: str | None` |
| 请求体 | `PatchWriteRequest` |
| 认证 | `VerifiedDep` |
| 响应 | `BaseResponse[EnhancedConfigResponse]`（返回合并后的最新配置） |

增量写入：深度合并 `patch` 到当前配置，未出现的字段保持原值。适合前端只提交单个 Section 的修改。

---

### 6.2 机器人配置路由（BotConfigRouter）

**文件路径：** `Plugin/components/router/config/bot_config_router.py`  
**挂载路径：** `/api/config-bot`

读写操作由前端直接调用主路由（`/api/config/bot`），本路由仅提供 Bot 配置独有的操作。

#### 接口列表

---

**`POST /api/config-bot/reload`** — 热重载机器人配置

| 项目 | 说明 |
|---|---|
| 认证 | `VerifiedDep` |
| 响应 | `BaseResponse[None]` |

触发 Neo-MoFox 核心的 `CoreConfig` 重新从文件加载，无需重启进程。部分配置项（如日志级别、Tick 间隔）可在运行时生效，BotConfigManager 负责将变更推送给对应的系统组件。

---

### 6.3 模型配置路由（ModelConfigRouter）

**文件路径：** `Plugin/components/router/config/model_config_router.py`  
**挂载路径：** `/api/config-model`

读写由主路由处理，本路由提供模型领域特有操作。

#### 接口列表

---

**`POST /api/config-model/test`** — 测试模型连通性

| 项目 | 说明 |
|---|---|
| 认证 | `VerifiedDep` |
| 请求体 | `ModelTestRequest` |
| 响应 | `BaseResponse[ModelTestResult]` |

```python
class ModelTestRequest(BaseModel):
    """模型测试请求。"""
    provider_name: str       # 提供商名称（对应 model.toml 中 api_providers[].name）
    model_name: str          # 模型 name 字段（model.toml 中 models[].name）
    test_prompt: str = "你好"  # 测试用的提示词
    timeout: int = 15        # 超时时间（秒）

class ModelTestResult(BaseModel):
    """模型测试结果。"""
    success: bool
    response_text: str | None    # 模型返回的文本（成功时）
    latency_ms: float | None     # 请求耗时（毫秒）
    error_message: str | None    # 错误信息（失败时）
    model_identifier: str        # 实际使用的 model_identifier
    provider_base_url: str       # 使用的 base_url
```

ModelConfigManager 直接从 `model.toml` 读取对应提供商的 `api_key` 和 `base_url`，通过大模型API进行请求测试，记录响应和耗时。

---

**`GET /api/config-model/providers`** — 获取提供商列表

| 项目 | 说明 |
|---|---|
| 认证 | `VerifiedDep` |
| 响应 | `BaseResponse[list[str]]` |

返回当前 `model.toml` 中所有提供商的 `name` 列表，供前端渲染下拉选择。

---

**`GET /api/config-model/models`** — 获取模型列表

| 项目 | 说明 |
|---|---|
| 认证 | `VerifiedDep` |
| 查询参数 | `provider: str | None`（不填则返回全部） |
| 响应 | `BaseResponse[list[str]]` |

---

### 6.4 插件配置路由（PluginConfigRouter）

**文件路径：** `Plugin/components/router/config/plugin_config_router.py`  
**挂载路径：** `/api/config-plugin`

读写由主路由处理，本路由提供插件配置枚举与 Schema 查询能力。

#### 接口列表

---

**`GET /api/config-plugin/list`** — 获取可配置插件列表

| 项目 | 说明 |
|---|---|
| 认证 | `VerifiedDep` |
| 响应 | `BaseResponse[list[PluginConfigEntry]]` |

```python
class PluginConfigEntry(BaseModel):
    """可配置插件的摘要信息。"""
    plugin_name: str         # 插件名（config_api 中的 plugin_name）
    config_name: str         # 配置文件名（不含 .toml）
    config_path: str         # 配置文件路径（相对路径）
    config_description: str  # 配置描述（来自 BaseConfig.config_description）
    is_loaded: bool          # 是否已被 ConfigManager 加载（运行时可用）
```

PluginConfigManager 通过 `config_api.get_loaded_plugins()` 获取运行时已加载的插件配置列表，同时扫描 `config/plugins/` 目录补充未加载（仅有文件但插件未运行）的条目。

---

**`GET /api/config-plugin/{plugin_name}/schema`** — 获取插件配置 Schema

| 项目 | 说明 |
|---|---|
| 路径参数 | `plugin_name: str` |
| 认证 | `VerifiedDep` |
| 响应 | `BaseResponse[list[SectionSchema]]` |

通过 `config_api.get_config(plugin_name)` 获取配置类，调用 `ConfigParser.extract_schema` 提取 Schema。前端可在渲染插件配置表单前先获取 Schema，再调用主路由的 `GET /api/config/plugin` 获取当前值，两者合并后渲染。

或者，前端也可以直接调用主路由的 `GET /api/config/plugin?plugin_name=xxx`，它已经返回了 `EnhancedConfigResponse`（同时包含 schema 和 data）。本接口仅为只需要 Schema 而不需要当前值的场景提供（如展示配置描述页面时）。

---

## 7. 完整数据流

### 7.1 读取配置流

```
前端           主路由                     MainConfigManager       ConfigParser
  │                │                              │                     │
  │  GET /api/config/bot                          │                     │
  │─────────────────>│                            │                     │
  │                  │  get_config("bot")         │                     │
  │                  │───────────────────────────>│                     │
  │                  │                            │  read_toml(path)    │
  │                  │                            │────────────────────>│
  │                  │                            │  <── dict ──────────│
  │                  │                            │  extract_schema(CoreConfig)
  │                  │                            │────────────────────>│
  │                  │                            │  <── SectionSchema[]│
  │                  │                            │  build_enhanced_response(...)
  │                  │                            │────────────────────>│
  │                  │                            │<── EnhancedConfigResponse
  │                  │<── EnhancedConfigResponse ─│
  │<── BaseResponse ─│
  │
  │  （前端用 schema 渲染表单，用 data 填充初始值）
```

### 7.2 增量写入流

```
前端           主路由                     MainConfigManager       ConfigParser
  │                │                              │                     │
  │  PATCH /api/config/bot  { data: { bot: { log_level: "DEBUG" } } }
  │─────────────────>│                            │                     │
  │                  │  patch_write("bot", patch)  │                     │
  │                  │───────────────────────────>│                     │
  │                  │                            │  read_toml(path)    │
  │                  │                            │────────────────────>│
  │                  │                            │  current = dict     │
  │                  │                            │  deep_merge(current, patch)
  │                  │                            │────────────────────>│
  │                  │                            │  merged = dict      │
  │                  │                            │  CoreConfig.model_validate(merged) [校验]
  │                  │                            │  write_toml(path, CoreConfig, merged)
  │                  │                            │────────────────────>│
  │                  │                            │  （写回文件，保留注释）
  │                  │                            │  build_enhanced_response(...)
  │                  │<── EnhancedConfigResponse ─│
  │<── BaseResponse ─│
```

### 7.3 模型测试流

```
前端           ModelConfigRouter       ModelConfigManager
  │                  │                       │
  │  POST /api/config/model/test             │
  │─────────────────>│                       │
  │                  │  test_model(...)      │
  │                  │──────────────────────>│
  │                  │                       │  从 model.toml 读取 provider 信息
  │                  │                       │  构造临时 openai.AsyncOpenAI 客户端
  │                  │                       │  发送 chat.completions 请求
  │                  │                       │  记录耗时
  │                  │<── ModelTestResult ───│
  │<── BaseResponse ─│
```

---

## 8. 接口汇总

| 方法 | 路径 | 说明 | 路由类 |
|---|---|---|---|
| `GET` | `/api/config/{config_type}` | 获取增强配置（含 Schema） | `MainConfigRouter` |
| `PUT` | `/api/config/{config_type}` | 全量写入配置 | `MainConfigRouter` |
| `PATCH` | `/api/config/{config_type}` | 增量写入配置 | `MainConfigRouter` |
| `POST` | `/api/config/bot/reload` | 热重载机器人配置 | `BotConfigRouter` |
| `POST` | `/api/config/model/test` | 测试模型连通性 | `ModelConfigRouter` |
| `GET` | `/api/config/model/providers` | 获取提供商名称列表 | `ModelConfigRouter` |
| `GET` | `/api/config/model/models` | 获取模型名称列表 | `ModelConfigRouter` |
| `GET` | `/api/config/plugin/list` | 获取可配置插件列表 | `PluginConfigRouter` |
| `GET` | `/api/config/plugin/{plugin_name}/schema` | 获取插件配置 Schema | `PluginConfigRouter` |

**路径参数约束：**

- `config_type` 值域：`"bot"` | `"model"` | `"plugin"`
- `plugin_name` 参数：`config_type=plugin` 时，通用接口需通过查询参数 `?plugin_name=xxx` 传入

---

## 9. 插件注册

四个新路由组件需在 `Plugin/plugin.py` 的 `get_components()` 中注册：

```python
from .components.router.config.main_config_router import MainConfigRouter
from .components.router.config.bot_config_router import BotConfigRouter
from .components.router.config.model_config_router import ModelConfigRouter
from .components.router.config.plugin_config_router import PluginConfigRouter

def get_components(self) -> list[type]:
    return [
        AuthRouter,
        DashboardRouter,
        WebuiSettingsRouter,
        WallpaperRouter,
        # 配置管理路由组
        MainConfigRouter,
        BotConfigRouter,
        ModelConfigRouter,
        PluginConfigRouter,
    ]
```

`MainConfigRouter` 挂载于 `/api/config`，三个子路由分别挂载于 `/api/config-bot`、`/api/config-model`、`/api/config-plugin`

---

*文档结束*
