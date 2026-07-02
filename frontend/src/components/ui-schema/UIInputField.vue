<!--
  @file UIInputField.vue
  @description 文本输入框组件，支持各种输入类型和校验。
  消费共享工具：dataStore（getValueByPath / setValueByPath）、formValidator（validateField）。
-->
<template>
  <div class="ui-input-field" :class="{ 'has-error': touched && errorMessage }">
    <label v-if="node.attrs.label" :for="node.attrs.id" class="field-label">
      {{ node.attrs.label }}
      <span v-if="node.attrs.required === 'true'" class="required-star">*</span>
    </label>
    <div class="input-wrapper">
      <input
        :id="node.attrs.id"
        :type="node.attrs.type || 'text'"
        v-model="boundValue"
        :placeholder="node.attrs.placeholder || ''"
        :disabled="node.attrs.disabled === 'true'"
        @blur="handleBlur"
        class="text-input"
      />
    </div>
    <span v-if="touched && errorMessage" class="error-message">{{ errorMessage }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, watch } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import { getValueByPath, setValueByPath } from '@/utils/dataStore'
import { validateField, type FieldRule } from '@/utils/formValidator'

interface Props {
  node: UiNode
  /** 页面级数据存储 */
  store?: Record<string, any>
  /** API 基础路径前缀 */
  apiBase?: string
}

const props = defineProps<Props>()

const dataStore = props.store || inject<any>('uiSchemaDataStore')
const getValue = inject<any>('uiSchemaGetValue', getValueByPath)
const setValue = inject<any>('uiSchemaSetValue', setValueByPath)

const bindPath = computed(() => props.node.attrs['data-bind'])

const boundValue = computed({
  get: () => {
    if (!bindPath.value) return ''
    return getValue(dataStore, bindPath.value) ?? ''
  },
  set: (val) => {
    if (!bindPath.value) return
    const type = props.node.attrs.type
    const parsedVal = type === 'number' && val !== '' ? Number(val) : val
    setValue(dataStore, bindPath.value, parsedVal)
  },
})

const touched = ref(false)
const errorMessage = ref('')

// 从节点属性构建 FieldRule
const fieldRule = computed<FieldRule>(() => {
  const a = props.node.attrs
  return {
    id: a.id || '',
    label: a.label,
    dataBind: a['data-bind'],
    type: a.type,
    required: a.required === 'true',
    minLength: a['min-length'] ? Number(a['min-length']) : undefined,
    maxLength: a['max-length'] ? Number(a['max-length']) : undefined,
    min: a.min ? Number(a.min) : undefined,
    max: a.max ? Number(a.max) : undefined,
    pattern: a.pattern,
    errorMessage: a['error-message'],
  }
})

function handleBlur() {
  touched.value = true
  runValidation(boundValue.value)
}

function runValidation(val: any): boolean {
  const error = validateField(fieldRule.value, val)
  errorMessage.value = error || ''
  return !error
}

// 监听绑定值，实时校验
watch(
  boundValue,
  (newVal) => {
    const isValid = runValidation(newVal)
    if (!dataStore.errors) {
      dataStore.errors = {}
    }
    if (!isValid) {
      dataStore.errors[props.node.attrs.id] = errorMessage.value
    } else {
      delete dataStore.errors[props.node.attrs.id]
    }
  },
  { immediate: true },
)

// 监听全局校验触发器
watch(
  () => dataStore?.validationTrigger,
  (trigger) => {
    if (trigger) {
      touched.value = true
      const isValid = runValidation(boundValue.value)
      if (!dataStore.errors) {
        dataStore.errors = {}
      }
      if (!isValid) {
        dataStore.errors[props.node.attrs.id] = errorMessage.value
      } else {
        delete dataStore.errors[props.node.attrs.id]
      }
    }
  },
)
</script>

<style scoped>
.ui-input-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface);
}

.required-star {
  color: var(--md-sys-color-error);
  margin-left: 2px;
}

.input-wrapper {
  position: relative;
  width: 100%;
}

.text-input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 16px;
  font-size: 14px;
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container-low);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  outline: none;
  transition: all 0.2s;
  font-family: inherit;
}

.text-input:focus {
  border-color: var(--md-sys-color-primary);
  background: var(--md-sys-color-surface);
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-primary-rgb), 0.12);
}

.text-input:disabled {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
  opacity: 0.38;
  cursor: not-allowed;
}

.has-error .text-input {
  border-color: var(--md-sys-color-error);
}

.has-error .text-input:focus {
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-error-rgb), 0.12);
}

.error-message {
  font-size: 12px;
  color: var(--md-sys-color-error);
}
</style>
