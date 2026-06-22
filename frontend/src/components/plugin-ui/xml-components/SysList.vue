<script setup lang="ts">
/**
 * SysList - 列表组件。
 *
 * 渲染数组数据为列表项。
 */
import { computed } from 'vue'

const props = defineProps<{
  /** JSON 数据数组 */
  data?: string | any[]
  /** 是否有分割线 */
  divider?: string
}>()

const parsedData = computed<any[]>(() => {
  if (!props.data) return []
  if (Array.isArray(props.data)) return props.data
  try { return JSON.parse(props.data) } catch { return [] }
})
</script>

<template>
  <div class="sys-list" :class="{ 'sys-list--divider': divider !== 'false' }">
    <div v-for="(item, idx) in parsedData" :key="idx" class="sys-list-item">
      {{ typeof item === 'object' ? JSON.stringify(item) : item }}
    </div>
    <div v-if="parsedData.length === 0" class="sys-list-empty">暂无数据</div>
    <slot />
  </div>
</template>

<style scoped>
.sys-list { display: flex; flex-direction: column; width: 100%; }
.sys-list-item { padding: 0.625rem 0.75rem; font-size: 0.875rem; color: var(--md-sys-color-on-surface); }
.sys-list--divider .sys-list-item + .sys-list-item { border-top: 1px solid var(--md-sys-color-outline-variant); }
.sys-list-empty { padding: 1.5rem; text-align: center; color: var(--md-sys-color-on-surface-variant); font-size: 0.875rem; }
</style>
