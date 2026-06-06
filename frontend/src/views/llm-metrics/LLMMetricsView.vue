<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppShell from '../../components/common/AppShell.vue'
import Icon from '../../components/common/Icon.vue'
import TokenUsageChart from '../../components/features/llm-metrics/TokenUsageChart.vue'
import ModelRankingChart from '../../components/features/llm-metrics/ModelRankingChart.vue'
import { useI18n } from '../../utils/i18n'
import {
  getLastHoursSummary,
  getOverview,
  getRecentRequestsByTime,
  listStreams,
} from '../../api/modules/llm-metrics'
import type {
  LLMMetricsOverview,
  LLMModelMetrics,
  LLMRecentRequest,
  LLMRequestMetrics,
  LLMStreamMetrics,
} from '../../api/types/llm-metrics'

const { t, locale } = useI18n()

const overview = ref<LLMMetricsOverview | null>(null)
const lastHoursOverview = ref<LLMMetricsOverview | null>(null)
const streams = ref<LLMStreamMetrics[]>([])
const recentRequests = ref<LLMRecentRequest[]>([])
const isLoading = ref(true)
const isRefreshing = ref(false)
const lastUpdatedAt = ref('')
const selectedHours = ref(24)
const modelRankingMode = ref<'chart' | 'list'>('chart')

let pollTimer: number | null = null

const hourOptions = [1, 5, 24, 72]

const emptyOverview: LLMMetricsOverview = {
  total_requests: 0,
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_cost: 0,
  success_rate: 0,
  cache_hit_rate: 0,
}

const safeOverview = computed<LLMMetricsOverview>(() => overview.value ?? emptyOverview)
const windowOverview = computed<LLMMetricsOverview>(() => lastHoursOverview.value ?? safeOverview.value)
const selectedWindowStart = computed(() => Date.now() - selectedHours.value * 60 * 60 * 1000)
const filteredRecentRequests = computed(() => recentRequests.value.filter((item) => {
  const milliseconds = normalizeTimestamp(item.timestamp)
  return milliseconds !== null && milliseconds >= selectedWindowStart.value
}))

const totalTokens = computed(() => getOverviewInputTokens(windowOverview.value) + getOverviewOutputTokens(windowOverview.value))
const averageCost = computed(() => {
  const requestCount = normalizedNumber(windowOverview.value.total_requests)
  if (requestCount <= 0) return 0
  return normalizedNumber(windowOverview.value.total_cost) / requestCount
})

const recentSuccessCount = computed(() => filteredRecentRequests.value.filter((item) => Boolean(item.success)).length)
const recentFailureCount = computed(() => Math.max(filteredRecentRequests.value.length - recentSuccessCount.value, 0))

const modelMetricsInWindow = computed<LLMModelMetrics[]>(() => {
  const metrics = new Map<string, LLMModelMetrics>()

  filteredRecentRequests.value.forEach((item) => {
    const provider = item.provider ?? item.api_provider ?? 'unknown'
    const modelName = item.model_name || 'unknown'
    const key = `${provider}:${modelName}`
    const current = metrics.get(key) ?? {
      model_name: modelName,
      model_identifier: item.model_identifier,
      provider,
      api_provider: item.api_provider ?? provider,
      total_requests: 0,
      success_count: 0,
      error_count: 0,
      success_rate: 0,
      total_prompt_tokens: 0,
      total_completion_tokens: 0,
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_tokens: 0,
      total_cache_hit_tokens: 0,
      total_cost: 0,
      avg_latency: 0,
    }

    const latency = normalizedNumber(item.latency)
    current.total_requests += 1
    current.success_count += item.success ? 1 : 0
    current.error_count += item.success ? 0 : 1
    current.total_prompt_tokens = normalizedNumber(current.total_prompt_tokens) + normalizedNumber(item.prompt_tokens)
    current.total_completion_tokens = normalizedNumber(current.total_completion_tokens) + normalizedNumber(item.completion_tokens)
    current.total_input_tokens = normalizedNumber(current.total_input_tokens) + getRequestInputTokens(item)
    current.total_output_tokens = normalizedNumber(current.total_output_tokens) + getRequestOutputTokens(item)
    current.total_tokens += getRequestTotalTokens(item)
    current.total_cache_hit_tokens = normalizedNumber(current.total_cache_hit_tokens) + normalizedNumber(item.cache_hit_tokens)
    current.total_cost += normalizedNumber(item.cost)
    current.avg_latency += latency
    metrics.set(key, current)
  })

  return Array.from(metrics.values())
    .map((item) => ({
      ...item,
      success_rate: item.total_requests > 0 ? item.success_count / item.total_requests : 0,
      avg_latency: item.total_requests > 0 ? item.avg_latency / item.total_requests : 0,
    }))
    .sort((left, right) => right.total_requests - left.total_requests)
})

const requestMetricsInWindow = computed<LLMRequestMetrics[]>(() => {
  const metrics = new Map<string, LLMRequestMetrics>()

  filteredRecentRequests.value.forEach((item) => {
    const requestName = item.request_name || '(未命名)'
    const current = metrics.get(requestName) ?? {
      request_name: requestName,
      total_requests: 0,
      success_count: 0,
      error_count: 0,
      success_rate: 0,
      total_prompt_tokens: 0,
      total_completion_tokens: 0,
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_tokens: 0,
      total_cache_hit_tokens: 0,
      total_cost: 0,
      avg_latency: 0,
    }

    current.total_requests += 1
    current.success_count += item.success ? 1 : 0
    current.error_count += item.success ? 0 : 1
    current.total_prompt_tokens = normalizedNumber(current.total_prompt_tokens) + normalizedNumber(item.prompt_tokens)
    current.total_completion_tokens = normalizedNumber(current.total_completion_tokens) + normalizedNumber(item.completion_tokens)
    current.total_input_tokens = normalizedNumber(current.total_input_tokens) + getRequestInputTokens(item)
    current.total_output_tokens = normalizedNumber(current.total_output_tokens) + getRequestOutputTokens(item)
    current.total_tokens += getRequestTotalTokens(item)
    current.total_cache_hit_tokens = normalizedNumber(current.total_cache_hit_tokens) + normalizedNumber(item.cache_hit_tokens)
    current.total_cost += normalizedNumber(item.cost)
    current.avg_latency += normalizedNumber(item.latency)
    metrics.set(requestName, current)
  })

  return Array.from(metrics.values())
    .map((item) => ({
      ...item,
      success_rate: item.total_requests > 0 ? item.success_count / item.total_requests : 0,
      avg_latency: item.total_requests > 0 ? item.avg_latency / item.total_requests : 0,
    }))
    .sort((left, right) => right.total_requests - left.total_requests)
})

const streamInfoById = computed(() => {
  const infoMap = new Map<string, LLMStreamMetrics>()
  streams.value.forEach((stream) => {
    infoMap.set(stream.stream_id, stream)
  })
  return infoMap
})

const streamMetricsInWindow = computed<LLMStreamMetrics[]>(() => {
  const metrics = new Map<string, LLMStreamMetrics>()

  filteredRecentRequests.value.forEach((item) => {
    const streamId = item.stream_id ?? 'unknown'
    const streamInfo = streamInfoById.value.get(streamId)
    const current = metrics.get(streamId) ?? {
      stream_id: streamId,
      platform: streamInfo?.platform,
      chat_type: streamInfo?.chat_type,
      group_id: streamInfo?.group_id,
      group_name: streamInfo?.group_name,
      person_id: streamInfo?.person_id,
      message_count: streamInfo?.message_count,
      is_group_chat: streamInfo?.is_group_chat,
      is_private_chat: streamInfo?.is_private_chat,
      total_requests: 0,
      total_prompt_tokens: 0,
      total_completion_tokens: 0,
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_cache_hit: 0,
      total_cache_miss: 0,
      cache_hit_rate: 0,
      total_cost: 0,
      success_rate: 0,
    }

    current.total_requests += 1
    current.total_prompt_tokens = normalizedNumber(current.total_prompt_tokens) + normalizedNumber(item.prompt_tokens)
    current.total_completion_tokens = normalizedNumber(current.total_completion_tokens) + normalizedNumber(item.completion_tokens)
    current.total_input_tokens = normalizedNumber(current.total_input_tokens) + getRequestInputTokens(item)
    current.total_output_tokens = normalizedNumber(current.total_output_tokens) + getRequestOutputTokens(item)
    current.total_cache_hit += normalizedNumber(item.cache_hit_tokens)
    current.total_cache_miss += normalizedNumber(item.cache_miss_tokens)
    current.total_cost += normalizedNumber(item.cost)
    current.success_rate = normalizedNumber(current.success_rate) + (item.success ? 1 : 0)
    metrics.set(streamId, current)
  })

  return Array.from(metrics.values())
    .map((item) => ({
      ...item,
      cache_hit_rate: item.total_cache_hit + item.total_cache_miss > 0 ? item.total_cache_hit / (item.total_cache_hit + item.total_cache_miss) : 0,
      success_rate: item.total_requests > 0 ? normalizedNumber(item.success_rate) / item.total_requests : 0,
    }))
    .sort((left, right) => right.total_requests - left.total_requests)
})

const topModel = computed(() => modelMetricsInWindow.value[0] ?? null)
const topRequest = computed(() => requestMetricsInWindow.value[0] ?? null)

const modelRows = computed(() => {
  const maxRequests = Math.max(...modelMetricsInWindow.value.map((item) => normalizedNumber(item.total_requests)), 1)
  return modelMetricsInWindow.value.slice(0, 12).map((item) => {
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
  const maxRequests = Math.max(...requestMetricsInWindow.value.map((item) => normalizedNumber(item.total_requests)), 1)
  return requestMetricsInWindow.value.slice(0, 12).map((item) => {
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

const formatStreamChatType = (stream: LLMStreamMetrics): string => {
  if (stream.is_group_chat || stream.chat_type === 'group') return '群聊'
  if (stream.chat_type === 'discuss') return '讨论组'
  if (stream.is_private_chat || stream.chat_type === 'private') return '私聊'
  return '未知会话'
}

const formatStreamTarget = (stream: LLMStreamMetrics): string => {
  if (stream.is_group_chat || stream.chat_type === 'group' || stream.chat_type === 'discuss') {
    return stream.group_name || stream.group_id || '未知群组'
  }
  if (stream.is_private_chat || stream.chat_type === 'private') {
    return stream.person_id || '未知私聊'
  }
  return stream.stream_id
}

const streamRows = computed(() => streamMetricsInWindow.value.slice(0, 12).map((item) => ({
  ...item,
  total_requests: normalizedNumber(item.total_requests),
  total_input_tokens: normalizedNumber(item.total_input_tokens),
  total_output_tokens: normalizedNumber(item.total_output_tokens),
  total_cost: normalizedNumber(item.total_cost),
  success_rate: normalizedNumber(item.success_rate),
  display_platform: item.platform || 'unknown',
  display_chat_type: formatStreamChatType(item),
  display_target: formatStreamTarget(item),
})))

const recentTrend = computed(() => [...filteredRecentRequests.value].slice(0, 18).reverse().map((item) => ({
  id: item.id,
  label: formatTime(item.timestamp),
  success: Boolean(item.success),
  cacheHit: Boolean(item.cache_hit),
  inputTokens: getRequestInputTokens(item),
  outputTokens: getRequestOutputTokens(item),
  tokens: getRequestTotalTokens(item),
})))

const hasTokenChartData = computed(() => totalTokens.value > 0 || recentTrend.value.some((item) => item.tokens > 0))

const tokenSegments = computed(() => {
  const input = getOverviewInputTokens(windowOverview.value)
  const output = getOverviewOutputTokens(windowOverview.value)
  const total = input + output

  if (total <= 0) {
    return { input: 0, output: 0 }
  }

  return {
    input: (input / total) * 100,
    output: (output / total) * 100,
  }
})

const statCards = computed(() => [
  {
    label: t('llmMetrics.stats.totalRequests'),
    value: formatNumber(windowOverview.value.total_requests),
    icon: 'material-symbols:send-time-extension-outline-rounded',
    tone: 'primary',
    hint: t('llmMetrics.stats.totalRequestsHint', { count: formatNumber(windowOverview.value.total_requests) }),
  },
  {
    label: t('llmMetrics.stats.totalTokens'),
    value: formatCompact(totalTokens.value),
    icon: 'material-symbols:data-array-rounded',
    tone: 'secondary',
    hint: `${t('llmMetrics.stats.input')} ${formatCompact(getOverviewInputTokens(windowOverview.value))} · ${t('llmMetrics.stats.output')} ${formatCompact(getOverviewOutputTokens(windowOverview.value))}`,
  },
  {
    label: t('llmMetrics.stats.totalCost'),
    value: formatCurrency(windowOverview.value.total_cost),
    icon: 'material-symbols:payments-outline-rounded',
    tone: 'tertiary',
    hint: t('llmMetrics.stats.avgCost', { cost: formatCurrency(averageCost.value) }),
  },
  {
    label: t('llmMetrics.stats.successRate'),
    value: formatPercent(windowOverview.value.success_rate),
    icon: 'material-symbols:verified-rounded',
    tone: windowOverview.value.success_rate >= 0.9 ? 'success' : 'warning',
    hint: t('llmMetrics.stats.cacheHit', { rate: formatPercent(windowOverview.value.cache_hit_rate) }),
  },
])

async function fetchMetrics(refreshing = false): Promise<void> {
  if (refreshing) {
    isRefreshing.value = true
  } else {
    isLoading.value = true
  }

  try {
    const [overviewData, lastHoursData, streamData, recentData] = await Promise.all([
      getOverview(),
      getLastHoursSummary(selectedHours.value),
      listStreams(),
      getRecentRequestsByTime(selectedHours.value, 1000, 0),
    ])
    console.log('Fetched metrics:', { overviewData, lastHoursData, streamData, recentData })

    overview.value = overviewData
    lastHoursOverview.value = lastHoursData
    streams.value = [...streamData].sort((left, right) => right.total_requests - left.total_requests)
    recentRequests.value = [...recentData].sort((left, right) => {
      const leftTimestamp = normalizeTimestamp(left.timestamp) ?? 0
      const rightTimestamp = normalizeTimestamp(right.timestamp) ?? 0
      return rightTimestamp - leftTimestamp
    })
    lastUpdatedAt.value = new Date().toLocaleString()
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

async function changeHours(hours: number): Promise<void> {
  selectedHours.value = hours
  await fetchMetrics(true)
}

function normalizedNumber(value: number | string | null | undefined): number {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : 0
}

function getOverviewInputTokens(metrics: LLMMetricsOverview): number {
  return normalizedNumber(metrics.total_input_tokens ?? metrics.total_tokens_in ?? metrics.total_prompt_tokens)
}

function getOverviewOutputTokens(metrics: LLMMetricsOverview): number {
  return normalizedNumber(metrics.total_output_tokens ?? metrics.total_tokens_out ?? metrics.total_completion_tokens)
}

function getRequestInputTokens(request: LLMRecentRequest): number {
  return normalizedNumber(request.input_tokens ?? request.prompt_tokens)
}

function getRequestOutputTokens(request: LLMRecentRequest): number {
  return normalizedNumber(request.output_tokens ?? request.completion_tokens)
}

function getRequestTotalTokens(request: LLMRecentRequest): number {
  const total = normalizedNumber(request.total_tokens)
  if (total > 0) return total
  return getRequestInputTokens(request) + getRequestOutputTokens(request)
}

function formatNumber(value: number | null | undefined): string {
  return new Intl.NumberFormat(locale.value).format(normalizedNumber(value))
}

function formatCompact(value: number | null | undefined): string {
  const safeValue = normalizedNumber(value)
  return new Intl.NumberFormat(locale.value, {
    notation: safeValue >= 10000 ? 'compact' : 'standard',
    maximumFractionDigits: 1,
  }).format(safeValue)
}

function formatCurrency(value: number | null | undefined): string {
  const safeValue = normalizedNumber(value)
  return new Intl.NumberFormat(locale.value, {
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
  return new Date(milliseconds).toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit' })
}

function formatDateTime(timestamp: number | null | undefined): string {
  const milliseconds = normalizeTimestamp(timestamp)
  if (milliseconds === null) return '—'
  return new Date(milliseconds).toLocaleString(locale.value)
}

onMounted(() => {
  fetchMetrics()
  pollTimer = window.setInterval(() => fetchMetrics(true), 10000)
})

onUnmounted(() => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
  }
})
</script>

<template>
  <AppShell>
    <div class="llm-metrics-page">
      <section class="time-window-toolbar" :aria-label="t('llmMetrics.filters.timeRange')">
        <div class="time-window-copy">
          <span class="eyebrow">{{ t('llmMetrics.filters.timeRange') }}</span>
          <strong>{{ t('llmMetrics.filters.currentRange') }}</strong>
          <small>{{ formatNumber(windowOverview.total_requests) }} {{ t('llmMetrics.stats.totalRequests') }} · {{ formatCurrency(windowOverview.total_cost) }}</small>
        </div>
        <div class="time-window-actions">
          <div class="filter-buttons time-window-buttons">
            <button
              v-for="hours in hourOptions"
              :key="hours"
              :class="{ active: selectedHours === hours }"
              @click="changeHours(hours)"
            >
              {{ t('llmMetrics.filters.hours', { hours: String(hours) }) }}
            </button>
          </div>
          <span v-if="lastUpdatedAt" class="updated-label">
            {{ t('llmMetrics.lastUpdated') }}: {{ lastUpdatedAt }}
          </span>
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
            <div class="token-summary-row">
              <span><i class="input-dot"></i>{{ t('llmMetrics.stats.input') }} {{ formatNumber(getOverviewInputTokens(windowOverview)) }}</span>
              <span><i class="output-dot"></i>{{ t('llmMetrics.stats.output') }} {{ formatNumber(getOverviewOutputTokens(windowOverview)) }}</span>
            </div>
          </div>

          <div v-if="hasTokenChartData" class="echart-card token-chart" :aria-label="t('llmMetrics.tokens.recentTrend')">
            <TokenUsageChart
              :input-tokens="getOverviewInputTokens(windowOverview)"
              :output-tokens="getOverviewOutputTokens(windowOverview)"
              :trend="recentTrend"
              :input-label="t('llmMetrics.stats.input')"
              :output-label="t('llmMetrics.stats.output')"
              :fallback-label="t('llmMetrics.filters.currentRange')"
              :locale="locale"
            />
          </div>
          <div v-else class="empty-state compact-empty">{{ isLoading ? t('llmMetrics.loading') : t('llmMetrics.empty.recent') }}</div>
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

          <div class="last-hours-card">
            <span>{{ t('llmMetrics.filters.currentRange') }}</span>
            <strong>{{ formatNumber(lastHoursOverview?.total_requests ?? 0) }}</strong>
            <small>{{ t('llmMetrics.stats.totalRequests') }} · {{ formatCurrency(lastHoursOverview?.total_cost ?? 0) }}</small>
          </div>
        </article>
      </section>

      <section class="ranking-grid">
        <article class="panel ranking-panel">
          <div class="panel-heading ranking-heading">
            <div>
              <span class="eyebrow">{{ t('llmMetrics.sections.models') }}</span>
              <h3>{{ t('llmMetrics.models.title') }}</h3>
            </div>
            <div class="ranking-actions">
              <span v-if="topModel" class="pill">{{ topModel.provider }}</span>
              <div class="mode-switch" aria-label="模型使用排行显示模式">
                <button :class="{ active: modelRankingMode === 'chart' }" @click="modelRankingMode = 'chart'">图表</button>
                <button :class="{ active: modelRankingMode === 'list' }" @click="modelRankingMode = 'list'">列表</button>
              </div>
            </div>
          </div>

          <div v-if="modelRows.length && modelRankingMode === 'chart'" class="echart-card ranking-chart">
            <ModelRankingChart
              :rows="modelRows"
              :metric-label="t('llmMetrics.stats.totalRequests')"
              :locale="locale"
            />
          </div>
          <div v-else-if="modelRows.length" class="ranking-list">
            <div v-for="model in modelRows" :key="`${model.provider}:${model.model_name}`" class="ranking-row ranking-row--stacked">
              <div class="row-main">
                <span class="row-title">{{ model.model_name }}</span>
                <span class="row-meta">{{ model.provider }} · {{ formatLatency(model.avg_latency) }}</span>
                <span class="row-token-line">{{ formatCompact(normalizedNumber(model.total_input_tokens) + normalizedNumber(model.total_output_tokens)) }} tokens · {{ formatCurrency(model.total_cost) }}</span>
              </div>
              <div class="row-value">
                <strong>{{ formatNumber(model.total_requests) }}</strong>
              </div>
              <div class="row-bar"><i :style="{ width: `${model.share}%` }"></i></div>
            </div>
          </div>
          <div v-else class="empty-state">{{ isLoading ? t('llmMetrics.loading') : t('llmMetrics.empty.models') }}</div>
        </article>

        <article class="panel ranking-panel request-ranking-panel">
          <div class="panel-heading request-ranking-heading">
            <div>
              <span class="eyebrow">{{ t('llmMetrics.sections.requests') }}</span>
              <h3>{{ t('llmMetrics.requests.title') }}</h3>
              <span v-if="topRequest" class="pill request-top-pill">{{ topRequest.request_name }}</span>
            </div>
          </div>

          <div v-if="requestRows.length" class="request-ranking-list">
            <div v-for="request in requestRows" :key="request.request_name" class="ranking-row ranking-row--stacked request-ranking-row">
              <div class="row-main">
                <span class="row-title">{{ request.request_name }}</span>
                <span class="row-meta">{{ formatPercent(request.success_rate) }} · {{ formatLatency(request.avg_latency) }}</span>
                <span class="row-token-line">{{ formatCompact(normalizedNumber(request.total_input_tokens) + normalizedNumber(request.total_output_tokens)) }} tokens · {{ formatCurrency(request.total_cost) }}</span>
              </div>
              <div class="row-value">
                <strong>{{ formatNumber(request.total_requests) }}</strong>
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
                <span class="stream-id">{{ stream.display_target }}</span>
                <small>{{ stream.display_platform }} · {{ stream.display_chat_type }} · {{ formatCompact(normalizedNumber(stream.total_input_tokens) + normalizedNumber(stream.total_output_tokens)) }} tokens</small>
                <small v-if="stream.group_id" class="stream-raw-id">群号：{{ stream.group_id }}</small>
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

          <div v-if="filteredRecentRequests.length" class="recent-table-wrap">
            <table class="recent-table">
              <thead>
                <tr>
                  <th>{{ t('llmMetrics.recent.time') }}</th>
                  <th>{{ t('llmMetrics.recent.request') }}</th>
                  <th>{{ t('llmMetrics.recent.model') }}</th>
                  <th>{{ t('llmMetrics.recent.url') }}</th>
                  <th>{{ t('llmMetrics.recent.tokens') }}</th>
                  <th>{{ t('llmMetrics.recent.cost') }}</th>
                  <th>{{ t('llmMetrics.recent.status') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in filteredRecentRequests" :key="item.id">
                  <td>{{ formatDateTime(item.timestamp) }}</td>
                  <td>{{ item.request_name }}</td>
                  <td>{{ item.model_name }}</td>
                  <td>{{ item.provider ?? item.api_provider ?? '—' }}</td>
                  <td>{{ formatNumber(getRequestTotalTokens(item)) }}</td>
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

.time-window-toolbar {
  position: sticky;
  top: var(--app-top-bar-height, 64px);
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-block-start: calc(var(--page-padding, 1.5rem) * -1);
  margin-inline: calc(var(--page-padding, 1.5rem) * -1);
  padding: 0.85rem var(--page-padding, 1.5rem);
  border-block: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 72%, transparent);
  border-inline: 0;
  border-radius: 0;
  background: color-mix(in srgb, var(--md-sys-color-surface) 88%, transparent);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04), 0 2px 8px rgba(0, 0, 0, 0.027), 0 1px 3px rgba(0, 0, 0, 0.02);
  backdrop-filter: blur(14px);
}

.time-window-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.25rem;
}

.time-window-copy strong {
  color: var(--md-sys-color-on-surface);
  font-size: 1rem;
  font-weight: 800;
}

.time-window-copy small {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8125rem;
}

.time-window-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
}

.time-window-buttons {
  justify-content: flex-end;
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
.row-token-line,
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
  margin-bottom: 1rem;
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

.token-summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8125rem;
}

.token-summary-row span {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}

.token-summary-row i {
  width: 0.625rem;
  height: 0.625rem;
  flex-shrink: 0;
  border-radius: 50%;
}

.input-dot {
  background: var(--md-sys-color-primary);
}

.output-dot {
  background: var(--md-sys-color-tertiary);
}

.echart-card {
  min-width: 0;
  overflow: visible;
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 54%, transparent);
  border-radius: 1rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 64%, transparent);
}

.echart-card :deep(.echarts),
.echart-card :deep(canvas) {
  overflow: visible !important;
}

.token-chart {
  height: 220px;
  padding: 0.75rem;
}

.token-chart :deep(.echarts),
.ranking-chart :deep(.echarts) {
  width: 100%;
  height: 100%;
}

.ranking-heading,
.request-ranking-heading {
  align-items: flex-start;
}

.request-ranking-heading > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
}

.request-top-pill {
  max-width: 100%;
  margin-top: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ranking-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}

.mode-switch {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 72%, transparent);
  border-radius: 9999px;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 72%, transparent);
}

.mode-switch button {
  border: 0;
  padding: 0.3rem 0.65rem;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.75rem;
  font-weight: 800;
  cursor: pointer;
}

.mode-switch button.active {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.ranking-chart {
  height: 360px;
  padding: 0.75rem;
}

.compact-empty {
  min-height: 220px;
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
.request-ranking-list,
.stream-list {
  display: flex;
  max-height: 360px;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  padding-right: 0.25rem;
  scrollbar-width: thin;
  scrollbar-color: var(--md-sys-color-outline-variant) transparent;
}

.request-ranking-row {
  padding: 0.9rem;
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 54%, transparent);
  border-radius: 1rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 52%, transparent);
}

.ranking-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
}

.ranking-row--stacked {
  align-items: start;
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
.row-token-line,
.row-value span,
.stream-card small,
.stream-stats span,
.last-hours-card small,
.last-hours-card span {
  font-size: 0.75rem;
}

.row-token-line {
  display: block;
  margin-top: 0.1rem;
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

.stream-raw-id {
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.82;
}

.stream-stats {
  align-items: flex-end;
  flex-shrink: 0;
}

.recent-table-wrap {
  max-height: 420px;
  overflow: auto;
  border-radius: 1rem;
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 54%, transparent);
}

.recent-table {
  width: 100%;
  min-width: 860px;
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
  position: sticky;
  top: 0;
  z-index: 1;
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
  .time-window-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .time-window-actions,
  .time-window-buttons {
    justify-content: flex-start;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
  }

  .metric-card,
  .panel {
    padding: 1rem;
  }

  .metric-card {
    min-height: 126px;
    gap: 0.75rem;
  }

  .metric-icon {
    width: 40px;
    height: 40px;
    border-radius: 0.875rem;
  }

  .metric-content strong {
    font-size: 1.25rem;
  }

  .metric-content small {
    font-size: 0.6875rem;
  }

  .token-chart {
    height: 190px;
    padding: 0.5rem;
  }

  .quality-grid {
    grid-template-columns: 1fr;
  }

  .ranking-list,
  .stream-list {
    max-height: 300px;
  }

  .recent-table-wrap {
    max-height: 360px;
  }
}

@media (max-width: 480px) {
  .stat-grid {
    gap: 0.625rem;
  }

  .metric-card {
    min-height: 118px;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.75rem;
  }

  .metric-icon {
    width: 34px;
    height: 34px;
  }

  .metric-content span {
    font-size: 0.72rem;
  }

  .metric-content strong {
    font-size: 1.05rem;
  }

  .metric-content small {
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .ranking-heading,
  .ranking-actions {
    flex-direction: column;
    align-items: flex-start;
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
