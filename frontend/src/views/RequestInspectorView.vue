<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import Icon from '../components/common/Icon.vue'
import { useDialogStore } from '../utils/dialog'
import { useToastStore } from '../utils/toast'
import { useI18n } from '../utils/i18n'
import {
  clearInspectorRequests,
  getInspectorAnalytics,
  getInspectorRequest,
  listInspectorRequests,
} from '../api/modules/request-inspector'
import type {
  InspectorAnalytics,
  InspectorMessageBlock,
  InspectorRequestDetail,
  InspectorRequestSummary,
} from '../api/types/request-inspector'

const dialogStore = useDialogStore()
const toastStore = useToastStore()
const { t } = useI18n()

const requests = ref<InspectorRequestSummary[]>([])
const selectedRequest = ref<InspectorRequestDetail | null>(null)
const analytics = ref<InspectorAnalytics | null>(null)
const isLoading = ref(true)
const isDetailLoading = ref(false)
const isRefreshing = ref(false)
const searchText = ref('')
const selectedRole = ref('all')
const viewMode = ref<'rendered' | 'raw'>('rendered')
const lastUpdatedAt = ref('')
const isRequestListOpen = ref(false)

let pollTimer: number | null = null

const filteredRequests = computed(() => {
  const keyword = searchText.value.trim().toLowerCase()
  return requests.value.filter((item) => {
    const haystack = [
      item.id,
      item.api_name,
      item.model,
      item.api_provider,
      item.request_name,
      item.ts_str,
    ].join(' ').toLowerCase()
    return !keyword || haystack.includes(keyword)
  }).slice().reverse()
})

const roleOptions = computed(() => {
  const roles = new Set<string>()
  selectedRequest.value?.rendered.messages.forEach((message) => roles.add(message.role))
  return ['all', ...Array.from(roles)]
})

const visibleMessages = computed(() => {
  const messages = selectedRequest.value?.rendered.messages ?? []
  if (selectedRole.value === 'all') return messages
  return messages.filter((message) => message.role === selectedRole.value)
})

const rawJson = computed(() => JSON.stringify(selectedRequest.value?.params ?? {}, null, 2))

const totalCaptured = computed(() => requests.value.length)
const totalMessages = computed(() => requests.value.reduce((sum, item) => sum + item.msg_count, 0))
const totalTools = computed(() => requests.value.reduce((sum, item) => sum + item.tool_count, 0))
const statsSummary = computed(() => analytics.value?.summary ?? {})

onMounted(async () => {
  await refreshAll()
  pollTimer = window.setInterval(refreshAll, 10000)
})

onUnmounted(() => {
  if (pollTimer !== null) window.clearInterval(pollTimer)
})

async function refreshAll(): Promise<void> {
  isLoading.value = true
  try {
    await Promise.all([refreshListOnly(), refreshAnalytics()])
  } finally {
    isLoading.value = false
  }
}

async function refreshListOnly(): Promise<void> {
  isRefreshing.value = true
  try {
    requests.value = await listInspectorRequests()
    lastUpdatedAt.value = new Date().toLocaleTimeString()
    if (!selectedRequest.value && requests.value.length > 0) {
      await selectRequest(requests.value[requests.value.length - 1].id)
    }
  } finally {
    isRefreshing.value = false
  }
}

async function refreshAnalytics(): Promise<void> {
  analytics.value = await getInspectorAnalytics()
}

async function selectRequest(requestId: number): Promise<void> {
  isDetailLoading.value = true
  selectedRole.value = 'all'
  try {
    selectedRequest.value = await getInspectorRequest(requestId)
    isRequestListOpen.value = false
  } finally {
    isDetailLoading.value = false
  }
}

async function clearRequests(): Promise<void> {
  const confirmed = await dialogStore.confirm(
    t('requestInspector.dialogs.clearMessage'),
    t('requestInspector.dialogs.clearTitle'),
    t('requestInspector.actions.clear'),
    t('requestInspector.dialogs.cancel'),
  )
  if (!confirmed) return
  await clearInspectorRequests()
  selectedRequest.value = null
  requests.value = []
  toastStore.show(t('requestInspector.toast.clearSuccess'), 'success')
}

function roleClass(role: string): string {
  return `role-${role.replace(/[^a-z0-9_-]/gi, '-').toLowerCase()}`
}

function blockTitle(block: InspectorMessageBlock): string {
  if (block.label) return block.label
  if (block.type === 'tool_call') return t('requestInspector.blocks.toolCall')
  if (block.type === 'tool_result') return t('requestInspector.blocks.toolResult')
  if (block.type === 'media') return block.title ?? t('requestInspector.blocks.media')
  if (block.type === 'unknown') return t('requestInspector.blocks.unknown')
  return t('requestInspector.blocks.content')
}

function formatMetric(value: unknown): string {
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(3)
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return '—'
  return JSON.stringify(value)
}

function formatTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString()
}
</script>

<template>
  <AppShell no-padding>
    <section class="inspector-page">
      <header class="inspector-top-bar">
        <div class="top-bar-left">
          <button class="request-title-button" type="button" @click="isRequestListOpen = !isRequestListOpen">
            <h2>{{ selectedRequest ? `#${selectedRequest.id} ${selectedRequest.model}` : t('requestInspector.list.title') }}</h2>
            <Icon icon="material-symbols:expand-more-rounded" width="20" height="20" class="request-title-chevron" :class="{ open: isRequestListOpen }" />
          </button>
          <p>{{ selectedRequest ? `${selectedRequest.api_name} · ${selectedRequest.api_provider}` : t('requestInspector.list.count', { filtered: String(filteredRequests.length), total: String(requests.length) }) }}</p>
        </div>
        <div class="top-bar-status">
          <span>{{ t('requestInspector.stats.lastUpdated') }} {{ lastUpdatedAt || '—' }}</span>
          <strong>{{ totalCaptured }}</strong>
        </div>
      </header>

      <button v-if="isRequestListOpen" class="mobile-menu-backdrop" type="button" aria-label="Close request list" @click="isRequestListOpen = false"></button>
      <aside class="mobile-request-menu" :class="{ open: isRequestListOpen }" aria-label="request list">
          <div class="panel-toolbar">
            <div class="request-list-heading">
              <div class="request-list-title-row">
                <div>
                  <span class="request-list-eyebrow">{{ t('requestInspector.list.eyebrow') }}</span>
                  <h2>{{ t('requestInspector.list.title') }}</h2>
                </div>
                <button class="mobile-close-button" type="button" aria-label="Close request list" @click="isRequestListOpen = false">
                  <Icon icon="material-symbols:close-rounded" width="20" height="20" />
                </button>
              </div>
              <p>{{ t('requestInspector.list.count', { filtered: String(filteredRequests.length), total: String(requests.length) }) }}</p>
            </div>
            <div class="inspector-status-card">
              <div class="status-row">
                <span>{{ t('requestInspector.stats.lastUpdated') }}</span>
                <strong>{{ lastUpdatedAt || '—' }}</strong>
              </div>
              <div class="status-metrics">
                <span>{{ t('requestInspector.stats.capturedRequests') }} <strong>{{ totalCaptured }}</strong></span>
                <span>{{ t('requestInspector.stats.totalMessages') }} <strong>{{ totalMessages }}</strong></span>
                <span>{{ t('requestInspector.stats.toolDeclarations') }} <strong>{{ totalTools }}</strong></span>
                <span>{{ t('requestInspector.stats.statsRequests') }} <strong>{{ formatMetric(statsSummary.total_requests) }}</strong></span>
              </div>
              <button class="danger-button" :disabled="requests.length === 0" @click="clearRequests">
                <Icon icon="material-symbols:delete-outline-rounded" width="18" height="18" />
                {{ t('requestInspector.actions.clear') }}
              </button>
            </div>
          </div>

          <div v-if="!selectedRequest" class="mobile-select-hint">
            <Icon icon="material-symbols:touch-app-outline-rounded" width="22" height="22" />
            <span>{{ t('requestInspector.list.mobileHint') }}</span>
          </div>

          <input v-model="searchText" class="search-input" :placeholder="t('requestInspector.list.searchPlaceholder')" />

          <div v-if="isLoading" class="empty-state">{{ t('requestInspector.list.loading') }}</div>
          <div v-else-if="filteredRequests.length === 0" class="empty-state">{{ t('requestInspector.list.empty') }}</div>
          <div v-else class="request-list">
            <button v-for="item in filteredRequests" :key="item.id" class="request-item"
              :class="{ active: selectedRequest?.id === item.id }" @click="selectRequest(item.id)">
              <span class="request-item-top">
                <strong>#{{ item.id }} {{ item.model }}</strong>
                <em>{{ item.ts_str }}</em>
              </span>
              <span class="request-item-name">{{ item.request_name || item.api_name }}</span>
              <span class="request-item-meta">{{ item.api_provider }} · {{ t('requestInspector.list.messages', { count: String(item.msg_count) }) }} · {{
                t('requestInspector.list.tools', { count: String(item.tool_count) }) }}</span>
            </button>
          </div>
      </aside>

      <div class="workspace-card">
        <aside class="request-list-panel">
          <div class="panel-toolbar">
            <div class="request-list-heading">
              <div class="request-list-title-row">
                <div>
                  <span class="request-list-eyebrow">{{ t('requestInspector.list.eyebrow') }}</span>
                  <h2>{{ t('requestInspector.list.title') }}</h2>
                </div>
              </div>
              <p>{{ t('requestInspector.list.count', { filtered: String(filteredRequests.length), total: String(requests.length) }) }}</p>
            </div>
            <div class="inspector-status-card">
              <div class="status-row">
                <span>{{ t('requestInspector.stats.lastUpdated') }}</span>
                <strong>{{ lastUpdatedAt || '—' }}</strong>
              </div>
              <div class="status-metrics">
                <span>{{ t('requestInspector.stats.capturedRequests') }} <strong>{{ totalCaptured }}</strong></span>
                <span>{{ t('requestInspector.stats.totalMessages') }} <strong>{{ totalMessages }}</strong></span>
                <span>{{ t('requestInspector.stats.toolDeclarations') }} <strong>{{ totalTools }}</strong></span>
                <span>{{ t('requestInspector.stats.statsRequests') }} <strong>{{ formatMetric(statsSummary.total_requests) }}</strong></span>
              </div>
              <button class="danger-button" :disabled="requests.length === 0" @click="clearRequests">
                <Icon icon="material-symbols:delete-outline-rounded" width="18" height="18" />
                {{ t('requestInspector.actions.clear') }}
              </button>
            </div>
          </div>

          <div v-if="!selectedRequest" class="mobile-select-hint">
            <Icon icon="material-symbols:touch-app-outline-rounded" width="22" height="22" />
            <span>{{ t('requestInspector.list.mobileHint') }}</span>
          </div>

          <input v-model="searchText" class="search-input" :placeholder="t('requestInspector.list.searchPlaceholder')" />

          <div v-if="isLoading" class="empty-state">{{ t('requestInspector.list.loading') }}</div>
          <div v-else-if="filteredRequests.length === 0" class="empty-state">{{ t('requestInspector.list.empty') }}</div>
          <div v-else class="request-list">
            <button v-for="item in filteredRequests" :key="item.id" class="request-item"
              :class="{ active: selectedRequest?.id === item.id }" @click="selectRequest(item.id)">
              <span class="request-item-top">
                <strong>#{{ item.id }} {{ item.model }}</strong>
                <em>{{ item.ts_str }}</em>
              </span>
              <span class="request-item-name">{{ item.request_name || item.api_name }}</span>
              <span class="request-item-meta">{{ item.api_provider }} · {{ t('requestInspector.list.messages', { count: String(item.msg_count) }) }} · {{
                t('requestInspector.list.tools', { count: String(item.tool_count) }) }}</span>
            </button>
          </div>
        </aside>

        <main class="detail-panel">
          <div v-if="!selectedRequest" class="detail-empty detail-placeholder">
            <Icon icon="material-symbols:plagiarism-outline-rounded" width="48" height="48" />
            <div>
              <span class="eyebrow">{{ t('requestInspector.detail.eyebrow') }}</span>
              <h2>{{ t('requestInspector.detail.emptyTitle') }}</h2>
              <p>{{ t('requestInspector.detail.emptyPrefix') }}<span class="desktop-text">{{ t('requestInspector.detail.leftSide') }}</span><span class="mobile-text">{{ t('requestInspector.detail.below') }}</span>{{ t('requestInspector.detail.emptySuffix') }}</p>
            </div>
            <div class="placeholder-grid">
              <article>
                <strong>{{ totalCaptured }}</strong>
                <span>{{ t('requestInspector.detail.currentCaptured') }}</span>
              </article>
              <article>
                <strong>{{ totalMessages }}</strong>
                <span>{{ t('requestInspector.detail.accumulatedMessages') }}</span>
              </article>
              <article>
                <strong>{{ totalTools }}</strong>
                <span>{{ t('requestInspector.detail.toolDeclarationCount') }}</span>
              </article>
            </div>
            <p class="placeholder-tip">{{ t('requestInspector.detail.tipPrefix') }}<span class="desktop-text">{{ t('requestInspector.detail.leftSide') }}</span><span class="mobile-text">{{ t('requestInspector.detail.below') }}</span>{{ t('requestInspector.detail.tipSuffix') }}</p>
          </div>

          <template v-else>
            <div class="detail-header">
              <div>
                <span class="eyebrow">#{{ selectedRequest.id }} · {{ formatTime(selectedRequest.ts) }}</span>
                <h2>{{ selectedRequest.model }}</h2>
                <p>{{ selectedRequest.api_name }} · {{ selectedRequest.api_provider }}</p>
              </div>
              <div class="segmented">
                <button :class="{ active: viewMode === 'rendered' }" @click="viewMode = 'rendered'">{{ t('requestInspector.viewMode.rendered') }}</button>
                <button :class="{ active: viewMode === 'raw' }" @click="viewMode = 'raw'">{{ t('requestInspector.viewMode.raw') }}</button>
              </div>
            </div>

            <div v-if="isDetailLoading" class="empty-state">{{ t('requestInspector.detail.loading') }}</div>

            <template v-else-if="viewMode === 'rendered'">
              <section class="overview-grid">
                <div v-for="item in selectedRequest.rendered.overview" :key="item.label" class="overview-item">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </section>

              <section v-if="selectedRequest.rendered.tools.length" class="section-card">
                <h3>{{ t('requestInspector.tools.title') }}</h3>
                <article v-for="tool in selectedRequest.rendered.tools" :key="tool.index" class="tool-card">
                  <div class="tool-title">
                    <strong>{{ tool.name }}</strong>
                    <span>{{ tool.kind }}</span>
                  </div>
                  <p>{{ tool.description || t('requestInspector.tools.noDescription') }}</p>
                  <div class="property-list">
                    <span v-for="property in tool.properties" :key="property.name" class="property-pill">
                      {{ property.name }} · {{ property.type }}{{ property.required ? ' *' : '' }}
                    </span>
                  </div>
                </article>
              </section>

              <section class="section-card">
                <div class="message-toolbar">
                  <h3>{{ t('requestInspector.messages.title') }}</h3>
                  <select v-model="selectedRole" class="role-select">
                    <option v-for="role in roleOptions" :key="role" :value="role">
                      {{ role === 'all' ? t('requestInspector.messages.allRoles') : role }}
                    </option>
                  </select>
                </div>

                <article v-for="message in visibleMessages" :key="message.index" class="message-card"
                  :class="roleClass(message.role)">
                  <header>
                    <span>{{ message.label }}</span>
                    <small>#{{ message.index }} {{ message.meta }}</small>
                  </header>
                  <div v-for="(block, blockIndex) in message.blocks" :key="`${message.index}-${blockIndex}`"
                    class="message-block" :class="`block-${block.type}`">
                    <strong>{{ blockTitle(block) }}</strong>
                    <pre v-if="block.type === 'tool_call'">{{ block.arguments_text }}</pre>
                    <pre v-else-if="block.type === 'tool_result' || block.type === 'unknown'">{{ block.text }}</pre>
                    <p v-else>{{ block.text || block.meta || '—' }}</p>
                    <small v-if="block.call_id">call_id: {{ block.call_id }}</small>
                    <small v-if="block.name">name: {{ block.name }}</small>
                  </div>
                </article>
              </section>
            </template>

            <pre v-else class="raw-json">{{ rawJson }}</pre>
          </template>
        </main>
      </div>
    </section>
  </AppShell>
</template>

<style scoped>
.inspector-page {
  height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.workspace-card,
.section-card {
  border: 1px solid var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.eyebrow {
  color: var(--md-sys-color-primary);
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

h2,
h3,
p {
  margin: 0;
}

.detail-header p,
.panel-toolbar p {
  color: var(--md-sys-color-on-surface-variant);
}

.danger-button,
.segmented button {
  display: inline-flex;
  align-items: center;
  gap: .45rem;
  border: 0;
  border-radius: 999px;
  padding: .7rem 1rem;
  font-weight: 700;
  cursor: pointer;
}

.danger-button {
  color: var(--md-sys-color-on-error-container);
  background: var(--md-sys-color-error-container);
}

button:disabled {
  cursor: not-allowed;
  opacity: .55;
}

.mobile-select-hint {
  display: none;
  align-items: center;
  gap: .6rem;
  margin-bottom: .9rem;
  padding: .9rem 1rem;
  border-radius: 18px;
  background: color-mix(in srgb, var(--md-sys-color-primary-container) 78%, transparent);
  color: var(--md-sys-color-on-primary-container);
  font-size: 1rem;
  font-weight: 800;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--md-sys-color-primary) 18%, transparent);
}

.inspector-top-bar {
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 10px 16px;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  flex-shrink: 0;
  z-index: 10;
}

.top-bar-left {
  min-width: 0;
}

.request-title-button {
  display: inline-flex;
  align-items: center;
  gap: .25rem;
  max-width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--md-sys-color-on-surface);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.request-title-button h2 {
  overflow: hidden;
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.request-title-chevron {
  color: var(--md-sys-color-on-surface-variant);
  transition: transform .18s ease;
  flex: 0 0 auto;
}

.request-title-chevron.open {
  transform: rotate(180deg);
}

.top-bar-left p,
.top-bar-status span {
  overflow: hidden;
  margin: 0;
  color: var(--md-sys-color-on-surface-variant);
  font-size: .76rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-bar-status {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  flex: 0 0 auto;
}

.top-bar-status strong {
  min-width: 1.75rem;
  padding: .22rem .5rem;
  border-radius: 999px;
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
  text-align: center;
}

.mobile-menu-backdrop,
.mobile-request-menu {
  display: none;
}

.workspace-card {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  flex: 1;
  min-height: 0;
  border-radius: 0;
  overflow: hidden;
}

.request-list-panel {
  border-right: 1px solid var(--md-sys-color-outline-variant);
  padding: 1rem;
  overflow: auto;
  min-height: 0;
}

.mobile-list-button,
.mobile-close-button,
.mobile-drawer-scrim {
  display: none;
}

.panel-toolbar {
  display: flex;
  flex-direction: column;
  gap: .8rem;
  margin-bottom: .75rem;
}

.request-list-heading {
  display: flex;
  flex-direction: column;
  gap: .18rem;
  padding: .2rem 0 .35rem;
}

.request-list-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: .75rem;
}

.inspector-status-card {
  display: flex;
  flex-direction: column;
  gap: .75rem;
  padding: .85rem;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 18px;
  background: color-mix(in srgb, var(--md-sys-color-surface) 72%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.status-row,
.status-metrics {
  display: flex;
  gap: .5rem;
}

.status-row {
  align-items: center;
  justify-content: space-between;
}

.status-row span,
.status-metrics span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: .78rem;
  font-weight: 600;
}

.status-row strong,
.status-metrics strong {
  color: var(--md-sys-color-on-surface);
}

.status-metrics {
  flex-wrap: wrap;
}

.status-metrics span {
  padding: .35rem .55rem;
  border-radius: 999px;
  background: var(--md-sys-color-surface-container-high);
}

.request-list-eyebrow {
  color: var(--md-sys-color-primary);
  font-size: .86rem;
  font-weight: 800;
  letter-spacing: .04em;
}

.request-list-heading h2 {
  font-size: 1.65rem;
  line-height: 1.1;
  letter-spacing: -.03em;
}

.search-input,
.role-select {
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 14px;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  padding: .75rem .9rem;
  outline: none;
}

.search-input { width: 100%; margin-bottom: 1rem; }
.request-list { display: flex; flex-direction: column; gap: .45rem; }
.request-item { width: 100%; text-align: left; display: flex; flex-direction: column; gap: .4rem; padding: .9rem; border: 1px solid transparent; border-radius: 18px; background: transparent; color: var(--md-sys-color-on-surface); cursor: pointer; }

.request-item:hover,
.request-item.active {
  background: var(--md-sys-color-secondary-container);
  border-color: var(--md-sys-color-outline-variant);
}

.request-item-top {
  display: flex;
  justify-content: space-between;
  gap: .5rem;
}

.request-item-top em,
.request-item-meta {
  color: var(--md-sys-color-on-surface-variant);
  font-size: .78rem;
  font-style: normal;
}

.request-item-name {
  font-weight: 700;
  word-break: break-word;
}

.detail-panel {
  flex: 1;
  min-width: 0;
  padding: 1.25rem;
  overflow: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.detail-empty,
.empty-state {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .6rem;
  color: var(--md-sys-color-on-surface-variant);
  text-align: center;
}

.detail-placeholder {
  flex: 1;
  min-height: 420px;
  align-items: stretch;
  padding: 1.5rem;
  border-radius: 24px;
  background: color-mix(in srgb, var(--md-sys-color-primary-container) 22%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--md-sys-color-primary) 14%, transparent);
}

.mobile-text {
  display: none;
}

.detail-placeholder>svg {
  align-self: center;
  color: var(--md-sys-color-primary);
}

.detail-placeholder h2 {
  margin-top: .35rem;
  color: var(--md-sys-color-on-surface);
  font-size: clamp(1.6rem, 3vw, 2.35rem);
  letter-spacing: -.04em;
}

.detail-placeholder p {
  max-width: 720px;
  margin: 0 auto;
  line-height: 1.7;
}

.placeholder-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
  width: 100%;
  margin: .8rem 0;
}

.placeholder-grid article {
  display: flex;
  flex-direction: column;
  gap: .2rem;
  padding: 1rem;
  border-radius: 18px;
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
}

.placeholder-grid strong {
  color: var(--md-sys-color-on-surface);
  font-size: 1.65rem;
}

.placeholder-grid span,
.placeholder-tip {
  color: var(--md-sys-color-on-surface-variant);
  font-size: .88rem;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.segmented {
  display: inline-flex;
  padding: .25rem;
  border-radius: 999px;
  background: var(--md-sys-color-surface-container-high);
}

.segmented button {
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
}

.segmented button.active {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: .75rem;
  margin-bottom: 1rem;
}

.overview-item {
  padding: .85rem;
  border-radius: 16px;
  background: var(--md-sys-color-surface-container);
  display: flex;
  flex-direction: column;
  gap: .25rem;
}

.overview-item span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: .8rem;
}

.overview-item strong {
  color: var(--md-sys-color-on-surface);
  word-break: break-word;
}

.section-card {
  padding: 1rem;
  border-radius: 22px;
  margin-bottom: 1rem;
}

.tool-card {
  padding: .85rem 0;
  border-top: 1px solid var(--md-sys-color-outline-variant);
}

.tool-title,
.message-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.tool-title span,
.property-pill {
  border-radius: 999px;
  padding: .25rem .55rem;
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
  font-size: .75rem;
  font-weight: 700;
}

.property-list {
  display: flex;
  flex-wrap: wrap;
  gap: .45rem;
  margin-top: .6rem;
}

.message-card {
  border-left: 4px solid var(--md-sys-color-outline);
  border-radius: 18px;
  padding: .9rem;
  background: var(--md-sys-color-surface-container);
  margin-top: .75rem;
}

.message-card header {
  display: flex;
  justify-content: space-between;
  gap: .75rem;
  margin-bottom: .75rem;
}

.message-card header span {
  font-weight: 800;
}

.message-card header small,
.message-block small {
  color: var(--md-sys-color-on-surface-variant);
}

.role-system {
  border-left-color: #7c3aed;
}

.role-user {
  border-left-color: #0f766e;
}

.role-assistant {
  border-left-color: #d97706;
}

.role-tool {
  border-left-color: #2563eb;
}

.message-block {
  border-radius: 14px;
  padding: .75rem;
  background: var(--md-sys-color-surface);
  margin-top: .55rem;
  display: flex;
  flex-direction: column;
  gap: .35rem;
}

.message-block p {
  white-space: pre-wrap;
  line-height: 1.6;
}

pre {
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-block pre,
.raw-json {
  border-radius: 16px;
  padding: 1rem;
  background: #1f1b16;
  color: #fff3e0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  line-height: 1.55;
}

.raw-json {
  min-height: 520px;
}

@media (max-width: 1100px) {
  .inspector-top-bar {
    display: flex;
  }

  .workspace-card {
    display: flex;
  }

  .request-list-panel {
    display: none;
  }

  .mobile-menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 70;
    display: block;
    border: 0;
    background: rgba(0, 0, 0, .32);
    animation: fade-in .15s ease;
  }

  .mobile-request-menu {
    position: fixed;
    top: 4.5rem;
    left: .75rem;
    right: .75rem;
    z-index: 80;
    display: block;
    max-height: min(76vh, 620px);
    overflow: auto;
    padding: 1rem;
    border: 1px solid var(--md-sys-color-outline-variant);
    border-radius: 20px;
    background: var(--md-sys-color-surface);
    box-shadow: 0 8px 32px rgba(0, 0, 0, .12), 0 2px 8px rgba(0, 0, 0, .08);
    transform: translateY(-12px) scale(.98);
    opacity: 0;
    pointer-events: none;
    transition: transform .18s ease, opacity .18s ease;
  }

  .mobile-request-menu.open {
    transform: translateY(0) scale(1);
    opacity: 1;
    pointer-events: auto;
  }

  .mobile-close-button {
    display: none;
  }

  .detail-panel { max-height: none; }
  .desktop-text { display: none; }
  .mobile-text { display: inline; }
  .mobile-select-hint { display: flex; }
}

@media (max-width: 720px) {

  .detail-header,
  .tool-title,
  .message-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .workspace-card {
    border-radius: 0;
  }

  .detail-panel,
  .request-list-panel {
    padding: .85rem;
  }

  .request-list-heading h2 {
    font-size: 1.95rem;
  }

  .request-list-eyebrow {
    font-size: .95rem;
  }

  .placeholder-grid {
    grid-template-columns: 1fr;
  }

  .request-item-top,
  .message-card header {
    flex-direction: column;
  }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>

