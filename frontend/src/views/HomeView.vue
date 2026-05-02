<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import StatCard from '../components/dashboard/StatCard.vue'
import DataPanel from '../components/dashboard/DataPanel.vue'
import MessageTrendChart from '../components/dashboard/MessageTrendChart.vue'
import PlatformStatsChart from '../components/dashboard/PlatformStatsChart.vue'
import Icon from '../components/common/Icon.vue'
import { useRouter } from 'vue-router'
import { healthCheck } from '../api/modules/settings'
import { getDashboardOverview, getMessageTrend, getPlatformStatistics } from '../api/modules/dashboard'
import type { DashboardOverview, MessageTrend, PlatformStatistics } from '../api/types/dashboard'

const router = useRouter()

type HealthStatus = 'loading' | 'healthy' | 'error'
const healthStatus = ref<HealthStatus>('loading')
const dashboardData = ref<DashboardOverview | null>(null)
const messageTrend = ref<MessageTrend | null>(null)
const platformStats = ref<PlatformStatistics | null>(null)
const lastUpdate = ref<string>('')
const isLoading = ref(true)
const trendDays = ref(7)

let pollTimer: number | null = null

const fetchData = async () => {
  try {
    await healthCheck()
    healthStatus.value = 'healthy'
    
    const [overview, trend, stats] = await Promise.all([
      getDashboardOverview(),
      getMessageTrend(trendDays.value),
      getPlatformStatistics()
    ])
    
    dashboardData.value = overview
    messageTrend.value = trend
    platformStats.value = stats
    lastUpdate.value = new Date(overview.updated_at).toLocaleString()
  } catch {
    healthStatus.value = 'error'
  } finally {
    isLoading.value = false
  }
}

const handleTrendDaysChange = async (days: number) => {
  trendDays.value = days
  try {
    messageTrend.value = await getMessageTrend(days)
  } catch (error) {
    console.error('获取消息趋势失败:', error)
  }
}

onMounted(() => {
  fetchData()
  pollTimer = window.setInterval(fetchData, 30000) // 30秒轮询
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// 计算运行时间（秒转可读格式）
const formatUptime = (seconds: number): string => {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  const parts = []
  if (days > 0) parts.push(`${days}天`)
  if (hours > 0) parts.push(`${hours}小时`)
  if (minutes > 0) parts.push(`${minutes}分钟`)
  
  return parts.join(' ') || '刚启动'
}

const runtimeItems = computed(() => {
  if (!dashboardData.value) return []
  const { runtime } = dashboardData.value
  return [
    {
      label: '活跃任务',
      value: `${runtime.task.active_tasks} / ${runtime.task.total_tasks}`
    },
    {
      label: '协程池守护',
      value: runtime.task.daemon_tasks
    },
    {
      label: '事件订阅',
      value: runtime.event.total_subscriptions
    },
    {
      label: '调度成功率',
      value: `${(runtime.scheduler.success_rate * 100).toFixed(1)}%`
    }
  ]
})

const llmItems = computed(() => {
  if (!dashboardData.value) return []
  const { llm } = dashboardData.value
  return [
    {
      label: '总请求数',
      value: llm.total_requests
    },
    {
      label: '成功率',
      value: `${(llm.success_rate * 100).toFixed(1)}%`
    },
    {
      label: '输入 Token',
      value: llm.total_tokens_in.toLocaleString()
    },
    {
      label: '输出 Token',
      value: llm.total_tokens_out.toLocaleString()
    },
    {
      label: '总花费',
      value: `$${llm.total_cost.toFixed(4)}`
    }
  ]
})

const quickLinks = [
  {
    label: '主题设置',
    desc: '自定义颜色、外观主题',
    icon: 'material-symbols:format-paint-outline-rounded',
    to: '/settings/theme',
  },
  {
    label: '通用设置',
    desc: '语言、字体与系统行为',
    icon: 'material-symbols:tune-rounded',
    to: '/settings/general',
  },
  {
    label: '数据管理',
    desc: '导出 / 导入配置文件',
    icon: 'material-symbols:storage-rounded',
    to: '/settings/data',
  },
]
</script>

<template>
  <AppShell>
    <PageHeader
      title="控制台"
      subtitle="实时监控和统计数据"
      icon="material-symbols:dashboard-outline-rounded"
    />

    <div class="dashboard-layout">
      <!-- 左侧主内容区 -->
      <div class="main-content">
        <!-- 核心数据卡片 - 第一行4个 -->
        <section class="stat-grid-top">
        <StatCard
          v-if="healthStatus === 'loading'"
          label="后端状态"
          value="检测中..."
          icon="material-symbols:progress-activity"
          color-variant="outline"
          :loading="true"
        />
        <StatCard
          v-else-if="healthStatus === 'healthy'"
          label="后端状态"
          value="运行中"
          icon="material-symbols:check-circle-outline-rounded"
          color-variant="success"
        />
        <StatCard
          v-else
          label="后端状态"
          value="未连接"
          icon="material-symbols:cancel-outline-rounded"
          color-variant="error"
        />
        
        <StatCard
          label="今日消息"
          :value="dashboardData?.business.messages.today_total ?? '—'"
          icon="material-symbols:message-outline-rounded"
          color-variant="primary"
          :loading="isLoading"
        />
        
        <StatCard
          label="运行时间"
          :value="formatUptime(dashboardData?.runtime.scheduler.uptime_seconds ?? 0)"
          icon="material-symbols:schedule-rounded"
          color-variant="secondary"
          :loading="isLoading"
        />
        
        <StatCard
          label="注册组件"
          :value="dashboardData?.business.components.total_count ?? '—'"
          icon="material-symbols:widgets-outline-rounded"
          color-variant="tertiary"
          :loading="isLoading"
        />
      </section>

      <!-- 小型数据卡片网格 -->
      <section class="mini-grid">
        <DataPanel
          title="运行总览"
          icon="material-symbols:memory-rounded"
          :items="runtimeItems"
          :loading="isLoading"
        />
        
        <DataPanel
          title="LLM 数据"
          icon="material-symbols:smart-toy-outline-rounded"
          :items="llmItems"
          :loading="isLoading"
        />
        
        <div class="data-panel">
          <div class="panel-header">
            <Icon icon="material-symbols:hub-outline-rounded" width="24" height="24" />
            <h3>连接统计</h3>
          </div>
          <div class="panel-content">
            <div class="data-item">
              <span>活跃会话</span>
              <strong>{{ dashboardData?.business.streams.active_count ?? '—' }}</strong>
            </div>
            <div class="data-item">
              <span>活跃适配器</span>
              <strong>{{ dashboardData?.runtime.adapter.active_count ?? '—' }}</strong>
            </div>
            <div class="data-item">
              <span>已加载插件</span>
              <strong>{{ dashboardData?.business.plugins.loaded_count ?? '—' }}</strong>
            </div>
          </div>
        </div>

        <div class="data-panel">
          <div class="panel-header">
            <Icon icon="material-symbols:monitor-heart-outline-rounded" width="24" height="24" />
            <h3>健康状态</h3>
          </div>
          <div class="panel-content">
            <div class="data-item">
              <span>调度器运行</span>
              <strong :class="{ 'status-ok': dashboardData?.runtime.scheduler.is_running }">
                {{ dashboardData?.runtime.scheduler.is_running ? '正常' : '停止' }}
              </strong>
            </div>
            <div class="data-item">
              <span>进程池状态</span>
              <strong :class="{ 'status-ok': dashboardData?.runtime.task.process_pool_running }">
                {{ dashboardData?.runtime.task.process_pool_running ? '运行中' : '未运行' }}
              </strong>
            </div>
            <div class="data-item">
              <span>失败插件</span>
              <strong :class="{ 'status-error': (dashboardData?.business.plugins.failed_count ?? 0) > 0 }">
                {{ dashboardData?.business.plugins.failed_count ?? 0 }}
              </strong>
            </div>
          </div>
        </div>
      </section>

      <!-- 图表区 -->
      <section class="charts-grid">
        <MessageTrendChart 
          :data="messageTrend"
          :loading="isLoading"
          @change-days="handleTrendDaysChange"
        />
        <PlatformStatsChart 
          :data="platformStats"
          :loading="isLoading"
        />
      </section>

        <div class="update-time" v-if="lastUpdate">
          最后更新时间：{{ lastUpdate }}
        </div>
      </div>

      <!-- 右侧快速入口 -->
      <aside class="side-content">
        <section class="quick-section">
          <h2 class="section-title">快速入口</h2>
          <div class="quick-grid">
            <button
              v-for="link in quickLinks"
              :key="link.to"
              class="quick-card"
              @click="router.push(link.to)"
            >
              <div class="quick-icon">
                <Icon :icon="link.icon" width="24" height="24" />
              </div>
              <div class="quick-text">
                <span class="quick-label">{{ link.label }}</span>
                <span class="quick-desc">{{ link.desc }}</span>
              </div>
              <Icon icon="material-symbols:arrow-forward-ios-rounded" width="16" height="16" class="quick-arrow" />
            </button>
          </div>
        </section>
      </aside>
    </div>
  </AppShell>
</template>

<style scoped>
.dashboard-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  width: 100%;
  max-width: 100%;
}

@media (min-width: 1280px) {
  .dashboard-layout {
    grid-template-columns: 1fr 320px;
  }
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0;
  overflow: hidden;
}

/* 核心数据卡片网格 - 第一行固定4个 */
.stat-grid-top {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

@media (max-width: 1200px) {
  .stat-grid-top {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stat-grid-top {
    grid-template-columns: 1fr;
  }
  
  .dashboard-layout {
    gap: 1rem;
  }
  
  .main-content {
    gap: 1rem;
  }
}

/* 小型数据卡片网格 - 保持4列对齐 */
.mini-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

@media (max-width: 1200px) {
  .mini-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .mini-grid {
    grid-template-columns: 1fr;
  }
}

.data-panel {
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 86%, transparent);
  border-radius: 1.25rem;
  padding: 1.5rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(8px);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 240px;
}

.data-panel:hover {
  transform: translateY(-2px);
  box-shadow: 0px 6px 20px rgba(24, 28, 32, 0.08);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  color: var(--md-sys-color-primary);
}

.panel-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
}

.data-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.data-item:last-child {
  border-bottom: none;
}

.data-item span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.9375rem;
}

.data-item strong {
  color: var(--md-sys-color-on-surface);
  font-size: 0.9375rem;
  font-weight: 600;
}

.data-item strong.status-ok {
  color: var(--md-sys-color-tertiary, #4caf82);
}

.data-item strong.status-error {
  color: var(--md-sys-color-error);
}

/* 图表网格 - 2:1比例 */
.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  min-width: 0;
  overflow: hidden;
}

@media (max-width: 1024px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

.update-time {
  text-align: right;
  font-size: 0.75rem;
  color: var(--md-sys-color-on-surface-variant);
  padding-top: 0.5rem;
}

/* 快速入口 */
.side-content {
  min-width: 0;
}

@media (max-width: 1279px) {
  .side-content {
    grid-column: 1;
  }
}

.section-title {
  margin: 0 0 1rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.quick-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.quick-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 86%, transparent);
  border-radius: 1rem;
  border: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: background 0.15s, transform 0.15s;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.03);
  backdrop-filter: blur(8px);
}

.quick-card:hover {
  background: color-mix(in srgb, var(--md-sys-color-surface-container-highest) 92%, transparent);
  transform: translateX(4px);
}

.quick-icon {
  width: 44px;
  height: 44px;
  border-radius: 0.875rem;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.quick-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.quick-label {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.quick-desc {
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant);
}

.quick-arrow {
  color: var(--md-sys-color-on-surface-variant);
  flex-shrink: 0;
}
</style>
