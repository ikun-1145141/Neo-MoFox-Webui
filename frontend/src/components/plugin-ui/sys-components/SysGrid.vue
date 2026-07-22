<script setup lang="ts">
/**
 * SysGrid - 网格布局容器。
 *
 * CSS Grid 布局，支持 columns、gap、rows 等属性。
 */
defineProps<{
  columns?: string
  rows?: string
  gap?: string
  padding?: string
}>()
</script>

<template>
  <div
    class="sys-grid"
    :style="{
      gridTemplateColumns: columns && /^\d+$/.test(columns) ? `repeat(${columns}, 1fr)` : columns || 'repeat(auto-fit, minmax(200px, 1fr))',
      gridTemplateRows: rows || undefined,
      gap: gap || '1rem',
      padding: padding || undefined,
    }"
  >
    <slot />
  </div>
</template>

<style scoped>
.sys-grid {
  display: grid;
  width: 100%;
  animation: sys-fade-in var(--md-sys-motion-duration-medium) var(--md-sys-motion-decelerated);
}
</style>
