# 请求监视器开发说明

本模块必须与新版 Neo-MoFox 主程序配套部署，不能只升级 WebUI。采集、协议解析、脱敏、原始数据预算与生命周期均归主程序；WebUI 无 SDK 包装器、monkey patch、私有 `_records` 访问或重复解析。旧 `RequestInspectorHelper` 已移除。

## 接口契约

统一认证为现有 `VerifiedDep`，使用 `BaseResponse<T>` 的 `code/data/message`。新接口：

| Method | Path | data 类型 |
|---|---|---|
| GET | `/webui/api/request-inspector/records` | `InspectorRecordsSnapshot` |
| GET | `/webui/api/request-inspector/records/{record_id}` | `InspectorRecordDetail` |
| DELETE | `/webui/api/request-inspector/records` | `InspectorClearResult` |

旧 `/requests`、`/requests/{id}`、`/analytics` 不再注册，无别名、无兼容数据回退。主程序缺少新公共接口时返回可见错误，提示配套升级。

Pydantic 模型位于 `Plugin/utils/request_inspector_types.py`，前端一一对应于 `frontend/src/api/types/request-inspector.ts`。Manager 只调用 `get_inspector().snapshot()`、`get_record()`、`clear_snapshot()` 并验证边界模型，不重新组装采集业务。

列表包含 `instance_id`、`revision`、`capacity`、轻量 `records` 和当前缓冲 `stats`，不包含任何请求/响应正文。详情按需读取，携带 `instance_id` 和 `version`。不存在的记录返回 HTTP 404、`code=404`、`data=null`。清空返回 `instance_id/revision/cleared_count`，不会取消执行中的模型调用。

## 数据语义

- 仅内存最近 200 条；主程序重启记录清空、`instance_id` 改变。当前缓冲统计与历史 LLM 用量统计分离。
- `captured` 仅捕获/导入，`pending/running/streaming` 为非终态；`succeeded/failed/cancelled` 为执行终态。
- 框架重试/模型切换各占一条，使用逻辑请求 ID 和 attempt 关联。SDK 内部重试不拆分。
- `response.kind` 为 chat/embedding/rerank；实际 token 缺失显示 `—`，估算输入单独展示。
- 原始数据是 SDK JSON，不是网络抓包。非流 `raw_response`、流 `raw_events`，单条原始数据默认预算 2 MiB；超限保留已保存前缀并标记截断，标准化响应继续采集。
- 凭据在保存前脱敏；复制/导出与展示使用同一份快照。`capture_info` 显示脱敏、截断、原始/请求/元数据不可用状态。

## 前端结构与刷新

页面只负责编排和导出/复制/确认操作；业务展示拆到 `components/request-monitor`，状态和轮询在 `composables/useRequestMonitor.ts`。

与 AppShell 共用 900px 断点：桌面双栏；小于 900px 为列表→详情→返回的单屏布局，首次进入始终停在列表，自动选中或刷新不会跳入详情。返回保留筛选、列表位置及同一记录的标签、树展开与各标签滚动位置；清空、淘汰或重启失去选择时回到列表。断点切换不重建监视器、不增加轮询。手机详情采用单一纵向滚动容器，返回入口和标签保持可达；深层 JSON 仅在树容器内横向滚动。列表仅在摘要中本地筛选关键词/状态/模型，不预取所有正文。

详情为四个同级标签，默认请求体：

- **请求体**：直接展示 `params` 的结构树，保留 `messages/input/system/instructions/tools`、生成参数及 `extra_body/extra_headers/extra_query` 原有层级和未知字段。消息视图消费 `rendered.messages`；`metadata` 单独列出，不合并进请求体。
- **LLM 返回**：使用标准化 `response` 展示正文、已有推理、用量和结束原因；Embedding 显示向量数量、数组维度及按需展开的数值，Rerank 保留未知结果字段。失败/取消不会隐藏已采集的部分响应。
- **工具**：定义来自 `rendered.tools`，模型调用来自 `response.tool_calls`，已有结果来自消息中的 `tool_result`。参数字符串仅做通用 JSON 解析，不完整时保留原文，不重新解析供应商协议、不追踪真实执行。
- **原始 JSON**：可选择请求参数、SDK 响应、流事件、元数据或完整记录，支持结构/文本视图、复制和下载。

内容安全地作为文本展示，不执行模型 HTML、不自动加载媒体地址。耗时、token、逻辑 ID 和 attempt 仅在普通请求信息中显示，不做统计看板。

可见页面在上一轮请求完成 2 秒后再刷新，避免慢请求重叠。摘要版本变化时才更新选中详情，不抢选新记录。页面隐藏停止调度，恢复可见立即同步；失败保留最后成功数据、由统一 Axios 拦截器提示一次并暂停自动刷新。用户可手动刷新/继续。暂停状态下手动刷新只同步一次，不自动恢复轮询。暂停和页面隐藏会中止或作废在途读取，但不撤销正在处理的 DELETE。

清空成功才清理选择和详情；清空失败/超时保留旧快照、标记结果未确认并暂停自动刷新，因为服务端可能已清空而响应未送达。主程序重启或记录淘汰会使旧选择失效；新增记录和筛选不会抢选其他记录。较旧的 revision、version 或跨实例详情不覆盖较新的快照。

AbortSignal + 刷新代次 + 选择代次防止乱序响应覆盖、清空后复活和卸载后写状态；进程切换或记录淘汰使旧详情失效。清空、取消、卸载都必须同时清理请求和计时器。切换标签、流式刷新不会重置选中请求或滚动位置。

## 测试与本地联调

默认将两个仓库并列放置，主程序目录命名为 `Neo-MoFox`。如主程序位于其他路径，请设置环境变量 `NEO_MOFOX_ROOT` 指向其根目录；接口测试与本地 smoke server 均遵循该配置。

```shell
# WebUI 根目录，需 Python 插件依赖和相邻主程序源码
python -m unittest discover -s tests -p test_request_monitor.py -v
python -m unittest discover -s tests -p test_model_config.py -v
# frontend 目录（不增加测试框架）
node --test tests/model-test.test.mjs tests/request-monitor.test.mjs tests/request-monitor-components.test.mjs
npm run build
# 主程序根目录
python -m pytest test/kernel/llm/test_request_monitor.py test/kernel/llm/test_request_inspector.py --no-cov
```

接口测试隔离框架注册入口，使用真实主程序 inspector、真实 Manager、Pydantic、Router 和认证依赖。前端测试使用 Vue 响应式状态和受控时钟/API 验证竞态。主程序测试在原生适配器中使用 SDK-shaped fake，不需要真实密钥。

生产构建后，可运行 `python tests/request_monitor_smoke_server.py`：仅在 `127.0.0.1:9188` 启动开发夹具，使用真实五类原生适配器/缓冲/API、受控 SDK 数据和本地测试登录。打开 `/webui/frontend/request-inspector`，输入任意非空测试密码。此脚本不属于主程序运行时，不读取实际凭据，不连接真实供应商。请勿对外部署。


## 结构树、复制与性能边界

- `InspectorJsonTree` 使用迭代式可见节点遍历，不递归展开整个输入。对象和数组每页 100 个子节点，可以前后翻页；单视图最多 1500 行，超限明确提示折叠部分分支。
- 节点显示字段名/数组索引、JSON 类型和长度；空字符串、空容器、null、0、false 与 `[unavailable]` 不混为一谈。
- 字段路径使用 JSON Pointer 转义（`~` → `~0`、`/` → `~1`），仅访问对象自身属性，不通过 eval 或原型解析路径。
- 长字符串先预览，响应/原始 JSON 文本每次展开 4096 个字符。复制子树、完整文本及下载使用完整安全数据，不使用显示截短后的文本。
- 当前记录最多保留四个已访问面板。非激活面板保留 DOM、展开和滚动位置，但不接收流式更新；切换回来使用最新详情。切换记录、清空和重启释放旧面板。
- 树展开状态按当前记录/数据范围及路径管理，版本更新保留有效路径，移除失效路径，缓存有界。不将请求正文写入浏览器持久化存储。
- `raw_bytes` 是原始 SDK JSON 的保存量，原始响应和事件共用默认 2 MiB 预算；不是网络流量、完整记录大小或总进程内存限制。请求参数及标准化输出仍可能很大。

## 安全与错误处理

- 脱敏由主程序完成，WebUI 不另取 SDK 对象。`capture_info.redacted=true` 才显示发生过敏感字段替换；false 不是数据不敏感的保证。普通用户消息和业务内容可能仍包含隐私。
- 截断、请求/原始/元数据不可用按实际标记展示。完整记录下载保留 `capture_info`、instance_id、version、状态及错误信息；范围下载仅导出所选字段，完整性说明仍保留在页面。
- Manager 检查公共接口可用性，不回退到旧 helper 或私有 `_records`。Router 的错误日志仅记录固定操作名/错误类别，不输出异常正文、Pydantic input_value、动态字段路径或 traceback。
- Axios 仍负责全局错误提示。详情 404 通过显式 `handledErrorStatuses: [404]` 交由页面内“已清空或淘汰”状态处理，不重复弹 Toast；该配置不得屏蔽 401/403。主动取消读取不是网络失败。

## 离线验证与手动验收

后端测试覆盖认证、契约、未知字段、三种响应结果、主程序不兼容以及异常泄密；前端使用现有 Node `node:test`、真实 Vue SFC/内存渲染器和受控传输/时钟，不增加测试框架。

Smoke server 中五类原生适配器使用受控 SDK；另外标为 `UI fixture / ...` 的展示样例通过公共采集接口构造，用于大数组、特殊键、工具结果、不完整参数、取消、重试、截断及不可用状态。这些 UI 样例不宣称是真实供应商调用。测试设置只保存在内存中。

手动验收建议：桌面/窄屏、深浅主题、中英文；展开结构及数组翻页；切标签和刷新保留选择/展开/滚动；查看工具定义/调用/已有结果；复制与下载；截断/不可用提示；暂停恢复和清空确认。

本模块要求主程序原生请求监视器公共契约。当前开发联调使用主程序提交 `df0fe713b27142f9afeb96355e9e3f362b46f6d4`，不假定相关上游 PR 已合并。

### 手机适配验收

离线 smoke server 含 30 条标为 `UI fixture / mobile` 的长名称、长消息、29 个工具、多层 JSON、大数组和错误样例。设置 `NEO_MOFOX_ROOT` 指向配套主程序源码，生产构建后运行此服务，不需要真实模型或机器人。

检查 320/375/390/430/768/899/900/1280px、横竖屏及深浅主题；确认列表/详情到底可达、无整页横向溢出、工具类型和箭头对齐、触屏复制操作常驻且按钮至少 44px、默认请求消息和 JSON 文本不变。视口模拟与真实 iOS/Android 测试应分开报告。


### 空正文与长字符串展示回归

- Chat 正文为 null、空字符串或纯空白时不再显示空白文本框；只有工具调用时明确提示没有文本正文，在 LLM 返回面板展示已采集的工具调用结构，并可切换到工具标签查看参数。
- 标准化正文有内容时仍原样展示；流式正文到达后自动更新，错误或取消不隐藏已有内容。不从工具参数猜测或拼造普通正文，不重新解析 SDK 协议。
- 结构树和工具共用的长字符串展开改为独立多行文本区域，每次增加 4096 个字符；未显示完时保留明确计数和继续展开入口，全部展开后不再人为添加省略号。短字符串直接换行，避免 CSS 单行省略隐藏内容。
- 展开状态随同一记录更新保留，切换记录重置；复制仍使用完整安全数据。覆盖空正文、工具调用、流更新、多页字符串、工具定义和调用参数的组件回归，浏览器验证独立于真实供应商调用。

### 返回消息视图

LLM 返回与请求体使用相同的消息卡片和结构树切换布局，默认返回消息。正文、推理和工具调用分别作为消息内容展示；工具调用没有普通正文时直接展示调用名称、原参数和调用 ID，不把工具参数伪造成正文。结构树保留完整标准化 response，复制按钮复制完整安全响应。切换视图保留消息展开和树状态，同一记录流更新不重置视图。
