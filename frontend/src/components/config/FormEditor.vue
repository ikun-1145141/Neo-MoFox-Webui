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
                  <div class="field-header">
                    <label :for="`${section.name}-${itemIndex}-${field.key}`" class="field-label">
                      <span class="field-title-zh">{{ getFieldTitle(field) }}</span>
                      <span class="field-name-en">{{ field.key }}</span>
                      <div v-if="getFieldDescriptionText(field)" class="field-tooltip">
                        <Icon icon="material-symbols:help-outline-rounded" :size="16" class="help-icon" />
                        <div class="tooltip-popup">{{ getFieldDescriptionText(field) }}</div>
                      </div>
                    </label>
                  </div>

                  <!-- 根据 input_type 渲染不同的输入控件 -->
                  <component
                    :is="getFieldComponent(getRenderableField(field).input_type, field.type)"
                    :id="`${section.name}-${itemIndex}-${field.key}`"
                    :model-value="item[field.key]"
                    @update:model-value="updateListItemField(section.name, itemIndex, field.key, $event)"
                    :field="getRenderableField(field)"
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
                <div class="field-header">
                  <label :for="`${section.name}-${field.key}`" class="field-label">
                    <span class="field-title-zh">{{ getFieldTitle(field) }}</span>
                    <span class="field-name-en">{{ field.key }}</span>
                    <div v-if="getFieldDescriptionText(field)" class="field-tooltip">
                      <Icon icon="material-symbols:help-outline-rounded" :size="16" class="help-icon" />
                      <div class="tooltip-popup">{{ getFieldDescriptionText(field) }}</div>
                    </div>
                  </label>
                </div>

                <!-- 根据 input_type 渲染不同的输入控件 -->
                <component
                  :is="getFieldComponent(getRenderableField(field).input_type, field.type)"
                  :id="`${section.name}-${field.key}`"
                  :model-value="getSectionData(section.name)[field.key]"
                  @update:model-value="updateObjectField(section.name, field.key, $event)"
                  :field="getRenderableField(field)"
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
import DictField from './fields/DictField.vue'
import SliderField from './fields/SliderField.vue'

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

type SelectOption = string | number | { label: string; value: string | number }

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

// Schema
const sortedSchema = computed(() => {
  return props.schema
})

// 切换节的展开/折叠
function toggleSection(index: number) {
  if (expandedSections.value.has(index)) {
    expandedSections.value.delete(index)
  } else {
    expandedSections.value.add(index)
  }
}

// 根据路径获取嵌套对象的值
function getValueByPath(obj: any, path: string): any {
  const keys = path.split('.')
  let current = obj
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key]
    } else {
      return undefined
    }
  }
  return current
}

// 根据路径设置嵌套对象的值
function setValueByPath(obj: any, path: string, value: any): any {
  const keys = path.split('.')
  const result = { ...obj }
  let current = result
  
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i]
    if (!current[key] || typeof current[key] !== 'object' || Array.isArray(current[key])) {
      current[key] = {}
    } else {
      current[key] = { ...current[key] }
    }
    current = current[key]
  }
  
  current[keys[keys.length - 1]] = value
  return result
}

// 获取节数据
function getSectionData(sectionName: string) {
  let data = getValueByPath(props.modelValue, sectionName)
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    // 初始化节数据
    const newValue = setValueByPath(props.modelValue, sectionName, {})
    emit('update:modelValue', newValue)
    return {}
  }
  return data
}

// 获取列表项
function getListItems(sectionName: string): any[] {
  const items = getValueByPath(props.modelValue, sectionName)
  if (!Array.isArray(items)) {
    // 初始化为空数组
    const newValue = setValueByPath(props.modelValue, sectionName, [])
    emit('update:modelValue', newValue)
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

  const newValue = setValueByPath(props.modelValue, sectionName, [...items, newItem])
  emit('update:modelValue', newValue)
}

// 删除列表项
function removeListItem(sectionName: string, index: number) {
  const items = getListItems(sectionName)
  const newItems = items.filter((_, i) => i !== index)

  const newValue = setValueByPath(props.modelValue, sectionName, newItems)
  emit('update:modelValue', newValue)
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
  const newValue = setValueByPath(props.modelValue, sectionName, newItems)
  emit('update:modelValue', newValue)
}

// 更新对象字段值
function updateObjectField(sectionName: string, fieldKey: string, value: any) {
  const sectionData = getSectionData(sectionName)
  const newSectionData = {
    ...sectionData,
    [fieldKey]: value
  }
  const newValue = setValueByPath(props.modelValue, sectionName, newSectionData)
  emit('update:modelValue', newValue)
}

function getRenderableField(field: FieldSchema): FieldSchema {
  const explicitChoices = normalizeChoices(field.choices)
  
  if (!hasChoices(explicitChoices)) {
    return field
  }

  return {
    ...field,
    input_type: 'select',
    choices: explicitChoices,
  }
}

function getFieldTitle(field: FieldSchema): string {
  // 优先使用 label，如果 label 等于 key 则返回 key
  return field.label && field.label !== field.key ? field.label : field.key
}

function getFieldDescriptionText(field: FieldSchema): string {
  // 优先使用 hint，没有则使用 description 作为帮助提示
  return field.hint || field.description || ''
}

function hasChoices(value: unknown): value is SelectOption[] {
  return Array.isArray(value) && value.length > 0
}

function normalizeChoices(choices: unknown): SelectOption[] {
  if (!Array.isArray(choices)) return []

  const normalized: SelectOption[] = []
  choices.forEach((choice) => {
    if (typeof choice === 'string' || typeof choice === 'number') {
      normalized.push({
        label: String(choice),
        value: choice,
      })
      return
    }

    if (
      choice &&
      typeof choice === 'object' &&
      'value' in choice &&
      (typeof choice.value === 'string' || typeof choice.value === 'number')
    ) {
      const value = choice.value
      const label = 'label' in choice && typeof choice.label === 'string'
        ? choice.label
        : String(value)

      normalized.push({
        label,
        value,
      })
    }
  })

  return normalized
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
      return NumberField
    case 'slider':
      return SliderField
    case 'switch':
    case 'boolean':
      return BooleanField
    case 'select':
    case 'multiselect':
      return SelectField
    case 'list':
      return ListField
    case 'dict':
    case 'object':
    case 'json':
      return DictField
    case 'text':
      // text 类型时，根据字段类型推断
      if (fieldType) {
        if (fieldType === 'bool') return BooleanField
        if (fieldType.includes('int') || fieldType.includes('float')) return NumberField
        if (fieldType.includes('list') || fieldType.includes('array')) return ListField
        if (fieldType.includes('dict') || fieldType.includes('object')) return DictField
      }
      return TextField
    default:
      // 未知 input_type，根据字段类型回退
      if (fieldType) {
        if (fieldType === 'bool') return BooleanField
        if (fieldType.includes('int') || fieldType.includes('float')) return NumberField
        if (fieldType.includes('list') || fieldType.includes('array')) return ListField
        if (fieldType.includes('dict') || fieldType.includes('object')) return DictField
      }
      return TextField
  }
}
</script>

<style scoped>
.form-editor {
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
  overflow: visible;
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
  border-radius: inherit;
}

.section-accordion.expanded .section-header {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
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
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  padding: 16px;
}

.list-item-card .form-field {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
}

.field-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 4px;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  min-width: 0;
}

.field-title-zh {
  font-size: 14px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  flex-shrink: 0;
}

.field-name-en {
  font-size: 13px;
  font-weight: 400;
  color: var(--md-sys-color-on-surface-variant);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.required-mark {
  color: var(--md-sys-color-error);
}

.field-tooltip {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: help;
  margin-left: 2px;
  flex-shrink: 0;
}

.help-icon {
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.6;
  transition: opacity 0.2s;
}

.field-tooltip:hover .help-icon {
  opacity: 1;
}

.tooltip-popup {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-4px);
  background: var(--md-sys-color-inverse-surface, #313033);
  color: var(--md-sys-color-inverse-on-surface, #f4eff4);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
  width: max-content;
  max-width: 260px;
  white-space: normal;
  z-index: 100;
  transition: all 0.2s;
  pointer-events: none;
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
  font-weight: normal;
  text-align: left;
}

.field-tooltip:hover .tooltip-popup {
  visibility: visible;
  opacity: 1;
  transform: translateX(-50%) translateY(-8px);
}

/* ===== 移动端适配 ===== */
@media screen and (max-width: 768px) {
  .form-editor {
    padding: 12px;
  }

  .section-header {
    padding: 12px 16px;
  }

  .section-content {
    padding: 0 16px 16px 16px;
  }

  .form-field {
    padding: 12px;
  }

  .tooltip-popup {
    left: auto;
    right: 0;
    transform: translateY(-4px);
  }

  .field-tooltip:hover .tooltip-popup {
    transform: translateY(-8px);
  }
}

/* 对象节样式 */
.object-section {
  background: transparent;
  border-radius: 12px;
  padding: 8px 0;
}
</style>
