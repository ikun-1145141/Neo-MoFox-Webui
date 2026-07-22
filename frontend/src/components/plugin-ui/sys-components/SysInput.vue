<script setup lang="ts">
/**
 * SysInput - 单行文本输入框。
 *
 * 无状态：value prop in、change 事件 out，不在内部维护业务值。
 *
 * 注意：作为自定义元素使用时（HTML 轨），<sys-input>.value 必须能取到
 * 用户当前输入的文本（与原生 <input>.value 行为一致）。Vue 自定义元素的
 * prop 不会随内部 native input 的输入自动回流，故在 onMounted 时
 * 显式在 host 实例上重定义 value 属性，getter 返回 liveValue，
 * setter 同步 liveValue 并 emit change。
 */
import { ref, computed, watch, onMounted } from 'vue'

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

/** native <input> 元素引用，用于反查 host 自定义元素 */
const innerInputRef = ref<HTMLInputElement | null>(null)

/**
 * 实时值：跟踪 prop 变化与用户输入。
 *
 * 不能直接读 props.value 作为 native <input> 的绑定值 —— 用户每输入一个
 * 字符，native input 的 value 已变化，但 props.value 仍是父级传入的旧值
 * （Vue prop 单向流动，内部输入不会回写 prop）。用 liveValue 桥接：
 * - watch(props.value)：父级更新 prop 时同步到 liveValue
 * - handleInput：用户输入时同步到 liveValue
 * - native input 绑定 :value="liveValue"，确保 UI 与状态一致
 */
const liveValue = ref<string>(props.value != null ? String(props.value) : '')

watch(
  () => props.value,
  (v) => {
    liveValue.value = v != null ? String(v) : ''
  }
)

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
  const target = event.target as HTMLInputElement
  liveValue.value = target.value
  emit('change', target.value)
}
function handleFocus(ev: FocusEvent): void {
  isFocused.value = true
  emit('focus', ev)
}
function handleBlur(ev: FocusEvent): void {
  isFocused.value = false
  emit('blur', ev)
}

onMounted(() => {
  // 让 <sys-input>.value 返回用户实际输入的文本（对齐原生 <input>.value 语义）。
  //
  // Vue 3.5 CE 在 _resolveProps 中对每个 declared prop 用
  //   Object.defineProperty(this, key, { get, set })
  // 定义实例访问器，且未指定 configurable: true → 默认 false，
  // 因此不能用 Object.defineProperty(host, 'value', ...) 重定义。
  //
  // 但 getter 内部调用 this._getProp(key)（_resolveProps 源码：
  //   get() { return this._getProp(key); }）。
  // _getProp 是 VueElement.prototype 上的普通方法（writable），
  // 在实例上覆写它即可让 host.value 走我们的 liveValue，
  // 不影响 Vue 内部 _createVNode 用 this._props 传 props 给 SFC 的路径。
  //
  // 同理覆写 _setProp，使 host.value = 'foo' 能立即同步 liveValue
  // （否则需等 watch(props.value) 异步触发，会有一个 tick 的延迟）。
  const nativeInput = innerInputRef.value
  if (!nativeInput) return
  const rootNode = nativeInput.getRootNode()
  const host = rootNode instanceof ShadowRoot
    ? (rootNode.host as any | null)
    : (nativeInput.closest('sys-input') as any | null)
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
        ref="innerInputRef"
        class="sys-input"
        :type="type || 'text'"
        :placeholder="isFocused ? '' : placeholder"
        :value="liveValue"
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
