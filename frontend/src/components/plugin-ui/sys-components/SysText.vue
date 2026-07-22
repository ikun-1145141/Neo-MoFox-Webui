<script setup lang="ts">
/**
 * SysText - 文本显示组件。
 */
import { computed, type CSSProperties } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: string
    color?: string
    align?: string
    bold?: boolean
    italic?: boolean
    truncate?: boolean
  }>(),
  {
    variant: 'body',
  }
)

const style = computed<CSSProperties>(() => ({
  color: props.color || undefined,
  textAlign: props.align as CSSProperties['textAlign'] || undefined,
  fontWeight: props.bold ? '600' : undefined,
  fontStyle: props.italic ? 'italic' : undefined,
  display: props.align ? 'block' : undefined,
}))
</script>

<template>
  <span
    class="sys-text"
    :class="[`sys-text--${variant}`, { 'sys-text--truncate': truncate }]"
    :style="style"
  >
    <slot />
  </span>
</template>

<style scoped>
.sys-text {
  color: var(--md-sys-color-on-surface, #1a1b20);
  animation: sys-fade-in var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-text--body {
  font-size: 0.875rem;
  line-height: 1.5;
}

.sys-text--title {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.01em;
}

.sys-text--subtitle {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.4;
}

.sys-text--caption {
  font-size: 0.75rem;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  line-height: 1.4;
}

.sys-text--headline {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.sys-text--overline {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--md-sys-color-on-surface-variant, #44474e);
}

.sys-text--truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
</style>
