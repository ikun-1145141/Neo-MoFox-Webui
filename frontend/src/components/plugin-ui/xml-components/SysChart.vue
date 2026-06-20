<script setup lang="ts">
/**
 * SysChart - 基于 ECharts 的图表组件。
 *
 * 接收 JSON 格式的 ECharts 配置，渲染为交互式图表。
 * 支持 line / bar / pie / scatter / radar 等常用图表类型，
 * 也支持直接传入完整的 ECharts option 对象实现自定义图表。
 * 自动读取 MD3 主题色变量，与主页面保持一致的主题风格。
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
import { ref, watch, onMounted, onUnmounted, nextTick, shallowRef } from 'vue'
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
  /** 主题：light / dark，默认跟随系统 */
  theme?: string
  /** 是否显示 loading 动画 */
  loading?: string
}>()

const chartRef = ref<HTMLDivElement | null>(null)
const chartInstance = shallowRef<ECharts | null>(null)
const hasError = ref(false)
const errorMessage = ref('')

/** 缓存上一次 data 序列化结果，避免重复渲染 */
let lastDataSnapshot = ''

/** 获取 MD3 CSS 变量颜色 */
function getMd3Colors() {
  const root = document.documentElement
  const get = (varName: string, fallback: string) =>
    getComputedStyle(root).getPropertyValue(varName).trim() || fallback

  return {
    primary: get('--md-sys-color-primary', '#0058bd'),
    secondary: get('--md-sys-color-secondary', '#565e71'),
    tertiary: get('--md-sys-color-tertiary', '#705575'),
    surface: get('--md-sys-color-surface', '#f9f9ff'),
    surfaceContainer: get('--md-sys-color-surface-container', '#edeef4'),
    surfaceContainerLow: get('--md-sys-color-surface-container-low', '#f3f3fa'),
    onSurface: get('--md-sys-color-on-surface', '#1a1b20'),
    onSurfaceVariant: get('--md-sys-color-on-surface-variant', '#44474e'),
    outlineVariant: get('--md-sys-color-outline-variant', '#c4c7cf'),
    primaryContainer: get('--md-sys-color-primary-container', '#d9e2ff'),
  }
}

/** 解析 data prop */
function parseData(): SimpleChartData | null {
  if (!props.data) return null
  if (typeof props.data === 'object') return props.data as SimpleChartData
  try {
    return JSON.parse(props.data) as SimpleChartData
  } catch {
    hasError.value = true
    errorMessage.value = '图表数据 JSON 解析失败'
    return null
  }
}

/** 根据 type 和 data 构建完整的 ECharts option（带主题色） */
function buildChartOption(data: SimpleChartData): EChartsOption | null {
  hasError.value = false
  errorMessage.value = ''

  // 方式二：直接使用完整 option，注入主题色
  if (data.option) {
    const colors = getMd3Colors()
    const option = { ...data.option }
    // 如果用户没指定颜色，注入 MD3 配色
    if (!option.color) {
      option.color = [colors.primary, colors.secondary, colors.tertiary, '#8e97f7', '#a0c4ff', '#ffd6a5']
    }
    if (!option.backgroundColor) {
      option.backgroundColor = 'transparent'
    }
    return option
  }

  // 方式一：根据 type 构建 option
  const type = props.type || 'line'
  const colors = getMd3Colors()

  const colorPalette = [
    colors.primary,
    colors.secondary,
    colors.tertiary,
    '#8e97f7',
    '#a0c4ff',
    '#ffd6a5',
  ]

  const baseOption: EChartsOption = {
    backgroundColor: 'transparent',
    color: colorPalette,
    tooltip: {
      trigger: type === 'pie' ? 'item' : 'axis',
      backgroundColor: colors.surfaceContainer,
      borderColor: colors.outlineVariant,
      borderWidth: 1,
      textStyle: { color: colors.onSurface },
      padding: [8, 12],
      borderRadius: 8,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  }

  if (data.title) {
    baseOption.title = {
      text: data.title,
      left: 'center',
      textStyle: {
        fontSize: 14,
        fontWeight: 500,
        color: colors.onSurface,
      },
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
        axisLine: { lineStyle: { color: colors.outlineVariant } },
        axisLabel: { color: colors.onSurfaceVariant },
      }
      baseOption.yAxis = {
        type: 'value',
        axisLine: { lineStyle: { color: colors.outlineVariant } },
        axisLabel: { color: colors.onSurfaceVariant },
        splitLine: { lineStyle: { color: colors.outlineVariant, opacity: 0.3 } },
      }
      if (series.length > 1) {
        baseOption.legend = {
          top: data.title ? 30 : 0,
          textStyle: { color: colors.onSurface },
        }
      }
      baseOption.series = series.map((s) => ({
        name: s.name || '',
        type: type as 'line' | 'bar',
        data: s.data || [],
        smooth: type === 'line',
        itemStyle: { borderRadius: type === 'bar' ? 4 : 0 },
      }))
      break
    }

    case 'pie': {
      baseOption.legend = {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
        textStyle: { color: colors.onSurface },
      }
      baseOption.series = [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: colors.surfaceContainerLow,
            borderWidth: 2,
          },
          label: { show: false },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold',
              color: colors.onSurface,
            },
          },
          data: series.map((s) => ({ name: s.name || '', value: s.value ?? 0 })),
        },
      ]
      break
    }

    case 'scatter': {
      baseOption.xAxis = {
        type: 'value',
        axisLine: { lineStyle: { color: colors.outlineVariant } },
        axisLabel: { color: colors.onSurfaceVariant },
        splitLine: { lineStyle: { color: colors.outlineVariant, opacity: 0.3 } },
      }
      baseOption.yAxis = {
        type: 'value',
        axisLine: { lineStyle: { color: colors.outlineVariant } },
        axisLabel: { color: colors.onSurfaceVariant },
        splitLine: { lineStyle: { color: colors.outlineVariant, opacity: 0.3 } },
      }
      if (series.length > 1) {
        baseOption.legend = {
          top: data.title ? 30 : 0,
          textStyle: { color: colors.onSurface },
        }
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
        axisLine: { lineStyle: { color: colors.outlineVariant } },
        splitLine: { lineStyle: { color: colors.outlineVariant, opacity: 0.5 } },
        splitArea: { areaStyle: { color: ['transparent'] } },
      }
      if (series.length > 1) {
        baseOption.legend = {
          top: data.title ? 30 : 0,
          textStyle: { color: colors.onSurface },
        }
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
}

/** 初始化或更新图表（安全检查 DOM 尺寸） */
function renderChart(): void {
  const el = chartRef.value
  if (!el) return

  // 防止 DOM 宽高为 0 时初始化 ECharts（会报错）
  if (el.clientWidth === 0 || el.clientHeight === 0) return

  const data = parseData()
  if (!data) {
    // 无数据时销毁已有实例
    if (chartInstance.value) {
      chartInstance.value.dispose()
      chartInstance.value = null
    }
    return
  }

  const option = buildChartOption(data)
  if (!option) return

  if (!chartInstance.value) {
    chartInstance.value = echarts.init(el)
  }

  chartInstance.value.setOption(option, true)

  if (props.loading === 'true') {
    chartInstance.value.showLoading({
      color: getMd3Colors().primary,
      maskColor: 'rgba(255, 255, 255, 0.4)',
    })
  } else {
    chartInstance.value.hideLoading()
  }
}

/** 自适应容器尺寸 */
function handleResize(): void {
  if (chartInstance.value && chartRef.value) {
    const { clientWidth, clientHeight } = chartRef.value
    if (clientWidth > 0 && clientHeight > 0) {
      chartInstance.value.resize()
    }
  }
}

/** 主题变更时重建图表 */
function handleThemeChange(): void {
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
  nextTick(() => renderChart())
}

let resizeObserver: ResizeObserver | null = null
let themeObserver: MutationObserver | null = null

onMounted(() => {
  // 延迟初始化，确保 DOM 已经有尺寸
  nextTick(() => renderChart())

  // 监听容器 resize
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => {
      // 如果图表实例还没创建（之前 DOM 宽高为 0），尝试创建
      if (!chartInstance.value) {
        renderChart()
      } else {
        handleResize()
      }
    })
    resizeObserver.observe(chartRef.value)
  }

  // 监听主题变化（data-theme 属性变更 / style 变更）
  themeObserver = new MutationObserver(() => {
    handleThemeChange()
  })
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme', 'style'],
  })
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  themeObserver?.disconnect()
  chartInstance.value?.dispose()
  chartInstance.value = null
})

// 监听 data / type / loading 变化，用快照对比避免无意义重渲染
watch(
  [() => props.data, () => props.type, () => props.loading],
  () => {
    const snapshot = JSON.stringify([props.data, props.type, props.loading])
    if (snapshot === lastDataSnapshot) return
    lastDataSnapshot = snapshot

    hasError.value = false
    errorMessage.value = ''
    nextTick(() => renderChart())
  },
  { immediate: false }
)

// 监听 theme prop 变化
watch(() => props.theme, () => {
  handleThemeChange()
})
</script>

<template>
  <div class="sys-chart" :style="{ height: height || '300px' }">
    <!-- 正常图表渲染区 -->
    <div
      v-show="!hasError && parseData()"
      ref="chartRef"
      class="sys-chart-canvas"
    />

    <!-- 错误状态 -->
    <div v-if="hasError" class="sys-chart-placeholder sys-chart-error">
      <span class="material-symbols-rounded">error_outline</span>
      <span>{{ errorMessage }}</span>
    </div>

    <!-- 无数据状态 -->
    <div v-else-if="!parseData()" class="sys-chart-placeholder">
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
