<script setup lang="ts">
/** SysTextarea - 多行文本输入组件。 */
import { ref, watch } from 'vue'

const props = defineProps<{
  label?: string
  placeholder?: string
  value?: string
  disabled?: boolean
  rows?: string
  error?: string
  maxlength?: string | number
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

function handleInput(event: Event): void {
  emit('change', (event.target as HTMLTextAreaElement).value)
}
</script>

<template>
  <div class="sys-textarea-wrapper">
    <label
      v-if="label"
      class="sys-textarea-label"
      :class="{ 'sys-textarea-label--focused': isFocused || (value !== undefined && value !== '') }"
    >{{ label }}</label>
    <textarea
      class="sys-textarea"
      :class="{ 'sys-textarea--error': error, 'sys-textarea--focused': isFocused }"
      :placeholder="placeholder"
      :value="value"
      :disabled="disabled"
      :rows="parseInt(rows || '3')"
      :maxlength="maxlength ? parseInt(String(maxlength)) : undefined"
      @input="handleInput"
      @focus="isFocused = true; $emit('focus', $event)"
      @blur="isFocused = false; $emit('blur', $event)"
    />
    <Transition name="sys-fade">
      <span
        v-if="error"
        :key="shakeKey"
        class="sys-textarea-error"
      >{{ error }}</span>
    </Transition>
  </div>
</template>

<style scoped>
.sys-textarea-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.sys-textarea-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  transition: color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-textarea-label--focused {
  color: var(--md-sys-color-primary, #0058bd);
}

.sys-textarea {
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--md-sys-color-outline, #74767f);
  border-radius: 8px;
  font-size: 0.875rem;
  background: var(--md-sys-color-surface, #fff);
  color: var(--md-sys-color-on-surface, #1a1b20);
  outline: none;
  resize: vertical;
  font-family: inherit;
  min-height: 80px;
  transition:
    border-color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-textarea--focused {
  border-color: var(--md-sys-color-primary, #0058bd);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 12%, transparent);
}

.sys-textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sys-textarea--error {
  border-color: var(--md-sys-color-error, #ba1a1a);
}

.sys-textarea--error.sys-textarea--focused {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--md-sys-color-error, #ba1a1a) 12%, transparent);
}

.sys-textarea-error {
  font-size: 0.75rem;
  color: var(--md-sys-color-error, #ba1a1a);
  animation: sys-shake 0.4s var(--md-sys-motion-emphasized);
}
</style>
