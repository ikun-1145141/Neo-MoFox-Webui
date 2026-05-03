<!--
  @file BooleanField.vue
  @description 布尔值开关字段组件
-->
<template>
  <div class="boolean-field">
    <label class="switch">
      <input
        type="checkbox"
        :checked="modelValue"
        @change="handleChange"
        :disabled="readonly"
      />
      <span class="slider"></span>
    </label>
    <span class="value-label">{{ modelValue ? '启用' : '禁用' }}</span>
  </div>
</template>

<script setup lang="ts">
import type { FieldSchema } from '@/api/types/config'

interface Props {
  modelValue: boolean
  field: FieldSchema
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function handleChange(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.checked)
}
</script>

<style scoped>
.boolean-field {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch {
  position: relative;
  display: inline-block;
  width: 52px;
  height: 32px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: var(--md-sys-color-surface-container-highest);
  border: 2px solid var(--md-sys-color-outline);
  transition: 0.3s;
  border-radius: 34px;
}

.slider:before {
  position: absolute;
  content: '';
  height: 20px;
  width: 20px;
  left: 4px;
  bottom: 4px;
  background-color: var(--md-sys-color-outline);
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: var(--md-sys-color-primary);
  border-color: var(--md-sys-color-primary);
}

input:checked + .slider:before {
  transform: translateX(20px);
  background-color: var(--md-sys-color-on-primary);
}

input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}

.value-label {
  font-size: 14px;
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 500;
}
</style>
