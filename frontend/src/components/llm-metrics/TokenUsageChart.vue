<!-- LLM Token 使用结构与近期 Token 趋势横向柱状图组件。 -->
<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'

use([
  CanvasRenderer,
  BarChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
])

interface TokenTrendItem {
  id: number | string
  label: string
  success: boolean
  cacheHit: boolean
  inputTokens: number
  outputTokens: number
  tokens: number
}

interface ChartThemeColors {
  primary: string
  tertiary: string
  surface: string
  onSurface: string
  onSurfaceVariant: string
  outline: string
}

interface Props {
  inputTokens: number
  outputTokens: number
  trend: TokenTrendItem[]
  inputLabel: string
  outputLabel: string
  fallbackLabel: string
  locale: string
}

const props = defineProps<Props>()

const option = computed<EChartsOption>(() => {
  const colors = getChartThemeColors()
  const hasRecentData = props.trend.some((item) => item.tokens > 0)
  const recentRows = hasRecentData ? [...props.trend].slice(-8).reverse() : []
  const categoryData = hasRecentData ? recentRows.map((item) => item.label) : [props.fallbackLabel]
  const inputData = hasRecentData ? recentRows.map((item) => item.inputTokens) : [props.inputTokens]
  const outputData = hasRecentData ? recentRows.map((item) => item.outputTokens) : [props.outputTokens]

  return {
    backgroundColor: 'transparent',
    color: [colors.primary, colors.tertiary],
    grid: {
      top: 48,
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
      valueFormatter: (value) => `${formatNumber(Number(value))} tokens`,
    },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: {
        color: colors.onSurfaceVariant,
        fontSize: 12,
        fontWeight: 600,
      },
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
          opacity: 0.36,
        },
      },
    },
    yAxis: {
      type: 'category',
      data: categoryData,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: {
        color: colors.onSurface,
        fontSize: 12,
        fontWeight: 700,
        width: 72,
        overflow: 'truncate',
      },
    },
    series: [
      {
        name: props.inputLabel,
        type: 'bar',
        stack: 'tokens',
        barMaxWidth: 16,
        data: inputData,
        itemStyle: {
          borderRadius: [999, 0, 0, 999],
          color: colors.primary,
        },
      },
      {
        name: props.outputLabel,
        type: 'bar',
        stack: 'tokens',
        barMaxWidth: 16,
        data: outputData,
        itemStyle: {
          borderRadius: [0, 999, 999, 0],
          color: colors.tertiary,
        },
      },
    ],
  }
})

function getChartThemeColors(): ChartThemeColors {
  if (typeof window === 'undefined') {
    return {
      primary: '#0075de',
      tertiary: '#2a9d99',
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
    tertiary: getColor('--md-sys-color-tertiary', '#2a9d99'),
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
