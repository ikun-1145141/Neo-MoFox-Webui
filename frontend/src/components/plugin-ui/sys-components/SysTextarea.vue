<script setup lang="ts">
/**
 * SysTextarea - 多行文本输入组件。
 *
 * 作为自定义元素使用时（HTML 轨），<sys-textarea>.value 必须能取到
 * 用户当前输入的文本（与原生 <textarea>.value 行为一致）。Vue 自定义元素的
 * prop 不会随内部 native textarea 的输入自动回流，故在 onMounted 时
 * 显式在 host 实例上重定义 value 属性，getter 返回 liveValue，
 * setter 同步 liveValue 并 emit change。
 */
import { ref, watch, onMounted } from 'vue'

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

/** native <textarea> 元素引用，用于反查 host 自定义元素 */
const innerTextareaRef = ref<HTMLTextAreaElement | null>(null)

watch(
  () => props.error,
  (err, prev) => {
    if (err && err !== prev) shakeKey.value++
  }
)

/**
 * 实时值：跟踪 prop 变化与用户输入。
 * 说明同 SysInput.vue 的 liveValue。
 */
const liveValue = ref<string>(props.value ?? '')

watch(
  () => props.value,
  (v) => {
    liveValue.value = v ?? ''
  }
)

function handleInput(event: Event): void {
  const target = event.target as HTMLTextAreaElement
  liveValue.value = target.value
  emit('change', target.value)
}

onMounted(() => {
  // 让 <sys-textarea>.value 返回用户实际输入的文本。
  // 详见 SysInput.vue 同段说明（Vue 3.5 CE 的 _resolveProps 用
  // 非 configurable 访问器定义 prop，无法用 Object.defineProperty
  // 重定义；改为覆写 _getProp / _setProp 实例方法）。
  const nativeTextarea = innerTextareaRef.value
  if (!nativeTextarea) return
  const rootNode = nativeTextarea.getRootNode()
  const host = rootNode instanceof ShadowRoot
    ? (rootNode.host as any | null)
    : (nativeTextarea.closest('sys-textarea') as any | null)
  if (!host || typeof host._getProp !== 'function') return

  const originalGetProp = host._getProp.bind(host)
  host._getProp = (key: string) => {
    if (key === 'value') {
      return liveValue.value
    }
    return originalGetProp(key)
  }

  const originalSetProp = host._setProp.bind(host)
  host._setProp = (key: string, val: any, shouldReflect?: boolean, shouldUpdate?: boolean) => {
    if (key === 'value') {
      liveValue.value = val == null ? '' : String(val)
    }
    return originalSetProp(key, val, shouldReflect, shouldUpdate)
  }
})
</script>

<template>
  <div class="sys-textarea-wrapper">
    <label
      v-if="label"
      class="sys-textarea-label"
      :class="{ 'sys-textarea-label--focused': isFocused || (value !== undefined && value !== '') }"
    >{{ label }}</label>
    <textarea
      ref="innerTextareaRef"
      class="sys-textarea"
      :class="{ 'sys-textarea--error': error, 'sys-textarea--focused': isFocused }"
      :placeholder="placeholder"
      :value="liveValue"
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
