<script setup lang="ts">
/** SysSwitch - 开关组件。 */
import { computed } from 'vue'

const props = defineProps<{
  label?: string
  value?: string | boolean
  disabled?: boolean
  color?: string
}>()

const emit = defineEmits<{
  (e: 'change', value: boolean): void
}>()

function isChecked(): boolean {
  if (typeof props.value === 'boolean') return props.value
  return props.value === 'true'
}

function handleChange(event: Event): void {
  emit('change', (event.target as HTMLInputElement).checked)
}

const trackColor = computed(() => {
  if (props.color) {
    return isChecked() ? props.color : undefined
  }
  return undefined
})
</script>

<template>
  <label
    class="sys-switch"
    :class="{ 'sys-switch--disabled': disabled }"
  >
    <input
      type="checkbox"
      class="sys-switch-input"
      :checked="isChecked()"
      :disabled="disabled"
      @change="handleChange"
    >
    <span
      class="sys-switch-track"
      :class="{ 'sys-switch-track--checked': isChecked() }"
      :style="{ background: isChecked() ? trackColor : undefined }"
    >
      <span class="sys-switch-thumb" />
    </span>
    <span
      v-if="label"
      class="sys-switch-label"
    >{{ label }}</span>
  </label>
</template>

<style scoped>
.sys-switch {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.sys-switch--disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.sys-switch-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.sys-switch-track {
  position: relative;
  width: 52px;
  height: 32px;
  border-radius: 16px;
  background: var(--md-sys-color-surface-container-highest, #e6e0e9);
  border: 2px solid var(--md-sys-color-outline, #74767f);
  transition:
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    border-color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-switch-track--checked {
  background: var(--md-sys-color-primary, #0058bd);
  border-color: var(--md-sys-color-primary, #0058bd);
}

.sys-switch-thumb {
  position: absolute;
  top: 50%;
  left: 8px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--md-sys-color-outline, #74767f);
  transform: translateY(-50%);
  transition:
    transform var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized),
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    width var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized),
    height var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
}

.sys-switch-track--checked .sys-switch-thumb {
  transform: translate(20px, -50%);
  background: var(--md-sys-color-on-primary, #fff);
}

/* 拖动态拉长（active 时） */
.sys-switch-input:active:not(:disabled) + .sys-switch-track .sys-switch-thumb {
  width: 24px;
}

.sys-switch-input:active:not(:disabled) + .sys-switch-track--checked .sys-switch-thumb {
  transform: translate(12px, -50%);
}

.sys-switch-label {
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface, #1a1b20);
}
</style>
