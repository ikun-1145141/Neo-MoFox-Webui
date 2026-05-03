<!--
  @file SelectField.vue
  @description 选择字段组件（下拉选择）
-->
<template>
  <select
    :value="modelValue"
    @change="handleChange"
    :disabled="readonly"
    class="select-field"
  >
    <option value="">-- 请选择 --</option>
    <option
      v-for="(choice, index) in field.choices"
      :key="index"
      :value="choice"
    >
      {{ choice }}
    </option>
  </select>
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
  'update:modelValue': [value: string | number]
}>()

function handleChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<style scoped>
.select-field {
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
  cursor: pointer;
}

.select-field:focus {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 3px rgba(0, 88, 189, 0.1);
}

.select-field:disabled {
  background: var(--md-sys-color-surface-container-low);
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
