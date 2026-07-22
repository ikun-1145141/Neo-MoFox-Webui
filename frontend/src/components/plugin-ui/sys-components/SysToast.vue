<script setup lang="ts">
/**
 * SysToast - Toast 浮层组件。
 *
 * 用于 HTML 轨通过 `<sys-toast>` 元素直接显示 toast。
 * XML 轨通常通过 `notify:` 指令 / `sys.ui.notify()` 触发，无需直接使用此组件。
 *
 * 命令式 API：
 *   const el = document.createElement('sys-toast')
 *   el.setAttribute('message', '保存成功')
 *   el.setAttribute('level', 'success')
 *   el.show()  // 等价于上面三步，立即显示
 */
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = withDefaults(
  defineProps<{
    /** Toast 文本 */
    message?: string
    /** 级别：info / success / warning / error */
    level?: string
    /** 显示时长（毫秒），0 表示不自动关闭 */
    duration?: number
    /** 显示位置：top / bottom */
    placement?: string
  }>(),
  {
    message: '',
    level: 'info',
    duration: 3000,
    placement: 'top',
  }
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'show'): void
}>()

const visible = ref(false)
let timer: number | null = null

function show(): void {
  visible.value = true
  emit('show')
  if (timer) window.clearTimeout(timer)
  if (props.duration > 0) {
    timer = window.setTimeout(close, props.duration)
  }
}

function close(): void {
  visible.value = false
  if (timer) {
    window.clearTimeout(timer)
    timer = null
  }
  emit('close')
}

watch(
  () => props.message,
  (msg) => {
    if (msg) show()
    else close()
  }
)

onMounted(() => {
  if (props.message) show()
})

onUnmounted(() => {
  if (timer) window.clearTimeout(timer)
})

defineExpose({ show, close })
</script>

<template>
  <Transition name="sys-toast">
    <div
      v-if="visible"
      class="sys-toast"
      :class="[`sys-toast--${level}`, `sys-toast--${placement}`]"
      role="status"
      @click="close"
    >
      <span
        v-if="level === 'success'"
        class="material-symbols-rounded sys-toast-icon"
      >check_circle</span>
      <span
        v-else-if="level === 'error'"
        class="material-symbols-rounded sys-toast-icon"
      >error</span>
      <span
        v-else-if="level === 'warning'"
        class="material-symbols-rounded sys-toast-icon"
      >warning</span>
      <span
        v-else
        class="material-symbols-rounded sys-toast-icon"
      >info</span>
      <span class="sys-toast-message">{{ message }}</span>
    </div>
  </Transition>
</template>

<style scoped>
.sys-toast {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  pointer-events: auto;
  max-width: 360px;
  color: var(--md-sys-color-on-surface, #1a1b20);
  background: var(--md-sys-color-surface-container-high, #fff);
}

.sys-toast--success {
  border-left: 4px solid var(--md-sys-color-primary, #0058bd);
}

.sys-toast--error {
  border-left: 4px solid var(--md-sys-color-error, #ba1a1a);
}

.sys-toast--warning {
  border-left: 4px solid #f59e0b;
}

.sys-toast--info {
  border-left: 4px solid var(--md-sys-color-outline, #74767f);
}

.sys-toast-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.sys-toast--success .sys-toast-icon {
  color: var(--md-sys-color-primary, #0058bd);
}

.sys-toast--error .sys-toast-icon {
  color: var(--md-sys-color-error, #ba1a1a);
}

.sys-toast--warning .sys-toast-icon {
  color: #f59e0b;
}

.sys-toast-message {
  flex: 1;
  word-break: break-word;
}

/* Transition */
.sys-toast-enter-active {
  transition:
    opacity var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized),
    transform var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized);
}

.sys-toast-leave-active {
  transition:
    opacity var(--md-sys-motion-duration-short) var(--md-sys-motion-accelerated),
    transform var(--md-sys-motion-duration-short) var(--md-sys-motion-accelerated);
}

.sys-toast-enter-from,
.sys-toast-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

.sys-toast--bottom.sys-toast-enter-from,
.sys-toast--bottom.sys-toast-leave-to {
  transform: translateY(12px);
}
</style>
