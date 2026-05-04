<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent
} from 'echarts/components'
import type { EChartsOption } from 'echarts'
import type { MessageTrend } from '../../api/types/dashboard'

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  ToolboxComponent
])

interface Props {
  data: MessageTrend | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  changeDays: [days: number]
}>()

const selectedDays = ref(7)

const chartOption = computed<EChartsOption>(() => {
  if (!props.data) {
    return {
      title: { text: '加载中...', left: 'center', top: 'middle' }
    }
  }

  const dates = props.data.date_range
  const totalData = dates.map(date => props.data!.daily_stats[date]?.total || 0)
  const inboundData = dates.map(date => props.data!.daily_stats[date]?.inbound || 0)
  const outboundData = dates.map(date => props.data!.daily_stats[date]?.outbound || 0)

  // 获取CSS变量颜色
  const root = document.documentElement
  const primaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-primary').trim()
  const tertiaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-tertiary').trim()
  const secondaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-secondary').trim()
  const surfaceColor = getComputedStyle(root).getPropertyValue('--md-sys-color-surface-container').trim()
  const onSurfaceColor = getComputedStyle(root).getPropertyValue('--md-sys-color-on-surface').trim()
  const onSurfaceVariantColor = getComputedStyle(root).getPropertyValue('--md-sys-color-on-surface-variant').trim()

  return {
    backgroundColor: 'transparent',
    grid: {
      top: 60,
      right: 40,
      bottom: 50,
      left: 50,
      containLabel: true
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: {
          color: onSurfaceVariantColor,
          opacity: 0.3
        }
      },
      backgroundColor: surfaceColor || 'rgba(255, 255, 255, 0.95)',
      borderColor: onSurfaceVariantColor || '#e0e0e0',
      borderWidth: 1,
      textStyle: {
        color: onSurfaceColor || '#000'
      },
      padding: [12, 16],
      borderRadius: 8
    },
    legend: {
      data: ['总消息数', '入站消息', '出站消息'],
      top: 10,
      textStyle: {
        color: onSurfaceColor || '#000'
      }
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        color: onSurfaceVariantColor || '#666'
      },
      axisLine: {
        lineStyle: {
          color: onSurfaceVariantColor || '#e0e0e0'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '消息数量',
      nameTextStyle: {
        color: onSurfaceVariantColor || '#666'
      },
      axisLabel: {
        color: onSurfaceVariantColor || '#666'
      },
      axisLine: {
        lineStyle: {
          color: onSurfaceVariantColor || '#e0e0e0'
        }
      },
      splitLine: {
        lineStyle: {
          color: onSurfaceVariantColor || '#f0f0f0',
          opacity: 0.2
        }
      }
    },
    series: [
      {
        name: '总消息数',
        type: 'line',
        data: totalData,
        smooth: true,
        lineStyle: {
          width: 3
        },
        itemStyle: {
          color: primaryColor || '#6750a4'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: primaryColor ? `${primaryColor}40` : 'rgba(103, 80, 164, 0.25)' },
              { offset: 1, color: primaryColor ? `${primaryColor}00` : 'rgba(103, 80, 164, 0)' }
            ]
          }
        }
      },
      {
        name: '入站消息',
        type: 'line',
        data: inboundData,
        smooth: true,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: tertiaryColor || '#4caf82'
        }
      },
      {
        name: '出站消息',
        type: 'line',
        data: outboundData,
        smooth: true,
        lineStyle: {
          width: 2
        },
        itemStyle: {
          color: secondaryColor || '#f59e0b'
        }
      }
    ]
  }
})

watch(selectedDays, (newDays) => {
  emit('changeDays', newDays)
})
</script>

<template>
  <div class="chart-container">
    <div class="chart-header">
      <div class="header-left">
        <h3>消息趋势分析</h3>
        <div class="summary-tags" v-if="data">
          <span class="tag">总计: {{ data.summary.total_messages }}</span>
          <span class="tag">日均: {{ data.summary.avg_per_day }}</span>
          <span class="tag" :class="{ positive: data.summary.growth_rate > 0, negative: data.summary.growth_rate < 0 }">
            增长率: {{ data.summary.growth_rate > 0 ? '+' : '' }}{{ data.summary.growth_rate }}%
          </span>
        </div>
      </div>
      <div class="time-selector">
        <button
          v-for="days in [7, 30, 90]"
          :key="days"
          :class="{ active: selectedDays === days }"
          @click="selectedDays = days"
        >
          过去{{ days }}天
        </button>
      </div>
    </div>
    <div class="chart-content">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>
      <VChart v-else :option="chartOption" :autoresize="true" style="width: 100%; height: 100%;" />
    </div>
  </div>
</template>

<style scoped>
.chart-container {
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 95%, transparent);
  border-radius: 1.25rem;
  padding: 1.5rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(12px);
  height: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

@media (max-width: 640px) {
  .chart-container {
    min-height: 350px;
    padding: 1rem;
  }
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-left {
  flex: 1;
  min-width: 200px;
}

.chart-header h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.summary-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.tag {
  padding: 0.25rem 0.75rem;
  border-radius: 0.5rem;
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.75rem;
  font-weight: 500;
}

.tag.positive {
  background: color-mix(in srgb, var(--md-sys-color-tertiary) 20%, transparent);
  color: var(--md-sys-color-tertiary);
}

.tag.negative {
  background: color-mix(in srgb, var(--md-sys-color-error) 20%, transparent);
  color: var(--md-sys-color-error);
}

.time-selector {
  display: flex;
  gap: 0.5rem;
  background: var(--md-sys-color-surface-container);
  border-radius: 0.75rem;
  padding: 0.25rem;
}

.time-selector button {
  padding: 0.5rem 1rem;
  border: none;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
}

.time-selector button:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.time-selector button.active {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.chart-content {
  position: relative;
  flex: 1;
  min-height: 300px;
  min-width: 0;
  overflow: hidden;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 300px;
  gap: 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--md-sys-color-outline-variant);
  border-top-color: var(--md-sys-color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-state p {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.875rem;
}
</style>
