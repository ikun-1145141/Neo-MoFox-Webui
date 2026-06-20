<script setup lang="ts">
/** SysSwitch - 开关组件。 */
const props = defineProps<{ label?: string; value?: string | boolean; disabled?: boolean }>()
const emit = defineEmits<{ (e: 'change', value: boolean): void }>()
function handleChange(event: Event): void { emit('change', (event.target as HTMLInputElement).checked) }
/** 将 value 解析为布尔值，支持 string 和 boolean 类型。 */
function isChecked(): boolean {
  if (typeof props.value === 'boolean') return props.value
  return props.value === 'true'
}
</script>
<template>
  <label class="sys-switch">
    <input type="checkbox" class="sys-switch-input" :checked="isChecked()" :disabled="disabled"
      @change="handleChange" />
    <span class="sys-switch-track"><span class="sys-switch-thumb" /></span>
    <span v-if="label" class="sys-switch-label">{{ label }}</span>
  </label>
</template>
<style scoped>
.sys-switch {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.sys-switch-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.sys-switch-track {
  position: relative;
  width: 40px;
  height: 24px;
  border-radius: 12px;
  background: var(--md-sys-color-surface-container-highest);
  transition: background 0.2s;
}

.sys-switch-input:checked+.sys-switch-track {
  background: var(--md-sys-color-primary);
}

.sys-switch-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--md-sys-color-on-surface-variant);
  transition: transform 0.2s, background 0.2s;
}

.sys-switch-input:checked+.sys-switch-track .sys-switch-thumb {
  transform: translateX(16px);
  background: var(--md-sys-color-on-primary);
}

.sys-switch-label {
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface);
}

.sys-switch-input:disabled~* {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
