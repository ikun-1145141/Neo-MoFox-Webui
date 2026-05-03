<!--
  @file TextField.vue  @description 文本输入字段组件
-->
<template>
  <input
    :type="field.input_type"
    :value="modelValue"
    @input="handleInput"
    :readonly="readonly"
    :placeholder="field.placeholder || field.description || field.label"
    :pattern="field.pattern || undefined"
    class="text-field"
  />
</template>

<script setup lang="ts">
import type { FieldSchema } from '@/api/types/config'

interface Props {
  modelValue: string | number
  field: FieldSchema
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}
</script>

<style scoped>
.text-field {
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

.text-field:focus {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 3px rgba(0, 88, 189, 0.1);
}

.text-field:read-only {
  background: var(--md-sys-color-surface-container-low);
  cursor: not-allowed;
}

.text-field::placeholder {
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.6;
}
</style>
