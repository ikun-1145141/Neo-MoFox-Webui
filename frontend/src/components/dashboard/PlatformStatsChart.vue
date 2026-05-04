<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import type { EChartsOption } from 'echarts'
import type { PlatformStatistics } from '../../api/types/dashboard'
import { useI18n } from '../../utils/i18n'

const { t } = useI18n()

use([
  CanvasRenderer,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent
])

interface Props {
  data: PlatformStatistics | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const chartOption = computed<EChartsOption>(() => {
  if (!props.data || props.data.platforms.length === 0) {
    return {
      title: { 
        text: props.loading ? t('home.charts.platformStats.loading') : t('home.charts.platformStats.noData'), 
        left: 'center', 
        top: 'middle' 
      }
    }
  }

  // 获取CSS变量颜色
  const root = document.documentElement
  const primaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-primary').trim()
  const secondaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-secondary').trim()
  const tertiaryColor = getComputedStyle(root).getPropertyValue('--md-sys-color-tertiary').trim()
  const surfaceColor = getComputedStyle(root).getPropertyValue('--md-sys-color-surface-container').trim()
  const onSurfaceColor = getComputedStyle(root).getPropertyValue('--md-sys-color-on-surface').trim()
  const onSurfaceVariantColor = getComputedStyle(root).getPropertyValue('--md-sys-color-on-surface-variant').trim()
  const surfaceContainerColor = getComputedStyle(root).getPropertyValue('--md-sys-color-surface-container-low').trim()

  // 生成渐变色系
  const colorPalette = [
    primaryColor || '#6750a4',
    secondaryColor || '#625b71',
    tertiaryColor || '#7d5260',
    '#8e97f7',
    '#a0c4ff',
    '#ffd6a5'
  ]

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)',
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
      orient: 'horizontal',
      bottom: 10,
      left: 'center',
      formatter: (name: string) => {
        const platform = props.data!.platforms.find(p => p.platform === name)
        return `${name}: ${platform?.count || 0}`
      },
      textStyle: {
        color: onSurfaceColor || '#000'
      }
    },
    color: colorPalette,
    series: [
      {
        name: t('home.charts.platformStats.platformMessages'),
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: surfaceContainerColor || '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 18,
            fontWeight: 'bold',
            formatter: '{b}\n{d}%',
            color: onSurfaceColor || '#000'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.2)'
          }
        },
        labelLine: {
          show: false
        },
        data: props.data.platforms.map(p => ({
          value: p.count,
          name: p.platform
        }))
      }
    ]
  }
})
</script>

<template>
  <div class="chart-container">
    <div class="chart-header">
      <h3>{{ t('home.charts.platformStats.title') }}</h3>
      <div class="total-badge" v-if="data">
        {{ t('home.charts.platformStats.total') }}: {{ data.total }} {{ t('home.charts.platformStats.messages') }}
      </div>
    </div>
    <div class="chart-content">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>{{ t('home.charts.platformStats.loading') }}</p>
      </div>
      <div v-else-if="!data || data.platforms.length === 0" class="empty-state">
        <p>{{ t('home.charts.platformStats.noPlatformData') }}</p>
      </div>
      <VChart v-else :option="chartOption" :autoresize="true" style="width: 100%; height: 100%;" />
    </div>
    
    <!-- 平台列表 -->
    <div class="platform-list" v-if="data && data.platforms.length > 0">
      <div 
        v-for="platform in data.platforms" 
        :key="platform.platform"
        class="platform-item"
      >
        <span class="platform-name">{{ platform.platform }}</span>
        <div class="platform-stats">
          <span class="count">{{ platform.count }}</span>
          <span class="percentage">{{ platform.percentage }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-container {
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
  border-radius: 1.25rem;
  padding: 1.5rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(12px);
  height: 100%;
  min-height: 450px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

@media (max-width: 640px) {
  .chart-container {
    min-height: 400px;
    padding: 1rem;
  }
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.chart-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.total-badge {
  padding: 0.375rem 0.875rem;
  border-radius: 0.75rem;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  font-size: 0.875rem;
  font-weight: 600;
}

.chart-content {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 250px;
  min-width: 0;
  overflow: hidden;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 250px;
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

.loading-state p,
.empty-state p {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.875rem;
}

.platform-list {
  margin-top: 1.5rem;
  border-top: 1px solid var(--md-sys-color-outline-variant);
  padding-top: 1rem;
}

.platform-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 50%, transparent);
}

.platform-item:last-child {
  border-bottom: none;
}

.platform-name {
  font-size: 0.9375rem;
  color: var(--md-sys-color-on-surface);
  font-weight: 500;
}

.platform-stats {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.count {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.percentage {
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant);
  padding: 0.25rem 0.5rem;
  background: var(--md-sys-color-surface-container-highest);
  border-radius: 0.5rem;
}
</style>
