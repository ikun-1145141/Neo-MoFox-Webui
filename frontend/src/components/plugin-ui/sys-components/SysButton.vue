<script setup lang="ts">
/**
 * SysButton - 按钮组件。
 *
 * 变体：filled / outlined / text / tonal / elevated
 * 支持 loading 状态、icon、ripple 涟漪动画。
 */
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: string
    icon?: string
    disabled?: boolean
    loading?: string | boolean
    block?: boolean
    size?: string
  }>(),
  {
    variant: 'filled',
    loading: false,
    block: false,
    size: 'medium',
  }
)

const emit = defineEmits<{
  (e: 'click', ev: MouseEvent): void
}>()

const ripples = ref<Array<{ id: number; x: number; y: number; size: number }>>([])
let rippleId = 0

function onClick(ev: MouseEvent): void {
  if (props.disabled || props.loading === 'true' || props.loading === true) return

  // ripple
  const target = ev.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const size = Math.max(rect.width, rect.height)
  const x = ev.clientX - rect.left - size / 2
  const y = ev.clientY - rect.top - size / 2
  const id = ++rippleId
  ripples.value.push({ id, x, y, size })
  window.setTimeout(() => {
    ripples.value = ripples.value.filter((r) => r.id !== id)
  }, 600)

  emit('click', ev)
}

const isLoading = () => props.loading === 'true' || props.loading === true
</script>

<template>
  <button
    class="sys-button"
    :class="[`sys-button--${variant}`, `sys-button--${size}`, { 'sys-button--block': block }]"
    :disabled="disabled || isLoading()"
    @click="onClick"
  >
    <span
      v-if="isLoading()"
      class="material-symbols-rounded sys-button-spinner"
    >progress_activity</span>
    <span
      v-else-if="icon"
      class="material-symbols-rounded sys-button-icon"
    >{{ icon }}</span>
    <span class="sys-button-content">
      <slot />
    </span>
    <span class="sys-button-ripple-container">
      <span
        v-for="r in ripples"
        :key="r.id"
        class="sys-button-ripple"
        :style="{ left: r.x + 'px', top: r.y + 'px', width: r.size + 'px', height: r.size + 'px' }"
      />
    </span>
  </button>
</template>

<style scoped>
.sys-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  overflow: hidden;
  transition:
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    transform var(--md-sys-motion-duration-x-short) var(--md-sys-motion-emphasized),
    color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.sys-button--small {
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
}

.sys-button--medium {
  padding: 0.5rem 1.25rem;
}

.sys-button--large {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
}

.sys-button--block {
  display: flex;
  width: 100%;
}

.sys-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Filled */
.sys-button--filled {
  background: var(--md-sys-color-primary, #0058bd);
  color: var(--md-sys-color-on-primary, #fff);
}

.sys-button--filled:hover:not(:disabled) {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15), 0 2px 6px rgba(0, 0, 0, 0.1);
  filter: brightness(1.08);
}

.sys-button--filled:active:not(:disabled) {
  transform: scale(0.96);
  filter: brightness(0.95);
}

/* Outlined */
.sys-button--outlined {
  background: transparent;
  color: var(--md-sys-color-primary, #0058bd);
  border: 1px solid var(--md-sys-color-outline, #74767f);
}

.sys-button--outlined:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 8%, transparent);
  border-color: var(--md-sys-color-primary, #0058bd);
}

.sys-button--outlined:active:not(:disabled) {
  transform: scale(0.96);
}

/* Text */
.sys-button--text {
  background: transparent;
  color: var(--md-sys-color-primary, #0058bd);
}

.sys-button--text:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 8%, transparent);
}

.sys-button--text:active:not(:disabled) {
  transform: scale(0.96);
}

/* Tonal */
.sys-button--tonal {
  background: var(--md-sys-color-secondary-container, #d9e2ff);
  color: var(--md-sys-color-on-secondary-container, #001a41);
}

.sys-button--tonal:hover:not(:disabled) {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
  filter: brightness(1.05);
}

.sys-button--tonal:active:not(:disabled) {
  transform: scale(0.96);
}

/* Elevated */
.sys-button--elevated {
  background: var(--md-sys-color-surface-container-low, #fff);
  color: var(--md-sys-color-primary, #0058bd);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1), 0 1px 4px rgba(0, 0, 0, 0.05);
}

.sys-button--elevated:hover:not(:disabled) {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15), 0 4px 12px rgba(0, 0, 0, 0.08);
  filter: brightness(1.02);
}

.sys-button--elevated:active:not(:disabled) {
  transform: scale(0.96);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.sys-button-icon {
  font-size: 18px;
  transition: transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
}

.sys-button:hover:not(:disabled) .sys-button-icon {
  transform: scale(1.1);
}

.sys-button-spinner {
  font-size: 18px;
  animation: sys-spin 1s var(--md-sys-motion-linear) infinite;
}

.sys-button-content {
  position: relative;
  z-index: 1;
}

.sys-button-ripple-container {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.sys-button-ripple {
  position: absolute;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.25;
  transform: scale(0);
  animation: sys-ripple var(--md-sys-motion-duration-medium) var(--md-sys-motion-standard) forwards;
  pointer-events: none;
}
</style>
