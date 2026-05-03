# Neo-MoFox-Webui 后端插件

这是 Neo-MoFox-Webui 的后端插件，提供 WebUI 的 HTTP API 接口。

## 安装

将此 `Plugin` 目录复制到 Neo-MoFox 的 `plugins/` 目录下：

```bash
# 在 Neo-MoFox 项目根目录
cp -r /path/to/Neo-MoFox-Webui/Plugin plugins/webui
```

或者创建符号链接：

```bash
# Windows (管理员权限)
mklink /D plugins\webui \path\to\Neo-MoFox-Webui\Plugin

# Linux/macOS
ln -s /path/to/Neo-MoFox-Webui/Plugin plugins/webui
```

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
