<!--
  @file UIDatePicker.vue
  @description 日期选择器组件，支持日期选择和校验。
  消费共享工具：dataStore（getValueByPath / setValueByPath）、formValidator（validateField）。
-->
<template>
  <div class="ui-date-picker" :class="{ 'has-error': touched && errorMessage }">
    <label v-if="node.attrs.label" :for="node.attrs.id" class="field-label">
      {{ node.attrs.label }}
      <span v-if="node.attrs.required === 'true'" class="required-star">*</span>
    </label>
    <div class="input-wrapper">
      <input
        type="date"
        :id="node.attrs.id"
        v-model="boundValue"
        :min="node.attrs['min-date'] || undefined"
        :max="node.attrs['max-date'] || undefined"
        :disabled="node.attrs.disabled === 'true'"
        @blur="handleBlur"
        class="date-input"
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
    errorMessage: a['error-message'],
  }
})

function handleBlur() {
  touched.value = true
  runValidation(boundValue.value)
}

function runValidation(val: any): boolean {
  // 先用 formValidator 做基础校验
  const baseError = validateField(fieldRule.value, val)
  if (baseError) {
    errorMessage.value = baseError
    return false
  }

  // 日期范围校验
  const attrs = props.node.attrs
  const minDate = attrs['min-date']
  const maxDate = attrs['max-date']
  const customError = attrs['error-message']

  if (val !== undefined && val !== null && val !== '') {
    if (minDate && val < minDate) {
      errorMessage.value = customError || `日期不能早于 ${minDate}`
      return false
    }
    if (maxDate && val > maxDate) {
      errorMessage.value = customError || `日期不能晚于 ${maxDate}`
      return false
    }
  }

  errorMessage.value = ''
  return true
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
.ui-date-picker {
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

.date-input {
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

.date-input:focus {
  border-color: var(--md-sys-color-primary);
  background: var(--md-sys-color-surface);
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-primary-rgb), 0.12);
}

.date-input:disabled {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
  opacity: 0.38;
  cursor: not-allowed;
}

.has-error .date-input {
  border-color: var(--md-sys-color-error);
}

.has-error .date-input:focus {
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-error-rgb), 0.12);
}

.error-message {
  font-size: 12px;
  color: var(--md-sys-color-error);
}
</style>
