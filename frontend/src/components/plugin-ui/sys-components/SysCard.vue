<script setup lang="ts">
/**
 * SysCard - 卡片容器。
 *
 * MD3 风格的 Surface 容器，带圆角、阴影和内边距。
 */
import { ref } from 'vue'

withDefaults(
  defineProps<{
    title?: string
    variant?: string
    padding?: string
    clickable?: boolean
  }>(),
  {
    variant: 'elevated',
    padding: '1rem',
    clickable: false,
  }
)

const isHovered = ref(false)
</script>

<template>
  <div
    class="sys-card"
    :class="[`sys-card--${variant}`, { 'sys-card--clickable': clickable, 'sys-card--hovered': isHovered }]"
    :style="{ padding }"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <header
      v-if="title || $slots.header"
      class="sys-card-header"
    >
      <slot name="header">
        <h3 class="sys-card-title">{{ title }}</h3>
      </slot>
      <slot name="actions" />
    </header>
    <div class="sys-card-body">
      <slot />
    </div>
    <footer
      v-if="$slots.footer"
      class="sys-card-footer"
    >
      <slot name="footer" />
    </footer>
  </div>
</template>

<style scoped>
.sys-card {
  border-radius: 12px;
  width: 100%;
  animation: sys-fade-in var(--md-sys-motion-duration-medium) var(--md-sys-motion-decelerated);
  transition:
    box-shadow var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized),
    transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized),
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-card--elevated {
  background: var(--md-sys-color-surface, #fff);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05), 0 2px 8px rgba(0, 0, 0, 0.04);
}

.sys-card--outlined {
  background: var(--md-sys-color-surface, #fff);
  border: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
}

.sys-card--filled {
  background: var(--md-sys-color-surface-container, #f3f3fa);
}

.sys-card--clickable {
  cursor: pointer;
}

.sys-card--clickable.sys-card--hovered {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1), 0 8px 24px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.sys-card--clickable:active {
  transform: translateY(0);
}

.sys-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 0.75rem;
}

.sys-card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface, #1a1b20);
}

.sys-card-body {
  width: 100%;
}

.sys-card-footer {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
}
</style>
