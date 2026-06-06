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
import { useI18n } from '../utils/i18n'

const { t } = useI18n()

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
  if (days > 0) parts.push(`${days}${t('home.uptime.days')}`)
  if (hours > 0) parts.push(`${hours}${t('home.uptime.hours')}`)
  if (minutes > 0) parts.push(`${minutes}${t('home.uptime.minutes')}`)
  
  return parts.join(' ') || t('home.uptime.justStarted')
}

const normalizedNumber = (value: number | string | null | undefined): number => {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : 0
}

const formatNumber = (value: number | string | null | undefined): string => {
  return normalizedNumber(value).toLocaleString()
}

const formatPercent = (value: number | string | null | undefined): string => {
  return `${(normalizedNumber(value) * 100).toFixed(1)}%`
}

const formatCurrency = (value: number | string | null | undefined): string => {
  return `$${normalizedNumber(value).toFixed(4)}`
}

const getLlmInputTokens = (llm: DashboardOverview['llm']): number => {
  return normalizedNumber(llm.total_input_tokens ?? llm.total_tokens_in ?? llm.total_prompt_tokens)
}

const getLlmOutputTokens = (llm: DashboardOverview['llm']): number => {
  return normalizedNumber(llm.total_output_tokens ?? llm.total_tokens_out ?? llm.total_completion_tokens)
}

const runtimeItems = computed(() => {
  if (!dashboardData.value) return []
  const { runtime } = dashboardData.value
  return [
    {
      label: t('home.runtime.activeTasks'),
      value: `${runtime.task.active_tasks} / ${runtime.task.total_tasks}`
    },
    {
      label: t('home.runtime.daemonTasks'),
      value: runtime.task.daemon_tasks
    },
    {
      label: t('home.runtime.eventSubscriptions'),
      value: runtime.event.total_subscriptions
    },
    {
      label: t('home.runtime.schedulerSuccessRate'),
      value: `${(runtime.scheduler.success_rate * 100).toFixed(1)}%`
    }
  ]
})

const llmItems = computed(() => {
  if (!dashboardData.value) return []
  const { llm } = dashboardData.value
  return [
    {
      label: t('home.llm.totalRequests'),
      value: formatNumber(llm.total_requests)
    },
    {
      label: t('home.llm.successRate'),
      value: formatPercent(llm.success_rate)
    },
    {
      label: t('home.llm.inputTokens'),
      value: formatNumber(getLlmInputTokens(llm))
    },
    {
      label: t('home.llm.outputTokens'),
      value: formatNumber(getLlmOutputTokens(llm))
    },
    {
      label: t('home.llm.totalCost'),
      value: formatCurrency(llm.total_cost)
    }
  ]
})

const quickLinks = computed(() => [
  {
    label: t('home.quickLinks.home.label'),
    desc: t('home.quickLinks.home.desc'),
    icon: 'material-symbols:home-outline-rounded',
    to: '/',
  },
  {
    label: t('home.quickLinks.config.label'),
    desc: t('home.quickLinks.config.desc'),
    icon: 'material-symbols:tune-rounded',
    to: '/config',
  },
  {
    label: t('home.quickLinks.plugins.label'),
    desc: t('home.quickLinks.plugins.desc'),
    icon: 'material-symbols:extension-outline-rounded',
    to: '/plugins',
  },
  {
    label: t('home.quickLinks.configPlugins.label'),
    desc: t('home.quickLinks.configPlugins.desc'),
    icon: 'material-symbols:settings-outline-rounded',
    to: '/config/plugins',
  },
  {
    label: t('home.quickLinks.settings.label'),
    desc: t('home.quickLinks.settings.desc'),
    icon: 'material-symbols:setting-outline-rounded',
    to: '/settings',
  },
])
</script>

<template>
  <AppShell>
    <div class="home-header-card">
      <PageHeader
        :title="t('home.title')"
        :subtitle="t('home.subtitle')"
        icon="material-symbols:dashboard-outline-rounded"
      />
    </div>

    <div class="dashboard-layout">
      <!-- 左侧主内容区 -->
      <div class="main-content">
        <!-- 核心数据卡片 - 第一行4个 -->
        <section class="stat-grid-top">
        <StatCard
          v-if="healthStatus === 'loading'"
          :label="t('home.stats.backendStatus')"
          :value="t('home.stats.checking')"
          icon="material-symbols:progress-activity"
          color-variant="outline"
          :loading="true"
        />
        <StatCard
          v-else-if="healthStatus === 'healthy'"
          :label="t('home.stats.backendStatus')"
          :value="t('home.stats.running')"
          icon="material-symbols:check-circle-outline-rounded"
          color-variant="success"
        />
        <StatCard
          v-else
          :label="t('home.stats.backendStatus')"
          :value="t('home.stats.disconnected')"
          icon="material-symbols:cancel-outline-rounded"
          color-variant="error"
        />
        
        <StatCard
          :label="t('home.stats.todayMessages')"
          :value="dashboardData?.business.messages.today_total ?? '—'"
          icon="material-symbols:message-outline-rounded"
          color-variant="primary"
          :loading="isLoading"
        />
        
        <StatCard
          :label="t('home.stats.uptime')"
          :value="formatUptime(dashboardData?.runtime.scheduler.uptime_seconds ?? 0)"
          icon="material-symbols:schedule-rounded"
          color-variant="secondary"
          :loading="isLoading"
        />
        
        <StatCard
          :label="t('home.stats.registeredComponents')"
          :value="dashboardData?.business.components.total_count ?? '—'"
          icon="material-symbols:widgets-outline-rounded"
          color-variant="tertiary"
          :loading="isLoading"
        />
      </section>

      <!-- 小型数据卡片网格 -->
      <section class="mini-grid">
        <DataPanel
          :title="t('home.runtime.title')"
          icon="material-symbols:memory-rounded"
          :items="runtimeItems"
          :loading="isLoading"
        />
        
        <DataPanel
          :title="t('home.llm.title')"
          icon="material-symbols:smart-toy-outline-rounded"
          :items="llmItems"
          :loading="isLoading"
        />
        
        <div class="data-panel">
          <div class="panel-header">
            <Icon icon="material-symbols:hub-outline-rounded" width="24" height="24" />
            <h3>{{ t('home.plugins.title') }}</h3>
          </div>
          <div class="panel-content">
            <div class="data-item">
              <span>{{ t('home.plugins.loaded') }}</span>
              <strong>{{ dashboardData?.business.plugins.loaded_count ?? '—' }}</strong>
            </div>
            <div class="data-item">
              <span>{{ t('home.plugins.failed') }}</span>
              <strong :class="{ 'status-error': (dashboardData?.business.plugins.failed_count ?? 0) > 0 }">
                {{ dashboardData?.business.plugins.failed_count ?? 0 }}
              </strong>
            </div>
          </div>
        </div>

        <div class="data-panel">
          <div class="panel-header">
            <Icon icon="material-symbols:monitor-heart-outline-rounded" width="24" height="24" />
            <h3>{{ t('home.adapter.title') }}</h3>
          </div>
          <div class="panel-content">
            <div class="data-item">
              <span>{{ t('home.adapter.status.online') }}</span>
              <strong class="status-ok">{{ dashboardData?.runtime.adapter.active_count ?? '—' }}</strong>
            </div>
            <div class="data-item">
              <span>{{ t('home.plugins.failed') }}</span>
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
          {{ t('home.update.lastUpdate') }}: {{ lastUpdate }}
        </div>
      </div>

      <!-- 右侧快捷入口 -->
      <aside class="sidebar-content">
        <section class="quick-section">
          <h2 class="section-title">{{ t('home.quickLinks.title') }}</h2>
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
.home-header-card {
  margin-bottom: 1.5rem;
  padding: 1.5rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
  border-radius: 1.25rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(12px);
}

.home-header-card :deep(.page-header) {
  margin-bottom: 0;
}

.dashboard-layout {
  width: 100%;
  max-width: 100%;
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 1.5rem;
}

@media (max-width: 1440px) {
  .dashboard-layout {
    grid-template-columns: 1fr 280px;
  }
}

@media (max-width: 1200px) {
  .dashboard-layout {
    grid-template-columns: 1fr;
  }
  
  .sidebar-content {
    order: -1; /* 在移动端将快捷入口移到顶部 */
  }
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0;
  overflow: hidden;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
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
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.625rem;
  }

  .stat-grid-top :deep(.stat-card) {
    gap: 0.5rem;
    padding: 0.75rem;
    border-radius: 0.875rem;
  }

  .stat-grid-top :deep(.stat-icon) {
    width: 22px;
    height: 22px;
  }

  .stat-grid-top :deep(.stat-val) {
    font-size: 0.9375rem;
  }

  .stat-grid-top :deep(.stat-label) {
    font-size: 0.6875rem;
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
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.625rem;
  }

  .mini-grid :deep(.data-panel),
  .mini-grid > .data-panel {
    min-height: 150px;
    padding: 0.75rem;
    border-radius: 0.875rem;
  }

  .mini-grid :deep(.panel-header),
  .mini-grid > .data-panel .panel-header {
    gap: 0.375rem;
    margin-bottom: 0.625rem;
  }

  .mini-grid :deep(.panel-header svg),
  .mini-grid > .data-panel .panel-header svg {
    width: 20px;
    height: 20px;
  }

  .mini-grid :deep(.panel-header h3),
  .mini-grid > .data-panel .panel-header h3 {
    font-size: 0.875rem;
  }

  .mini-grid :deep(.panel-content),
  .mini-grid > .data-panel .panel-content {
    gap: 0.375rem;
  }

  .mini-grid :deep(.data-item),
  .mini-grid > .data-panel .data-item {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.125rem;
    padding: 0.375rem 0;
  }

  .mini-grid :deep(.data-item span),
  .mini-grid :deep(.data-item strong),
  .mini-grid > .data-panel .data-item span,
  .mini-grid > .data-panel .data-item strong {
    font-size: 0.75rem;
    line-height: 1.25;
  }
}

.data-panel {
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
  border-radius: 1.25rem;
  padding: 1.5rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(12px);
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

.section-title {
  margin: 0 0 1rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.quick-section {
  position: sticky;
  top: 5rem; /* 增加 top 的距离，避免被顶部的导航栏遮挡 */
}

.quick-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

@media (max-width: 1200px) {
  .quick-section {
    position: static;
  }
  
  .quick-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
  }
}

@media (max-width: 640px) {
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.625rem;
  }

  .quick-card {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.5rem;
    min-height: 104px;
    padding: 0.75rem;
    border-radius: 0.875rem;
  }

  .quick-icon {
    width: 32px;
    height: 32px;
    border-radius: 0.625rem;
  }

  .quick-icon svg {
    width: 20px;
    height: 20px;
  }

  .quick-text {
    gap: 0.0625rem;
    min-width: 0;
  }

  .quick-label {
    font-size: 0.8125rem;
    line-height: 1.2;
  }

  .quick-desc {
    display: -webkit-box;
    overflow: hidden;
    font-size: 0.6875rem;
    line-height: 1.25;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .quick-arrow {
    display: none;
  }
}

.quick-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
  border-radius: 1rem;
  border: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: background 0.15s, transform 0.15s;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.03);
  backdrop-filter: blur(12px);
}

.quick-card:hover {
  background: color-mix(in srgb, var(--md-sys-color-surface-container-highest) 92%, transparent);
  transform: translateY(-2px);
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
