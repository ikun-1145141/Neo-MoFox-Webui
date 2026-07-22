<script setup lang="ts">
/**
 * SysHbox - 水平布局容器。
 */
defineProps<{
  gap?: string
  justify?: string
  align?: string
  wrap?: string
  padding?: string
  fill?: boolean
}>()
</script>

<template>
  <div
    class="sys-hbox"
    :style="{
      gap: gap || '0.5rem',
      justifyContent: justify || 'flex-start',
      alignItems: align || 'center',
      flexWrap: wrap === 'true' ? 'wrap' : 'nowrap',
      padding: padding || undefined,
      flex: fill ? '1' : undefined,
    }"
  >
    <slot />
  </div>
</template>

<style scoped>
.sys-hbox {
  display: flex;
  flex-direction: row;
  width: 100%;
  animation: sys-fade-in var(--md-sys-motion-duration-medium) var(--md-sys-motion-decelerated);
}
</style>
