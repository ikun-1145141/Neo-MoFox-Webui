<script setup lang="ts">
/**
 * SysChart - 图表组件（占位实现）。
 *
 * 完整实现需要接入 ECharts，此处提供占位骨架。
 */
defineProps<{
  /** 图表类型：line / bar / pie */
  type?: string
  /** 图表数据 JSON */
  data?: string
  /** 高度 */
  height?: string
}>()
</script>

<template>
  <div class="sys-chart" :style="{ height: height || '300px' }">
    <div class="sys-chart-placeholder">
      <span class="material-symbols-rounded">bar_chart</span>
      <span>{{ type || 'chart' }} 图表</span>
    </div>
    <slot />
  </div>
</template>

<style scoped>
.sys-chart {
  width: 100%;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--md-sys-color-surface-container-lowest);
}

.sys-chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: var(--md-sys-color-on-surface-variant);
}

.sys-chart-placeholder .material-symbols-rounded {
  font-size: 40px;
  opacity: 0.5;
}
</style>
