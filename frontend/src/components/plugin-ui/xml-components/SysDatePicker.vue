<script setup lang="ts">
/** SysDatePicker - 日期选择组件。 */
defineProps<{ label?: string; value?: string; disabled?: boolean; type?: string }>()
const emit = defineEmits<{ (e: 'change', value: string): void }>()
function handleChange(event: Event): void { emit('change', (event.target as HTMLInputElement).value) }
</script>
<template>
  <div class="sys-date-picker-wrapper">
    <label v-if="label" class="sys-date-picker-label">{{ label }}</label>
    <input :type="type || 'date'" class="sys-date-picker" :value="value" :disabled="disabled" @change="handleChange" />
  </div>
</template>
<style scoped>
.sys-date-picker-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.sys-date-picker-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
}

.sys-date-picker {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 8px;
  font-size: 0.875rem;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  outline: none;
}

.sys-date-picker:focus {
  border-color: var(--md-sys-color-primary);
}

.sys-date-picker:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
