<!--
  @file ConfigEditor.vue
  @description 统一配置编辑器（代码模式 + 表单模式）
  
  功能：
  - 右上角图标按钮切换编辑模式
  - 代码模式：使用 TomlEditor
  - 表单模式：使用 FormEditor
  - 数据双向绑定与转换
  - 保存按钮与状态管理
-->
<template>
  <div class="config-editor">
    <!-- 工具栏 -->
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <h2 class="config-title">{{ title }}</h2>
        <span v-if="configPath" class="config-path">{{ configPath }}</span>
      </div>

      <div class="toolbar-right">
        <!-- 模式切换按钮 -->
        <button
          type="button"
          class="mode-toggle-btn"
          @click="toggleMode"
          :title="editMode === 'code' ? '切换到表单模式' : '切换到代码模式'"
        >
          <Icon
            :icon="editMode === 'code' ? 'material-symbols:edit-note-rounded' : 'material-symbols:code-rounded'"
            :size="20"
          />
          <span>{{ editMode === 'code' ? '表单模式' : '代码模式' }}</span>
        </button>

        <!-- 保存按钮 -->
        <button
          type="button"
          class="save-btn"
          @click="handleSave"
          :disabled="isSaving || !hasChanges"
          :title="hasChanges ? '保存更改' : '无更改'"
        >
          <Icon
            v-if="!isSaving"
            icon="material-symbols:save-outline-rounded"
            :size="20"
          />
          <Icon
            v-else
            icon="material-symbols:progress-activity"
            :size="20"
            class="spinning"
          />
          <span>{{ isSaving ? '保存中...' : '保存' }}</span>
        </button>
      </div>
    </div>

    <!-- 编辑器内容区 -->
    <div class="editor-content">
      <!-- 代码模式 -->
      <TomlEditor
        v-if="editMode === 'code'"
        v-model="codeContent"
        :readonly="readonly"
      />

      <!-- 表单模式 -->
      <FormEditor
        v-else
        v-model="formData"
        :schema="schema"
        :readonly="readonly"
      />
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMessage" class="error-banner">
      <Icon icon="material-symbols:error-outline-rounded" :size="20" />
      <span>{{ errorMessage }}</span>
      <button type="button" @click="errorMessage = ''" class="close-btn">
        <Icon icon="material-symbols:close-rounded" :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { parse as parseToml } from 'toml'
import Icon from '../common/Icon.vue'
import TomlEditor from './TomlEditor.vue'
import FormEditor from './FormEditor.vue'
import type { SectionSchema } from '@/api/types/config'

/**
 * 简单的对象转 TOML 字符串（用于展示）
 * 注意：这是简化实现，不支持所有 TOML 特性
 */
function stringifyToml(obj: Record<string, any>, indent = 0): string {
  const lines: string[] = []
  const indentStr = '  '.repeat(indent)

  for (const [key, value] of Object.entries(obj)) {
    if (value === null || value === undefined) {
      continue
    }

    if (Array.isArray(value)) {
      // 数组表 [[key]]
      if (value.length > 0 && typeof value[0] === 'object' && value[0] !== null) {
        value.forEach((item) => {
          lines.push(`${indentStr}[[${key}]]`)
          for (const [k, v] of Object.entries(item)) {
            lines.push(`${indentStr}${k} = ${tomlValue(v)}`)
          }
          lines.push('')
        })
      } else {
        lines.push(`${indentStr}${key} = ${tomlValue(value)}`)
      }
    } else if (typeof value === 'object' && value !== null) {
      // 节 [key]
      lines.push(`${indentStr}[${key}]`)
      for (const [k, v] of Object.entries(value)) {
        lines.push(`${indentStr}${k} = ${tomlValue(v)}`)
      }
      lines.push('')
    } else {
      lines.push(`${indentStr}${key} = ${tomlValue(value)}`)
    }
  }

  return lines.join('\n')
}

function tomlValue(value: any): string {
  if (typeof value === 'string') {
    return `"${value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`
  } else if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  } else if (typeof value === 'number') {
    return String(value)
  } else if (Array.isArray(value)) {
    return `[${value.map(tomlValue).join(', ')}]`
  } else if (value instanceof Date) {
    return value.toISOString()
  }
  return String(value)
}

// Props
interface Props {
  title?: string
  configPath?: string
  schema?: SectionSchema[]
  modelValue?: Record<string, any>
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '配置编辑器',
  schema: () => [],
  modelValue: () => ({}),
  readonly: false,
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
  save: [data: Record<string, any>]
}>()

// 编辑模式：'code' | 'form'
const editMode = ref<'code' | 'form'>('form')

// 表单数据（响应式）
const formData = ref<Record<string, any>>({ ...props.modelValue })

// 代码内容（TOML 字符串）
const codeContent = ref<string>('')

// 保存状态
const isSaving = ref(false)
const errorMessage = ref('')

// 原始数据（用于检测变更）
const originalData = ref<Record<string, any>>({ ...props.modelValue })

// 是否有未保存的更改
const hasChanges = computed(() => {
  return JSON.stringify(formData.value) !== JSON.stringify(originalData.value)
})

// 初始化代码内容
watch(
  () => props.modelValue,
  (newValue) => {
    try {
      codeContent.value = stringifyToml(newValue)
      formData.value = { ...newValue }
      originalData.value = { ...newValue }
    } catch (error: any) {
      errorMessage.value = `TOML 序列化失败: ${error.message}`
    }
  },
  { immediate: true }
)

// 切换编辑模式
function toggleMode() {
  if (editMode.value === 'code') {
    // 从代码模式切换到表单模式
    try {
      const parsed = parseToml(codeContent.value)
      formData.value = parsed
      errorMessage.value = ''
    } catch (error: any) {
      errorMessage.value = `TOML 解析失败: ${error.message}，已保留代码模式`
      return
    }
    editMode.value = 'form'
  } else {
    // 从表单模式切换到代码模式
    try {
      codeContent.value = stringifyToml(formData.value)
      errorMessage.value = ''
    } catch (error: any) {
      errorMessage.value = `TOML 序列化失败: ${error.message}，已保留表单模式`
      return
    }
    editMode.value = 'code'
  }
}

// 处理保存
async function handleSave() {
  if (isSaving.value || !hasChanges.value) return

  try {
    isSaving.value = true
    errorMessage.value = ''

    // 获取最新数据
    let dataToSave: Record<string, any>

    if (editMode.value === 'code') {
      // 代码模式：解析 TOML
      try {
        dataToSave = parseToml(codeContent.value)
      } catch (error: any) {
        errorMessage.value = `TOML 格式错误: ${error.message}`
        return
      }
    } else {
      // 表单模式：直接使用表单数据
      dataToSave = formData.value
    }

    // 触发保存事件
    emit('save', dataToSave)
    emit('update:modelValue', dataToSave)

    // 更新原始数据
    originalData.value = { ...dataToSave }
  } catch (error: any) {
    errorMessage.value = `保存失败: ${error.message}`
  } finally {
    isSaving.value = false
  }
}

// 监听代码内容变化（尝试实时解析）
watch(codeContent, (newCode) => {
  if (editMode.value === 'code') {
    try {
      const parsed = parseToml(newCode)
      formData.value = parsed
    } catch {
      // 解析失败时不更新表单数据
    }
  }
})

// 监听表单数据变化（尝试实时序列化）
watch(
  formData,
  (newData) => {
    if (editMode.value === 'form') {
      try {
        codeContent.value = stringifyToml(newData)
      } catch {
        // 序列化失败时不更新代码内容
      }
    }
  },
  { deep: true }
)
</script>

<style scoped>
.config-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--md-sys-color-surface-container-low);
  border-radius: 12px;
  overflow: hidden;
}

/* 工具栏 */
.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--md-sys-color-surface);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.config-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

.config-path {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  font-family: 'Consolas', 'Monaco', monospace;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-toggle-btn,
.save-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.mode-toggle-btn {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.mode-toggle-btn:hover {
  background: var(--md-sys-color-secondary);
  color: var(--md-sys-color-on-secondary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.save-btn {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.save-btn:hover:not(:disabled) {
  background: var(--md-sys-color-primary);
  box-shadow: 0 2px 8px rgba(0, 88, 189, 0.3);
  transform: translateY(-1px);
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 编辑器内容区 */
.editor-content {
  flex: 1;
  overflow: hidden;
  padding: 16px;
}

/* 错误提示 */
.error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
  border-top: 1px solid var(--md-sys-color-error);
  font-size: 14px;
  flex-shrink: 0;
}

.error-banner .close-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-banner .close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}
</style>
