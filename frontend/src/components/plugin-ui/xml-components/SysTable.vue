<script setup lang="ts">
/**
 * SysTable - 数据表格组件。
 *
 * 接收 JSON 数据和列配置，渲染为 MD3 风格表格。
 */
import { computed } from 'vue'

const props = defineProps<{
  /** JSON 数据（字符串或已解析数组） */
  data?: string | any[]
  /** 列定义 JSON：[{ key, label, width? }] */
  columns?: string | any[]
  /** 是否显示斑马纹 */
  striped?: string
  /** 每页行数 */
  pageSize?: string
}>()

const parsedData = computed<any[]>(() => {
  if (!props.data) return []
  if (Array.isArray(props.data)) return props.data
  try { return JSON.parse(props.data) } catch { return [] }
})

const parsedColumns = computed<Array<{ key: string; label: string; width?: string }>>(() => {
  if (!props.columns) {
    // 自动从数据推断列
    if (parsedData.value.length > 0) {
      return Object.keys(parsedData.value[0]).map(k => ({ key: k, label: k }))
    }
    return []
  }
  if (Array.isArray(props.columns)) return props.columns
  try { return JSON.parse(props.columns) } catch { return [] }
})
</script>

<template>
  <div class="sys-table-wrapper">
    <table class="sys-table" :class="{ 'sys-table--striped': striped === 'true' }">
      <thead>
        <tr>
          <th v-for="col in parsedColumns" :key="col.key" :style="{ width: col.width }">{{ col.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, idx) in parsedData" :key="idx">
          <td v-for="col in parsedColumns" :key="col.key">{{ row[col.key] }}</td>
        </tr>
        <tr v-if="parsedData.length === 0">
          <td :colspan="parsedColumns.length" class="sys-table-empty">暂无数据</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.sys-table-wrapper { width: 100%; overflow-x: auto; }
.sys-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.sys-table th { padding: 0.625rem 0.75rem; text-align: left; font-weight: 600; color: var(--md-sys-color-on-surface-variant); border-bottom: 1px solid var(--md-sys-color-outline-variant); background: var(--md-sys-color-surface-container-low); }
.sys-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--md-sys-color-outline-variant); color: var(--md-sys-color-on-surface); }
.sys-table--striped tbody tr:nth-child(even) { background: var(--md-sys-color-surface-container-lowest); }
.sys-table-empty { text-align: center; color: var(--md-sys-color-on-surface-variant); padding: 2rem 0.75rem; }
</style>
