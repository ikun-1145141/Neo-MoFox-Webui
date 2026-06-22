📋 Neo-MoFox WebUI 更新公告

🆕 新功能

【插件 UI 扩展系统】
• 新增插件 UI 扩展子系统，支持插件通过 XML 声明式方式自定义界面
• 后端实现：新增 PluginUI 路由（发现、Schema、静态资源）、PluginUI Service、PluginUI Manager，以及完整的常量/路径/类型/验证器工具链
• 前端实现：新增 API 模块、TypeScript 类型定义、插件导航列表、页面容器、响应式变量 Store、PluginUIView 视图及动态路由
• 新增 XML 渲染器，支持 XML 字符串转 Vue VNode 树，处理定义、属性和子节点
• 新增管道执行器（Pipe Executor），支持 on-click 等事件中的链式命令执行（如 api:saveUser() | notify:'保存成功' | refresh:usersTable）
• 新增占位符解析器（Placeholder Parser），支持表达式中的嵌套花括号解析
• 新增表达式求值器（Expression Evaluator）
• 新增 API 模板引擎，支持第三方 API 调用模板
• 内置 20+ XML UI 组件：SysButton、SysCard、SysTable、SysForm、SysInput、SysSelect、SysTabs、SysDialog、SysChart、SysIcon 等
• 新增 demo_ui_plugin 示例插件，展示 XML UI 的完整用法
• 新增 XSD Schema（plugin_ui_v3_1.xsd），为插件 UI 的 XML 声明提供结构校验

【移动端适配】
• 更新移动端媒体查询断点，增强移动端导航体验
• PluginUIView 增加移动端变体支持，适配手机端布局

【其他】
• 新增前端实现计划文档，详细规划插件扩展系统的前端架构与开发里程碑

🐛 Bug 修复

• 修复 Chat Router 和 Log Router 中 WebSocket 认证逻辑重复的问题，统一使用 verify_websocket_token 函数，消除冗余代码
• 将配置管理中的 schema 字段重命名为 sections，统一前后端数据结构
