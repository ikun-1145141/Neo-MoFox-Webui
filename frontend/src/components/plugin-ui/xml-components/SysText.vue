<script setup lang="ts">
/**
 * SysText - 文本显示组件。
 */
import { computed, type CSSProperties } from 'vue'

const props = defineProps<{
  /** 文本变体：body / title / subtitle / caption */
  variant?: string
  /** 文本颜色 */
  color?: string
  /** 文本对齐 */
  align?: string
  /** 是否加粗 */
  bold?: string
}>()

const style = computed<CSSProperties>(() => ({
  color: props.color || undefined,
  textAlign: (props.align as CSSProperties['textAlign']) || undefined,
  fontWeight: props.bold === 'true' ? '600' : undefined,
  display: props.align ? 'block' : undefined,
}))
</script>

<template>
  <span
    class="sys-text"
    :class="`sys-text--${variant || 'body'}`"
    :style="style"
  >
    <slot />
  </span>
</template>

<style scoped>
.sys-text { color: var(--md-sys-color-on-surface); }
.sys-text--body { font-size: 0.875rem; line-height: 1.5; }
.sys-text--title { font-size: 1.25rem; font-weight: 700; line-height: 1.3; }
.sys-text--subtitle { font-size: 1rem; font-weight: 600; line-height: 1.4; }
.sys-text--caption { font-size: 0.75rem; color: var(--md-sys-color-on-surface-variant); line-height: 1.4; }
</style>
