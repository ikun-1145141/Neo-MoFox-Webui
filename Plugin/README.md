# Neo-MoFox-Webui 后端插件

这是 Neo-MoFox-Webui 的后端插件，提供完整的 WebUI 管理界面和 HTTP API 接口。

## 🚀 快速安装

### 方法 1: 克隆预编译版本（推荐）

从 `webui-static` 分支克隆即可直接使用，无需编译前端：

```bash
# 克隆静态分支
git clone -b webui-static https://github.com/YourRepo/Neo-MoFox-Webui.git

# 将 Plugin 目录复制到 Neo-MoFox 的 plugins 目录
cp -r Neo-MoFox-Webui/Plugin /path/to/Neo-MoFox/plugins/webui
```

### 方法 2: 从源码编译

如果需要修改前端代码：

```bash
# 克隆主分支
git clone https://github.com/YourRepo/Neo-MoFox-Webui.git
cd Neo-MoFox-Webui

# 安装并编译前端
cd frontend
npm install
npm run build

# 复制编译产物到插件静态目录
cd ..
mkdir -p Plugin/static
cp -r frontend/dist/* Plugin/static/

# 复制插件到 Neo-MoFox
cp -r Plugin /path/to/Neo-MoFox/plugins/webui
```

### 方法 3: 开发模式（符号链接）

```bash
# Windows (管理员权限)
mklink /D plugins\webui \path\to\Neo-MoFox-Webui\Plugin

# Linux/macOS
ln -s /path/to/Neo-MoFox-Webui/Plugin plugins/webui
```

## 🌐 访问地址

插件启动后，可通过以下地址访问：

- **前端界面**: `http://localhost:8000/webui/frontend/`
- **API 接口**: `http://localhost:8000/api/`

## 🤖 自动部署

每次提交到主分支时，GitHub Actions 会自动：

1. ✅ 编译前端代码
2. ✅ 复制到 `Plugin/static/`
3. ✅ 推送到 `webui-static` 分支

用户只需克隆 `webui-static` 分支即可获得包含编译前端的完整插件。

## 架构

```
Plugin/
├── manifest.json          # 插件元数据
├── plugin.py             # 插件入口
├── components/           # 组件层
│   └── router/
│       └── webui_router.py  # Router 组件
├── managers/             # 管理器层
│   └── config_manager.py    # 配置管理器
├── storage/              # 存储层
│   ├── base.py              # 存储基类
│   └── settings.py          # 设置存储
└── utils/                # 工具层
    └── response.py          # 统一响应模型
```

## 开发规范

- 所有 API 返回值必须使用 `BaseResponse` 模型
- 所有存储类必须继承 `BaseStorage`
- 配置读写必须通过 `ConfigManager`
- 数据路径固定为 `data/json_storage/WebUI_data/`
