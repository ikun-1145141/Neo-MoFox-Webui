# 集成插件市场

Neo-MoFox-WebUI 1.0.17 将插件市场直接集成到 `neo-mofox-webui`。页面、市场索引、安装服务和 API 都属于同一个插件，不需要再安装 `plugin_market_webui`。

## 运行链路

```text
WebUI /plugin-market
  -> /webui/plugin-market/
  -> PluginMarketRouter
  -> PluginMarketService
  -> 官方市场 HTTPS API
```

市场只在用户打开页面或主动刷新时读取索引。搜索、分类和排序在浏览器本地完成。下载安装、SHA-256 校验、ZIP 检查和磁盘写入在线程中执行，只有可选的插件加载留在异步流程中。

## 配置

首次加载后，Neo-MoFox 会生成：

```text
config/plugins/neo-mofox-webui/config.toml
```

默认策略如下：

```toml
[market]
enabled = true
index_url = "https://39.96.71.162/api/v1/plugins"
request_timeout_seconds = 20
max_package_size_mb = 50
index_cache_seconds = 30
page_size = 50

[install]
enabled = false
allow_overwrite = false
auto_load_after_install = false
max_installs_per_10_minutes = 5
```

修改 `market.enabled` 或 `install.enabled` 后必须重启 Neo-MoFox，因为它们决定启动时注册哪些路由。

## 关闭语义

`market.enabled = false` 不只是隐藏侧栏。WebUI 插件不会把 `PluginMarketRouter` 返回给 Neo-MoFox，因此以下页面和 API 均不存在：

```text
/webui/plugin-market/
/webui/plugin-market/api/health
/webui/plugin-market/api/plugins
/webui/plugin-market/api/plugins/{plugin_id}
/webui/plugin-market/api/resolve
/webui/plugin-market/api/install
```

前端同时从认证后的 `/webui/api/webui/features` 读取功能状态，隐藏导航入口，并阻止直接进入 `/plugin-market`。后端不注册 Router 才是安全边界，前端控制只负责保持界面一致。

`install.enabled = false` 时仍可浏览市场，但不会注册 `POST /webui/plugin-market/api/install`，页面中的安装按钮显示为禁用状态。

## 安装授权

市场安装需要同时满足：

1. WebUI `X-API-Key` 认证通过。
2. `install.enabled = true`。
3. 请求提供正确的 `X-Plugin-Install-Token`。

安装授权码首次启用安装功能时自动生成：

```text
config/plugins/neo-mofox-webui/install.token
```

该文件不会通过 WebUI API 返回。不要把 WebUI API Key 当作安装授权码；后端会显式拒绝这种用法。授权失败和安装操作均写入服务端日志，并包含来源 IP、插件 ID、版本和结果。安装接口还包含并发锁、授权失败限流和十分钟安装次数限制。

## 包校验

安装器只接受市场记录中的 `.mfp` 或 `.zip`，并执行以下检查：

- 市场、版本详情、下载及每次重定向都必须使用 HTTPS 公网地址。
- 校验下载体积、SHA-256 和市场记录中的文件大小。
- 拒绝绝对路径、`..` 路径穿越和符号链接。
- 限制压缩包解压后的总大小。
- 要求唯一的根级或一级目录 `manifest.json`。
- 检查入口文件、插件 ID 和版本是否与市场记录一致。
- 拒绝覆盖目录版插件。
- 默认拒绝覆盖已有 `.mfp`，默认不在安装后立即加载代码。

## 已安装状态

市场列表会联合 WebUI 插件管理器判断本地状态，包括已加载和未加载插件：

- 未安装：安装开启时显示“安装最新版”。
- 已安装且当前已加载并有配置：显示“配置”，跳转到 `/webui/frontend/config/plugins?plugin=<plugin_id>`。
- 已安装但未加载或没有配置：显示不可点击的“已安装”。

后端安装接口也会拒绝重复安装，不能通过绕过前端按钮覆盖该判断。

## 热重载

1.0.17 保留 1.0.16 已有的热重载能力：

- Bot 配置热重载。
- Model 配置热重载。
- MCP 配置热重载。
- 插件配置热重载。
- 插件本体重载。
- WebUI 的 `auto_reload_after_save` 设置。

市场开关本身影响组件注册，因此不走热重载，修改后需要重启 Neo-MoFox。
