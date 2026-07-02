<!--
  @file UITextarea.vue
  @description 文本域输入组件，支持多行文本输入和校验。
  消费共享工具：dataStore（getValueByPath / setValueByPath）、formValidator（validateField）。
-->
<template>
  <div class="ui-textarea" :class="{ 'has-error': touched && errorMessage }">
    <label v-if="node.attrs.label" :for="node.attrs.id" class="field-label">
      {{ node.attrs.label }}
      <span v-if="node.attrs.required === 'true'" class="required-star">*</span>
    </label>
    <div class="textarea-wrapper">
      <textarea
        :id="node.attrs.id"
        v-model="boundValue"
        :rows="Number(node.attrs.rows || 3)"
        :placeholder="node.attrs.placeholder || ''"
        :disabled="node.attrs.disabled === 'true'"
        @blur="handleBlur"
        class="textarea-input"
      ></textarea>
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
  store?: Record<string, any>
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
    setValue(dataStore, bindPath.value, val)
  },
})

const touched = ref(false)
const errorMessage = ref('')

const fieldRule = computed<FieldRule>(() => {
  const a = props.node.attrs
  return {
    id: a.id || '',
    label: a.label,
    dataBind: a['data-bind'],
    required: a.required === 'true',
    minLength: a['min-length'] ? Number(a['min-length']) : undefined,
    maxLength: a['max-length'] ? Number(a['max-length']) : undefined,
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

watch(
  boundValue,
  (newVal) => {
    const isValid = runValidation(newVal)
    if (!dataStore.errors) dataStore.errors = {}
    if (!isValid) {
      dataStore.errors[props.node.attrs.id] = errorMessage.value
    } else {
      delete dataStore.errors[props.node.attrs.id]
    }
  },
  { immediate: true },
)

watch(
  () => dataStore?.validationTrigger,
  (trigger) => {
    if (trigger) {
      touched.value = true
      const isValid = runValidation(boundValue.value)
      if (!dataStore.errors) dataStore.errors = {}
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
.ui-textarea {
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

.textarea-wrapper {
  position: relative;
  width: 100%;
}

.textarea-input {
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
  resize: vertical;
}

.textarea-input:focus {
  border-color: var(--md-sys-color-primary);
  background: var(--md-sys-color-surface);
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-primary-rgb), 0.12);
}

.textarea-input:disabled {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
  opacity: 0.38;
  cursor: not-allowed;
}

.has-error .textarea-input {
  border-color: var(--md-sys-color-error);
}

.has-error .textarea-input:focus {
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-error-rgb), 0.12);
}

.error-message {
  font-size: 12px;
  color: var(--md-sys-color-error);
}
</style>
