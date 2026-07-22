<script setup lang="ts">
/**
 * SysInput - 单行文本输入框。
 *
 * 无状态：value prop in、change 事件 out，不在内部维护业务值。
 */
import { ref, computed, watch } from 'vue'

const props = defineProps<{
  /** 输入框标签 */
  label?: string
  /** 占位文本 */
  placeholder?: string
  /** 输入类型 */
  type?: string
  /** 当前值 */
  value?: string | number
  /** 是否禁用 */
  disabled?: boolean
  /** 是否只读 */
  readonly?: boolean
  /** 错误提示 */
  error?: string
  /** 是否在聚焦时有动画（默认 true） */
  animated?: boolean
}>()

const emit = defineEmits<{
  (e: 'change', value: string): void
  (e: 'focus', ev: FocusEvent): void
  (e: 'blur', ev: FocusEvent): void
}>()

const isFocused = ref(false)
const shakeKey = ref(0)

// 错误提示出现时触发一次抖动动画
watch(
  () => props.error,
  (err, prev) => {
    if (err && err !== prev) shakeKey.value++
  }
)

const inputClasses = computed(() => ({
  'sys-input--error': !!props.error,
  'sys-input--focused': isFocused.value,
  'sys-input--disabled': props.disabled,
  'sys-input--readonly': props.readonly,
}))

function handleInput(event: Event): void {
  emit('change', (event.target as HTMLInputElement).value)
}
function handleFocus(ev: FocusEvent): void {
  isFocused.value = true
  emit('focus', ev)
}
function handleBlur(ev: FocusEvent): void {
  isFocused.value = false
  emit('blur', ev)
}
</script>

<template>
  <div
    class="sys-input-wrapper"
    :class="{ 'has-label': label }"
  >
    <label
      v-if="label"
      class="sys-input-label"
      :class="{ 'sys-input-label--float': isFocused || (value !== undefined && value !== '') }"
    >
      {{ label }}
    </label>
    <div class="sys-input-box" :class="inputClasses">
      <input
        class="sys-input"
        :type="type || 'text'"
        :placeholder="isFocused ? '' : placeholder"
        :value="value"
        :disabled="disabled"
        :readonly="readonly"
        :aria-invalid="!!error"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
      />
      <span
        class="sys-input-underline"
        :class="{ 'sys-input-underline--error': !!error }"
      />
    </div>
    <Transition name="sys-fade">
      <span
        v-if="error"
        :key="shakeKey"
        class="sys-input-error"
      >{{ error }}</span>
    </Transition>
  </div>
</template>

<style scoped>
.sys-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  position: relative;
}

.sys-input-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  transition:
    color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
}

.sys-input-label--float {
  color: var(--md-sys-color-primary, #0058bd);
}

.sys-input-box {
  position: relative;
  display: flex;
  align-items: center;
  border: 1px solid var(--md-sys-color-outline, #74767f);
  border-radius: 8px;
  background: var(--md-sys-color-surface, #fff);
  transition:
    border-color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-input-box--focused {
  border-color: var(--md-sys-color-primary, #0058bd);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 12%, transparent);
}

.sys-input-box--error {
  border-color: var(--md-sys-color-error, #ba1a1a);
}

.sys-input-box--error.sys-input-box--focused {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--md-sys-color-error, #ba1a1a) 12%, transparent);
}

.sys-input {
  flex: 1;
  padding: 0.625rem 0.875rem;
  border: none;
  background: transparent;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface, #1a1b20);
  outline: none;
  font-family: inherit;
  width: 100%;
}

.sys-input::placeholder {
  color: var(--md-sys-color-on-surface-variant, #44474e);
  opacity: 0.7;
}

.sys-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sys-input:read-only {
  cursor: default;
}

.sys-input-underline {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background: var(--md-sys-color-primary, #0058bd);
  transform: scaleX(0);
  transform-origin: center;
  transition: transform var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized);
  border-radius: 2px;
  pointer-events: none;
}

.sys-input-box--focused .sys-input-underline {
  transform: scaleX(1);
}

.sys-input-underline--error {
  background: var(--md-sys-color-error, #ba1a1a);
}

.sys-input-error {
  font-size: 0.75rem;
  color: var(--md-sys-color-error, #ba1a1a);
  animation: sys-shake 0.4s var(--md-sys-motion-emphasized);
  transform-origin: left;
}
</style>
