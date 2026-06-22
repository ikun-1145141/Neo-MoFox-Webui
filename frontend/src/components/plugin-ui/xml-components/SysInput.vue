<script setup lang="ts">
/**
 * SysInput - 输入框组件。
 */
defineProps<{
  /** 输入框标签 */
  label?: string
  /** 占位文本 */
  placeholder?: string
  /** 输入类型 */
  type?: string
  /** 当前值 */
  value?: string
  /** 是否禁用 */
  disabled?: boolean
  /** 错误提示 */
  error?: string
  /** 绑定的变量路径 */
  bind_value?: string
  /** 渲染上下文 */
  __xmlContext?: any
}>()

const emit = defineEmits<{
  (e: 'change', value: string): void
}>()

function handleInput(event: Event): void {
  const target = event.target as HTMLInputElement
  emit('change', target.value)
}
</script>

<template>
  <div class="sys-input-wrapper">
    <label v-if="label" class="sys-input-label">{{ label }}</label>
    <input
      class="sys-input"
      :class="{ 'sys-input--error': error }"
      :type="type || 'text'"
      :placeholder="placeholder"
      :value="value"
      :disabled="disabled"
      @input="handleInput"
    />
    <span v-if="error" class="sys-input-error">{{ error }}</span>
  </div>
</template>

<style scoped>
.sys-input-wrapper { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.sys-input-label { font-size: 0.8125rem; font-weight: 500; color: var(--md-sys-color-on-surface-variant); }
.sys-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 8px;
  font-size: 0.875rem;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  outline: none;
  transition: border-color 0.15s;
}
.sys-input:focus { border-color: var(--md-sys-color-primary); }
.sys-input:disabled { opacity: 0.5; cursor: not-allowed; }
.sys-input--error { border-color: var(--md-sys-color-error); }
.sys-input-error { font-size: 0.75rem; color: var(--md-sys-color-error); }
</style>
