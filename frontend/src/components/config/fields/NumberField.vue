<!--
  @file NumberField.vue
  @description 数字输入字段组件
-->
<template>
  <input
    type="number"
    :value="modelValue"
    @input="handleInput"
    @blur="handleBlur"
    :readonly="readonly"
    :placeholder="field.placeholder || field.description || field.label"
    :min="minAttr"
    :max="maxAttr"
    :step="stepAttr"
    class="number-field"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FieldSchema } from '@/api/types/config'

interface Props {
  modelValue: number
  field: FieldSchema
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

const minAttr = computed(() => props.field.ge ?? props.field.gt ?? undefined)
const maxAttr = computed(() => props.field.le ?? props.field.lt ?? undefined)

const stepAttr = computed(() => {
  if (props.field.step != null) return props.field.step
  return props.field.type.includes('float') ? 'any' : undefined
})

function getStep(): number {
  if (props.field.step != null && props.field.step > 0) return props.field.step
  return props.field.type.includes('float') ? 1e-6 : 1
}

/** 将数字收敛到字段约束范围内，避免前端出现越界值。 */
function clampValue(value: number): number {
  const field = props.field
  let next = value

  if (field.ge != null && next < field.ge) next = field.ge
  if (field.gt != null && next <= field.gt) next = field.gt + getStep()
  if (field.le != null && next > field.le) next = field.le
  if (field.lt != null && next >= field.lt) next = field.lt - getStep()

  // 整数字段避免出现小数
  if (field.type.includes('int')) {
    next = Math.trunc(next)
  }

  return next
}

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  const parsed = parseFloat(target.value)

  if (!Number.isFinite(parsed)) {
    emit('update:modelValue', 0)
    return
  }

  const value = clampValue(parsed)

  // 输入值越界时立即回写输入框，确保界面上不会停留在越界数字。
  if (value !== parsed) {
    target.value = String(value)
  }

  emit('update:modelValue', value)
}

// 兜底处理自动填充、粘贴等不会触发 input 的场景。
function handleBlur(event: Event) {
  const target = event.target as HTMLInputElement
  const parsed = parseFloat(target.value)

  if (!Number.isFinite(parsed)) {
    target.value = String(props.modelValue ?? 0)
    return
  }

  const value = clampValue(parsed)
  if (value !== parsed) {
    target.value = String(value)
    emit('update:modelValue', value)
  }
}
</script>

<style scoped>
.number-field {
  width: 100%;
  padding: 12px 16px;
  font-size: 14px;
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  outline: none;
  transition: all 0.2s;
  font-family: inherit;
}

.number-field:focus {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 3px rgba(0, 88, 189, 0.1);
}

.number-field:read-only {
  background: var(--md-sys-color-surface-container-low);
  cursor: not-allowed;
}

.number-field::placeholder {
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.6;
}
</style>
