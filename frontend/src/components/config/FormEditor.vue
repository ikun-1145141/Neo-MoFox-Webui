<!--
  @file FormEditor.vue
  @description 基于 Schema 的可视化表单编辑器
  
  功能：
  - 根据 SectionSchema 动态生成表单
  - 折叠面板布局（Accordion）
  - 支持多种字段类型（text、number、boolean、select 等）
  - 实时数据校验
  - Material Design 3 样式
-->
<template>
  <div class="form-editor">
    <div v-if="!schema || schema.length === 0" class="empty-state">
      <Icon icon="material-symbols:info-outline-rounded" :size="48" />
      <p>暂无配置项</p>
    </div>

    <div v-else class="form-sections">
      <!-- 遍历配置节 -->
      <div
        v-for="(section, sectionIndex) in sortedSchema"
        :key="section.name"
        class="section-accordion"
        :class="{
          expanded: expandedSections.has(sectionIndex),
          'single-section': sortedSchema.length === 1
        }"
      >
        <!-- 节标题（可点击折叠/展开）- 多个配置节时显示 -->
        <div
          v-if="sortedSchema.length > 1"
          class="section-header"
          @click="toggleSection(sectionIndex)"
          :title="`点击${expandedSections.has(sectionIndex) ? '折叠' : '展开'}`"
        >
          <div class="section-header-content">
            <Icon
              :icon="
                expandedSections.has(sectionIndex)
                  ? 'material-symbols:expand-more-rounded'
                  : 'material-symbols:chevron-right-rounded'
              "
              :size="24"
              class="expand-icon"
            />
            <div class="section-title-group">
              <h3 class="section-title">{{ section.title || section.name }}</h3>
              <p v-if="section.description" class="section-description">
                {{ section.description }}
              </p>
            </div>
          </div>
          <span v-if="section.is_list" class="list-badge">列表</span>
        </div>

        <!-- 节内容（折叠面板 或 直接显示） -->
        <div
          v-show="sortedSchema.length === 1 || expandedSections.has(sectionIndex)"
          class="section-content"
          :class="{ 'single-section-content': sortedSchema.length === 1 }"
        >
          <!-- 列表类型的节（如 models、api_providers） -->
          <div v-if="section.is_list" class="list-section">
            <div
              v-for="(item, itemIndex) in getListItems(section.name)"
              :key="itemIndex"
              class="list-item-card"
            >
              <div class="list-item-header">
                <span class="list-item-index">#{{ itemIndex + 1 }}</span>
                <button
                  type="button"
                  class="icon-btn delete-btn"
                  @click="removeListItem(section.name, itemIndex)"
                  title="删除"
                >
                  <Icon icon="material-symbols:delete-outline-rounded" :size="20" />
                </button>
              </div>
              <div class="form-fields">
                <div
                  v-for="field in section.fields"
                  :key="field.key"
                  class="form-field"
                >
                  <label :for="`${section.name}-${itemIndex}-${field.key}`" class="field-label">
                    {{ field.label || field.key }}
                  </label>
                  <p v-if="field.description" class="field-description">{{ field.description }}</p>

                  <!-- 根据 input_type 渲染不同的输入控件 -->
                  <component
                    :is="getFieldComponent(field.input_type, field.type)"
                    :id="`${section.name}-${itemIndex}-${field.key}`"
                    :model-value="item[field.key]"
                    @update:model-value="updateListItemField(section.name, itemIndex, field.key, $event)"
                    :field="field"
                    :readonly="readonly"
                  />
                </div>
              </div>
            </div>

            <!-- 添加新项按钮 -->
            <button type="button" class="add-item-btn" @click="addListItem(section.name, section.fields)">
              <Icon icon="material-symbols:add-rounded" :size="20" />
              <span>添加 {{ section.title || section.name }}</span>
            </button>
          </div>

          <!-- 普通对象类型的节 -->
          <div v-else class="object-section">
            <div class="form-fields">
              <div
                v-for="field in section.fields"
                :key="field.key"
                class="form-field"
              >
                <label :for="`${section.name}-${field.key}`" class="field-label">
                  {{ field.label || field.key }}
                </label>
                <p v-if="field.description" class="field-description">{{ field.description }}</p>

                <!-- 根据 input_type 渲染不同的输入控件 -->
                <component
                  :is="getFieldComponent(field.input_type, field.type)"
                  :id="`${section.name}-${field.key}`"
                  :model-value="getSectionData(section.name)[field.key]"
                  @update:model-value="updateObjectField(section.name, field.key, $event)"
                  :field="field"
                  :readonly="readonly"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Icon from '../common/Icon.vue'
import type { SectionSchema, FieldSchema } from '@/api/types/config'

// 导入字段组件
import TextField from './fields/TextField.vue'
import NumberField from './fields/NumberField.vue'
import BooleanField from './fields/BooleanField.vue'
import SelectField from './fields/SelectField.vue'
import TextareaField from './fields/TextareaField.vue'
import ListField from './fields/ListField.vue'

// Props
interface Props {
  schema?: SectionSchema[]
  modelValue?: Record<string, any>
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  schema: () => [],
  modelValue: () => ({}),
  readonly: false,
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
}>()

// 展开状态（默认全部展开）
const expandedSections = ref<Set<number>>(new Set())

// 初始化展开第一个节（或单个节时总是展开）
watch(
  () => props.schema,
  (newSchema) => {
    if (newSchema && newSchema.length > 0) {
      if (newSchema.length === 1) {
        // 单个配置节时，总是展开
        expandedSections.value = new Set([0])
      } else if (expandedSections.value.size === 0) {
        // 多个配置节时，默认展开第一个
        expandedSections.value.add(0)
      }
    }
  },
  { immediate: true }
)

// 排序后的配置节（按 order 字段）
const sortedSchema = computed(() => {
  return [...props.schema].sort((a, b) => a.order - b.order)
})

// 切换节的展开/折叠
function toggleSection(index: number) {
  if (expandedSections.value.has(index)) {
    expandedSections.value.delete(index)
  } else {
    expandedSections.value.add(index)
  }
}

// 获取节数据
function getSectionData(sectionName: string) {
  if (!props.modelValue[sectionName]) {
    // 初始化节数据
    emit('update:modelValue', {
      ...props.modelValue,
      [sectionName]: {},
    })
  }
  return props.modelValue[sectionName] || {}
}

// 获取列表项
function getListItems(sectionName: string): any[] {
  const items = props.modelValue[sectionName]
  if (!Array.isArray(items)) {
    // 初始化为空数组
    emit('update:modelValue', {
      ...props.modelValue,
      [sectionName]: [],
    })
    return []
  }
  return items
}

// 添加列表项
function addListItem(sectionName: string, fields: FieldSchema[]) {
  const items = getListItems(sectionName)
  const newItem: Record<string, any> = {}

  // 根据字段默认值初始化新项
  fields.forEach((field) => {
    newItem[field.key] = field.default !== undefined ? field.default : getDefaultValueForType(field.type)
  })

  emit('update:modelValue', {
    ...props.modelValue,
    [sectionName]: [...items, newItem],
  })
}

// 删除列表项
function removeListItem(sectionName: string, index: number) {
  const items = getListItems(sectionName)
  const newItems = items.filter((_, i) => i !== index)

  emit('update:modelValue', {
    ...props.modelValue,
    [sectionName]: newItems,
  })
}

// 根据类型获取默认值
function getDefaultValueForType(type: string): any {
  if (type.includes('int') || type.includes('float')) return 0
  if (type === 'bool') return false
  if (type.includes('list') || type.includes('array')) return []
  if (type.includes('dict') || type.includes('object')) return {}
  return ''
}

// 更新列表项字段值
function updateListItemField(sectionName: string, itemIndex: number, fieldKey: string, value: any) {
  const items = getListItems(sectionName)
  const newItems = [...items]
  newItems[itemIndex] = {
    ...newItems[itemIndex],
    [fieldKey]: value
  }
  emit('update:modelValue', {
    ...props.modelValue,
    [sectionName]: newItems,
  })
}

// 更新对象字段值
function updateObjectField(sectionName: string, fieldKey: string, value: any) {
  const sectionData = getSectionData(sectionName)
  emit('update:modelValue', {
    ...props.modelValue,
    [sectionName]: {
      ...sectionData,
      [fieldKey]: value
    },
  })
}

// 根据字段类型和 input_type 获取对应的字段组件
function getFieldComponent(inputType: string, fieldType?: string) {
  // 优先使用 input_type
  switch (inputType) {
    case 'password':
    case 'email':
    case 'url':
      return TextField
    case 'textarea':
      return TextareaField
    case 'number':
    case 'slider':
      return NumberField
    case 'switch':
    case 'boolean':
      return BooleanField
    case 'select':
    case 'multiselect':
      return SelectField
    case 'list':
      return ListField
    case 'text':
      // text 类型时，根据字段类型推断
      if (fieldType) {
        if (fieldType === 'bool') return BooleanField
        if (fieldType.includes('int') || fieldType.includes('float')) return NumberField
        if (fieldType.includes('list') || fieldType.includes('array')) return ListField
      }
      return TextField
    default:
      // 未知 input_type，根据字段类型回退
      if (fieldType) {
        if (fieldType === 'bool') return BooleanField
        if (fieldType.includes('int') || fieldType.includes('float')) return NumberField
        if (fieldType.includes('list') || fieldType.includes('array')) return ListField
      }
      return TextField
  }
}
</script>

<style scoped>
.form-editor {
  height: 100%;
  overflow-y: auto;
  padding: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--md-sys-color-on-surface-variant);
  gap: 12px;
}

.form-sections {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 折叠面板样式 */
.section-accordion {
  background: var(--md-sys-color-surface-container-low);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.section-accordion.expanded {
  background: var(--md-sys-color-surface-container);
}

/* 单个配置节时的简化样式 */
.section-accordion.single-section {
  border: none;
  background: transparent;
  border-radius: 0;
}

.section-content.single-section-content {
  padding: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.section-header:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.section-header-content {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.expand-icon {
  color: var(--md-sys-color-on-surface-variant);
  transition: transform 0.2s;
  flex-shrink: 0;
}

.section-accordion.expanded .expand-icon {
  transform: rotate(0deg);
}

.section-title-group {
  flex: 1;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

.section-description {
  font-size: 13px;
  color: var(--md-sys-color-on-surface-variant);
  margin: 4px 0 0 0;
}

.list-badge {
  padding: 4px 12px;
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
}

.section-content {
  padding: 0 20px 20px 20px;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 列表节样式 */
.list-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-item-card {
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  padding: 16px;
}

.list-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.list-item-index {
  font-size: 14px;
  font-weight: 600;
  color: var(--md-sys-color-primary);
}

.icon-btn {
  background: none;
  border: none;
  color: var(--md-sys-color-on-surface-variant);
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.delete-btn {
  color: var(--md-sys-color-error);
}

.delete-btn:hover {
  background: var(--md-sys-color-error-container);
}

.add-item-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px 16px;
  background: var(--md-sys-color-surface);
  border: 2px dashed var(--md-sys-color-outline-variant);
  border-radius: 12px;
  color: var(--md-sys-color-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.add-item-btn:hover {
  background: var(--md-sys-color-primary-container);
  border-color: var(--md-sys-color-primary);
}

/* 表单字段样式 */
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface);
  display: flex;
  align-items: center;
  gap: 4px;
}

.required-mark {
  color: var(--md-sys-color-error);
}

.field-description {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0;
  line-height: 1.4;
}

/* 对象节样式 */
.object-section {
  background: var(--md-sys-color-surface);
  border-radius: 12px;
  padding: 16px;
}
</style>
