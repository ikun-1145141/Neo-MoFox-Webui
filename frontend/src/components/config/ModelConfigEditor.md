# ModelConfigEditor 使用文档

## 概述

`ModelConfigEditor.vue` 是一个专门用于编辑模型配置的 Vue 组件，**不继承** `ConfigEditor`，而是完全独立实现。

## 主要特性

### 1. **三标签切换界面**
   - **供应商配置** - 管理 API 提供商（如 OpenAI、SiliconFlow 等）
   - **模型配置** - 管理具体的 AI 模型
   - **任务配置** - 管理模型任务（如 utils、vlm、embedding 等）

### 2. **列表式管理**
   - 卡片式展示所有配置项
   - 每个配置项显示关键信息
   - 快速操作按钮：测试、编辑、删除

### 3. **测试功能**
   - **供应商测试**: 验证配置完整性
   - **模型测试**: 实际调用 API 测试连通性

### 4. **代码模式**
   - 点击"代码模式"按钮切换到 TOML 编辑器
   - 直接编辑原始配置文件
   - 自动双向同步表单与代码

### 5. **Material Design 3 样式**
   - 遵循 MD3 设计规范
   - 响应式布局
   - 流畅的动画过渡

## 使用方法

### 基础用法

```vue
<template>
  <ModelConfigEditor
    title="模型配置"
    config-path="config/model.toml"
    :schema="schema"
    v-model="configData"
    @save="handleSave"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ModelConfigEditor from '@/components/config/ModelConfigEditor.vue'
import type { SectionSchema } from '@/api/types/config'

// 配置数据
const configData = ref({
  api_providers: [
    {
      name: 'SiliconFlow',
      base_url: 'https://api.siliconflow.cn/v1',
      api_key: 'your-api-key',
      client_type: 'openai',
      max_retry: 3,
      timeout: 30,
      retry_interval: 10,
    }
  ],
  models: [
    {
      name: 'deepseek-v3',
      model_identifier: 'deepseek-ai/deepseek-v3',
      api_provider: 'SiliconFlow',
      price_in: 2.0,
      price_out: 8.0,
      max_context: 32768,
      tool_call_compat: false,
      anti_truncation: false,
    }
  ],
  model_tasks: {
    utils: {
      model_list: ['deepseek-v3'],
      max_tokens: 4096,
      temperature: 0.7,
    }
  }
})

// Schema 定义（可选）
const schema = ref<SectionSchema[]>([])

// 保存处理
function handleSave(data: Record<string, any>) {
  console.log('保存配置:', data)
  // 调用 API 保存到后端
}
</script>
```

### Props

| 属性 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `title` | `string` | 必填 | 编辑器标题 |
| `configPath` | `string` | - | 配置文件路径（显示用） |
| `schema` | `SectionSchema[]` | `[]` | 配置 Schema（暂未使用） |
| `modelValue` | `Record<string, any>` | `{}` | 配置数据 |
| `readonly` | `boolean` | `false` | 是否只读模式 |

### Events

| 事件 | 参数 | 说明 |
|-----|------|------|
| `update:modelValue` | `value: Record<string, any>` | 配置数据变更 |
| `save` | `data: Record<string, any>` | 保存按钮点击 |

## 数据结构

### 供应商配置 (api_providers)

```typescript
interface ApiProvider {
  name: string              // 提供商名称
  base_url: string          // API 基础 URL
  api_key: string | string[] // API 密钥（支持多密钥轮询）
  client_type: string       // 客户端类型（openai/gemini/bedrock）
  max_retry: number         // 最大重试次数
  timeout: number           // 超时时间（秒）
  retry_interval: number    // 重试间隔（秒）
}
```

### 模型配置 (models)

```typescript
interface Model {
  name: string                  // 模型名称
  model_identifier: string      // 模型标识符
  api_provider: string          // 所属提供商
  price_in: number              // 输入价格（每百万 token）
  price_out: number             // 输出价格（每百万 token）
  force_stream_mode: boolean    // 是否强制流式输出
  max_context: number           // 最大上下文长度
  tool_call_compat: boolean     // Tool Call 兼容模式
  extra_params: Record<string, any> // 额外参数
  anti_truncation: boolean      // 是否启用反截断
}
```

### 任务配置 (model_tasks)

```typescript
interface ModelTask {
  model_list: string[]      // 模型列表
  max_tokens?: number       // 最大 tokens
  temperature?: number      // 温度参数
  [key: string]: any        // 其他任务特定参数
}

// 任务配置是一个字典
type ModelTasks = Record<string, ModelTask>
```

## 功能说明

### 添加配置

1. **添加供应商**: 点击"添加供应商"按钮，填写供应商信息
2. **添加模型**: 点击"添加模型"按钮，选择供应商并填写模型信息
3. **添加任务**: 点击"添加任务"按钮，输入任务名称并配置参数

### 测试功能

#### 测试供应商
- 点击供应商卡片的"播放"按钮
- 验证供应商下是否有配置的模型
- 显示验证结果

#### 测试模型
- 点击模型卡片的"播放"按钮
- 实际调用 API 发送测试消息（"你好"）
- 显示延迟、响应内容或错误信息

### 编辑与删除

- **编辑**: 点击"编辑"按钮（TODO: 待实现编辑对话框）
- **删除**: 点击"删除"按钮，确认后删除配置项

### 代码模式

1. 点击工具栏的"代码模式"按钮
2. 显示 TOML 格式的配置文件
3. 可直接编辑 TOML 代码
4. 点击"表单模式"按钮切换回卡片视图

## 与 ConfigEditor 的区别

| 特性 | ModelConfigEditor | ConfigEditor |
|-----|------------------|--------------|
| 继承关系 | 完全独立实现 | 通用配置编辑器 |
| UI 布局 | 顶栏标签 + 列表卡片 | 单一表单 |
| 适用场景 | 模型配置专用 | 通用配置 |
| 测试功能 | 内置供应商/模型测试 | 无 |
| 管理功能 | 添加/编辑/删除操作 | 仅编辑 |
| 代码模式 | 保留 | 保留 |

## TODO

- [ ] 实现编辑对话框（供应商/模型/任务）
- [ ] 添加表单验证
- [ ] 改进测试功能（批量测试）
- [ ] 添加导入/导出功能
- [ ] 支持拖拽排序

## 样式变量

组件使用 Material Design 3 CSS 变量：

```css
--md-sys-color-surface
--md-sys-color-on-surface
--md-sys-color-primary
--md-sys-color-on-primary
--md-sys-color-secondary-container
--md-sys-color-outline-variant
--md-sys-color-error-container
--md-sys-color-tertiary-container
```

确保在应用中定义这些变量。
