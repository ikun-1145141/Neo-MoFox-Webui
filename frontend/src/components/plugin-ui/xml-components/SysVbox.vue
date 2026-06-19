<script setup lang="ts">
/**
 * SysVbox - 垂直布局容器。
 *
 * 将子元素纵向排列，支持 gap、align、justify 等布局属性。
 */
defineProps<{
  /** 子元素间距（CSS 值） */
  gap?: string
  /** 主轴对齐 */
  justify?: string
  /** 交叉轴对齐 */
  align?: string
  /** 内边距（CSS 值） */
  padding?: string
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
}
</style>
