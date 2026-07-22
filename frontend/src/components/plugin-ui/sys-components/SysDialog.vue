<script setup lang="ts">
/**
 * SysDialog - 对话框组件。
 *
 * 无状态、模式中立：通过 `open` prop 控制显隐，通过 `close` / `update:open`
 * 事件回写状态。具体的状态存储（变量池 / 本地 ref / 等）由调用方决定。
 *
 * XML 轨：xml-renderer.ts 检测到 <dialog id="x"> 时自动展开为
 *   :open="store.get('__dialog_x_open') === true"
 *   @update:open="store.set('__dialog_x_open', $event)"
 *   @close="store.set('__dialog_x_open', false)"
 * 作者侧语义保持 <dialog id="x"> 不变。
 *
 * HTML 轨：作者通过 sys.ui.dialog.open(id) 写入变量后由 sys-bridge 触发，
 * 或直接传 open prop 控制。
 *
 * 布尔属性约定：HTML 自定义元素 attribute 永远是 string，故
 * closeOnBackdrop / closeOnEsc / noTransition / open 一律声明为
 * `boolean | string` 并用 isTrueXxx() computed 强制 coerce ——
 * 让 close-on-backdrop / close-on-backdrop="true" 两种写法都等价于 true。
 */
import { computed, watch, onUnmounted } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 对话框标题 */
    title?: string
    /** 是否打开 */
    open?: boolean | string
    /** 点击遮罩关闭（默认 true） */
    closeOnBackdrop?: boolean | string
    /** ESC 关闭（默认 true） */
    closeOnEsc?: boolean | string
    /** 是否禁用过渡（用于嵌套场景） */
    noTransition?: boolean | string
  }>(),
  {
    open: false,
    closeOnBackdrop: true,
    closeOnEsc: true,
    noTransition: false,
  }
)

/**
 * 把 boolean | string 形态的 prop coerce 为 boolean。
 * HTML attribute 可能传入 "true" / "false" 字符串，或无值（presence）。
 */
function coerceBool(v: boolean | string | undefined, fallback: boolean): boolean {
  if (v === undefined || v === null) return fallback
  if (typeof v === 'boolean') return v
  // string 形态：空字符串（HTML 无值 attribute）或 "true" → true
  if (v === '' || v === 'true') return true
  if (v === 'false') return false
  return fallback
}

const isOpen = computed(() => coerceBool(props.open, false))
const isCloseOnBackdrop = computed(() => coerceBool(props.closeOnBackdrop, true))
const isCloseOnEsc = computed(() => coerceBool(props.closeOnEsc, true))
const isNoTransition = computed(() => coerceBool(props.noTransition, false))

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'update:open', value: boolean): void
}>()

function close(): void {
  emit('update:open', false)
  emit('close')
}

function onBackdrop(): void {
  if (isCloseOnBackdrop.value) close()
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && isCloseOnEsc.value) {
    e.stopPropagation()
    close()
  }
}

watch(
  isOpen,
  (open) => {
    if (open) {
      document.addEventListener('keydown', onKeydown)
    } else {
      document.removeEventListener('keydown', onKeydown)
    }
  }
)

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Transition :name="isNoTransition ? undefined : 'sys-dialog-overlay'">
    <div
      v-if="isOpen"
      class="sys-dialog-overlay"
      @click.self="onBackdrop"
    >
      <Transition
        :name="isNoTransition ? undefined : 'sys-dialog-panel'"
        appear
      >
        <div
          v-if="isOpen"
          class="sys-dialog"
          role="dialog"
          aria-modal="true"
        >
          <header v-if="title || $slots.header" class="sys-dialog-header">
            <slot name="header">
              <h2 class="sys-dialog-title">{{ title }}</h2>
            </slot>
            <button
              class="sys-dialog-close"
              aria-label="关闭"
              @click="close"
            >
              <span class="material-symbols-rounded">close</span>
            </button>
          </header>
          <div class="sys-dialog-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="sys-dialog-footer">
            <slot name="footer" :close="close" />
          </footer>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.sys-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.sys-dialog {
  background: var(--md-sys-color-surface-container-high, #fff);
  color: var(--md-sys-color-on-surface, #1a1b20);
  border-radius: 28px;
  padding: 24px;
  min-width: 320px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.15),
    0 16px 56px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.sys-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.sys-dialog-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 500;
  letter-spacing: 0;
  color: var(--md-sys-color-on-surface, #1a1b20);
}

.sys-dialog-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  cursor: pointer;
  transition:
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
}

.sys-dialog-close:hover {
  background: var(--md-sys-color-surface-container-highest, #e6e0e9);
}

.sys-dialog-close:active {
  transform: scale(0.9);
}

.sys-dialog-close .material-symbols-rounded {
  font-size: 24px;
}

.sys-dialog-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  font-size: 0.875rem;
  line-height: 1.5;
}

.sys-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
}
</style>

<style>
/* Transition 类必须是非 scoped 才能作用到 Teleport/根节点 */

.sys-dialog-overlay-enter-active,
.sys-dialog-overlay-leave-active {
  transition: opacity var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}
.sys-dialog-overlay-enter-from,
.sys-dialog-overlay-leave-to {
  opacity: 0;
}

.sys-dialog-panel-enter-active {
  transition:
    opacity var(--md-sys-motion-duration-medium) var(--md-sys-motion-decelerated),
    transform var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized);
  transition-delay: 60ms;
}
.sys-dialog-panel-leave-active {
  transition:
    opacity var(--md-sys-motion-duration-short) var(--md-sys-motion-accelerated),
    transform var(--md-sys-motion-duration-short) var(--md-sys-motion-accelerated);
}
.sys-dialog-panel-enter-from,
.sys-dialog-panel-leave-to {
  opacity: 0;
  transform: scale(0.85) translateY(-8px);
}
</style>
