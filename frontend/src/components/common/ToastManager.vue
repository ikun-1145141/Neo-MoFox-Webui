<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { useToastStore } from '../../utils/toast'
import type { ToastType } from '../../utils/toast'

const toast = useToastStore()

const iconMap: Record<ToastType, string> = {
  success: 'material-symbols:check-circle-outline-rounded',
  error: 'material-symbols:error-outline-rounded',
  info: 'material-symbols:info-outline-rounded',
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="item in toast.items"
          :key="item.id"
          class="toast-item"
          :class="`toast-${item.type}`"
        >
          <Icon :icon="iconMap[item.type]" width="20" height="20" />
          <span>{{ item.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
  pointer-events: none;
}
.toast-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem 1.25rem;
  border-radius: 9999px;
  font-size: 0.9rem;
  font-weight: 500;
  box-shadow: 0px 8px 24px rgba(24, 28, 32, 0.15);
  pointer-events: auto;
  white-space: nowrap;
}
.toast-success {
  background: var(--md-sys-color-primary-container, #d3e4ff);
  color: var(--md-sys-color-on-primary-container, #001b3f);
}
.toast-error {
  background: var(--md-sys-color-error-container, #ffdad6);
  color: var(--md-sys-color-on-error-container, #410002);
}
.toast-info {
  background: var(--md-sys-color-surface-container-highest, #e2e2e9);
  color: var(--md-sys-color-on-surface, #1b1b1f);
}

/* 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.25s, transform 0.25s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
