# Neo-MoFox-Webui 后端安装与使用指南

## 快速开始

### 1. 安装插件到 Neo-MoFox

有两种方式将后端插件安装到 Neo-MoFox：

#### 方式一：复制目录（推荐开发环境）

```bash
# 进入 Neo-MoFox 项目根目录
cd /path/to/Neo-MoFox

# 复制插件目录
cp -r /path/to/Neo-MoFox-Webui/Plugin plugins/webui
```

#### 方式二：创建符号链接（推荐生产环境）

**Windows（需要管理员权限）：**
```powershell
# 进入 Neo-MoFox 项目根目录
cd E:\delveoper\mmc010\Neo-MoFox

# 创建符号链接
mklink /D plugins\webui E:\delveoper\mmc010\Neo-MoFox-Webui\Plugin
```

**Linux/macOS：**
```bash
# 进入 Neo-MoFox 项目根目录
cd /path/to/Neo-MoFox

# 创建符号链接
ln -s /path/to/Neo-MoFox-Webui/Plugin plugins/webui
```

### 2. 启动 Neo-MoFox

```bash
cd /path/to/Neo-MoFox
uv run main.py
```

插件会自动加载，你应该能看到类似以下的日志：

```
[INFO] WebUI 插件 v1.0.0 已加载
[INFO] API 路径: /api/webui
[INFO] WebUI Router 已启动
```

### 3. 测试 API

打开浏览器或使用 curl 测试：

```bash
# 健康检查
curl http://localhost:8000/api/webui/health

# 获取设置
curl http://localhost:8000/api/webui/settings

# 更新设置
curl -X POST http://localhost:8000/api/webui/settings \
  -H "Content-Type: application/json" \
  -d '{"updates": {"theme": {"mode": "dark"}}}'
```

## API 文档

### 基础路径

所有 API 的基础路径为：`/api/webui`

### 响应格式

所有接口返回统一的 JSON 格式：

```json
{
  "code": 200,
  "data": {},
  "message": "success"
}
```

- `code`: 业务状态码，200 表示成功
- `data`: 实际返回的数据
- `message`: 状态描述

### 接口列表

#### 1. 健康检查

```
GET /api/webui/health
```

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "status": "healthy"
  },
  "message": "WebUI 后端运行正常"
}
```

#### 2. 获取设置

```
GET /api/webui/settings
```

**响应示例：**
```json
{
  "code": 200,
  "data": {
    "theme": {
      "mode": "auto",
      "primary_color": "#0058bd"
    },
    "ui": {
      "language": "zh-CN",
      "font_size": "medium"
    },
    "system": {
      "auto_update": false,
      "check_update_on_startup": true
    }
  },
  "message": "获取设置成功"
}
```

#### 3. 更新设置（部分更新）

```
POST /api/webui/settings
```

**请求体：**
```json
{
  "updates": {
    "theme": {
      "mode": "dark"
    }
  }
}
```

**响应：** 返回更新后的完整设置对象

#### 4. 替换设置（完全替换）

```
PUT /api/webui/settings
```

**请求体：**
```json
{
  "settings": {
    "theme": {
      "mode": "dark",
      "primary_color": "#0058bd"
    },
    "ui": {
      "language": "zh-CN",
      "font_size": "medium"
    },
    "system": {
      "auto_update": false,
      "check_update_on_startup": true
    }
  }
}
```

**响应：** 返回保存后的设置对象

#### 5. 重置设置

```
POST /api/webui/settings/reset
```

**响应：** 返回重置后的默认设置对象

## 配置说明

### 主题设置 (theme)

- `mode`: 主题模式
  - `"light"`: 浅色模式
  - `"dark"`: 深色模式
  - `"auto"`: 自动跟随系统
- `primary_color`: 主色调，HEX 颜色值（如 `"#0058bd"`）

### 界面设置 (ui)

- `language`: 界面语言
  - `"zh-CN"`: 简体中文
  - `"en-US"`: 英语
- `font_size`: 字体大小
  - `"small"`: 小
  - `"medium"`: 中等
  - `"large"`: 大

### 系统设置 (system)

- `auto_update`: 是否自动更新（布尔值）
- `check_update_on_startup`: 启动时检查更新（布尔值）

## 数据存储

所有数据存储在以下路径：

```
Neo-MoFox/
└── data/
    └── json_storage/
        └── WebUI_data/
            └── settings.json  # 设置文件
```

## 故障排查

### 插件未加载

1. 检查插件目录是否正确：`plugins/webui/`
2. 检查 `manifest.json` 是否存在
3. 查看 Neo-MoFox 启动日志是否有错误信息

### API 访问失败

1. 确认 Neo-MoFox 已启动
2. 检查端口是否正确（默认 8000）
3. 检查 CORS 设置（开发环境允许所有来源）

### 设置保存失败

1. 检查 `data/json_storage/WebUI_data/` 目录是否有写权限
2. 查看日志文件获取详细错误信息

## 开发

### 添加新的设置项

1. 修改 `Plugin/storage/settings.py` 中的 Pydantic 模型
2. 更新默认值
3. 前端对应更新 TypeScript 类型定义

### 添加新的 API 接口

1. 在 `Plugin/components/router/webui_router.py` 的 `register_endpoints()` 方法中添加新端点
2. 如需新的业务逻辑，在 `Plugin/managers/` 中创建对应的 Manager
3. 如需新的数据存储，在 `Plugin/storage/` 中创建对应的 Storage 类

## 许可证

与 Neo-MoFox 主项目相同
