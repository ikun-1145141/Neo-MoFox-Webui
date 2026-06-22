<script setup lang="ts">
/**
 * SysHbox - 水平布局容器。
 *
 * 将子元素横向排列，支持 gap、align、justify、wrap 等属性。
 */
defineProps<{
  /** 子元素间距 */
  gap?: string
  /** 主轴对齐 */
  justify?: string
  /** 交叉轴对齐 */
  align?: string
  /** 是否换行 */
  wrap?: string
  /** 内边距 */
  padding?: string
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
}
</style>
