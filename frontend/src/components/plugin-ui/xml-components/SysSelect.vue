<script setup lang="ts">
/** SysSelect - 下拉选择组件。 */
defineProps<{ label?: string; options?: string; value?: string; disabled?: boolean; placeholder?: string }>()
const emit = defineEmits<{ (e: 'change', value: string): void }>()
function handleChange(event: Event): void { emit('change', (event.target as HTMLSelectElement).value) }
</script>
<template>
  <div class="sys-select-wrapper">
    <label v-if="label" class="sys-select-label">{{ label }}</label>
    <select class="sys-select" :value="value" :disabled="disabled" @change="handleChange">
      <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
      <slot />
    </select>
  </div>
</template>
<style scoped>
.sys-select-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.sys-select-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
}

.sys-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 8px;
  font-size: 0.875rem;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  outline: none;
  cursor: pointer;
}

.sys-select:focus {
  border-color: var(--md-sys-color-primary);
}

.sys-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
