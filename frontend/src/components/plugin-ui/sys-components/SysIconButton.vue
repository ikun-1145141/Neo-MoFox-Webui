<script setup lang="ts">
/** SysIconButton - 图标按钮组件。 */
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    icon?: string
    disabled?: boolean
    loading?: string
    variant?: string
    size?: string
  }>(),
  {
    icon: 'circle',
    variant: 'standard',
    size: 'medium',
    loading: 'false',
  }
)

const emit = defineEmits<{
  (e: 'click', ev: MouseEvent): void
}>()

const ripples = ref<Array<{ id: number; x: number; y: number; size: number }>>([])
let rippleId = 0

function onClick(ev: MouseEvent): void {
  if (props.disabled || props.loading === 'true') return
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

const sizes: Record<string, string> = {
  small: '32px',
  medium: '40px',
  large: '48px',
}
</script>

<template>
  <button
    class="sys-icon-button"
    :class="[`sys-icon-button--${variant}`, `sys-icon-button--${size}`]"
    :style="{ width: sizes[size] || '40px', height: sizes[size] || '40px' }"
    :disabled="disabled || loading === 'true'"
    :aria-label="icon"
    @click="onClick"
  >
    <span
      v-if="loading === 'true'"
      class="material-symbols-rounded sys-icon-button-spinner"
    >progress_activity</span>
    <span
      v-else
      class="material-symbols-rounded sys-icon-button-icon"
    >{{ icon }}</span>
    <span class="sys-icon-button-ripple-container">
      <span
        v-for="r in ripples"
        :key="r.id"
        class="sys-icon-button-ripple"
        :style="{ left: r.x + 'px', top: r.y + 'px', width: r.size + 'px', height: r.size + 'px' }"
      />
    </span>
  </button>
</template>

<style scoped>
.sys-icon-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  cursor: pointer;
  overflow: hidden;
  transition:
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    transform var(--md-sys-motion-duration-x-short) var(--md-sys-motion-emphasized),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.sys-icon-button:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-highest, #e6e0e9);
}

.sys-icon-button:active:not(:disabled) {
  transform: scale(0.85);
}

.sys-icon-button:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}

/* Variants */
.sys-icon-button--filled {
  background: var(--md-sys-color-primary, #0058bd);
  color: var(--md-sys-color-on-primary, #fff);
}

.sys-icon-button--filled:hover:not(:disabled) {
  background: var(--md-sys-color-primary, #0058bd);
  filter: brightness(1.08);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.sys-icon-button--tonal {
  background: var(--md-sys-color-secondary-container, #d9e2ff);
  color: var(--md-sys-color-on-secondary-container, #001a41);
}

.sys-icon-button--outlined {
  background: transparent;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  border: 1px solid var(--md-sys-color-outline, #74767f);
}

.sys-icon-button-icon,
.sys-icon-button-spinner {
  font-size: 22px;
  transition: transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
}

.sys-icon-button-spinner {
  animation: sys-spin 1s var(--md-sys-motion-linear) infinite;
}

.sys-icon-button:hover:not(:disabled) .sys-icon-button-icon {
  transform: scale(1.1);
}

.sys-icon-button-ripple-container {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.sys-icon-button-ripple {
  position: absolute;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.2;
  transform: scale(0);
  animation: sys-ripple var(--md-sys-motion-duration-medium) var(--md-sys-motion-standard) forwards;
  pointer-events: none;
}
</style>
