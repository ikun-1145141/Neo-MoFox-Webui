# Neo-MoFox WebUI 插件前端扩展系统设计文档

**版本**: 2.0.0  
**作者**: MoFox Team  
**日期**: 2026-05-04  
**状态**: 设计完成 - 待评审

---

## 📋 目录

1. [系统概述](#1-系统概述)
2. [核心设计理念](#2-核心设计理念)
3. [插件注册流程](#3-插件注册流程)
4. [XML Schema 规范](#4-xml-schema-规范)
5. [表单与数据校验](#5-表单与数据校验)
6. [后端交互机制](#6-后端交互机制)
7. [前端渲染架构](#7-前端渲染架构)
8. [安全与权限](#8-安全与权限)
9. [完整示例](#9-完整示例)
10. [开发指南](#10-开发指南)

---

## 1. 系统概述

### 1.1 设计目标

为 Neo-MoFox 插件提供**低代码前端扩展能力**，允许插件开发者通过简洁的 **XML** 描述文件，动态向 WebUI 注册自定义页面，实现：

- ✅ **零前端代码**：无需编写 Vue 组件即可创建完整页面
- ✅ **动态注册**：插件运行时通过 WebUI Service API 注册页面
- ✅ **声明式交互**：在 XML 中直接声明 API 端点、请求方法、数据格式
- ✅ **完整表单支持**：包含字段校验（required、类型、正则）和数据序列化
- ✅ **Material Design 3**：自动渲染为符合 MD3 规范的界面

### 1.2 适用场景

| 场景 | 复杂度 | 推荐方案 |
|------|--------|----------|
| 简单配置表单 | ⭐ | 使用现有 ConfigBase 系统（无需本方案）|
| 数据列表与 CRUD | ⭐⭐ | 使用本 XML Schema 系统 |
| 统计仪表盘 | ⭐⭐⭐ | 使用本系统 + 自定义图表组件 |
| 复杂交互逻辑 | ⭐⭐⭐⭐ | 直接编写 Vue 组件（不适用本方案）|

### 1.3 架构分层

```
┌─────────────────────────────────────────────────────┐
│              插件开发者层                            │
│  调用 WebUI Service.register_ui_page(xml_string)    │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────┐
│              WebUI Service 层                       │
│  - 接收 XML 注册请求                                 │
│  - 校验 XML 合法性（XSD 验证）                       │
│  - 存储页面元数据（内存 + 可选持久化）                │
│  - 提供 /api/ui/discovery 聚合端点                  │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────┐
│              前端渲染层                              │
│  - 获取已注册页面列表                                │
│  - 解析 XML → 组件树                                │
│  - 渲染预设组件（15+ MD3 组件）                      │
│  - 执行表单校验与 API 调用                           │
└─────────────────────────────────────────────────────┘
```

---

## 2. 核心设计理念

### 2.1 动态注册 vs 静态声明

**旧方案（已废弃）**：插件在 Service 中实现 `expose_ui_pages()` 方法，返回硬编码的 XML 文件路径。

**新方案（本设计）**：插件在初始化时（或任意时刻）调用 WebUI Service 的 API，传入 XML 字符串动态注册页面。

**优势**：
- 插件可以根据运行时状态（配置、数据库数据）生成 XML
- 无需在插件目录中存放 XML 文件
- 支持热更新（重新调用 API 即可更新页面）

### 2.2 XML 驱动的声明式 UI

插件开发者通过 **语义化 XML 标签** 描述页面结构，前端自动渲染为对应的 Vue 组件。

**核心原则**：
1. **标签即组件**：`<input-field>` → `UIInputField.vue`
2. **属性即配置**：`<input-field type="email" required="true" />`
3. **嵌套即布局**：`<container layout="vertical">` 包含子组件
4. **绑定即数据流**：`data-bind="form.username"` 自动双向绑定
5. **端点即交互**：`api-endpoint="/api/users"` 自动发起请求

### 2.3 表单与数据流

表单提交遵循以下流程：

```
用户填写表单
    ↓
前端执行校验（required、类型、正则）
    ↓
构建请求体（按 XML 声明的结构）
    ↓
发送 HTTP 请求（POST/PUT/DELETE）
    ↓
处理响应（成功/失败回调）
    ↓
更新 UI 状态（刷新列表、关闭对话框等）
```

---

## 3. 插件注册流程

### 3.1 插件侧调用

**时机**：插件的 `on_plugin_loaded()` 生命周期钩子中。

**步骤**：

1. **获取 WebUI Service 实例**

```python
from src.core.managers import get_service_manager

webui_service = get_service_manager().get_service("webui:service:webui_ui")
if not webui_service:
    logger.warning("WebUI 插件未加载，无法注册前端页面")
    return
```

2. **构建 XML 字符串**

```python
# 方式一：硬编码 XML
page_xml = """
<ui-page schema-version="1.0">
  <metadata>
    <title>用户管理</title>
    <icon>person</icon>
  </metadata>
  <layout>
    <container layout="vertical">
      <input-field id="username" label="用户名" required="true" />
    </container>
  </layout>
</ui-page>
"""

# 方式二：动态生成 XML（根据配置）
from xml.etree.ElementTree import Element, SubElement, tostring

root = Element("ui-page", {"schema-version": "1.0"})
metadata = SubElement(root, "metadata")
SubElement(metadata, "title").text = "用户管理"
# ... 构建完整 XML 树
page_xml = tostring(root, encoding="unicode")
```

3. **调用注册 API**

```python
success = await webui_service.register_ui_page(
    plugin_name="my_plugin",
    page_id="user-management",
    page_xml=page_xml,
    order=100,  # 排序权重（可选）
)

if success:
    logger.info("前端页面注册成功: user-management")
else:
    logger.error("前端页面注册失败")
```

### 3.2 WebUI Service 处理逻辑

**职责**：
1. **XML 校验**：使用 XSD Schema 验证 XML 合法性
2. **元数据提取**：解析 `<metadata>` 节点，获取标题、图标、描述等
3. **存储注册信息**：将 XML 内容和元数据存入内存字典
4. **去重处理**：如果同一 `plugin_name:page_id` 已存在，覆盖旧数据
5. **触发前端更新**：可选地通过 WebSocket 通知前端刷新页面列表

**数据结构**：

```python
# WebUI Service 内部存储
_registered_pages: dict[str, dict[str, PageRegistration]] = {}
# 结构：{"plugin_name": {"page_id": PageRegistration}}

class PageRegistration:
    plugin_name: str
    page_id: str
    page_xml: str          # 完整 XML 内容
    title: str
    description: str | None
    icon: str | None
    order: int             # 排序权重
    registered_at: float   # 注册时间戳
```

### 3.3 前端发现流程

1. **用户访问 `/plugins` 页面**
2. **前端调用 `/api/ui/discovery`**
3. **WebUI Service 返回所有已注册页面的元数据**
4. **前端渲染"插件页面" Tab，左侧显示页面列表**
5. **用户点击某个页面**
6. **前端调用 `/api/ui/schema/{plugin}/{page_id}`，获取完整 XML**
7. **解析 XML → 组件树 → 渲染**

---

## 4. XML Schema 规范

### 4.1 根节点

```xml
<ui-page schema-version="1.0" xmlns="https://mofox.studio/ui-schema/v1">
  <metadata>...</metadata>
  <layout>...</layout>
</ui-page>
```

**属性**：
- `schema-version`：**必需**，当前为 `"1.0"`
- `xmlns`：命名空间，用于 XSD 验证

### 4.2 元数据节点 `<metadata>`

```xml
<metadata>
  <title>用户管理</title>
  <description>管理系统用户的增删改查</description>
  <icon>person</icon>
  <api-base>/api/my-plugin</api-base>
</metadata>
```

**字段说明**：
- `<title>`：**必需**，页面标题，显示在侧边栏和顶部
- `<description>`：可选，页面描述，显示在页面顶部
- `<icon>`：可选，Material Symbols 图标名称（如 `person`、`analytics`）
- `<api-base>`：可选，API 端点前缀，所有相对路径 API 会自动拼接此前缀

### 4.3 布局容器 `<container>`

```xml
<container layout="vertical" spacing="16" padding="24">
  <!-- 子组件 -->
</container>
```

**属性**：
- `layout`：布局方式
  - `vertical`：垂直排列（默认）
  - `horizontal`：水平排列
  - `grid`：网格布局
- `spacing`：子组件间距（px）
- `padding`：容器内边距（px）
- `align`：对齐方式（`start` | `center` | `end`）
- `justify`：主轴对齐（`start` | `center` | `end` | `space-between`）

**Grid 专属属性**：
- `columns`：列数（数字或 `auto-fit`）
- `row-gap`：行间距
- `col-gap`：列间距

---

## 5. 表单与数据校验

### 5.1 输入框 `<input-field>`

```xml
<input-field
  id="username"
  label="用户名"
  type="text"
  placeholder="请输入用户名"
  required="true"
  min-length="3"
  max-length="20"
  pattern="^[a-zA-Z0-9_]+$"
  error-message="用户名只能包含字母、数字和下划线"
  data-bind="form.username"
/>
```

**属性详解**：

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 唯一标识符 |
| `label` | string | ❌ | 标签文本 |
| `type` | string | ❌ | 输入类型（`text` | `password` | `email` | `number` | `url` | `tel`）|
| `placeholder` | string | ❌ | 占位文本 |
| `required` | boolean | ❌ | 是否必填（默认 `false`）|
| `disabled` | boolean | ❌ | 是否禁用 |
| `min-length` | number | ❌ | 最小长度 |
| `max-length` | number | ❌ | 最大长度 |
| `min` | number | ❌ | 最小值（仅 `type="number"`）|
| `max` | number | ❌ | 最大值（仅 `type="number"`）|
| `pattern` | string | ❌ | 正则表达式校验 |
| `error-message` | string | ❌ | 自定义错误提示（校验失败时显示）|
| `data-bind` | string | ❌ | 数据绑定路径（双向绑定）|

**预设校验类型**：

当 `type` 为特定值时，自动添加内置校验：

- `email`：自动校验邮箱格式（`pattern="^[^@]+@[^@]+\.[^@]+$"`）
- `url`：自动校验 URL 格式
- `tel`：自动校验手机号（根据地区）

### 5.2 选择框 `<select>`

```xml
<select
  id="role"
  label="角色"
  required="true"
  data-bind="form.role"
>
  <option value="">请选择</option>
  <option value="admin">管理员</option>
  <option value="user">普通用户</option>
  <option value="guest">访客</option>
</select>
```

**动态选项（从 API 加载）**：

```xml
<select
  id="department"
  label="部门"
  required="true"
  data-bind="form.department"
  options-from-api="true"
  api-endpoint="/api/departments"
  option-label-key="name"
  option-value-key="id"
/>
```

**属性说明**：
- `options-from-api`：是否从 API 加载选项
- `api-endpoint`：API 端点（返回格式：`{ data: [{ id, name }, ...] }`）
- `option-label-key`：选项显示字段名
- `option-value-key`：选项值字段名

### 5.3 开关 `<switch>`

```xml
<switch
  id="enabled"
  label="启用账户"
  data-bind="form.enabled"
/>
```

**默认值**：未绑定数据时，默认为 `false`。

### 5.4 滑块 `<slider>`

```xml
<slider
  id="priority"
  label="优先级"
  min="1"
  max="10"
  step="1"
  required="true"
  data-bind="form.priority"
/>
```

### 5.5 日期选择器 `<date-picker>`

```xml
<date-picker
  id="birthdate"
  label="出生日期"
  format="YYYY-MM-DD"
  required="true"
  min-date="1900-01-01"
  max-date="2010-12-31"
  data-bind="form.birthdate"
/>
```

### 5.6 文本域 `<textarea>`

```xml
<textarea
  id="description"
  label="描述"
  rows="5"
  placeholder="请输入描述..."
  required="true"
  min-length="10"
  max-length="500"
  data-bind="form.description"
/>
```

---

## 6. 后端交互机制

### 6.1 按钮与 API 调用

```xml
<button
  type="primary"
  api-endpoint="/api/users"
  api-method="POST"
  api-data-from="form"
  confirm-message="确认提交用户信息？"
  on-success="show-toast:提交成功;refresh-table:usersTable"
  on-error="show-toast:提交失败"
>
  提交
</button>
```

**属性详解**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `type` | string | 按钮样式（`primary` | `secondary` | `danger` | `text`）|
| `api-endpoint` | string | API 端点（支持路径参数，如 `/api/users/:id`）|
| `api-method` | string | HTTP 方法（`GET` | `POST` | `PUT` | `DELETE`）|
| `api-data-from` | string | 请求体数据来源路径（如 `form` 表示 `dataStore.form`）|
| `confirm-message` | string | 点击前弹出确认对话框（可选）|
| `on-success` | string | 成功后执行的动作（多个动作用 `;` 分隔）|
| `on-error` | string | 失败后执行的动作 |

**支持的动作类型**：

- `show-toast:<message>`：显示 Toast 通知
- `refresh-table:<table_id>`：刷新指定数据表格
- `close-dialog`：关闭当前对话框
- `navigate:<path>`：导航到指定路由
- `reload-page`：重新加载当前页面

### 6.2 数据表格 `<data-table>`

```xml
<data-table
  id="usersTable"
  api-endpoint="/api/users"
  api-method="GET"
  data-bind="response.data.users"
  pagination="true"
  page-size="20"
  auto-refresh="false"
>
  <column key="id" label="ID" width="80" sortable="true" />
  <column key="username" label="用户名" sortable="true" />
  <column key="email" label="邮箱" />
  <column key="role" label="角色">
    <template>
      <tag :color="row.role === 'admin' ? 'primary' : 'default'">
        {{ row.role }}
      </tag>
    </template>
  </column>
  <column key="actions" label="操作" width="150">
    <template>
      <button type="text" size="small" action="open-dialog:editDialog">编辑</button>
      <button
        type="text"
        color="danger"
        size="small"
        api-endpoint="/api/users/:id"
        api-method="DELETE"
        confirm-message="确认删除该用户？"
        on-success="refresh-table:usersTable"
      >
        删除
      </button>
    </template>
  </column>
</data-table>
```

**属性说明**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | string | 表格唯一 ID（用于刷新） |
| `api-endpoint` | string | 数据源 API |
| `api-method` | string | 请求方法（通常为 `GET`）|
| `data-bind` | string | 响应数据路径（如 `response.data.users`）|
| `pagination` | boolean | 是否分页 |
| `page-size` | number | 每页条数 |
| `auto-refresh` | boolean | 页面加载时是否自动刷新 |
| `selectable` | boolean | 是否可选中行 |

**列定义 `<column>`**：

- `key`：数据字段名
- `label`：列标题
- `width`：列宽度（px 或百分比）
- `sortable`：是否可排序
- `<template>`：自定义渲染（支持 Vue 模板语法）

### 6.3 请求体数据结构

**场景 1：简单表单提交**

```xml
<input-field id="username" data-bind="form.username" required="true" />
<input-field id="email" data-bind="form.email" required="true" />

<button
  api-endpoint="/api/users"
  api-method="POST"
  api-data-from="form"
>
  提交
</button>
```

**请求体**：

```json
{
  "username": "alice",
  "email": "alice@example.com"
}
```

**场景 2：嵌套数据结构**

```xml
<input-field id="name" data-bind="user.profile.name" />
<input-field id="age" data-bind="user.profile.age" type="number" />

<button
  api-endpoint="/api/users"
  api-method="POST"
  api-data-from="user"
>
  提交
</button>
```

**请求体**：

```json
{
  "profile": {
    "name": "Alice",
    "age": 25
  }
}
```

### 6.4 路径参数替换

```xml
<!-- 表格行中的删除按钮 -->
<button
  api-endpoint="/api/users/:id"
  api-method="DELETE"
  api-data-from="row"
>
  删除
</button>
```

**数据上下文**：

```json
{
  "row": {
    "id": 123,
    "username": "alice"
  }
}
```

**实际请求**：

```
DELETE /api/users/123
```

**替换规则**：
- `:id` 会被替换为 `row.id` 的值
- 支持多个路径参数（如 `/api/posts/:postId/comments/:commentId`）

### 6.5 响应处理

**标准响应格式**（与 WebUI 其他 API 一致）：

```json
{
  "code": 200,
  "data": {
    "users": [
      { "id": 1, "username": "alice" }
    ]
  },
  "message": "success"
}
```

**前端自动处理**：
- `code !== 200`：触发 `on-error` 动作，显示 `message`
- `code === 200`：触发 `on-success` 动作，将 `data` 存入 `dataStore.response`

---

## 7. 前端渲染架构

### 7.1 页面加载流程

```
用户点击侧边栏中的"用户管理"
    ↓
前端调用 GET /api/ui/schema/my_plugin/user-management
    ↓
WebUI Service 返回 XML 字符串
    ↓
前端解析 XML → JSON Schema
    ↓
SchemaRenderer.vue 递归渲染组件树
    ↓
组件挂载时执行 auto-load API（如有）
    ↓
用户交互 → 触发 API 调用 → 更新 dataStore → 响应式更新 UI
```

### 7.2 数据存储 `dataStore`

```typescript
// 全局数据存储（每个页面独立）
const dataStore = reactive<Record<string, any>>({
  form: {},           // 表单数据
  response: {},       // 最近一次 API 响应
  tables: {},         // 表格数据
  dialogs: {},        // 对话框状态
  // 插件可以定义自己的命名空间
})
```

**数据绑定示例**：

```xml
<input-field id="username" data-bind="form.username" />
```

**内部实现**：

```typescript
const boundValue = computed({
  get: () => getValueByPath(dataStore, 'form.username'),
  set: (val) => setValueByPath(dataStore, 'form.username', val),
})
```

### 7.3 组件映射表

| XML 标签 | Vue 组件 | 功能 |
|----------|----------|------|
| `<container>` | `UIContainer.vue` | 布局容器 |
| `<input-field>` | `UIInputField.vue` | 输入框 |
| `<textarea>` | `UITextarea.vue` | 文本域 |
| `<select>` | `UISelect.vue` | 下拉选择 |
| `<switch>` | `UISwitch.vue` | 开关 |
| `<slider>` | `UISlider.vue` | 滑块 |
| `<date-picker>` | `UIDatePicker.vue` | 日期选择器 |
| `<button>` | `UIButton.vue` | 按钮 |
| `<dialog>` | `UIDialog.vue` | 对话框 |
| `<data-table>` | `UIDataTable.vue` | 数据表格 |
| `<card>` | `UICard.vue` | 卡片 |
| `<tag>` | `UITag.vue` | 标签 |
| `<tabs>` | `UITabs.vue` | 标签页 |
| `<line-chart>` | `UILineChart.vue` | 折线图 |
| `<bar-chart>` | `UIBarChart.vue` | 柱状图 |
| `<pie-chart>` | `UIPieChart.vue` | 饼图 |

### 7.4 校验流程

```
用户点击提交按钮
    ↓
遍历所有 required 字段，检查是否为空
    ↓
遍历所有带 pattern 的字段，执行正则校验
    ↓
遍历所有 min-length/max-length 字段，检查长度
    ↓
如有错误，显示红色错误提示，阻止提交
    ↓
校验通过，构建请求体
    ↓
发送 HTTP 请求
```

---

## 8. 安全与权限

### 8.1 XML 注入防护

**风险**：插件传入恶意 XML，尝试注入脚本或访问敏感数据。

**防护措施**：
1. **XSD 强校验**：所有 XML 必须符合预定义的 XSD Schema
2. **标签白名单**：只允许预设的组件标签，拒绝 `<script>`、`<iframe>` 等
3. **属性过滤**：移除 `on*` 事件属性（如 `onclick`）
4. **沙箱渲染**：Vue 组件在隔离上下文中运行

### 8.2 API 权限控制

**问题**：插件注册的页面可能调用任意 API 端点。

**解决方案**：
1. **插件级限制**：在 WebUI Service 注册时，记录 `plugin_name`
2. **API 请求拦截**：前端发起请求时，在请求头添加 `X-Plugin-Name`
3. **后端校验**：API 端点检查请求来源插件是否有权限调用

**示例**：

```python
# API 端点中的权限检查
@router.post("/api/users")
async def create_user(request: Request):
    plugin_name = request.headers.get("X-Plugin-Name")
    if plugin_name != "user_management_plugin":
        raise HTTPException(403, "无权访问此 API")
    # 业务逻辑
```

### 8.3 插件级页面可见性

**规则**：
- 只有**已启用**的插件注册的页面才会显示在侧边栏
- 插件被禁用时，前端自动隐藏其页面
- `/api/ui/discovery` 只返回已启用插件的页面

---

## 9. 完整示例

### 9.1 插件注册代码（Python）

```python
# my_plugin/user_management/plugin.py

from src.core.components.base.plugin import BasePlugin
from src.core.components.loader import register_plugin
from src.core.managers import get_service_manager
from src.kernel.logger import get_logger

logger = get_logger("user_management")

@register_plugin
class UserManagementPlugin(BasePlugin):
    plugin_name = "user_management"
    
    async def on_plugin_loaded(self) -> None:
        """插件加载后注册前端页面"""
        await self._register_user_list_page()
        await self._register_user_form_page()
    
    async def _register_user_list_page(self):
        """注册用户列表页面"""
        webui_service = get_service_manager().get_service("webui:service:webui_ui")
        if not webui_service:
            logger.warning("WebUI Service 未找到，跳过注册")
            return
        
        page_xml = """
        <ui-page schema-version="1.0">
          <metadata>
            <title>用户列表</title>
            <description>查看和管理所有用户</description>
            <icon>group</icon>
            <api-base>/api/user-management</api-base>
          </metadata>
          
          <layout>
            <container layout="vertical" spacing="24" padding="24">
              <!-- 搜索和新建按钮 -->
              <container layout="horizontal" justify="space-between">
                <input-field
                  id="searchQuery"
                  placeholder="搜索用户..."
                  type="text"
                  data-bind="search.query"
                />
                <button type="primary" action="open-dialog:createUserDialog">
                  新建用户
                </button>
              </container>
              
              <!-- 用户列表表格 -->
              <data-table
                id="usersTable"
                api-endpoint="/users"
                api-method="GET"
                data-bind="response.data.users"
                pagination="true"
                page-size="20"
                auto-refresh="true"
              >
                <column key="id" label="ID" width="80" sortable="true" />
                <column key="username" label="用户名" sortable="true" />
                <column key="email" label="邮箱" />
                <column key="role" label="角色">
                  <template>
                    <tag :color="row.role === 'admin' ? 'primary' : 'default'">
                      {{ row.role }}
                    </tag>
                  </template>
                </column>
                <column key="enabled" label="状态">
                  <template>
                    <tag :color="row.enabled ? 'success' : 'danger'">
                      {{ row.enabled ? '已启用' : '已禁用' }}
                    </tag>
                  </template>
                </column>
                <column key="actions" label="操作" width="150">
                  <template>
                    <button type="text" size="small" action="open-dialog:editDialog">
                      编辑
                    </button>
                    <button
                      type="text"
                      color="danger"
                      size="small"
                      api-endpoint="/users/:id"
                      api-method="DELETE"
                      confirm-message="确认删除该用户？"
                      on-success="show-toast:删除成功;refresh-table:usersTable"
                    >
                      删除
                    </button>
                  </template>
                </column>
              </data-table>
            </container>
          </layout>
        </ui-page>
        """
        
        success = await webui_service.register_ui_page(
            plugin_name=self.plugin_name,
            page_id="user-list",
            page_xml=page_xml,
            order=100,
        )
        
        if success:
            logger.info("用户列表页面注册成功")
        else:
            logger.error("用户列表页面注册失败")
    
    async def _register_user_form_page(self):
        """注册用户表单页面"""
        # 类似上面的流程，这里省略...
        pass
```

### 9.2 表单页面 XML

```xml
<ui-page schema-version="1.0">
  <metadata>
    <title>新建用户</title>
    <icon>person_add</icon>
    <api-base>/api/user-management</api-base>
  </metadata>
  
  <layout>
    <container layout="vertical" spacing="24" padding="24">
      <card title="基本信息" elevation="1">
        <container layout="vertical" spacing="16">
          <!-- 用户名（必填、3-20字符、只允许字母数字下划线） -->
          <input-field
            id="username"
            label="用户名"
            type="text"
            placeholder="请输入用户名"
            required="true"
            min-length="3"
            max-length="20"
            pattern="^[a-zA-Z0-9_]+$"
            error-message="用户名只能包含字母、数字和下划线，长度3-20位"
            data-bind="form.username"
          />
          
          <!-- 邮箱（必填、自动校验邮箱格式） -->
          <input-field
            id="email"
            label="邮箱"
            type="email"
            placeholder="user@example.com"
            required="true"
            error-message="请输入有效的邮箱地址"
            data-bind="form.email"
          />
          
          <!-- 密码（必填、最少8位） -->
          <input-field
            id="password"
            label="密码"
            type="password"
            placeholder="请输入密码"
            required="true"
            min-length="8"
            error-message="密码至少8位"
            data-bind="form.password"
          />
          
          <!-- 角色（必填、下拉选择） -->
          <select
            id="role"
            label="角色"
            required="true"
            data-bind="form.role"
          >
            <option value="">请选择角色</option>
            <option value="admin">管理员</option>
            <option value="user">普通用户</option>
            <option value="guest">访客</option>
          </select>
          
          <!-- 启用状态（开关、非必填、默认 true） -->
          <switch
            id="enabled"
            label="启用账户"
            data-bind="form.enabled"
          />
        </container>
      </card>
      
      <!-- 提交按钮 -->
      <container layout="horizontal" spacing="12" justify="end">
        <button type="secondary" action="navigate:/plugins">
          取消
        </button>
        <button
          type="primary"
          api-endpoint="/users"
          api-method="POST"
          api-data-from="form"
          confirm-message="确认创建该用户？"
          on-success="show-toast:用户创建成功;navigate:/plugins/user-list"
          on-error="show-toast:创建失败"
        >
          提交
        </button>
      </container>
    </container>
  </layout>
</ui-page>
```

### 9.3 统计仪表盘 XML

```xml
<ui-page schema-version="1.0">
  <metadata>
    <title>用户统计</title>
    <icon>analytics</icon>
    <api-base>/api/user-management</api-base>
  </metadata>
  
  <layout>
    <container layout="vertical" spacing="24" padding="24">
      <!-- 统计卡片（Grid 布局） -->
      <container layout="grid" columns="3" gap="16">
        <card title="总用户数" elevation="1">
          <container layout="vertical" align="center">
            <text style="font-size:36px;font-weight:700;color:var(--md-sys-color-primary)">
              {{ stats.totalUsers }}
            </text>
          </container>
        </card>
        
        <card title="活跃用户" elevation="1">
          <container layout="vertical" align="center">
            <text style="font-size:36px;font-weight:700;color:var(--md-sys-color-tertiary)">
              {{ stats.activeUsers }}
            </text>
          </container>
        </card>
        
        <card title="本月新增" elevation="1">
          <container layout="vertical" align="center">
            <text style="font-size:36px;font-weight:700;color:var(--md-sys-color-secondary)">
              {{ stats.newUsers }}
            </text>
          </container>
        </card>
      </container>
      
      <!-- 图表（Grid 布局） -->
      <container layout="grid" columns="2" gap="16">
        <!-- 用户增长趋势（折线图） -->
        <line-chart
          id="userGrowthChart"
          title="用户增长趋势"
          api-endpoint="/stats/user-growth"
          data-bind="response.data"
          x-key="date"
          y-key="count"
          height="400"
        />
        
        <!-- 角色分布（饼图） -->
        <pie-chart
          id="roleDistChart"
          title="角色分布"
          api-endpoint="/stats/role-distribution"
          data-bind="response.data"
          name-key="role"
          value-key="count"
          height="400"
        />
      </container>
    </container>
  </layout>
</ui-page>
```

---

## 10. 开发指南

### 10.1 快速开始（5 分钟）

**步骤 1：创建插件目录**

```
my_plugin/
├── manifest.json
├── plugin.py
└── service.py  # 可选，用于提供后端 API
```

**步骤 2：编写 plugin.py**

```python
from src.core.components.base.plugin import BasePlugin
from src.core.components.loader import register_plugin
from src.core.managers import get_service_manager

@register_plugin
class MyPlugin(BasePlugin):
    plugin_name = "my_plugin"
    
    async def on_plugin_loaded(self):
        webui_service = get_service_manager().get_service("webui:service:webui_ui")
        if not webui_service:
            return
        
        # 注册简单表单页面
        await webui_service.register_ui_page(
            plugin_name=self.plugin_name,
            page_id="simple-form",
            page_xml="""
            <ui-page schema-version="1.0">
              <metadata>
                <title>简单表单</title>
                <icon>edit</icon>
              </metadata>
              <layout>
                <container layout="vertical" spacing="16" padding="24">
                  <input-field
                    id="message"
                    label="消息"
                    required="true"
                    data-bind="form.message"
                  />
                  <button
                    type="primary"
                    api-endpoint="/api/my-plugin/submit"
                    api-method="POST"
                    api-data-from="form"
                  >
                    提交
                  </button>
                </container>
              </layout>
            </ui-page>
            """,
        )
```

**步骤 3：启动应用**

1. 加载插件
2. 访问 WebUI `/plugins` 页面
3. 切换到"插件页面" Tab
4. 在左侧找到"简单表单"
5. 填写并提交

### 10.2 常见模式

#### 模式 1：动态生成 XML（根据配置）

```python
async def _register_dynamic_page(self):
    # 从配置或数据库读取字段定义
    fields = self.get_field_definitions()
    
    # 动态构建 XML
    from xml.etree.ElementTree import Element, SubElement, tostring
    
    root = Element("ui-page", {"schema-version": "1.0"})
    metadata = SubElement(root, "metadata")
    SubElement(metadata, "title").text = "动态表单"
    
    layout = SubElement(root, "layout")
    container = SubElement(layout, "container", {"layout": "vertical", "spacing": "16"})
    
    for field in fields:
        SubElement(container, "input-field", {
            "id": field["id"],
            "label": field["label"],
            "required": str(field["required"]).lower(),
            "data-bind": f"form.{field['id']}",
        })
    
    page_xml = tostring(root, encoding="unicode")
    
    await webui_service.register_ui_page(
        plugin_name=self.plugin_name,
        page_id="dynamic-form",
        page_xml=page_xml,
    )
```

#### 模式 2：多页面插件

```python
async def on_plugin_loaded(self):
    pages = [
        ("list", self._get_list_page_xml()),
        ("form", self._get_form_page_xml()),
        ("stats", self._get_stats_page_xml()),
    ]
    
    webui_service = get_service_manager().get_service("webui:service:webui_ui")
    if not webui_service:
        return
    
    for page_id, page_xml in pages:
        await webui_service.register_ui_page(
            plugin_name=self.plugin_name,
            page_id=page_id,
            page_xml=page_xml,
        )
```

#### 模式 3：热更新页面

```python
async def update_page(self):
    """运行时更新页面（例如配置变更后）"""
    webui_service = get_service_manager().get_service("webui:service:webui_ui")
    
    # 重新调用 register，会覆盖旧的注册
    await webui_service.register_ui_page(
        plugin_name=self.plugin_name,
        page_id="form",
        page_xml=self._get_updated_form_xml(),
    )
    
    # 可选：通知前端刷新
    await webui_service.notify_page_updated(self.plugin_name, "form")
```

### 10.3 调试技巧

#### 1. XML 校验错误

**现象**：注册失败，日志显示"XML 校验失败"。

**排查**：
- 检查 XML 是否 well-formed（标签闭合、引号配对）
- 使用在线 XML 校验器
- 查看日志中的详细错误信息

#### 2. 数据绑定不生效

**现象**：输入框修改后，`dataStore.form` 未更新。

**排查**：
- 确认 `data-bind` 属性拼写正确
- 检查路径是否存在（如 `form.username`，`form` 对象必须已初始化）
- 打开浏览器开发者工具，查看 Vue DevTools

#### 3. API 调用失败

**现象**：点击按钮后无响应或报错。

**排查**：
- 检查 `api-endpoint` 是否正确
- 查看浏览器 Network 面板，确认请求是否发出
- 检查后端 API 是否正常响应
- 确认 `api-data-from` 路径是否正确

### 10.4 最佳实践

#### 1. 字段命名规范

- 使用小写字母和下划线（如 `user_name`）
- ID 属性与 `data-bind` 路径保持一致

```xml
<!-- ✅ 推荐 -->
<input-field id="user_name" data-bind="form.user_name" />

<!-- ❌ 不推荐 -->
<input-field id="userName" data-bind="form.user_name" />
```

#### 2. 错误提示用户友好

```xml
<!-- ✅ 提供详细错误提示 -->
<input-field
  id="username"
  required="true"
  pattern="^[a-zA-Z0-9_]+$"
  error-message="用户名只能包含字母、数字和下划线"
/>

<!-- ❌ 使用浏览器默认提示（英文、不友好） -->
<input-field
  id="username"
  required="true"
  pattern="^[a-zA-Z0-9_]+$"
/>
```

#### 3. 合理使用确认对话框

```xml
<!-- ✅ 危险操作添加确认 -->
<button
  api-method="DELETE"
  confirm-message="确认删除该用户？此操作不可恢复。"
>
  删除
</button>

<!-- ❌ 普通查询也弹确认框 -->
<button
  api-method="GET"
  confirm-message="确认查询用户列表？"
>
  查询
</button>
```

#### 4. API 端点使用 api-base

```xml
<!-- ✅ 使用 api-base，易于迁移 -->
<metadata>
  <api-base>/api/my-plugin</api-base>
</metadata>

<button api-endpoint="/users" />  <!-- 实际请求：/api/my-plugin/users -->

<!-- ❌ 硬编码完整路径 -->
<button api-endpoint="/api/my-plugin/users" />
```

### 10.5 性能优化

#### 1. 分页大数据

```xml
<!-- ✅ 启用分页 -->
<data-table
  pagination="true"
  page-size="20"
/>

<!-- ❌ 一次性加载所有数据 -->
<data-table
  pagination="false"
/>
```

#### 2. 避免自动刷新

```xml
<!-- ✅ 用户主动点击刷新 -->
<data-table auto-refresh="false" />
<button action="refresh-table:myTable">刷新</button>

<!-- ❌ 页面加载时自动刷新（可能导致重复请求） -->
<data-table auto-refresh="true" />
```

#### 3. 按需加载选项

```xml
<!-- ✅ 动态加载大量选项 -->
<select
  options-from-api="true"
  api-endpoint="/api/departments"
/>

<!-- ❌ 在 XML 中硬编码数千个选项 -->
<select>
  <option value="1">部门1</option>
  <option value="2">部门2</option>
  <!-- ... 数千行 ... -->
</select>
```

---

## 总结

本设计文档提供了完整的插件前端扩展系统架构，核心特性包括：

### ✅ 已实现的设计目标

1. **动态注册机制**：插件通过调用 WebUI Service API，传入 XML 字符串即时注册页面
2. **声明式 UI**：语义化 XML 标签自动渲染为 Material Design 3 组件
3. **完整表单支持**：包含 `required`、`min-length`、`pattern` 等校验规则
4. **后端交互**：支持 GET/POST/PUT/DELETE，可声明请求体结构和路径参数
5. **数据绑定**：`data-bind` 属性实现双向绑定
6. **安全防护**：XSD 校验、标签白名单、API 权限控制

### 📊 预计工作量

| 阶段 | 任务 | 工作量 |
|------|------|--------|
| Phase 1 | WebUI Service 实现（注册 API、存储、发现端点）| 1 周 |
| Phase 2 | XML 解析与 XSD 校验 | 0.5 周 |
| Phase 3 | 前端渲染器 + 15 个预设组件 | 3 周 |
| Phase 4 | 表单校验与 API 执行器 | 1 周 |
| Phase 5 | 示例插件 + 文档 | 1 周 |
| **总计** | | **6.5 周** |

### 🚀 下一步行动

1. **团队评审**：确认设计方案是否满足需求
2. **原型开发**：先实现 WebUI Service 注册 API 和简单表单渲染
3. **迭代验证**：用简单插件验证整个流程的可行性
4. **完整实现**：按 Phase 1-5 顺序开发

---

**设计文档版本历史**：
- v2.0.0 (2026-05-04): 重新设计为动态注册机制，增强表单校验和 POST 支持
- v1.0.0 (2026-05-03): 初始设计（已废弃）
