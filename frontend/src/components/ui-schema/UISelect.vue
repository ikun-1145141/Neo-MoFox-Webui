<!--
  @file UISelect.vue
  @description 下拉选择框组件，支持静态选项和从 API 动态加载选项。
  消费共享工具：dataStore（getValueByPath / setValueByPath）、apiExecutor（executeApiCall / resolveEndpoint）。
-->
<template>
  <div class="ui-select" :class="{ 'has-error': touched && errorMessage }">
    <label v-if="node.attrs.label" :for="node.attrs.id" class="field-label">
      {{ node.attrs.label }}
      <span v-if="node.attrs.required === 'true'" class="required-star">*</span>
    </label>
    <div class="select-wrapper">
      <select
        :id="node.attrs.id"
        v-model="boundValue"
        :disabled="node.attrs.disabled === 'true' || loading"
        @blur="handleBlur"
        class="select-input"
      >
        <option
          v-for="(opt, idx) in options"
          :key="idx"
          :value="opt.value"
        >
          {{ opt.label }}
        </option>
      </select>
      <span class="material-symbols-outlined select-arrow">arrow_drop_down</span>
    </div>
    <span v-if="touched && errorMessage" class="error-message">{{ errorMessage }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, watch, onMounted } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import { getValueByPath, setValueByPath } from '@/utils/dataStore'
import { executeApiCall } from '@/utils/apiExecutor'
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
const injectedApiBase = inject<string>('uiSchemaApiBase', '')
const pluginName = inject<string | null>('uiSchemaPluginName', null)

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
const loading = ref(false)
const dynamicOptions = ref<Array<{ label: string; value: any }>>([])

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

// 提取静态选项
const staticOptions = computed(() => {
  return props.node.children
    .filter((child) => child.tag === 'option')
    .map((child) => ({
      label: child.text || child.attrs.value || '',
      value: child.attrs.value ?? '',
    }))
})

// 最终选项列表
const options = computed(() => {
  if (props.node.attrs['options-from-api'] === 'true') {
    return dynamicOptions.value
  }
  return staticOptions.value
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

// 加载动态选项
async function loadDynamicOptions() {
  const attrs = props.node.attrs
  if (attrs['options-from-api'] !== 'true' || !attrs['api-endpoint']) return

  loading.value = true
  try {
    const apiBaseVal = props.apiBase || injectedApiBase
    const res = await executeApiCall<any>({
      endpoint: attrs['api-endpoint'],
      method: 'GET',
      apiBase: apiBaseVal,
      pluginName,
    })

    const list = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : [])

    const labelKey = attrs['option-label-key'] || 'name'
    const valueKey = attrs['option-value-key'] || 'id'

    dynamicOptions.value = list.map((item: any) => ({
      label: item[labelKey] || String(item),
      value: item[valueKey] !== undefined ? item[valueKey] : item,
    }))
  } catch (e) {
    console.error('Failed to load dynamic select options:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDynamicOptions()
})

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
.ui-select {
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

.select-wrapper {
  position: relative;
  width: 100%;
}

.select-input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 40px 12px 16px;
  font-size: 14px;
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container-low);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  outline: none;
  transition: all 0.2s;
  font-family: inherit;
  appearance: none;
  cursor: pointer;
}

.select-input:focus {
  border-color: var(--md-sys-color-primary);
  background: var(--md-sys-color-surface);
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-primary-rgb), 0.12);
}

.select-input:disabled {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
  opacity: 0.38;
  cursor: not-allowed;
}

.select-arrow {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--md-sys-color-on-surface-variant);
  pointer-events: none;
  font-size: 24px;
}

.has-error .select-input {
  border-color: var(--md-sys-color-error);
}

.has-error .select-input:focus {
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-error-rgb), 0.12);
}

.error-message {
  font-size: 12px;
  color: var(--md-sys-color-error);
}
</style>
