<!-- LLM 模型使用排行 ECharts 横向柱状图组件。 -->
<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'

use([
  CanvasRenderer,
  BarChart,
  GridComponent,
  TooltipComponent,
])

interface ModelRankingItem {
  model_name: string
  total_requests: number
}

interface ChartThemeColors {
  primary: string
  surface: string
  onSurface: string
  onSurfaceVariant: string
  outline: string
}

interface Props {
  rows: ModelRankingItem[]
  metricLabel: string
  locale: string
}

const props = defineProps<Props>()

const option = computed<EChartsOption>(() => {
  const colors = getChartThemeColors()
  const rows = [...props.rows].slice(0, 8).reverse()

  return {
    backgroundColor: 'transparent',
    color: [colors.primary],
    grid: {
      top: 12,
      right: 18,
      bottom: 18,
      left: 12,
      containLabel: true,
    },
    tooltip: {
      trigger: 'axis',
      appendToBody: true,
      confine: false,
      axisPointer: { type: 'shadow' },
      backgroundColor: colors.surface,
      borderColor: colors.outline,
      borderWidth: 1,
      borderRadius: 12,
      padding: [10, 12],
      extraCssText: 'z-index: 2147483647; pointer-events: none; box-shadow: 0 14px 28px rgba(0, 0, 0, 0.18);',
      textStyle: {
        color: colors.onSurface,
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      valueFormatter: (value) => formatNumber(Number(value)),
    },
    xAxis: {
      type: 'value',
      axisLabel: {
        color: colors.onSurfaceVariant,
        formatter: (value: number) => formatCompact(value),
      },
      splitLine: {
        lineStyle: {
          color: colors.outline,
          opacity: 0.32,
        },
      },
    },
    yAxis: {
      type: 'category',
      data: rows.map((item) => item.model_name),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: {
        color: colors.onSurface,
        fontSize: 12,
        fontWeight: 700,
        width: 100,
        overflow: 'truncate',
      },
    },
    series: [
      {
        name: props.metricLabel,
        type: 'bar',
        data: rows.map((item) => item.total_requests),
        barMaxWidth: 16,
        itemStyle: {
          borderRadius: 999,
          color: colors.primary,
        },
      },
    ],
  }
})

function getChartThemeColors(): ChartThemeColors {
  if (typeof window === 'undefined') {
    return {
      primary: '#0075de',
      surface: 'rgba(255, 255, 255, 0.96)',
      onSurface: 'rgba(0, 0, 0, 0.95)',
      onSurfaceVariant: '#615d59',
      outline: 'rgba(0, 0, 0, 0.1)',
    }
  }

  const styles = getComputedStyle(document.documentElement)
  const getColor = (name: string, fallback: string): string => styles.getPropertyValue(name).trim() || fallback

  return {
    primary: getColor('--md-sys-color-primary', '#0075de'),
    surface: getColor('--md-sys-color-surface-container', 'rgba(255, 255, 255, 0.96)'),
    onSurface: getColor('--md-sys-color-on-surface', 'rgba(0, 0, 0, 0.95)'),
    onSurfaceVariant: getColor('--md-sys-color-on-surface-variant', '#615d59'),
    outline: getColor('--md-sys-color-outline-variant', 'rgba(0, 0, 0, 0.1)'),
  }
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat(props.locale).format(Number.isFinite(value) ? value : 0)
}

function formatCompact(value: number): string {
  const safeValue = Number.isFinite(value) ? value : 0
  return new Intl.NumberFormat(props.locale, {
    notation: safeValue >= 10000 ? 'compact' : 'standard',
    maximumFractionDigits: 1,
  }).format(safeValue)
}
</script>

<template>
  <VChart :option="option" :autoresize="true" />
</template>
