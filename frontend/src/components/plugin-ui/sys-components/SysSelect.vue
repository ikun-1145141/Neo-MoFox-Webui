<script setup lang="ts">
/** SysSelect - 下拉选择组件。 */
import { ref, watch } from 'vue'

const props = defineProps<{
  label?: string
  value?: string
  disabled?: boolean
  placeholder?: string
  error?: string
}>()

const emit = defineEmits<{
  (e: 'change', value: string): void
  (e: 'focus', ev: FocusEvent): void
  (e: 'blur', ev: FocusEvent): void
}>()

const isFocused = ref(false)
const shakeKey = ref(0)

watch(
  () => props.error,
  (err, prev) => {
    if (err && err !== prev) shakeKey.value++
  }
)

function handleChange(event: Event): void {
  emit('change', (event.target as HTMLSelectElement).value)
}
function onFocus(ev: FocusEvent) {
  isFocused.value = true
  emit('focus', ev)
}
function onBlur(ev: FocusEvent) {
  isFocused.value = false
  emit('blur', ev)
}
</script>

<template>
  <div class="sys-select-wrapper">
    <label
      v-if="label"
      class="sys-select-label"
      :class="{ 'sys-select-label--focused': isFocused || (value !== undefined && value !== '') }"
    >{{ label }}</label>
    <div
      class="sys-select-box"
      :class="{ 'sys-select-box--focused': isFocused, 'sys-select-box--error': !!error }"
    >
      <select
        class="sys-select"
        :value="value"
        :disabled="disabled"
        @change="handleChange"
        @focus="onFocus"
        @blur="onBlur"
      >
        <option
          v-if="placeholder"
          value=""
          disabled
        >{{ placeholder }}</option>
        <slot />
      </select>
      <span class="sys-select-arrow material-symbols-rounded">expand_more</span>
    </div>
    <Transition name="sys-fade">
      <span
        v-if="error"
        :key="shakeKey"
        class="sys-select-error"
      >{{ error }}</span>
    </Transition>
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
  color: var(--md-sys-color-on-surface-variant, #44474e);
  transition: color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-select-label--focused {
  color: var(--md-sys-color-primary, #0058bd);
}

.sys-select-box {
  position: relative;
  display: flex;
  align-items: center;
  border: 1px solid var(--md-sys-color-outline, #74767f);
  border-radius: 8px;
  background: var(--md-sys-color-surface, #fff);
  transition:
    border-color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-select-box--focused {
  border-color: var(--md-sys-color-primary, #0058bd);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 12%, transparent);
}

.sys-select-box--error {
  border-color: var(--md-sys-color-error, #ba1a1a);
}

.sys-select-box--error.sys-select-box--focused {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--md-sys-color-error, #ba1a1a) 12%, transparent);
}

.sys-select {
  flex: 1;
  padding: 0.625rem 0.875rem;
  padding-right: 36px;
  border: none;
  background: transparent;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface, #1a1b20);
  outline: none;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  font-family: inherit;
}

.sys-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sys-select-arrow {
  position: absolute;
  right: 8px;
  font-size: 20px;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  pointer-events: none;
  transition: transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
}

.sys-select-box--focused .sys-select-arrow {
  transform: rotate(180deg);
}

.sys-select-error {
  font-size: 0.75rem;
  color: var(--md-sys-color-error, #ba1a1a);
  animation: sys-shake 0.4s var(--md-sys-motion-emphasized);
}
</style>
