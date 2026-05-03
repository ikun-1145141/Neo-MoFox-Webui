<!--
  @file TextareaField.vue
  @description 多行文本字段组件
-->
<template>
  <textarea
    :value="modelValue"
    @input="handleInput"
    :readonly="readonly"
    :placeholder="field.placeholder || field.description || field.label"
    :rows="field.rows || 4"
    class="textarea-field"
  ></textarea>
</template>

<script setup lang="ts">
import type { FieldSchema } from '@/api/types/config'

interface Props {
  modelValue: string
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
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}
</script>

<style scoped>
.textarea-field {
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
  resize: vertical;
  min-height: 100px;
}

.textarea-field:focus {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 3px rgba(0, 88, 189, 0.1);
}

.textarea-field:read-only {
  background: var(--md-sys-color-surface-container-low);
  cursor: not-allowed;
  resize: none;
}

.textarea-field::placeholder {
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.6;
}
</style>
