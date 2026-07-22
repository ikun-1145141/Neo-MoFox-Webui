<script setup lang="ts">
/** SysDatePicker - 日期选择组件。 */
import { ref } from 'vue'

defineProps<{
  label?: string
  value?: string
  disabled?: boolean
  type?: string
  min?: string
  max?: string
}>()

const emit = defineEmits<{
  (e: 'change', value: string): void
}>()

const isFocused = ref(false)

function handleChange(event: Event): void {
  emit('change', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="sys-date-picker-wrapper">
    <label
      v-if="label"
      class="sys-date-picker-label"
      :class="{ 'sys-date-picker-label--focused': isFocused || (value !== undefined && value !== '') }"
    >{{ label }}</label>
    <div
      class="sys-date-picker-box"
      :class="{ 'sys-date-picker-box--focused': isFocused }"
    >
      <input
        :type="type || 'date'"
        class="sys-date-picker"
        :value="value"
        :disabled="disabled"
        :min="min"
        :max="max"
        @change="handleChange"
        @focus="isFocused = true"
        @blur="isFocused = false"
      >
    </div>
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
  color: var(--md-sys-color-on-surface-variant, #44474e);
  transition: color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-date-picker-label--focused {
  color: var(--md-sys-color-primary, #0058bd);
}

.sys-date-picker-box {
  display: flex;
  align-items: center;
  border: 1px solid var(--md-sys-color-outline, #74767f);
  border-radius: 8px;
  background: var(--md-sys-color-surface, #fff);
  transition:
    border-color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-date-picker-box--focused {
  border-color: var(--md-sys-color-primary, #0058bd);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 12%, transparent);
}

.sys-date-picker {
  flex: 1;
  padding: 0.625rem 0.75rem;
  border: none;
  background: transparent;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface, #1a1b20);
  outline: none;
  font-family: inherit;
  cursor: pointer;
}

.sys-date-picker:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
