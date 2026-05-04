# Neo-MoFox 插件管理 API 调研报告

> **调研日期**: 2026-05-04  
> **目标**: 为 WebUI 插件管理页面提供技术支持

---

## 📋 目录

1. [插件管理核心 API](#1-插件管理核心-api)
2. [组件查询 API](#2-组件查询-api)
3. [组件类型体系](#3-组件类型体系)
4. [WebUI 现有架构](#4-webui-现有架构)
5. [配置管理架构](#5-配置管理架构)
6. [建议的数据模型](#6-建议的数据模型)
7. [实现路线图](#7-实现路线图)

---

## 1. 插件管理核心 API

### 1.1 基础 API (`plugin_api.py`)

**位置**: `src/app/plugin_system/api/plugin_api.py`

| 函数名 | 参数 | 返回值 | 说明 |
|--------|------|--------|------|
| `load_plugin` | `plugin_path: str` | `bool` | 按路径加载插件 |
| `load_plugin_from_manifest` | `plugin_path: str, manifest: PluginManifest` | `bool` | 从清单加载插件 |
| `unload_plugin` | `plugin_name: str` | `bool` | 卸载插件 |
| `reload_plugin` | `plugin_name: str` | `bool` | 重载插件 |
| `get_plugin` | `plugin_name: str` | `BasePlugin \| None` | 获取插件实例 |
| `get_all_plugins` | 无 | `dict[str, BasePlugin]` | 获取所有已加载插件 |
| `list_loaded_plugins` | 无 | `list[str]` | 列出所有已加载插件名称 |
| `get_manifest` | `plugin_name: str` | `PluginManifest \| None` | 获取插件清单 |
| `is_plugin_loaded` | `plugin_name: str` | `bool` | 检查插件是否已加载 |

**使用示例**:
```python
from src.app.plugin_system.api.plugin_api import (
    list_loaded_plugins,
    get_plugin,
    reload_plugin
)

# 获取所有插件名称
plugin_names = list_loaded_plugins()

# 获取插件实例
plugin = get_plugin("my_plugin")

# 重载插件
success = await reload_plugin("my_plugin")
```

---

## 2. 组件查询 API

### 2.1 通用组件注册表 (`registry.py`)

**位置**: `src/core/components/registry.py`

**核心方法**:
- `get(signature: str)` - 按签名获取组件类
- `get_by_plugin(plugin_name: str)` - 获取插件的所有组件
- `get_by_type(component_type: ComponentType)` - 获取特定类型的所有组件
- `get_by_plugin_and_type(plugin_name, component_type)` - 组合查询

**组件签名格式**: `plugin_name:component_type:component_name`  
**示例**: `"webui:router:dashboard_router"`

### 2.2 分类组件 API

#### Action API (`action_api.py`)
```python
from src.app.plugin_system.api.action_api import (
    get_all_actions,              # 获取所有 Action
    get_actions_for_plugin,       # 获取指定插件的 Action
    get_actions_for_chat,         # 获取适用于特定聊天的 Action
)

# 示例
actions = get_all_actions()  # 返回 dict[str, type[BaseAction]]
plugin_actions = get_actions_for_plugin("my_plugin")
```

#### Adapter API (`adapter_api.py`)
```python
from src.app.plugin_system.api.adapter_api import (
    start_adapter,                # 启动适配器
    stop_adapter,                 # 停止适配器
    restart_adapter,              # 重启适配器
    # ... 命令调用相关
)

# 示例
success = await start_adapter("qq:adapter:mofox_qq")
```

#### Command API (`command_api.py`)
```python
from src.app.plugin_system.api.command_api import (
    get_all_commands,             # 获取所有命令
    get_commands_for_plugin,      # 获取插件命令
    set_prefixes,                 # 设置命令前缀
)

# 示例
commands = get_all_commands()  # 返回 dict[str, type[BaseCommand]]
```

#### Router API (`router_api.py`)
```python
from src.app.plugin_system.api.router_api import (
    get_all_routers,              # 获取所有路由
    get_routers_for_plugin,       # 获取插件路由
    mount_router,                 # 挂载路由
    get_mounted_router,           # 获取已挂载的路由实例
)

# 示例
routers = get_all_routers()  # 返回 dict[str, type[BaseRouter]]
```

#### Agent API (`agent_api.py`)
```python
from src.app.plugin_system.api.agent_api import (
    get_all_agents,               # 获取所有 Agent
    get_agents_for_plugin,        # 获取插件 Agent
    get_agents_for_chat,          # 获取适用于特定聊天的 Agent
)
```

#### Service API (`service_api.py`)
```python
from src.app.plugin_system.api.service_api import (
    get_all_services,             # 获取所有 Service
    get_services_for_plugin,      # 获取插件 Service
    get_service,                  # 获取 Service 实例
)

# Service 是单例，通过签名获取实例
service = get_service("my_plugin:service:cache")
```

### 2.3 配置 API (`config_api.py`)

```python
from src.app.plugin_system.api.config_api import (
    get_config,                   # 获取插件配置实例
    get_loaded_plugins,           # 获取已加载配置的插件列表
    reload_config,                # 热重载配置
)

# 示例
config = get_config("my_plugin")  # 返回 BaseConfig | None
plugin_names = get_loaded_plugins()  # 返回 list[str]
```

---

## 3. 组件类型体系

### 3.1 ComponentType 枚举

**位置**: `src/core/components/types.py`

```python
class ComponentType(Enum):
    ACTION = "action"              # 动作组件（LLM Tool Calling）
    AGENT = "agent"                # 代理组件（任务编排）
    TOOL = "tool"                  # 工具组件（功能查询，已废弃）
    ADAPTER = "adapter"            # 适配器（平台通信）
    CHATTER = "chatter"            # 聊天器（对话逻辑）
    COMMAND = "command"            # 命令组件（命令处理）
    CONFIG = "config"              # 配置组件
    EVENT_HANDLER = "event_handler"  # 事件处理器
    SERVICE = "service"            # 服务组件（跨插件调用）
    ROUTER = "router"              # 路由组件（HTTP API）
    PLUGIN = "plugin"              # 插件根组件
```

### 3.2 组件特性对比表

| 组件类型 | 用途 | 实例化方式 | 关键属性 | API 支持 |
|---------|------|-----------|---------|---------|
| **Action** | LLM 主动响应 | 每次聊天创建 | `action_name`, `primary_action` | `action_api` |
| **Agent** | 任务编排协助 | 每次聊天创建 | `agent_name`, `usables[]` | `agent_api` |
| **Adapter** | 平台通信 | 插件加载时启动 | `platform`, `adapter_name` | `adapter_api` |
| **Chatter** | 对话逻辑核心 | 插件加载时创建 | `chatter_name`, `model_set` | `chatter_api` |
| **Command** | 命令处理 | 插件加载时注册 | `command_name`, `permission_level` | `command_api` |
| **Router** | HTTP API 路由 | 插件加载时挂载 | `custom_route_path`, `cors_origins` | `router_api` |
| **Service** | 跨插件服务 | 插件加载时创建（单例） | `service_name` | `service_api` |
| **EventHandler** | 事件订阅 | 插件加载时注册 | `event_type` | `event_api` |
| **Config** | 配置定义 | 插件实例化前加载 | 继承 `BaseConfig` | `config_api` |

### 3.3 获取插件组件列表

**方式1：通过插件实例**
```python
plugin = get_plugin("my_plugin")
components = plugin.get_components()  # 返回 list[type]
```

**方式2：通过注册表**
```python
from src.core.components.registry import get_global_registry

registry = get_global_registry()
components = registry.get_by_plugin("my_plugin")  # 返回 dict[str, type]
# 格式：{"plugin_name:type:name": <class>}
```

**方式3：按类型查询**
```python
from src.core.components.types import ComponentType

# 获取插件的所有 Action
actions = registry.get_by_plugin_and_type("my_plugin", ComponentType.ACTION)
# 返回 dict[str, type]，key 为 component_name
```

---

## 4. WebUI 现有架构

### 4.1 路由设计模式

**位置**: `Neo-MoFox-Webui/Plugin/components/router/`

#### 路由结构
```
router/
├── auth_router.py            # 认证路由 (/api/auth)
├── dashboard_router.py       # 仪表板 (/api/dashboard)
├── system_router.py          # 系统控制 (/api/system)
├── wallpaper_router.py       # 壁纸管理 (/api/wallpaper)
├── webui_router.py          # WebUI 设置 (/api/webui)
└── config/                   # 配置管理子路由
    ├── main_config_router.py      # 主配置路由 (/api/config)
    ├── bot_config_router.py       # Bot 配置 (/api/config-bot)
    ├── model_config_router.py     # 模型配置 (/api/config-model)
    └── plugin_config_router.py    # 插件配置 (/api/config-plugin)
```

#### 标准路由模板

```python
from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from fastapi import HTTPException
from ...utils.response import BaseResponse

class MyRouter(BaseRouter):
    """路由描述。"""
    
    router_name: str = "my_router"
    router_description: str = "路由功能描述"
    custom_route_path: str = "/api/my-router"
    cors_origins: list[str] = ["*"]
    
    dependencies: list[str] = []  # 组件依赖
    
    def __init__(self, plugin: "BasePlugin") -> None:
        super().__init__(plugin)
        self.manager = get_my_manager()  # 获取管理器
    
    def register_endpoints(self) -> None:
        """注册 API 端点。"""
        
        @self.app.get(
            "/list",
            response_model=BaseResponse[list[MyDataType]],
            dependencies=[VerifiedDep]  # 需要认证
        )
        async def list_items() -> BaseResponse[list[MyDataType]]:
            """获取列表。"""
            try:
                items = await self.manager.list_items()
                return BaseResponse.ok(data=items, message="获取成功")
            except Exception as e:
                logger.error(f"获取失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))
```

### 4.2 统一响应模型

**位置**: `Neo-MoFox-Webui/Plugin/utils/response.py`

```python
class BaseResponse(BaseModel, Generic[T]):
    code: int = 200              # 业务状态码
    data: T | None = None        # 业务数据
    message: str = "success"     # 状态描述
    
    @classmethod
    def ok(cls, data: Any = None, message: str = "success"):
        return cls(code=200, data=data, message=message)
    
    @classmethod
    def error(cls, code: int, message: str):
        return cls(code=code, data=None, message=message)
```

### 4.3 Manager 层模式

**位置**: `Neo-MoFox-Webui/Plugin/managers/`

**职责**: 处理业务逻辑，作为 Router 和存储层的中间层

```python
class MyManager:
    """管理器描述。"""
    
    async def list_items(self) -> list[MyDataType]:
        """获取列表。
        
        Returns:
            数据列表
            
        Raises:
            RuntimeError: 获取失败
        """
        try:
            # 调用 API 或存储层
            return items
        except Exception as e:
            logger.error(f"获取失败: {e}")
            raise RuntimeError(f"获取失败: {e}")
```

---

## 5. 配置管理架构

### 5.1 配置路由结构

**参考文档**: `Neo-MoFox-Webui/docs/配置管理模块实现总结.md`

#### 路由分层
1. **MainConfigRouter** - 统一读写入口
   - `GET /api/config/read/{config_type}` - 获取增强配置
   - `PUT /api/config/write/{config_type}` - 全量写入
   - `PATCH /api/config/patch/{config_type}` - 增量写入

2. **子路由** - 领域特化操作
   - **BotConfigRouter** (`/api/config-bot`) - Bot 配置热重载
   - **ModelConfigRouter** (`/api/config-model`) - 模型测试、提供商查询
   - **PluginConfigRouter** (`/api/config-plugin`) - 插件配置枚举、Schema 查询

### 5.2 配置跳转逻辑

**场景**: 插件管理页面点击"配置"按钮

```typescript
// 跳转到配置管理页面
const jumpToPluginConfig = (pluginName: string) => {
  router.push({
    name: 'PluginConfig',
    params: { pluginName },
    query: { from: 'plugin-manager' }
  })
}
```

**前端路由配置**:
```typescript
{
  path: '/settings/plugin/:pluginName',
  name: 'PluginConfig',
  component: () => import('@/views/settings/PluginConfigView.vue'),
  props: true
}
```

---

## 6. 建议的数据模型

### 6.1 插件列表数据模型

```typescript
/**
 * 插件摘要信息（列表展示）
 */
interface PluginSummary {
  plugin_name: string;           // 插件名
  plugin_description: string;    // 插件描述
  plugin_version: string;        // 版本号
  is_loaded: boolean;            // 是否已加载
  has_config: boolean;           // 是否有配置
  component_count: number;       // 组件总数
  component_types: string[];     // 包含的组件类型列表
}

/**
 * 插件详细信息
 */
interface PluginDetail extends PluginSummary {
  plugin_path: string;           // 插件路径
  manifest: PluginManifest;      // 插件清单
  components: PluginComponent[]; // 组件列表
  dependencies: string[];        // 依赖的组件签名列表
}

/**
 * 插件组件信息
 */
interface PluginComponent {
  signature: string;             // 组件签名
  component_type: string;        // 组件类型
  component_name: string;        // 组件名称
  description: string;           // 组件描述
  status: 'active' | 'inactive' | 'error';  // 状态
  // 针对不同类型的扩展属性
  extra?: {
    platform?: string;           // Adapter 专属
    custom_route_path?: string;  // Router 专属
    permission_level?: string;   // Command 专属
  };
}

/**
 * 插件清单（对应后端 PluginManifest）
 */
interface PluginManifest {
  name: string;
  version: string;
  description: string;
  author: string;
  license: string;
  repository?: string;
  dependencies?: {
    plugins?: string[];
    components?: string[];
  };
  entry_point: string;
  min_core_version: string;
}
```

### 6.2 后端响应模型（Pydantic）

```python
from pydantic import BaseModel, Field
from typing import Any

class PluginComponentInfo(BaseModel):
    """插件组件信息。"""
    signature: str = Field(..., description="组件签名")
    component_type: str = Field(..., description="组件类型")
    component_name: str = Field(..., description="组件名称")
    description: str = Field(default="", description="组件描述")
    status: str = Field(default="active", description="组件状态")
    extra: dict[str, Any] | None = Field(default=None, description="扩展属性")

class PluginSummary(BaseModel):
    """插件摘要信息。"""
    plugin_name: str = Field(..., description="插件名")
    plugin_description: str = Field(default="", description="插件描述")
    plugin_version: str = Field(default="1.0.0", description="版本号")
    is_loaded: bool = Field(..., description="是否已加载")
    has_config: bool = Field(default=False, description="是否有配置")
    component_count: int = Field(default=0, description="组件总数")
    component_types: list[str] = Field(default_factory=list, description="组件类型列表")

class PluginDetail(BaseModel):
    """插件详细信息。"""
    plugin_name: str
    plugin_description: str
    plugin_version: str
    is_loaded: bool
    has_config: bool
    plugin_path: str = Field(..., description="插件路径")
    manifest: dict[str, Any] = Field(..., description="插件清单")
    components: list[PluginComponentInfo] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
```

---

## 7. 实现路线图

### 7.1 后端实现（优先级）

#### Phase 1: Manager 层（核心逻辑）
**文件**: `Neo-MoFox-Webui/Plugin/managers/plugin_manager.py`

```python
class PluginWebManager:
    """插件管理器（WebUI 专用）。"""
    
    async def list_plugins(self) -> list[PluginSummary]:
        """获取插件列表。"""
        # 调用 plugin_api.list_loaded_plugins()
        # 调用 config_api.get_loaded_plugins() 检查配置
        # 提取组件信息
        
    async def get_plugin_detail(self, plugin_name: str) -> PluginDetail:
        """获取插件详情。"""
        # 调用 plugin_api.get_plugin()
        # 调用 plugin_api.get_manifest()
        # 提取组件详情
        
    async def reload_plugin(self, plugin_name: str) -> bool:
        """重载插件。"""
        # 调用 plugin_api.reload_plugin()
        
    async def get_plugin_components(
        self, 
        plugin_name: str,
        component_type: str | None = None
    ) -> list[PluginComponentInfo]:
        """获取插件组件列表。"""
        # 调用 registry.get_by_plugin()
        # 筛选组件类型
```

#### Phase 2: Router 层（API 端点）
**文件**: `Neo-MoFox-Webui/Plugin/components/router/plugin_router.py`

```python
class PluginRouter(BaseRouter):
    """插件管理路由。"""
    
    router_name: str = "plugin"
    custom_route_path: str = "/api/plugin"
    cors_origins: list[str] = ["*"]
    
    def register_endpoints(self) -> None:
        @self.app.get("/list", response_model=BaseResponse[list[PluginSummary]])
        async def list_plugins(): ...
        
        @self.app.get("/{plugin_name}", response_model=BaseResponse[PluginDetail])
        async def get_plugin_detail(plugin_name: str): ...
        
        @self.app.post("/{plugin_name}/reload", response_model=BaseResponse[dict])
        async def reload_plugin(plugin_name: str): ...
        
        @self.app.get("/{plugin_name}/components", response_model=BaseResponse[list[PluginComponentInfo]])
        async def get_plugin_components(plugin_name: str, component_type: str | None = None): ...
```

#### Phase 3: 数据模型（Pydantic）
**文件**: `Neo-MoFox-Webui/Plugin/utils/plugin_types.py`

定义上述 Pydantic 模型。

### 7.2 前端实现

#### Phase 1: API 层
**文件**: `frontend/src/api/modules/plugin.ts`

```typescript
import http from '../base'
import type { PluginSummary, PluginDetail, PluginComponentInfo } from '../types/plugin'

/**
 * 获取插件列表
 */
export function listPlugins(): Promise<PluginSummary[]> {
  return http.get('/api/plugin/list')
}

/**
 * 获取插件详情
 */
export function getPluginDetail(pluginName: string): Promise<PluginDetail> {
  return http.get(`/api/plugin/${pluginName}`)
}

/**
 * 重载插件
 */
export function reloadPlugin(pluginName: string): Promise<any> {
  return http.post(`/api/plugin/${pluginName}/reload`)
}

/**
 * 获取插件组件列表
 */
export function getPluginComponents(
  pluginName: string,
  componentType?: string
): Promise<PluginComponentInfo[]> {
  const params = componentType ? `?component_type=${componentType}` : ''
  return http.get(`/api/plugin/${pluginName}/components${params}`)
}
```

#### Phase 2: 类型定义
**文件**: `frontend/src/api/types/plugin.ts`

```typescript
export interface PluginSummary {
  plugin_name: string
  plugin_description: string
  plugin_version: string
  is_loaded: boolean
  has_config: boolean
  component_count: number
  component_types: string[]
}

export interface PluginDetail extends PluginSummary {
  plugin_path: string
  manifest: Record<string, any>
  components: PluginComponentInfo[]
  dependencies: string[]
}

export interface PluginComponentInfo {
  signature: string
  component_type: string
  component_name: string
  description: string
  status: 'active' | 'inactive' | 'error'
  extra?: Record<string, any>
}
```

#### Phase 3: 页面实现
**文件**: `frontend/src/views/plugins/PluginManagerView.vue`

**功能需求**:
1. 插件列表展示（表格/卡片）
2. 插件详情查看（对话框）
3. 插件重载按钮
4. 配置跳转按钮
5. 组件列表展示（可折叠）
6. 组件类型筛选

---

## 8. 关键注意事项

### 8.1 API 调用约定
1. ✅ **所有组件查询优先使用专用 API**（如 `action_api`、`router_api`）
2. ✅ **签名格式统一**: `plugin_name:component_type:component_name`
3. ✅ **异步操作**: 加载/卸载/重载都是异步函数，需要 `await`
4. ⚠️ **插件实例**: `get_plugin()` 返回的是插件实例，不是类

### 8.2 组件状态管理
- **Action/Agent**: 每次聊天动态创建，无持久状态
- **Adapter/Router**: 插件加载时启动，有持久状态
- **Service**: 单例模式，全局唯一实例
- **Command/EventHandler**: 注册后常驻

### 8.3 配置管理集成
- 使用 `config_api.get_loaded_plugins()` 获取有配置的插件列表
- 配置跳转使用路由参数：`/settings/plugin/:pluginName`
- 前端通过 `getPluginConfigSchema()` 获取配置 Schema

### 8.4 权限与安全
- 所有写操作路由必须添加 `VerifiedDep` 依赖
- 插件加载/卸载/重载属于敏感操作，需要最高权限
- 前端需要处理 401/403 错误

---

## 9. 参考资源

### 9.1 核心文档
- **架构设计**: `Neo-MoFox/MoFox 重构指导总览.md`
- **WebUI 设计**: `Neo-MoFox-Webui/docs/设计文档.md`
- **配置管理**: `Neo-MoFox-Webui/docs/配置管理模块实现总结.md`

### 9.2 代码参考
- **插件 API**: `Neo-MoFox/src/app/plugin_system/api/`
- **组件基类**: `Neo-MoFox/src/core/components/base/`
- **WebUI 路由**: `Neo-MoFox-Webui/Plugin/components/router/`

### 9.3 类型定义
- **ComponentType**: `Neo-MoFox/src/core/components/types.py`
- **EventType**: `Neo-MoFox/src/core/components/types.py`
- **配置类型**: `Neo-MoFox-Webui/Plugin/utils/config_types.py`

---

## 10. 下一步行动

### 立即可做
1. ✅ 创建 `plugin_types.py` - 定义 Pydantic 模型
2. ✅ 创建 `PluginWebManager` - 实现业务逻辑
3. ✅ 创建 `PluginRouter` - 实现 API 端点
4. ✅ 注册路由到 `WebuiPlugin`

### 前端对接
5. ✅ 创建 TypeScript 类型定义
6. ✅ 创建 API 调用函数
7. ✅ 实现插件管理页面
8. ✅ 实现配置跳转逻辑

### 测试验证
9. 📋 测试插件列表 API
10. 📋 测试插件详情 API
11. 📋 测试插件重载功能
12. 📋 测试组件查询功能

---

**报告完成时间**: 2026-05-04  
**编写者**: GitHub Copilot  
**版本**: v1.0
