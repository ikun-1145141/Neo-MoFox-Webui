<script setup lang="ts">
/**
 * SysChart - 基于 ECharts 的图表组件。
 *
 * 接收 JSON 格式的 ECharts 配置，渲染为交互式图表。
 * 支持 line / bar / pie / scatter / radar 等常用图表类型，
 * 也支持直接传入完整的 ECharts option 对象实现自定义图表。
 *
 * ═══════════════════════════════════════════════════════════════
 * 数据 JSON 格式说明（通过 data prop 传入，字符串或对象）：
 * ═══════════════════════════════════════════════════════════════
 *
 * 【方式一：简化格式】使用 type prop 指定图表类型 + data prop 传入数据
 *
 * --- 折线图 (type="line") ---
 * {
 *   "xAxis": ["Mon", "Tue", "Wed", "Thu", "Fri"],
 *   "series": [
 *     { "name": "邮件", "data": [120, 132, 101, 134, 90] },
 *     { "name": "访问", "data": [220, 182, 191, 234, 290] }
 *   ],
 *   "title": "周访问量统计"
 * }
 *
 * --- 柱状图 (type="bar") ---
 * {
 *   "xAxis": ["产品A", "产品B", "产品C"],
 *   "series": [
 *     { "name": "销量", "data": [150, 230, 180] }
 *   ],
 *   "title": "产品销量对比"
 * }
 *
 * --- 饼图 (type="pie") ---
 * {
 *   "series": [
 *     { "name": "搜索引擎", "value": 1048 },
 *     { "name": "直接访问", "value": 735 },
 *     { "name": "邮件营销", "value": 580 }
 *   ],
 *   "title": "访问来源分布"
 * }
 *
 * --- 散点图 (type="scatter") ---
 * {
 *   "series": [
 *     { "name": "样本A", "data": [[10, 8.04], [8, 6.95], [13, 7.58]] },
 *     { "name": "样本B", "data": [[9, 8.81], [11, 8.33], [14, 9.96]] }
 *   ],
 *   "title": "散点分布"
 * }
 *
 * --- 雷达图 (type="radar") ---
 * {
 *   "indicator": [
 *     { "name": "销售", "max": 6500 },
 *     { "name": "管理", "max": 16000 },
 *     { "name": "技术", "max": 30000 },
 *     { "name": "客服", "max": 38000 },
 *     { "name": "研发", "max": 52000 }
 *   ],
 *   "series": [
 *     { "name": "预算", "data": [4200, 3000, 20000, 35000, 50000] },
 *     { "name": "实际", "data": [5000, 14000, 28000, 26000, 42000] }
 *   ],
 *   "title": "部门能力评估"
 * }
 *
 * 【方式二：完整 ECharts option】不设置 type，data 中直接传入 ECharts option
 * {
 *   "option": {
 *     "title": { "text": "自定义图表" },
 *     "tooltip": {},
 *     "xAxis": { "type": "category", "data": ["A", "B", "C"] },
 *     "yAxis": { "type": "value" },
 *     "series": [{ "type": "bar", "data": [10, 20, 30] }]
 *   }
 * }
 *
 * ═══════════════════════════════════════════════════════════════
 */
import { computed, ref, watch, onMounted, onUnmounted, shallowRef } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption, ECharts } from 'echarts'

/** 简化数据格式的 series 条目 */
interface SimpleSeries {
  name?: string
  data?: number[] | number[][]
  value?: number
}

/** 简化数据格式 */
interface SimpleChartData {
  title?: string
  xAxis?: string[]
  yAxis?: string[]
  series?: SimpleSeries[]
  indicator?: Array<{ name: string; max: number }>
  option?: EChartsOption
}

const props = defineProps<{
  /** 图表类型：line / bar / pie / scatter / radar；留空则使用 data.option */
  type?: string
  /** 图表数据 JSON（字符串或已解析对象） */
  data?: string | SimpleChartData
  /** 图表高度，支持 CSS 单位，默认 300px */
  height?: string
  /** 主题：light / dark，默认 light */
  theme?: string
  /** 是否显示 loading 动画 */
  loading?: string
}>()

const chartRef = ref<HTMLDivElement | null>(null)
const chartInstance = shallowRef<ECharts | null>(null)
const hasError = ref(false)
const errorMessage = ref('')

/** 解析 data prop */
const parsedData = computed<SimpleChartData | null>(() => {
  if (!props.data) return null
  if (typeof props.data === 'object') return props.data as SimpleChartData
  try {
    return JSON.parse(props.data) as SimpleChartData
  } catch (e) {
    hasError.value = true
    errorMessage.value = '图表数据 JSON 解析失败'
    return null
  }
})

/** 根据 type 和 data 构建完整的 ECharts option */
const chartOption = computed<EChartsOption | null>(() => {
  const data = parsedData.value
  if (!data) return null

  hasError.value = false
  errorMessage.value = ''

  // 方式二：直接使用完整 option
  if (data.option) {
    return data.option
  }

  // 方式一：根据 type 构建 option
  const type = props.type || 'line'
  const baseOption: EChartsOption = {
    tooltip: { trigger: type === 'pie' ? 'item' : 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  }

  if (data.title) {
    baseOption.title = {
      text: data.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 500 },
    }
  }

  const series = data.series || []

  switch (type) {
    case 'line':
    case 'bar': {
      baseOption.xAxis = {
        type: 'category',
        data: data.xAxis || [],
        boundaryGap: type === 'bar',
      }
      baseOption.yAxis = { type: 'value' }
      if (series.length > 1) {
        baseOption.legend = { top: data.title ? 30 : 0 }
      }
      baseOption.series = series.map((s) => ({
        name: s.name || '',
        type: type as 'line' | 'bar',
        data: s.data || [],
        smooth: type === 'line',
      }))
      break
    }

    case 'pie': {
      baseOption.legend = { orient: 'vertical', left: 'left', top: 'middle' }
      baseOption.series = [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
          data: series.map((s) => ({ name: s.name || '', value: s.value ?? 0 })),
        },
      ]
      break
    }

    case 'scatter': {
      baseOption.xAxis = { type: 'value' }
      baseOption.yAxis = { type: 'value' }
      if (series.length > 1) {
        baseOption.legend = { top: data.title ? 30 : 0 }
      }
      baseOption.series = series.map((s) => ({
        name: s.name || '',
        type: 'scatter' as const,
        data: s.data || [],
      }))
      break
    }

    case 'radar': {
      baseOption.radar = {
        indicator: data.indicator || [],
      }
      if (series.length > 1) {
        baseOption.legend = { top: data.title ? 30 : 0 }
      }
      baseOption.series = [
        {
          type: 'radar',
          data: series.map((s) => ({
            name: s.name || '',
            value: s.data || [],
          })),
        },
      ]
      break
    }

    default: {
      hasError.value = true
      errorMessage.value = `不支持的图表类型: ${type}`
      return null
    }
  }

  return baseOption
})

/** 初始化或更新图表 */
function renderChart(): void {
  if (!chartRef.value) return

  if (!chartInstance.value) {
    const themeValue = props.theme === 'dark' ? 'dark' : undefined
    chartInstance.value = echarts.init(chartRef.value, themeValue)
  }

  const option = chartOption.value
  if (option) {
    chartInstance.value.setOption(option, true)
  }

  if (props.loading === 'true') {
    chartInstance.value.showLoading()
  } else {
    chartInstance.value.hideLoading()
  }
}

/** 自适应容器尺寸 */
function handleResize(): void {
  chartInstance.value?.resize()
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  renderChart()

  // 监听容器 resize
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(chartRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chartInstance.value?.dispose()
  chartInstance.value = null
})

watch([chartOption, () => props.loading], () => {
  renderChart()
})

watch(() => props.theme, () => {
  // 主题变更需要重新初始化
  chartInstance.value?.dispose()
  chartInstance.value = null
  renderChart()
})
</script>

<template>
  <div class="sys-chart" :style="{ height: height || '300px' }">
    <!-- 正常图表渲染区 -->
    <div
      v-show="!hasError && parsedData"
      ref="chartRef"
      class="sys-chart-canvas"
    />

    <!-- 错误状态 -->
    <div v-if="hasError" class="sys-chart-placeholder sys-chart-error">
      <span class="material-symbols-rounded">error_outline</span>
      <span>{{ errorMessage }}</span>
    </div>

    <!-- 无数据状态 -->
    <div v-else-if="!parsedData" class="sys-chart-placeholder">
      <span class="material-symbols-rounded">bar_chart</span>
      <span>{{ type || 'chart' }} 图表 - 暂无数据</span>
    </div>
  </div>
</template>

<style scoped>
.sys-chart {
  width: 100%;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  overflow: hidden;
  background: var(--md-sys-color-surface-container-lowest);
  position: relative;
}

.sys-chart-canvas {
  width: 100%;
  height: 100%;
}

.sys-chart-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--md-sys-color-on-surface-variant);
}

.sys-chart-placeholder .material-symbols-rounded {
  font-size: 40px;
  opacity: 0.5;
}

.sys-chart-error {
  color: var(--md-sys-color-error);
}

.sys-chart-error .material-symbols-rounded {
  opacity: 0.8;
}
</style>
