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
    <!-- 固定的头部 -->
    <div class="editor-header">
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
          :title="editMode === 'code' ? t('configEditor.modeToggle.toForm') : t('configEditor.modeToggle.toCode')"
        >
          <Icon
            :icon="editMode === 'code' ? 'material-symbols:edit-note-rounded' : 'material-symbols:code-rounded'"
            :size="20"
          />
          <span>{{ editMode === 'code' ? t('configEditor.modeToggle.formLabel') : t('configEditor.modeToggle.codeLabel') }}</span>
        </button>

        <!-- 保存按钮 -->
        <button
          type="button"
          class="save-btn"
          @click="handleSave"
          :disabled="isSaving || !hasChanges"
          :title="hasChanges ? t('configEditor.save.hasChanges') : t('configEditor.save.noChanges')"
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
          <span>{{ isSaving ? t('configEditor.save.saving') : t('configEditor.save.button') }}</span>
        </button>
      </div>
    </div>

    <!-- 配置节标签导航（仅表单模式显示且有多个配置节时） -->
    <div v-if="editMode === 'form' && sortedSchema.length > 1" class="section-tabs">
      <button
        v-for="(section, index) in sortedSchema"
        :key="section.name"
        type="button"
        class="section-tab"
        :class="{ active: activeSectionIndex === index }"
        @click="switchSection(index)"
        :title="section.description || section.title || section.name"
      >
        {{ section.title || section.name }}
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
        :schema="currentSectionSchema"
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
import { ref, computed, watch, onMounted } from 'vue'
import { parse as parseToml } from 'toml'
import { useI18n } from '@/utils/i18n'
import Icon from '../common/Icon.vue'
import TomlEditor from './TomlEditor.vue'
import FormEditor from './FormEditor.vue'
import { getRawConfig } from '@/api/modules/config'
import type { SectionSchema } from '@/api/types/config'
import { useToastStore } from '@/utils/toast'

const { t } = useI18n()

// Props
interface Props {
  title?: string
  configPath?: string
  configType?: 'bot' | 'model' | 'plugin'
  pluginName?: string
  schema?: SectionSchema[]
  modelValue?: Record<string, any>
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  schema: () => [],
  modelValue: () => ({}),
  readonly: false,
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
  save: [data: Record<string, any>]
}>()

// Toast 提示
const toast = useToastStore()

// 编辑模式：'code' | 'form'
const editMode = ref<'code' | 'form'>('form')

// 当前激活的配置节索引（仅表单模式使用）
const activeSectionIndex = ref(0)

// 表单数据（响应式）
const formData = ref<Record<string, any>>({ ...props.modelValue })

// 代码内容（TOML 字符串）
const codeContent = ref<string>('')

// 保存状态
const isSaving = ref(false)
const errorMessage = ref('')

// 原始数据（用于检测变更）
const originalData = ref<Record<string, any>>({ ...props.modelValue })

// 排序后的 schema（按 order 排序）
const sortedSchema = computed(() => {
  if (!props.schema || props.schema.length === 0) {
    return []
  }
  return [...props.schema].sort((a, b) => (a.order || 0) - (b.order || 0))
})

// 当前显示的配置节 schema（仅表单模式使用）
const currentSectionSchema = computed(() => {
  if (sortedSchema.value.length === 0) {
    return []
  }
  return [sortedSchema.value[activeSectionIndex.value]]
})

// 是否有未保存的更改
const hasChanges = computed(() => {
  return JSON.stringify(formData.value) !== JSON.stringify(originalData.value)
})

/**
 * 从后端获取原始 TOML 内容
 */
async function loadRawToml(): Promise<string> {
  if (!props.configType) {
    throw new Error(t('configEditor.errors.configTypeRequired'))
  }
  
  try {
    const rawContent = await getRawConfig(props.configType, props.pluginName)
    return rawContent
  } catch (error: any) {
    throw new Error(t('configEditor.errors.getRawTomlFailed', { error: error.message }))
  }
}

// 初始化时加载原始 TOML
onMounted(async () => {
  if (props.configType) {
    try {
      const rawToml = await loadRawToml()
      codeContent.value = rawToml
    } catch (error: any) {
      console.warn('加载原始 TOML 失败:', error)
      errorMessage.value = error.message
    }
  }
})

// 监听 modelValue 变化，更新表单数据
watch(
  () => props.modelValue,
  (newValue) => {
    formData.value = { ...newValue }
    originalData.value = { ...newValue }
  },
  { immediate: true, deep: true }
)

// 切换编辑模式
async function toggleMode() {
  if (editMode.value === 'code') {
    // 从代码模式切换到表单模式
    try {
      const parsed = parseToml(codeContent.value)
      formData.value = parsed
      errorMessage.value = ''
      // 重置到第一个配置节
      activeSectionIndex.value = 0
    } catch (error: any) {
      errorMessage.value = t('configEditor.errors.tomlParse', { error: error.message })
      return
    }
    editMode.value = 'form'
  } else {
    // 从表单模式切换到代码模式
    if (props.configType) {
      try {
        // 从后端重新加载原始 TOML
        const rawToml = await loadRawToml()
        codeContent.value = rawToml
        errorMessage.value = ''
      } catch (error: any) {
        errorMessage.value = t('configEditor.errors.loadRawToml', { error: error.message })
        return
      }
    }
    editMode.value = 'code'
  }
}

// 切换配置节
function switchSection(index: number) {
  if (index >= 0 && index < sortedSchema.value.length) {
    activeSectionIndex.value = index
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
        const errorMsg = t('configEditor.errors.tomlFormat', { error: error.message })
        errorMessage.value = errorMsg
        toast.show(errorMsg, 'error')
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
    
    // 显示成功提示
    toast.show(t('configEditor.save.success'), 'success')
  } catch (error: any) {
    const errorMsg = t('configEditor.save.failed', { error: error.message })
    errorMessage.value = errorMsg
    toast.show(errorMsg, 'error')
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
</script>

<style scoped>
.config-editor {
  display: flex;
  flex-direction: column;
  background: transparent;
  border-radius: 0;
  flex: 1;
  height: 100%;
  min-height: 0;
}

/* 固定的头部 */
.editor-header {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: 2;
}

/* 工具栏 */
.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: color-mix(in srgb, var(--md-sys-color-surface) 78%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  flex-shrink: 0;
}

/* 配置节标签导航 */
.section-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 16px;
  background: color-mix(in srgb, var(--md-sys-color-surface) 72%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  flex-shrink: 0;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--md-sys-color-outline-variant) transparent;
}

.section-tabs::-webkit-scrollbar {
  height: 6px;
}

.section-tabs::-webkit-scrollbar-track {
  background: transparent;
}

.section-tabs::-webkit-scrollbar-thumb {
  background: var(--md-sys-color-outline-variant);
  border-radius: 3px;
}

.section-tab {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  font-family: inherit;
  flex-shrink: 0;
}

.section-tab:hover {
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
}

.section-tab.active {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  font-weight: 600;
}

.section-tab.active:hover {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
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
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: color-mix(in srgb, var(--md-sys-color-surface) 80%, transparent);
  backdrop-filter: blur(16px);
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
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 85%, transparent);
}

/* ===== 移动端适配 ===== */
@media screen and (max-width: 768px) {
  .editor-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
  }

  .toolbar-left {
    width: 100%;
  }

  .toolbar-right {
    width: 100%;
    justify-content: space-between;
  }

  .mode-toggle-btn,
  .save-btn {
    flex: 1;
    justify-content: center;
  }

  .section-tabs {
    padding: 8px 12px;
    scrollbar-width: none;
  }
  .section-tabs::-webkit-scrollbar {
    display: none;
  }
  
  .section-tab {
    padding: 8px 16px;
    font-size: 13px;
  }
}
</style>
