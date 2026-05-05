# Neo-MoFox-WebUI

<div align="center">

**现代化、类型安全的 Neo-MoFox 机器人 Web 管理界面**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.x-blue.svg)](https://www.typescriptlang.org/)

</div>

---

## 📖 项目简介

Neo-MoFox-WebUI 是 Neo-MoFox 聊天机器人框架的官方 Web 管理界面，采用前后端分离架构，提供直观、优雅的可视化配置与监控体验。项目遵循 Material Design 3 设计规范，以**"策展画布"（The Curated Canvas）**为设计理念，通过留白、层次与克制的用色，打造高端、现代的管理界面。

### ✨ 设计亮点

- **无边框设计语言**：摒弃传统边框，通过背景色差异与环境光阴影构建视觉层次
- **动态主题系统**：支持从壁纸自动提取 Material Design 3 色板，实现个性化主题
- **响应式架构**：100% 响应式数据流，所有状态变更通过 Vue 响应系统驱动
- **类型安全优先**：前后端全链路类型约束，TypeScript 与 Pydantic 模型 1:1 对应

---

## 🎯 核心特性

### 已完成功能

#### 🔐 认证系统
- API Key 认证机制
- 基于 Token 的会话管理
- 登录/登出流程

#### ⚙️ 配置管理
- 统一的配置读写接口
- 实时配置同步与持久化
- 插件配置独立管理
- 核心配置可视化编辑

#### 🎨 主题与壁纸
- Material Design 3 动态取色
- 支持自定义主题色
- 静态/动态壁纸上传与预览
- 壁纸模糊度与透明度调节
- 深色/浅色主题自动切换

#### 📊 系统监控
- 系统状态实时查看
- 资源使用情况监控
- 仪表板数据可视化

#### 🏗️ 基础架构
- 统一的前后端通讯协议
- 全局错误处理与 Toast 提示
- WebSocket 长连接支持（日志流推送）
- 模块化的组件与路由系统

---

## 🛠️ 技术栈

### 后端
- **Python 3.10+**：核心语言
- **FastAPI**：高性能 HTTP 框架
- **Pydantic**：数据验证与类型约束
- **Neo-MoFox Plugin System**：插件系统集成

### 前端
- **Vue 3**：渐进式前端框架
- **TypeScript**：类型安全开发
- **Vite**：下一代前端构建工具
- **Material Design 3**：设计系统
- **MD3U**：MD3 动态取色库

---

## 📁 项目结构

```
Neo-MoFox-Webui/
├── Plugin/                          # 后端插件
│   ├── manifest.json                # 插件元数据
│   ├── plugin.py                    # 插件入口
│   ├── __init__.py                  # 包初始化
│   ├── components/                  # 组件层
│   │   └── router/                  # FastAPI 路由组件
│   │       ├── __init__.py
│   │       ├── auth_router.py       # 认证路由
│   │       ├── webui_router.py      # WebUI 核心路由
│   │       ├── dashboard_router.py  # 仪表板路由
│   │       ├── system_router.py     # 系统信息路由
│   │       ├── wallpaper_router.py  # 壁纸管理路由
│   │       └── config/              # 配置路由模块
│   │           ├── __init__.py
│   │           ├── bot_config_router.py     # 机器人配置路由
│   │           ├── main_config_router.py    # 主配置路由
│   │           ├── model_config_router.py   # 模型配置路由
│   │           └── plugin_config_router.py  # 插件配置路由
│   ├── managers/                    # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_manager.py          # 认证管理器
│   │   ├── config_manager.py        # 配置管理器
│   │   ├── dashboard_manager.py     # 仪表板管理器
│   │   ├── system_manager.py        # 系统管理器
│   │   ├── wallpaper_manager.py     # 壁纸管理器
│   │   └── config/                  # 配置管理模块
│   │       ├── __init__.py
│   │       ├── bot_config_manager.py    # 机器人配置管理
│   │       ├── main_config_manager.py   # 主配置管理
│   │       ├── model_config_manager.py  # 模型配置管理
│   │       └── plugin_config_manager.py # 插件配置管理
│   ├── storage/                     # 数据持久化层
│   │   ├── __init__.py
│   │   ├── base.py                  # 存储基类
│   │   └── settings.py              # 设置存储
│   └── utils/                       # 工具层
│       ├── __init__.py
│       ├── config_parser.py         # 配置解析工具
│       ├── config_types.py          # 配置类型定义
│       ├── llm_metrics.py           # LLM 指标工具
│       └── response.py              # 统一响应模型
│
├── frontend/                        # 前端项目
│   ├── public/                      # 静态资源
│   │   ├── favicon.svg
│   │   ├── icons.svg                # Material 图标集合
│   │   └── material-symbols/        # Material Symbols 字体
│   ├── src/
│   │   ├── App.vue                  # 根组件
│   │   ├── main.ts                  # 入口文件
│   │   ├── api/                     # API 调用层
│   │   │   ├── base.ts              # Axios 封装与拦截器
│   │   │   ├── config.ts            # API 配置
│   │   │   ├── types/               # TypeScript 类型定义
│   │   │   │   ├── base.ts          # 基础类型
│   │   │   │   ├── auth.ts          # 认证类型
│   │   │   │   ├── config.ts        # 配置类型
│   │   │   │   ├── dashboard.ts     # 仪表板类型
│   │   │   │   ├── settings.ts      # 设置类型
│   │   │   │   ├── system.ts        # 系统类型
│   │   │   │   └── wallpaper.ts     # 壁纸类型
│   │   │   └── modules/             # 按功能划分的 API 模块
│   │   │       ├── auth.ts          # 认证 API
│   │   │       ├── config.ts        # 配置 API
│   │   │       ├── dashboard.ts     # 仪表板 API
│   │   │       ├── settings.ts      # 设置 API
│   │   │       ├── system.ts        # 系统 API
│   │   │       └── wallpaper.ts     # 壁纸 API
│   │   ├── views/                   # 页面视图
│   │   │   ├── LoginView.vue        # 登录页
│   │   │   ├── HomeView.vue         # 主页
│   │   │   ├── ConfigView.vue       # 配置页
│   │   │   ├── PluginConfigView.vue # 插件配置页
│   │   │   ├── SettingsView.vue     # 设置页
│   │   │   └── settings/            # 设置子页面
│   │   │       ├── GeneralView.vue  # 通用设置
│   │   │       ├── ThemeView.vue    # 主题设置
│   │   │       └── DataView.vue     # 数据设置
│   │   ├── components/              # 可复用组件
│   │   │   ├── common/              # 通用组件
│   │   │   │   ├── AppShell.vue     # 应用外壳
│   │   │   │   ├── Icon.vue         # 图标组件
│   │   │   │   ├── MdSelect.vue     # Material 下拉选择
│   │   │   │   ├── PageHeader.vue   # 页面标题
│   │   │   │   ├── ToastManager.vue # Toast 提示管理
│   │   │   │   └── DialogManager.vue # 对话框管理
│   │   │   ├── config/              # 配置相关组件
│   │   │   │   ├── ConfigEditor.vue     # 配置编辑器
│   │   │   │   ├── FormEditor.vue       # 表单编辑器
│   │   │   │   ├── TomlEditor.vue       # TOML 编辑器
│   │   │   │   ├── ModelConfigEditor.vue # 模型配置编辑器
│   │   │   │   ├── ModelEditDialog.vue  # 模型编辑对话框
│   │   │   │   └── fields/              # 表单字段组件
│   │   │   │       ├── BooleanField.vue  # 布尔字段
│   │   │   │       ├── TextField.vue     # 文本字段
│   │   │   │       ├── NumberField.vue   # 数字字段
│   │   │   │       ├── SelectField.vue   # 选择字段
│   │   │   │       ├── TextareaField.vue # 多行文本字段
│   │   │   │       └── ListField.vue     # 列表字段
│   │   │   └── dashboard/           # 仪表板组件
│   │   │       ├── StatCard.vue         # 统计卡片
│   │   │       ├── DataPanel.vue        # 数据面板
│   │   │       ├── MessageTrendChart.vue    # 消息趋势图
│   │   │       ├── PlatformStatsChart.vue   # 平台统计图
│   │   │       └── index.ts             # 组件导出
│   │   ├── router/                  # Vue Router 配置
│   │   │   └── index.ts             # 路由定义
│   │   ├── composables/             # Vue 组合式函数
│   │   │   └── useDropdownManager.ts # 下拉菜单管理
│   │   ├── utils/                   # 工具函数
│   │   │   ├── md3theme.ts          # Material Design 3 主题
│   │   │   ├── toast.ts             # Toast 提示工具
│   │   │   ├── dialog.ts            # 对话框工具
│   │   │   └── toml-linter.ts       # TOML 语法检查
│   │   └── styles/                  # 样式文件
│   │       └── md3-variables.css    # Material Design 3 变量
│   ├── index.html                   # HTML 模板
│   ├── vite.config.ts               # Vite 配置
│   ├── package.json                 # 依赖管理
│   ├── tsconfig.json                # TypeScript 配置
│   ├── tsconfig.app.json            # 应用 TS 配置
│   └── tsconfig.node.json           # Node TS 配置
│
├── docs/                            # 文档
│   ├── DESIGN.md                    # 技术设计文档
│   ├── 设计文档.md                  # 设计文档（中文）
│   ├── backend-config-management-design.md  # 后端配置管理设计
│   └── 配置管理模块实现总结.md      # 配置管理实现总结
│
├── INSTALL.md                       # 安装指南
├── LICENSE                          # 许可证
├── README.md                        # 项目说明
└── .gitignore                       # Git 忽略文件
```

---

## 🚀 快速开始

### ⭐ 方式一：快速部署（推荐，生产环境）

**无需 Node.js/npm，无需构建，开箱即用！**

#### 1. 克隆预构建版本

```bash
# 进入 Neo-MoFox 的插件目录
cd /path/to/Neo-MoFox/plugins

# 克隆 webui-static 分支（包含预构建的前端）
git clone -b webui-static https://github.com/ikun-1145141/Neo-MoFox-Webui webui
```

#### 2. 配置 Neo-MoFox

编辑 `config/core.toml`：

```toml
[http_router]
enable_http_router = true
http_router_host = "127.0.0.1"
http_router_port = 8005
api_keys = ["your_secure_api_key_here"]
```

#### 3. 启动并访问

```bash
# 启动 Neo-MoFox
cd /path/to/Neo-MoFox
uv run main.py

# 在浏览器打开 http://localhost:8005
```

---

### 🛠️ 方式二：开发环境部署

**适用于需要修改前端代码的开发者。**

#### 前置要求

- Python 3.10+
- Node.js 18+ / npm 9+
- Neo-MoFox 核心框架

#### 1. 克隆源码

```bash
git clone https://github.com/ikun-1145141/Neo-MoFox-Webui
cd Neo-MoFox-Webui
```

#### 2. 安装插件

```bash
# 复制 Plugin 目录到 Neo-MoFox
cp -r Plugin /path/to/Neo-MoFox/plugins/webui
```

#### 3. 配置核心框架

编辑 `config/core.toml`（同方式一）

#### 4. 启动后端

```bash
cd /path/to/Neo-MoFox
uv run main.py
```

后端将在 `http://127.0.0.1:8005` 启动。

#### 5. 启动前端开发服务器

```bash
cd Neo-MoFox-Webui/frontend
npm install
npm run dev
```

前端将在 `http://localhost:9178` 启动，API 请求将自动代理到后端。

---

## 📐 开发规范

### 后端规范

- ✅ **强制使用 Pydantic**：所有 API 返回值与请求体必须使用 Pydantic 模型
- ✅ **统一响应结构**：所有接口继承 `BaseResponse[T]`
- ✅ **存储路径规范**：所有持久化数据存储在 `data/WebUI_data/`
- ✅ **类型注解**：所有函数必须标注完整的类型提示

### 前端规范

- ✅ **类型一致性**：`api/types/` 中的类型定义必须与后端 Pydantic 模型一致
- ✅ **100% 响应式**：所有状态使用 `ref`/`reactive` 包装
- ✅ **禁止直接操作 DOM**：所有 UI 变更通过数据驱动
- ✅ **图标规范**：统一使用本地化的 Material Design 3 Icons

### 通讯协议

所有 API 响应遵循统一格式：

```typescript
interface BaseResponse<T> {
  code: number       // 200 为成功，其他为错误码
  data: T            // 实际业务数据
  message: string    // 可读的状态描述
}
```

---

## 📚 文档

- [技术设计文档](docs/设计文档.md)- 完整的架构设计与开发规范
- [安装指南](./INSTALL.md) - 详细的部署与配置说明

---

## 📄 许可证

本项目采用 [GNU Affero General Public License v3.0](LICENSE) 开源协议。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！在贡献代码前，请阅读 [技术设计文档](docs/设计文档.md) 了解项目规范。

---

<div align="center">

**用现代化的界面，驾驭强大的机器人框架**

Made with ❤️ by MoFox Team

</div>

