<script setup lang="ts">
/** SysTextarea - 多行文本输入组件。 */
defineProps<{ label?: string; placeholder?: string; value?: string; disabled?: boolean; rows?: string; error?: string }>()
const emit = defineEmits<{ (e: 'change', value: string): void }>()
function handleInput(event: Event): void { emit('change', (event.target as HTMLTextAreaElement).value) }
</script>
<template>
  <div class="sys-textarea-wrapper">
    <label v-if="label" class="sys-textarea-label">{{ label }}</label>
    <textarea class="sys-textarea" :class="{ 'sys-textarea--error': error }" :placeholder="placeholder" :value="value"
      :disabled="disabled" :rows="parseInt(rows || '3')" @input="handleInput" />
    <span v-if="error" class="sys-textarea-error">{{ error }}</span>
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
  color: var(--md-sys-color-on-surface-variant);
}

.sys-textarea {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 8px;
  font-size: 0.875rem;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  outline: none;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.15s;
}

.sys-textarea:focus {
  border-color: var(--md-sys-color-primary);
}

.sys-textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sys-textarea--error {
  border-color: var(--md-sys-color-error);
}

.sys-textarea-error {
  font-size: 0.75rem;
  color: var(--md-sys-color-error);
}
</style>
