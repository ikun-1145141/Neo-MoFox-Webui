<script setup lang="ts">
/**
 * SysSpacer - 弹性空间占位组件。
 */
defineProps<{
  /** 固定高度（如 "16px"），不设则弹性填充 */
  height?: string
  /** 固定宽度 */
  width?: string
}>()
</script>

<template>
  <div
    class="sys-spacer"
    :style="{
      height: height || undefined,
      width: width || undefined,
      flex: (!height && !width) ? '1' : undefined,
    }"
    aria-hidden="true"
  />
</template>

<style scoped>
.sys-spacer {
  min-width: 0;
  min-height: 0;
}
</style>
