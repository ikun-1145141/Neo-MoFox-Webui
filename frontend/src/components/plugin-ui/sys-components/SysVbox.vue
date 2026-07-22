<script setup lang="ts">
/**
 * SysVbox - 垂直布局容器。
 *
 * 将子元素纵向排列，支持 gap、align、justify 等布局属性。
 */
defineProps<{
  gap?: string
  justify?: string
  align?: string
  padding?: string
  fill?: boolean
}>()
</script>

<template>
  <div
    class="sys-vbox"
    :style="{
      gap: gap || '0.5rem',
      justifyContent: justify || 'flex-start',
      alignItems: align || 'stretch',
      padding: padding || undefined,
      flex: fill ? '1' : undefined,
    }"
  >
    <slot />
  </div>
</template>

<style scoped>
.sys-vbox {
  display: flex;
  flex-direction: column;
  width: 100%;
  animation: sys-fade-in var(--md-sys-motion-duration-medium) var(--md-sys-motion-decelerated);
}
</style>
