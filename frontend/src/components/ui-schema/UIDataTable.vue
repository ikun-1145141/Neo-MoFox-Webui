<!--
  @file UIDataTable.vue
  @description 数据表格组件，支持 API 加载、分页、排序、选择和自定义列模板。
  消费共享工具：dataStore（getValueByPath / setValueByPath）、apiExecutor（executeApiCall / resolveEndpoint）。
-->
<template>
  <div class="ui-data-table">
    <!-- 表格主体 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th v-if="selectable" class="checkbox-cell">
              <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
            </th>
            <th
              v-for="col in columns"
              :key="col.key"
              :style="{ width: col.width }"
              :class="{ sortable: col.sortable }"
              @click="handleSort(col)"
            >
              <div class="header-content">
                <span>{{ col.label }}</span>
                <span v-if="col.sortable" class="material-symbols-outlined sort-icon">
                  {{ getSortIcon(col.key) }}
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" class="state-row">
            <td :colspan="totalColumns" class="state-cell">
              <div class="spinner"></div>
              <span>加载中...</span>
            </td>
          </tr>
          <tr v-else-if="tableData.length === 0" class="state-row">
            <td :colspan="totalColumns" class="state-cell">
              <span>暂无数据</span>
            </td>
          </tr>
          <tr
            v-else
            v-for="(row, rowIndex) in tableData"
            :key="rowIndex"
            :class="{ 'is-selected': selectedRows.has(row) }"
          >
            <td v-if="selectable" class="checkbox-cell">
              <input
                type="checkbox"
                :checked="selectedRows.has(row)"
                @change="toggleSelectRow(row)"
              />
            </td>
            <td v-for="col in columns" :key="col.key">
              <!-- 自定义模板渲染 -->
              <LocalContextWrapper v-if="col.templateNode" :row="row" :index="rowIndex">
                <SchemaRenderer
                  v-for="(child, childIndex) in col.templateNode.children"
                  :key="childIndex"
                  :node="child"
                  :store="store"
                  :api-base="apiBase"
                />
              </LocalContextWrapper>
              <!-- 默认文本渲染 -->
              <template v-else>
                {{ row[col.key] }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页器 -->
    <div v-if="pagination" class="pagination-container">
      <span class="total-count">共 {{ totalCount }} 条</span>
      <div class="pagination-controls">
        <button :disabled="currentPage === 1" @click="changePage(currentPage - 1)" class="pag-btn">
          <span class="material-symbols-outlined">chevron_left</span>
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)" class="pag-btn">
          <span class="material-symbols-outlined">chevron_right</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, watch, onMounted, provide } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import { getValueByPath, setValueByPath } from '@/utils/dataStore'
import { executeApiCall } from '@/utils/apiExecutor'
import SchemaRenderer from './SchemaRenderer.vue'

// 本地上下文包装组件，用于向子组件传递行数据
const LocalContextWrapper = {
  props: ['row', 'index'],
  setup(props: any, { slots }: any) {
    provide('uiSchemaLocalContext', { row: props.row, index: props.index })
    return () => slots.default?.()
  },
}

interface Props {
  node: UiNode
  store?: Record<string, any>
  apiBase?: string
}

const props = defineProps<Props>()

const dataStore = props.store || inject<any>('uiSchemaDataStore')
const getValue = inject<any>('uiSchemaGetValue', getValueByPath)
const setValue = inject<any>('uiSchemaSetValue', setValueByPath)
const injectedApiBase = inject<string>('uiSchemaApiBase', '')
const pluginName = inject<string | null>('uiSchemaPluginName', null)

const loading = ref(false)
const localTableData = ref<any[]>([])
const totalCount = ref(0)
const currentPage = ref(1)
const sortKey = ref('')
const sortOrder = ref<'asc' | 'desc' | ''>('')
const selectedRows = ref<Set<any>>(new Set())

const pagination = computed(() => props.node.attrs.pagination === 'true')
const pageSize = computed(() => Number(props.node.attrs['page-size'] || 20))
const selectable = computed(() => props.node.attrs.selectable === 'true')
const bindPath = computed(() => props.node.attrs['data-bind'])

// 解析列定义
const columns = computed(() => {
  return props.node.children
    .filter((child) => child.tag === 'column')
    .map((child) => {
      const templateNode = child.children.find((c) => c.tag === 'template')
      return {
        key: child.attrs.key || '',
        label: child.attrs.label || '',
        width: child.attrs.width || undefined,
        sortable: child.attrs.sortable === 'true',
        templateNode,
      }
    })
})

const totalColumns = computed(() => columns.value.length + (selectable.value ? 1 : 0))

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value) || 1)

// 数据源：优先从 dataStore 绑定路径获取，其次使用本地数据
const tableData = computed(() => {
  if (bindPath.value && dataStore) {
    const val = getValue(dataStore, bindPath.value)
    return Array.isArray(val) ? val : []
  }
  return localTableData.value
})

// 加载数据
async function fetchData() {
  const attrs = props.node.attrs
  const endpoint = attrs['api-endpoint']
  if (!endpoint) return

  loading.value = true
  try {
    const apiBaseVal = props.apiBase || injectedApiBase
    const params: Record<string, any> = {}

    if (pagination.value) {
      params.page = currentPage.value
      params.page_size = pageSize.value
    }
    if (sortKey.value && sortOrder.value) {
      params.sort_by = sortKey.value
      params.sort_order = sortOrder.value
    }

    const res = await executeApiCall<any>({
      endpoint,
      method: (attrs['api-method'] as any) || 'GET',
      apiBase: apiBaseVal,
      data: Object.keys(params).length > 0 ? params : undefined,
      pluginName,
    })

    // 兼容多种响应格式
    let list: any[] = []
    let total = 0

    if (Array.isArray(res)) {
      list = res
      total = res.length
    } else if (res && typeof res === 'object') {
      const dataObj = (res as any).data || res
      if (Array.isArray(dataObj)) {
        list = dataObj
        total = (res as any).total || dataObj.length
      } else {
        const arrayKey = Object.keys(dataObj).find((k) => Array.isArray(dataObj[k]))
        if (arrayKey) {
          list = dataObj[arrayKey]
          total = (res as any).total || (res as any).count || list.length
        }
      }
    }

    if (bindPath.value && dataStore) {
      setValue(dataStore, bindPath.value, list)
    } else {
      localTableData.value = list
    }

    totalCount.value = total
  } catch (e) {
    console.error('Failed to fetch table data:', e)
  } finally {
    loading.value = false
  }
}

// 排序处理
function handleSort(col: any) {
  if (!col.sortable) return
  if (sortKey.value === col.key) {
    if (sortOrder.value === 'asc') {
      sortOrder.value = 'desc'
    } else if (sortOrder.value === 'desc') {
      sortKey.value = ''
      sortOrder.value = ''
    } else {
      sortOrder.value = 'asc'
    }
  } else {
    sortKey.value = col.key
    sortOrder.value = 'asc'
  }
  fetchData()
}

function getSortIcon(key: string): string {
  if (sortKey.value !== key) return 'unfold_more'
  return sortOrder.value === 'asc' ? 'arrow_upward' : 'arrow_downward'
}

// 选择处理
const isAllSelected = computed(() => {
  return tableData.value.length > 0 && tableData.value.every((row) => selectedRows.value.has(row))
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    tableData.value.forEach((row) => selectedRows.value.delete(row))
  } else {
    tableData.value.forEach((row) => selectedRows.value.add(row))
  }
}

function toggleSelectRow(row: any) {
  if (selectedRows.value.has(row)) {
    selectedRows.value.delete(row)
  } else {
    selectedRows.value.add(row)
  }
}

function changePage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  fetchData()
}

onMounted(() => {
  if (props.node.attrs['auto-refresh'] !== 'false') {
    fetchData()
  }
})

// 监听刷新触发器
watch(
  () => dataStore?.tables?.[props.node.attrs.id]?.refreshTrigger,
  (trigger) => {
    if (trigger) {
      fetchData()
    }
  },
)
</script>

<style scoped>
.ui-data-table {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--md-sys-color-surface-container-low);
  border-radius: 16px;
  padding: 16px;
  box-sizing: border-box;
}

.table-container {
  overflow-x: auto;
  width: 100%;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 14px;
}

.data-table th {
  padding: 12px 16px;
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 500;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  user-select: none;
}

.data-table th.sortable {
  cursor: pointer;
}

.data-table th.sortable:hover {
  color: var(--md-sys-color-on-surface);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 4px;
}

.sort-icon {
  font-size: 16px;
}

.data-table td {
  padding: 12px 16px;
  color: var(--md-sys-color-on-surface);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  vertical-align: middle;
}

.data-table tr:hover td {
  background: var(--md-sys-color-surface-container-high);
}

.data-table tr.is-selected td {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.checkbox-cell {
  width: 48px;
  text-align: center;
  padding: 0;
}

.state-row {
  height: 120px;
}

.state-cell {
  text-align: center;
  color: var(--md-sys-color-on-surface-variant);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--md-sys-color-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 8px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 分页样式 */
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
}

.total-count {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pag-btn {
  background: transparent;
  border: none;
  color: var(--md-sys-color-on-surface);
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pag-btn:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-highest);
}

.pag-btn:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  font-weight: 500;
}
</style>
