<script setup lang="ts">
/**
 * SysTable - 数据表格组件。
 *
 * 接收 JSON 数据和列配置，渲染为 MD3 风格表格。
 * 支持行 hover、斑马纹、空状态、stagger 入场动画。
 */
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    data?: string | any[]
    columns?: string | any[]
    striped?: string
    pageSize?: string
    hoverable?: boolean
    animated?: boolean
  }>(),
  {
    hoverable: true,
    animated: true,
  }
)

const parsedData = computed<any[]>(() => {
  if (!props.data) return []
  if (Array.isArray(props.data)) return props.data
  try {
    const parsed = JSON.parse(props.data)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
})

const parsedColumns = computed<Array<{ key: string; label: string; width?: string; align?: string }>>(() => {
  if (!props.columns) {
    if (parsedData.value.length > 0) {
      return Object.keys(parsedData.value[0]).map((k) => ({ key: k, label: k }))
    }
    return []
  }
  if (Array.isArray(props.columns)) return props.columns
  try {
    const parsed = JSON.parse(props.columns)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
})

// 分页（简化版）
const currentPage = ref(1)
const pageSize = computed(() => parseInt(props.pageSize || '0'))
const totalPages = computed(() =>
  pageSize.value > 0 ? Math.max(1, Math.ceil(parsedData.value.length / pageSize.value)) : 1
)
const pagedData = computed(() => {
  if (pageSize.value <= 0) return parsedData.value
  const start = (currentPage.value - 1) * pageSize.value
  return parsedData.value.slice(start, start + pageSize.value)
})

function prevPage() {
  if (currentPage.value > 1) currentPage.value--
}
function nextPage() {
  if (currentPage.value < totalPages.value) currentPage.value++
}
</script>

<template>
  <div class="sys-table-wrapper">
    <table
      class="sys-table"
      :class="{ 'sys-table--striped': striped === 'true', 'sys-table--hoverable': hoverable }"
    >
      <thead>
        <tr>
          <th
            v-for="col in parsedColumns"
            :key="col.key"
            :style="`width: ${col.width || ''}; text-align: ${col.align || 'left'};`"
          >{{ col.label }}</th>
        </tr>
      </thead>
      <TransitionGroup
        name="sys-table-row"
        tag="tbody"
      >
        <tr
          v-for="(row, idx) in pagedData"
          :key="idx"
          class="sys-table-row"
          :style="animated ? { animationDelay: `${Math.min(idx, 12) * 30}ms` } : null"
        >
          <td
            v-for="col in parsedColumns"
            :key="col.key"
            :style="`text-align: ${col.align || 'left'};`"
          >{{ row[col.key] }}</td>
        </tr>
        <tr v-if="parsedData.length === 0" key="empty">
          <td
            :colspan="parsedColumns.length || 1"
            class="sys-table-empty"
          >
            <span class="material-symbols-rounded">inbox</span>
            <span>暂无数据</span>
          </td>
        </tr>
      </TransitionGroup>
    </table>
    <div v-if="pageSize > 0 && totalPages > 1" class="sys-table-pagination">
      <button class="sys-table-pagination-btn" :disabled="currentPage === 1" @click="prevPage">
        <span class="material-symbols-rounded">chevron_left</span>
      </button>
      <span class="sys-table-pagination-info">{{ currentPage }} / {{ totalPages }}</span>
      <button class="sys-table-pagination-btn" :disabled="currentPage === totalPages" @click="nextPage">
        <span class="material-symbols-rounded">chevron_right</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.sys-table-wrapper {
  width: 100%;
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
  background: var(--md-sys-color-surface, #fff);
}

.sys-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.sys-table th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-weight: 600;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  background: var(--md-sys-color-surface-container-low, #f3f3fa);
  border-bottom: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
  white-space: nowrap;
}

.sys-table td {
  padding: 0.625rem 1rem;
  border-bottom: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
  color: var(--md-sys-color-on-surface, #1a1b20);
}

.sys-table--striped .sys-table-row:nth-child(even) {
  background: var(--md-sys-color-surface-container-lowest, #ffffff);
}

.sys-table--hoverable .sys-table-row {
  transition: background var(--md-sys-motion-duration-x-short) var(--md-sys-motion-standard);
}

.sys-table--hoverable .sys-table-row:hover {
  background: color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 5%, transparent);
}

.sys-table-row {
  animation: sys-fade-in var(--md-sys-motion-duration-medium) var(--md-sys-motion-decelerated) both;
}

.sys-table-empty {
  text-align: center;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  padding: 3rem 1rem;
}

.sys-table-empty .material-symbols-rounded {
  display: block;
  font-size: 48px;
  opacity: 0.3;
  margin-bottom: 0.5rem;
}

.sys-table-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
}

.sys-table-pagination-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--md-sys-color-outline, #74767f);
  border-radius: 50%;
  background: transparent;
  color: var(--md-sys-color-on-surface, #1a1b20);
  cursor: pointer;
  transition: background var(--md-sys-motion-duration-x-short) var(--md-sys-motion-standard);
}

.sys-table-pagination-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 8%, transparent);
}

.sys-table-pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sys-table-pagination-info {
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  font-variant-numeric: tabular-nums;
}

/* TransitionGroup */
.sys-table-row-enter-active,
.sys-table-row-leave-active {
  transition:
    opacity var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    transform var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized);
}

.sys-table-row-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}

.sys-table-row-leave-to {
  opacity: 0;
  transform: translateX(4px);
}
</style>
