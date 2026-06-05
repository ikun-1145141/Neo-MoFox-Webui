<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppShell from '../../components/common/AppShell.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import Icon from '../../components/common/Icon.vue'
import { useI18n } from '../../utils/i18n'
import {
  getLastHoursSummary,
  getOverview,
  getRecentRequests,
  listModels,
  listRequestNames,
  listStreams,
} from '../../api/modules/llm-metrics'
import type {
  LLMMetricsOverview,
  LLMModelMetrics,
  LLMRecentRequest,
  LLMRequestMetrics,
  LLMStreamMetrics,
} from '../../api/types/llm-metrics'

const { t } = useI18n()

const overview = ref<LLMMetricsOverview | null>(null)
const lastHoursOverview = ref<LLMMetricsOverview | null>(null)
const models = ref<LLMModelMetrics[]>([])
const requestNames = ref<LLMRequestMetrics[]>([])
const streams = ref<LLMStreamMetrics[]>([])
const recentRequests = ref<LLMRecentRequest[]>([])
const isLoading = ref(true)
const isRefreshing = ref(false)
const lastUpdatedAt = ref('')
const selectedHours = ref(24)

let pollTimer: number | null = null

const hourOptions = [1, 5, 24, 72]

const safeOverview = computed<LLMMetricsOverview>(() => overview.value ?? {
  total_requests: 0,
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_cost: 0,
  success_rate: 0,
  cache_hit_rate: 0,
})

const totalTokens = computed(() => normalizedNumber(safeOverview.value.total_input_tokens) + normalizedNumber(safeOverview.value.total_output_tokens))
const averageCost = computed(() => {
  const requestCount = normalizedNumber(safeOverview.value.total_requests)
  if (requestCount <= 0) return 0
  return normalizedNumber(safeOverview.value.total_cost) / requestCount
})

const recentSuccessCount = computed(() => recentRequests.value.filter((item) => item.success).length)
const recentFailureCount = computed(() => Math.max(recentRequests.value.length - recentSuccessCount.value, 0))

const topModel = computed(() => models.value[0] ?? null)
const topRequest = computed(() => requestNames.value[0] ?? null)

const modelRows = computed(() => {
  const maxRequests = Math.max(...models.value.map((item) => normalizedNumber(item.total_requests)), 1)
  return models.value.slice(0, 6).map((item) => {
    const requestCount = normalizedNumber(item.total_requests)
    return {
      ...item,
      total_requests: requestCount,
      total_input_tokens: normalizedNumber(item.total_input_tokens),
      total_output_tokens: normalizedNumber(item.total_output_tokens),
      total_cost: normalizedNumber(item.total_cost),
      success_rate: normalizedNumber(item.success_rate),
      avg_latency: normalizedNumber(item.avg_latency),
      share: Math.max((requestCount / maxRequests) * 100, requestCount > 0 ? 6 : 0),
    }
  })
})

const requestRows = computed(() => {
  const maxRequests = Math.max(...requestNames.value.map((item) => normalizedNumber(item.total_requests)), 1)
  return requestNames.value.slice(0, 6).map((item) => {
    const requestCount = normalizedNumber(item.total_requests)
    return {
      ...item,
      total_requests: requestCount,
      total_input_tokens: normalizedNumber(item.total_input_tokens),
      total_output_tokens: normalizedNumber(item.total_output_tokens),
      total_cost: normalizedNumber(item.total_cost),
      success_rate: normalizedNumber(item.success_rate),
      avg_latency: normalizedNumber(item.avg_latency),
      share: Math.max((requestCount / maxRequests) * 100, requestCount > 0 ? 6 : 0),
    }
  })
})

const streamRows = computed(() => streams.value.slice(0, 5).map((item) => ({
  ...item,
  total_requests: normalizedNumber(item.total_requests),
  total_input_tokens: normalizedNumber(item.total_input_tokens),
  total_output_tokens: normalizedNumber(item.total_output_tokens),
  total_cost: normalizedNumber(item.total_cost),
  success_rate: normalizedNumber(item.success_rate),
})))

const tokenSegments = computed(() => {
  const input = normalizedNumber(safeOverview.value.total_input_tokens)
  const output = normalizedNumber(safeOverview.value.total_output_tokens)
  const total = input + output

  if (total <= 0) {
    return { input: 0, output: 0 }
  }

  return {
    input: (input / total) * 100,
    output: (output / total) * 100,
  }
})

const recentTrend = computed(() => {
  const rows = [...recentRequests.value].slice(0, 18).reverse()
  const maxTokens = Math.max(...rows.map((item) => normalizedNumber(item.total_tokens)), 1)
  return rows.map((item) => {
    const tokens = normalizedNumber(item.total_tokens)
    return {
      id: item.id,
      label: formatTime(item.timestamp),
      height: Math.max((tokens / maxTokens) * 100, tokens > 0 ? 8 : 0),
      success: item.success,
      cacheHit: item.cache_hit,
      tokens,
    }
  })
})

const statCards = computed(() => [
  {
    label: t('llmMetrics.stats.totalRequests'),
    value: formatNumber(safeOverview.value.total_requests),
    icon: 'material-symbols:send-time-extension-outline-rounded',
    tone: 'primary',
    hint: t('llmMetrics.stats.totalRequestsHint', { count: formatNumber(lastHoursOverview.value?.total_requests ?? 0) }),
  },
  {
    label: t('llmMetrics.stats.totalTokens'),
    value: formatCompact(totalTokens.value),
    icon: 'material-symbols:data-array-rounded',
    tone: 'secondary',
    hint: `${t('llmMetrics.stats.input')} ${formatCompact(safeOverview.value.total_input_tokens)} · ${t('llmMetrics.stats.output')} ${formatCompact(safeOverview.value.total_output_tokens)}`,
  },
  {
    label: t('llmMetrics.stats.totalCost'),
    value: formatCurrency(safeOverview.value.total_cost),
    icon: 'material-symbols:payments-outline-rounded',
    tone: 'tertiary',
    hint: t('llmMetrics.stats.avgCost', { cost: formatCurrency(averageCost.value) }),
  },
  {
    label: t('llmMetrics.stats.successRate'),
    value: formatPercent(safeOverview.value.success_rate),
    icon: 'material-symbols:verified-rounded',
    tone: safeOverview.value.success_rate >= 0.9 ? 'success' : 'warning',
    hint: t('llmMetrics.stats.cacheHit', { rate: formatPercent(safeOverview.value.cache_hit_rate) }),
  },
])

async function fetchMetrics(refreshing = false): Promise<void> {
  if (refreshing) {
    isRefreshing.value = true
  } else {
    isLoading.value = true
  }

  try {
    const [overviewData, lastHoursData, modelData, requestData, streamData, recentData] = await Promise.all([
      getOverview(),
      getLastHoursSummary(selectedHours.value),
      listModels(),
      listRequestNames(),
      listStreams(),
      getRecentRequests(40, 0),
    ])

    overview.value = overviewData
    lastHoursOverview.value = lastHoursData
    models.value = [...modelData].sort((left, right) => right.total_requests - left.total_requests)
    requestNames.value = [...requestData].sort((left, right) => right.total_requests - left.total_requests)
    streams.value = [...streamData].sort((left, right) => right.total_requests - left.total_requests)
    recentRequests.value = recentData
    lastUpdatedAt.value = new Date().toLocaleString()
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

async function changeHours(hours: number): Promise<void> {
  selectedHours.value = hours
  lastHoursOverview.value = await getLastHoursSummary(hours)
}

function normalizedNumber(value: number | null | undefined): number {
  return Number.isFinite(value) ? Number(value) : 0
}

function formatNumber(value: number | null | undefined): string {
  return new Intl.NumberFormat().format(normalizedNumber(value))
}

function formatCompact(value: number | null | undefined): string {
  const safeValue = normalizedNumber(value)
  return new Intl.NumberFormat(undefined, {
    notation: safeValue >= 10000 ? 'compact' : 'standard',
    maximumFractionDigits: 1,
  }).format(safeValue)
}

function formatCurrency(value: number | null | undefined): string {
  const safeValue = normalizedNumber(value)
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: safeValue >= 10 ? 2 : 4,
    maximumFractionDigits: safeValue >= 10 ? 2 : 4,
  }).format(safeValue)
}

function formatPercent(value: number | null | undefined): string {
  return `${(normalizedNumber(value) * 100).toFixed(1)}%`
}

function formatLatency(value: number | null | undefined): string {
  const safeValue = normalizedNumber(value)
  if (safeValue >= 1000) return `${(safeValue / 1000).toFixed(2)}s`
  return `${safeValue.toFixed(0)}ms`
}

function normalizeTimestamp(timestamp: number | null | undefined): number | null {
  const safeTimestamp = normalizedNumber(timestamp)
  if (safeTimestamp <= 0) return null
  return safeTimestamp > 1_000_000_000_000 ? safeTimestamp : safeTimestamp * 1000
}

function formatTime(timestamp: number | null | undefined): string {
  const milliseconds = normalizeTimestamp(timestamp)
  if (milliseconds === null) return '—'
  return new Date(milliseconds).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDateTime(timestamp: number | null | undefined): string {
  const milliseconds = normalizeTimestamp(timestamp)
  if (milliseconds === null) return '—'
  return new Date(milliseconds).toLocaleString()
}

onMounted(() => {
  fetchMetrics()
  pollTimer = window.setInterval(() => fetchMetrics(true), 30000)
})

onUnmounted(() => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
  }
})
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('llmMetrics.title')"
      :subtitle="t('llmMetrics.subtitle')"
      icon="material-symbols:bar-chart-rounded"
    />

    <div class="llm-metrics-page">
      <section class="hero-card">
        <div class="hero-copy">
          <span class="eyebrow">{{ t('llmMetrics.hero.eyebrow') }}</span>
          <h2>{{ t('llmMetrics.hero.title') }}</h2>
          <p>{{ t('llmMetrics.hero.desc') }}</p>
          <div class="hero-actions">
            <button class="primary-action" :disabled="isRefreshing" @click="fetchMetrics(true)">
              <Icon
                :icon="isRefreshing ? 'material-symbols:progress-activity' : 'material-symbols:refresh-rounded'"
                width="18"
                height="18"
                :class="{ spin: isRefreshing }"
              />
              {{ t('llmMetrics.actions.refresh') }}
            </button>
            <span v-if="lastUpdatedAt" class="updated-label">
              {{ t('llmMetrics.lastUpdated') }}: {{ lastUpdatedAt }}
            </span>
          </div>
        </div>

        <div class="hero-meter" aria-hidden="true">
          <div class="meter-ring">
            <div class="meter-value">{{ formatPercent(safeOverview.success_rate) }}</div>
            <div class="meter-label">{{ t('llmMetrics.stats.successRate') }}</div>
          </div>
          <div class="meter-chip">
            <Icon icon="material-symbols:cached-rounded" width="18" height="18" />
            {{ t('llmMetrics.stats.cacheHit', { rate: formatPercent(safeOverview.cache_hit_rate) }) }}
          </div>
        </div>
      </section>

      <section class="stat-grid" :aria-label="t('llmMetrics.sections.overview')">
        <article v-for="card in statCards" :key="card.label" class="metric-card" :class="card.tone">
          <div class="metric-icon">
            <Icon :icon="card.icon" width="26" height="26" />
          </div>
          <div class="metric-content">
            <span>{{ card.label }}</span>
            <strong>{{ isLoading ? '—' : card.value }}</strong>
            <small>{{ card.hint }}</small>
          </div>
        </article>
      </section>

      <section class="content-grid">
        <article class="panel token-panel">
          <div class="panel-heading">
            <div>
              <span class="eyebrow">{{ t('llmMetrics.sections.tokens') }}</span>
              <h3>{{ t('llmMetrics.tokens.title') }}</h3>
            </div>
            <Icon icon="material-symbols:token-rounded" width="24" height="24" />
          </div>

          <div class="token-stack">
            <div class="token-track">
              <div class="token-input" :style="{ width: `${tokenSegments.input}%` }"></div>
              <div class="token-output" :style="{ width: `${tokenSegments.output}%` }"></div>
            </div>
            <div class="token-legend">
              <span><i class="input-dot"></i>{{ t('llmMetrics.stats.input') }} {{ formatNumber(safeOverview.total_input_tokens) }}</span>
              <span><i class="output-dot"></i>{{ t('llmMetrics.stats.output') }} {{ formatNumber(safeOverview.total_output_tokens) }}</span>
            </div>
          </div>

          <div class="trend-bars" :aria-label="t('llmMetrics.tokens.recentTrend')">
            <div
              v-for="bar in recentTrend"
              :key="bar.id"
              class="trend-bar"
              :class="{ failed: !bar.success, cached: bar.cacheHit }"
              :style="{ height: `${bar.height}%` }"
              :title="`${bar.label} · ${formatNumber(bar.tokens)} tokens`"
            ></div>
          </div>
        </article>

        <article class="panel health-panel">
          <div class="panel-heading">
            <div>
              <span class="eyebrow">{{ t('llmMetrics.sections.quality') }}</span>
              <h3>{{ t('llmMetrics.quality.title') }}</h3>
            </div>
            <Icon icon="material-symbols:monitor-heart-outline-rounded" width="24" height="24" />
          </div>

          <div class="quality-grid">
            <div class="quality-item success">
              <span>{{ t('llmMetrics.quality.successful') }}</span>
              <strong>{{ recentSuccessCount }}</strong>
            </div>
            <div class="quality-item error">
              <span>{{ t('llmMetrics.quality.failed') }}</span>
              <strong>{{ recentFailureCount }}</strong>
            </div>
          </div>

          <div class="time-filter">
            <span>{{ t('llmMetrics.filters.timeRange') }}</span>
            <div class="filter-buttons">
              <button
                v-for="hours in hourOptions"
                :key="hours"
                :class="{ active: selectedHours === hours }"
                @click="changeHours(hours)"
              >
                {{ t('llmMetrics.filters.hours', { hours: String(hours) }) }}
              </button>
            </div>
          </div>

          <div class="last-hours-card">
            <span>{{ t('llmMetrics.filters.currentRange') }}</span>
            <strong>{{ formatNumber(lastHoursOverview?.total_requests ?? 0) }}</strong>
            <small>{{ t('llmMetrics.stats.totalRequests') }} · {{ formatCurrency(lastHoursOverview?.total_cost ?? 0) }}</small>
          </div>
        </article>
      </section>

      <section class="ranking-grid">
        <article class="panel ranking-panel">
          <div class="panel-heading">
            <div>
              <span class="eyebrow">{{ t('llmMetrics.sections.models') }}</span>
              <h3>{{ t('llmMetrics.models.title') }}</h3>
            </div>
            <span v-if="topModel" class="pill">{{ topModel.provider }}</span>
          </div>

          <div v-if="modelRows.length" class="ranking-list">
            <div v-for="model in modelRows" :key="`${model.provider}:${model.model_name}`" class="ranking-row">
              <div class="row-main">
                <span class="row-title">{{ model.model_name }}</span>
                <span class="row-meta">{{ model.provider }} · {{ formatLatency(model.avg_latency) }}</span>
              </div>
              <div class="row-value">
                <strong>{{ formatNumber(model.total_requests) }}</strong>
                <span>{{ formatCurrency(model.total_cost) }}</span>
              </div>
              <div class="row-bar"><i :style="{ width: `${model.share}%` }"></i></div>
            </div>
          </div>
          <div v-else class="empty-state">{{ isLoading ? t('llmMetrics.loading') : t('llmMetrics.empty.models') }}</div>
        </article>

        <article class="panel ranking-panel">
          <div class="panel-heading">
            <div>
              <span class="eyebrow">{{ t('llmMetrics.sections.requests') }}</span>
              <h3>{{ t('llmMetrics.requests.title') }}</h3>
            </div>
            <span v-if="topRequest" class="pill">{{ topRequest.request_name }}</span>
          </div>

          <div v-if="requestRows.length" class="ranking-list">
            <div v-for="request in requestRows" :key="request.request_name" class="ranking-row">
              <div class="row-main">
                <span class="row-title">{{ request.request_name }}</span>
                <span class="row-meta">{{ formatPercent(request.success_rate) }} · {{ formatLatency(request.avg_latency) }}</span>
              </div>
              <div class="row-value">
                <strong>{{ formatNumber(request.total_requests) }}</strong>
                <span>{{ formatCompact(normalizedNumber(request.total_input_tokens) + normalizedNumber(request.total_output_tokens)) }} tokens</span>
              </div>
              <div class="row-bar"><i :style="{ width: `${request.share}%` }"></i></div>
            </div>
          </div>
          <div v-else class="empty-state">{{ isLoading ? t('llmMetrics.loading') : t('llmMetrics.empty.requests') }}</div>
        </article>
      </section>

      <section class="table-grid">
        <article class="panel stream-panel">
          <div class="panel-heading">
            <div>
              <span class="eyebrow">{{ t('llmMetrics.sections.streams') }}</span>
              <h3>{{ t('llmMetrics.streams.title') }}</h3>
            </div>
            <Icon icon="material-symbols:account-tree-outline-rounded" width="24" height="24" />
          </div>

          <div v-if="streamRows.length" class="stream-list">
            <div v-for="stream in streamRows" :key="stream.stream_id" class="stream-card">
              <div>
                <span class="stream-id">{{ stream.stream_id }}</span>
                <small>{{ formatCompact(normalizedNumber(stream.total_input_tokens) + normalizedNumber(stream.total_output_tokens)) }} tokens</small>
              </div>
              <div class="stream-stats">
                <strong>{{ formatNumber(stream.total_requests) }}</strong>
                <span>{{ formatPercent(stream.success_rate) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">{{ isLoading ? t('llmMetrics.loading') : t('llmMetrics.empty.streams') }}</div>
        </article>

        <article class="panel recent-panel">
          <div class="panel-heading">
            <div>
              <span class="eyebrow">{{ t('llmMetrics.sections.recent') }}</span>
              <h3>{{ t('llmMetrics.recent.title') }}</h3>
            </div>
            <Icon icon="material-symbols:history-rounded" width="24" height="24" />
          </div>

          <div v-if="recentRequests.length" class="recent-table-wrap">
            <table class="recent-table">
              <thead>
                <tr>
                  <th>{{ t('llmMetrics.recent.time') }}</th>
                  <th>{{ t('llmMetrics.recent.request') }}</th>
                  <th>{{ t('llmMetrics.recent.model') }}</th>
                  <th>{{ t('llmMetrics.recent.tokens') }}</th>
                  <th>{{ t('llmMetrics.recent.cost') }}</th>
                  <th>{{ t('llmMetrics.recent.status') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in recentRequests.slice(0, 10)" :key="item.id">
                  <td>{{ formatDateTime(item.timestamp) }}</td>
                  <td>{{ item.request_name }}</td>
                  <td>{{ item.provider }} / {{ item.model_name }}</td>
                  <td>{{ formatNumber(item.total_tokens) }}</td>
                  <td>{{ formatCurrency(item.cost) }}</td>
                  <td>
                    <span class="status-pill" :class="item.success ? 'success' : 'error'">
                      {{ item.success ? t('llmMetrics.recent.success') : (item.error_type ?? t('llmMetrics.recent.failed')) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-state">{{ isLoading ? t('llmMetrics.loading') : t('llmMetrics.empty.recent') }}</div>
        </article>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.llm-metrics-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0;
}

.hero-card,
.panel,
.metric-card {
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 72%, transparent);
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04), 0 2px 8px rgba(0, 0, 0, 0.027), 0 1px 3px rgba(0, 0, 0, 0.02);
  backdrop-filter: blur(14px);
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 1.5rem;
  align-items: stretch;
  padding: 1.5rem;
  border-radius: 1.5rem;
  overflow: hidden;
  position: relative;
}

.hero-card::before {
  content: '';
  position: absolute;
  inset: -30% auto auto 50%;
  width: 420px;
  height: 420px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--md-sys-color-primary-container) 56%, transparent);
  filter: blur(40px);
  opacity: 0.6;
  pointer-events: none;
}

.hero-copy,
.hero-meter {
  position: relative;
  z-index: 1;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  border-radius: 9999px;
  padding: 0.25rem 0.625rem;
  background: color-mix(in srgb, var(--md-sys-color-primary-container) 74%, transparent);
  color: var(--md-sys-color-on-primary-container);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.hero-copy h2 {
  margin: 0.75rem 0 0;
  max-width: 760px;
  color: var(--md-sys-color-on-surface);
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: clamp(2rem, 5vw, 3.25rem);
  line-height: 1.04;
  letter-spacing: -0.045em;
}

.hero-copy p {
  max-width: 660px;
  margin: 0.75rem 0 0;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 1rem;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1.25rem;
}

.primary-action {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 40px;
  padding: 0.5rem 1rem;
  border: 1px solid transparent;
  border-radius: 9999px;
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
}

.primary-action:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.primary-action:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
}

.updated-label {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8125rem;
}

.hero-meter {
  display: flex;
  min-height: 230px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  border-radius: 1.25rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 76%, transparent);
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 60%, transparent);
}

.meter-ring {
  width: 160px;
  height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, var(--md-sys-color-surface-container) 58%, transparent 59%),
    conic-gradient(var(--md-sys-color-primary) calc(v-bind('normalizedNumber(safeOverview.success_rate)') * 100%), color-mix(in srgb, var(--md-sys-color-outline-variant) 42%, transparent) 0);
}

.meter-value {
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--md-sys-color-on-surface);
}

.meter-label {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8125rem;
}

.meter-chip,
.pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  width: fit-content;
  border-radius: 9999px;
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.meter-chip,
.pill {
  background: color-mix(in srgb, var(--md-sys-color-secondary-container) 76%, transparent);
  color: var(--md-sys-color-on-secondary-container);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.metric-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  min-height: 148px;
  padding: 1.25rem;
  border-radius: 1.25rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.metric-card:hover,
.panel:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(24, 28, 32, 0.08);
}

.metric-icon {
  display: flex;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.metric-card.secondary .metric-icon {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.metric-card.tertiary .metric-icon {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.metric-card.success .metric-icon {
  background: color-mix(in srgb, var(--md-sys-color-tertiary-container) 82%, transparent);
  color: var(--md-sys-color-tertiary);
}

.metric-card.warning .metric-icon {
  background: color-mix(in srgb, #ffe2bd 80%, var(--md-sys-color-surface-container));
  color: #a34b00;
}

.metric-content {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
}

.metric-content span,
.metric-content small,
.row-meta,
.row-value span,
.stream-card small,
.stream-stats span,
.last-hours-card small,
.last-hours-card span {
  color: var(--md-sys-color-on-surface-variant);
}

.metric-content span {
  font-size: 0.8125rem;
  font-weight: 600;
}

.metric-content strong {
  color: var(--md-sys-color-on-surface);
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.65rem;
  font-weight: 800;
  line-height: 1.1;
}

.metric-content small {
  font-size: 0.75rem;
  line-height: 1.35;
}

.content-grid,
.ranking-grid,
.table-grid {
  display: grid;
  gap: 1rem;
}

.content-grid {
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
}

.ranking-grid,
.table-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel {
  min-width: 0;
  border-radius: 1.25rem;
  padding: 1.25rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  color: var(--md-sys-color-primary);
}

.panel-heading h3 {
  margin: 0.5rem 0 0;
  color: var(--md-sys-color-on-surface);
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.token-stack {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.token-track {
  display: flex;
  height: 18px;
  overflow: hidden;
  border-radius: 9999px;
  background: var(--md-sys-color-surface-container-highest);
}

.token-input {
  background: var(--md-sys-color-primary);
}

.token-output {
  background: var(--md-sys-color-tertiary);
}

.token-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8125rem;
}

.token-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.token-legend i {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
}

.input-dot {
  background: var(--md-sys-color-primary);
}

.output-dot {
  background: var(--md-sys-color-tertiary);
}

.trend-bars {
  display: flex;
  align-items: end;
  gap: 0.45rem;
  height: 180px;
  margin-top: 1.25rem;
  padding: 1rem;
  border-radius: 1rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 64%, transparent);
}

.trend-bar {
  flex: 1;
  min-width: 6px;
  border-radius: 9999px 9999px 0 0;
  background: linear-gradient(180deg, var(--md-sys-color-primary), color-mix(in srgb, var(--md-sys-color-primary) 48%, transparent));
}

.trend-bar.cached {
  background: linear-gradient(180deg, var(--md-sys-color-tertiary), color-mix(in srgb, var(--md-sys-color-tertiary) 48%, transparent));
}

.trend-bar.failed {
  background: linear-gradient(180deg, var(--md-sys-color-error), color-mix(in srgb, var(--md-sys-color-error) 48%, transparent));
}

.quality-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.quality-item,
.last-hours-card {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem;
  border-radius: 1rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 70%, transparent);
}

.quality-item span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8125rem;
}

.quality-item strong,
.last-hours-card strong {
  color: var(--md-sys-color-on-surface);
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.5rem;
  font-weight: 800;
}

.quality-item.success strong {
  color: var(--md-sys-color-tertiary);
}

.quality-item.error strong {
  color: var(--md-sys-color-error);
}

.time-filter {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 1rem 0;
}

.time-filter > span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8125rem;
  font-weight: 700;
}

.filter-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.filter-buttons button {
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 9999px;
  padding: 0.4rem 0.7rem;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 700;
  cursor: pointer;
}

.filter-buttons button.active {
  border-color: transparent;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.ranking-list,
.stream-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.ranking-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
}

.row-main,
.row-value,
.stream-card > div,
.stream-stats {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.row-title,
.stream-id {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--md-sys-color-on-surface);
  font-weight: 800;
}

.row-meta,
.row-value span,
.stream-card small,
.stream-stats span,
.last-hours-card small,
.last-hours-card span {
  font-size: 0.75rem;
}

.row-value {
  align-items: flex-end;
}

.row-value strong,
.stream-stats strong {
  color: var(--md-sys-color-on-surface);
  font-weight: 800;
}

.row-bar {
  grid-column: 1 / -1;
  height: 8px;
  overflow: hidden;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--md-sys-color-outline-variant) 36%, transparent);
}

.row-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--md-sys-color-primary), var(--md-sys-color-tertiary));
}

.stream-card {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem;
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 54%, transparent);
  border-radius: 1rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 52%, transparent);
}

.stream-stats {
  align-items: flex-end;
  flex-shrink: 0;
}

.recent-table-wrap {
  overflow-x: auto;
  border-radius: 1rem;
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 54%, transparent);
}

.recent-table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
}

.recent-table th,
.recent-table td {
  padding: 0.8rem 0.9rem;
  border-bottom: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 48%, transparent);
  text-align: left;
  font-size: 0.8125rem;
}

.recent-table th {
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 82%, transparent);
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 800;
}

.recent-table td {
  color: var(--md-sys-color-on-surface);
}

.recent-table tr:last-child td {
  border-bottom: 0;
}

.status-pill.success {
  background: color-mix(in srgb, var(--md-sys-color-tertiary-container) 78%, transparent);
  color: var(--md-sys-color-tertiary);
}

.status-pill.error {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.empty-state {
  display: flex;
  min-height: 140px;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 54%, transparent);
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.9rem;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1200px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid,
  .ranking-grid,
  .table-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero-card {
    grid-template-columns: 1fr;
    padding: 1rem;
  }

  .hero-meter {
    min-height: 210px;
  }

  .stat-grid {
    grid-template-columns: 1fr;
  }

  .metric-card,
  .panel {
    padding: 1rem;
  }

  .trend-bars {
    height: 140px;
    gap: 0.3rem;
    padding: 0.75rem;
  }

  .quality-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .hero-copy h2 {
    font-size: 1.8rem;
  }

  .ranking-row {
    grid-template-columns: 1fr;
  }

  .row-value {
    align-items: flex-start;
  }

  .stream-card {
    flex-direction: column;
  }

  .stream-stats {
    align-items: flex-start;
  }
}
</style>
