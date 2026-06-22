<!--
  @file UIPieChart.vue
  @description 饼图组件，支持 API 数据加载和 MD3 主题自适应。
  消费共享工具：dataStore（getValueByPath / setValueByPath）、apiExecutor（executeApiCall / resolveEndpoint）。
-->
<template>
  <div class="ui-chart-container" :style="{ height: `${height}px` }">
    <div v-if="loading" class="chart-loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>
    <div v-else-if="chartData.length === 0" class="chart-empty">
      <span>暂无数据</span>
    </div>
    <v-chart v-else :option="chartOption" class="echart" autoresize />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, onMounted } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import { getValueByPath, setValueByPath } from '@/utils/dataStore'
import { executeApiCall } from '@/utils/apiExecutor'

// ECharts 导入
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'

use([
  CanvasRenderer,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
])

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

const loading = ref(false)
const localChartData = ref<any[]>([])

const height = computed(() => Number(props.node.attrs.height || 300))
const bindPath = computed(() => props.node.attrs['data-bind'])

// 最终图表数据
const chartData = computed<any[]>(() => {
  if (bindPath.value && dataStore) {
    const val = getValue(dataStore, bindPath.value)
    return Array.isArray(val) ? val : []
  }
  return localChartData.value
})

// 加载数据
async function fetchData() {
  const attrs = props.node.attrs
  const endpoint = attrs['api-endpoint']
  if (!endpoint) return

  loading.value = true
  try {
    const apiBaseVal = props.apiBase || injectedApiBase
    const res = await executeApiCall<any>({
      endpoint,
      method: (attrs['api-method'] as any) || 'GET',
      apiBase: apiBaseVal,
    })

    const list = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : [])

    if (bindPath.value && dataStore) {
      setValue(dataStore, bindPath.value, list)
    } else {
      localChartData.value = list
    }
  } catch (e) {
    console.error('Failed to fetch chart data:', e)
  } finally {
    loading.value = false
  }
}

// 动态计算 ECharts 配置
const chartOption = computed<EChartsOption>(() => {
  const attrs = props.node.attrs
  const title = attrs.title || ''
  const nameKey = attrs['name-key'] || 'name'
  const valueKey = attrs['value-key'] || 'value'

  const formattedData = chartData.value.map((item) => ({
    name: item[nameKey] || '',
    value: Number(item[valueKey] || 0),
  }))

  // 获取 MD3 主题颜色
  const root = document.documentElement
  const primaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-primary').trim() || '#6750a4'
  const secondaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-secondary').trim() || '#625b71'
  const tertiaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-tertiary').trim() || '#7d5260'
  const errorColor = getComputedStyle(root).getPropertyValue('--md-sys-color-error').trim() || '#ba1a1a'
  const surfaceColor = getComputedStyle(root).getPropertyValue('--md-sys-color-surface-container').trim() || '#f4f4f4'
  const onSurfaceColor = getComputedStyle(root).getPropertyValue('--md-sys-color-on-surface').trim() || '#000'
  const onSurfaceVariantColor = getComputedStyle(root).getPropertyValue('--md-sys-color-on-surface-variant').trim() || '#666'

  return {
    backgroundColor: 'transparent',
    title: {
      text: title,
      left: 'center',
      textStyle: {
        color: onSurfaceColor,
        fontSize: 16,
        fontWeight: 'bold',
      },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: surfaceColor,
      borderColor: onSurfaceVariantColor,
      borderWidth: 1,
      textStyle: {
        color: onSurfaceColor,
      },
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'horizontal',
      bottom: 'bottom',
      textStyle: {
        color: onSurfaceColor,
      },
    },
    color: [primaryColor, secondaryColor, tertiaryColor, errorColor, '#4caf50', '#ff9800', '#00bcd4'],
    series: [
      {
        type: 'pie',
        radius: '55%',
        center: ['50%', '50%'],
        data: formattedData,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
        label: {
          color: onSurfaceColor,
        },
      },
    ],
  }
})

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.ui-chart-container {
  width: 100%;
  position: relative;
  background: var(--md-sys-color-surface-container-low);
  border-radius: 16px;
  padding: 16px;
  box-sizing: border-box;
  border: 1px solid var(--md-sys-color-outline-variant);
}

.echart {
  width: 100%;
  height: 100%;
}

.chart-loading,
.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 14px;
  gap: 12px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--md-sys-color-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
