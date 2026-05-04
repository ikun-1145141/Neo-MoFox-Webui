<script setup lang="ts">
import { useDialogStore } from '../../utils/dialog'
import { onMounted, onBeforeUnmount } from 'vue'

const dialogStore = useDialogStore()

function handleBackdropClick(dialogId: number) {
  // 点击遮罩层关闭对话框
  dialogStore.close(dialogId)
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape' && dialogStore.items.length > 0) {
    // ESC 关闭最顶层对话框
    const topDialog = dialogStore.items[dialogStore.items.length - 1]
    dialogStore.close(topDialog.id)
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <Teleport to="body">
    <TransitionGroup name="dialog-stack">
      <div
        v-for="dialog in dialogStore.items"
        :key="dialog.id"
        class="dialog-backdrop"
        @click.self="handleBackdropClick(dialog.id)"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`dialog-title-${dialog.id}`"
        :aria-describedby="`dialog-message-${dialog.id}`"
      >
        <div class="dialog-container" @click.stop>
          <div v-if="dialog.title" :id="`dialog-title-${dialog.id}`" class="dialog-title">
            {{ dialog.title }}
          </div>
          <div :id="`dialog-message-${dialog.id}`" class="dialog-message">
            {{ dialog.message }}
          </div>
          <div class="dialog-actions">
            <button
              v-for="(btn, index) in dialog.buttons"
              :key="index"
              :class="['dialog-btn', `dialog-btn-${btn.variant || 'secondary'}`]"
              @click="btn.onClick"
            >
              {{ btn.text }}
            </button>
          </div>
        </div>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<style scoped>
/* ===== 遮罩层 ===== */
.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  /* Notion 风格的柔和遮罩 */
  background: color-mix(in srgb, var(--md-sys-color-surface) 45%, transparent);
  backdrop-filter: blur(4px);
}

/* ===== 对话框容器 ===== */
.dialog-container {
  position: relative;
  width: 100%;
  max-width: 400px;
  /* Notion 风格：纯白背景 */
  background: var(--md-sys-color-surface, #ffffff);
  /* MD3 圆角 - 16px 大圆角 */
  border-radius: 16px;
  /* Notion 风格：多层轻柔阴影 */
  box-shadow:
    rgba(0, 0, 0, 0.04) 0px 4px 18px,
    rgba(0, 0, 0, 0.027) 0px 2.025px 7.84688px,
    rgba(0, 0, 0, 0.02) 0px 0.8px 2.925px,
    rgba(0, 0, 0, 0.01) 0px 0.175px 1.04062px;
  /* Notion 风格：超细边框 */
  border: 1px solid var(--md-sys-color-outline-variant);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ===== 标题 ===== */
.dialog-title {
  margin: 0;
  /* NotionInter 字体，Notion 风格的温暖黑色 */
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: -0.125px;
  color: var(--md-sys-color-on-surface, rgba(0, 0, 0, 0.95));
}

/* ===== 消息内容 ===== */
.dialog-message {
  margin: 0;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.9375rem;
  font-weight: 400;
  line-height: 1.5;
  /* Notion 风格的温暖灰 */
  color: var(--md-sys-color-on-surface-variant, #615d59);
}

/* ===== 按钮组 ===== */
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.25rem;
}

/* ===== 按钮基础样式 ===== */
.dialog-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 2.5rem;
  padding: 0 1.25rem;
  border: none;
  border-radius: 4px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.15s,
    transform 0.1s,
    box-shadow 0.15s;
  user-select: none;
}

.dialog-btn:active {
  transform: scale(0.95);
}

/* ===== Primary 按钮（Notion Blue）===== */
.dialog-btn-primary {
  background: var(--md-sys-color-primary, #0075de);
  color: var(--md-sys-color-on-primary, #ffffff);
}

.dialog-btn-primary:hover {
  background: #005bab;
  box-shadow: 0px 2px 8px rgba(0, 117, 222, 0.25);
}

.dialog-btn-primary:focus-visible {
  outline: 2px solid var(--md-sys-color-primary, #0075de);
  outline-offset: 2px;
}

/* ===== Secondary 按钮（Notion 温暖灰）===== */
.dialog-btn-secondary {
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 60%, transparent);
  color: var(--md-sys-color-on-surface, rgba(0, 0, 0, 0.95));
}

.dialog-btn-secondary:hover {
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 80%, transparent);
  transform: scale(1.02);
}

.dialog-btn-secondary:focus-visible {
  outline: 2px solid var(--md-sys-color-outline, #74777f);
  outline-offset: 2px;
}

/* ===== Ghost 按钮 ===== */
.dialog-btn-ghost {
  background: transparent;
  color: var(--md-sys-color-on-surface-variant, #615d59);
}

.dialog-btn-ghost:hover {
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 50%, transparent);
  text-decoration: underline;
}

/* ===== 动画 ===== */
.dialog-stack-enter-active,
.dialog-stack-leave-active {
  transition:
    opacity 0.25s,
    transform 0.25s;
}

.dialog-stack-enter-from {
  opacity: 0;
}

.dialog-stack-enter-from .dialog-container {
  transform: scale(0.9) translateY(20px);
}

.dialog-stack-leave-to {
  opacity: 0;
}

.dialog-stack-leave-to .dialog-container {
  transform: scale(0.95);
}

/* ===== 响应式 ===== */
@media (max-width: 480px) {
  .dialog-container {
    max-width: 100%;
    margin: 0 1rem;
  }

  .dialog-actions {
    flex-direction: column;
    gap: 0.5rem;
  }

  .dialog-btn {
    width: 100%;
  }
}
</style>
