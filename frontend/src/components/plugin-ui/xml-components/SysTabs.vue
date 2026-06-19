<script setup lang="ts">
/**
 * SysTabs - 标签页容器。
 *
 * 简化的标签切换组件。子元素通过 label 属性定义 tab 标题。
 */
import { ref } from 'vue'

defineProps<{
  /** 默认选中的 tab 索引 */
  defaultTab?: string
}>()

const activeIndex = ref(0)

function setTab(index: number): void {
  activeIndex.value = index
}
</script>

<template>
  <div class="sys-tabs">
    <div class="sys-tabs-header" role="tablist">
      <!-- 这里简化处理：tabs 的子节点由父级 XML 渲染器提供 -->
      <slot name="tabs" />
    </div>
    <div class="sys-tabs-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.sys-tabs {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.sys-tabs-header {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  overflow-x: auto;
}

.sys-tabs-content {
  padding-top: 1rem;
}
</style>
