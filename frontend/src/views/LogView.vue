<script setup lang="ts">
/**
 * 日志查看器视图。
 *
 * 提供实时日志 WebSocket 推送和历史日志文件浏览功能，
 * 支持日志级别过滤、关键词搜索、自动滚动和历史日志滚动分页。
 */

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import Icon from '../components/common/Icon.vue'
import { useToastStore } from '../utils/toast'
import { useI18n } from '../utils/i18n'
import { getLogFiles, getLogContent } from '../api/modules/log'
import { API_BASE_URL } from '../api/config'
import type { RealtimeLogEntry, LogFileInfo, LogContentResponse, StructuredLogLine } from '../api/types/log'

type WsStatus = 'disconnected' | 'connecting' | 'connected'
type HistoryLoadMode = 'replace' | 'prepend' | 'append'
type HistoryMeta = Omit<LogContentResponse, 'content' | 'entries' | 'total_matches' | 'query'>

const toastStore = useToastStore()
const { t, locale } = useI18n()

const activeTab = ref<'realtime' | 'history'>('realtime')

const realtimeLogs = ref<RealtimeLogEntry[]>([])
const wsStatus = ref<WsStatus>('disconnected')
const autoScroll = ref(true)
const atBottom = ref(true)
const searchText = ref('')
const selectedLevels = ref<string[]>([])
const levelDropdownOpen = ref(false)
const levelDropdownRef = ref<HTMLElement | null>(null)
const logContainerRef = ref<HTMLElement | null>(null)
const lastRealtimeAt = ref<string>('')
const maxLogEntries = 2000

const logFiles = ref<LogFileInfo[]>([])
const selectedFile = ref<string>('')
const fileSearchText = ref('')
const historySearchText = ref('')
const isMobileFileMenuOpen = ref(false)
const historyLines = ref<string[]>([])
const historyEntries = ref<StructuredLogLine[]>([])
const historyLoading = ref(false)
const historyLoadingPrev = ref(false)
const historyLoadingNext = ref(false)
const historyMeta = ref<HistoryMeta | null>(null)
const historyStartOffset = ref(0)
const historyEndOffset = ref(0)
const historyHasPrev = ref(false)
const historyHasNext = ref(false)
const historyContainerRef = ref<HTMLElement | null>(null)
const loadedHistoryOffsets = ref<Set<number>>(new Set())
const historyChunkLimit = 65536

let ws: WebSocket | null = null
let heartbeatTimer: number | null = null

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const

const filteredLogs = computed(() => {
  const keyword = searchText.value.trim().toLowerCase()
  const levelFilter = selectedLevels.value
  return realtimeLogs.value.filter((entry) => {
    if (levelFilter.length > 0 && !levelFilter.includes(entry.level.toUpperCase())) {
      return false
    }

    if (keyword) {
      const haystack = `${entry.message} ${entry.logger_name} ${entry.display}`.toLowerCase()
      return haystack.includes(keyword)
    }

    return true
  })
})

const logStats = computed(() => {
  const stats: Record<string, number> = {}
  for (const entry of realtimeLogs.value) {
    const level = entry.level.toUpperCase()
    stats[level] = (stats[level] || 0) + 1
  }
  return stats
})

const filteredLogFiles = computed(() => {
  const keyword = fileSearchText.value.trim().toLowerCase()
  if (!keyword) return logFiles.value
  return logFiles.value.filter((file) => {
    const haystack = `${file.filename} ${file.modified_time} ${file.path}`.toLowerCase()
    return haystack.includes(keyword)
  })
})

const wsStatusText = computed(() => t(`log.status.${wsStatus.value}`))

const historyProgressText = computed(() => {
  const meta = historyMeta.value
  if (!meta) return t('log.history.unloadedProgress')
  const loadedSize = Math.max(0, historyEndOffset.value - historyStartOffset.value)
  return `${formatFileSize(loadedSize)} / ${formatFileSize(meta.total_size)}`
})

function visibleHistoryBadges(entry: StructuredLogLine): string[] {
  return entry.badges.filter((badge) => badge !== entry.source)
}

function visibleHistoryLineParts(entry: StructuredLogLine): Array<{ text: string; hit: boolean }> {
  const content = entry.message || entry.raw
  if (!entry.search_matches.length || content !== entry.raw) return [{ text: content, hit: false }]

  const parts: Array<{ text: string; hit: boolean }> = []
  let cursor = 0
  for (const match of entry.search_matches) {
    if (match.start > cursor) {
      parts.push({ text: content.slice(cursor, match.start), hit: false })
    }
    parts.push({ text: content.slice(match.start, match.end), hit: true })
    cursor = match.end
  }
  if (cursor < content.length) {
    parts.push({ text: content.slice(cursor), hit: false })
  }
  return parts
}

function fallbackHistoryEntries(lines: string[]): StructuredLogLine[] {
  return lines.map((line) => ({
    raw: line,
    timestamp: '',
    level: 'INFO',
    level_label: 'INFO',
    tone: 'info',
    color: '#0075de',
    source: '',
    message: line,
    badges: [],
    search_matches: [],
  }))
}

function historyEntryStyle(entry: StructuredLogLine): Record<string, string> {
  return {
    '--history-entry-color': entry.color || levelColor(entry.level),
    '--history-entry-bg': levelBg(entry.level),
  }
}

function historyFilterLevels(): string[] {
  return selectedLevels.value.length > 0 ? [...selectedLevels.value] : []
}

function connectWs(): void {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

  wsStatus.value = 'connecting'
  const origin = API_BASE_URL.replace(/^http/, 'ws')
  const token = sessionStorage.getItem('neo_token')
  const url = token
    ? `${origin}/webui/api/log/ws?token=${encodeURIComponent(token)}`
    : `${origin}/webui/api/log/ws`

  console.info('[LogView] connecting realtime log websocket', {
    apiBaseUrl: API_BASE_URL,
    origin,
    hasToken: Boolean(token),
    url,
  })

  ws = new WebSocket(url)

  ws.onopen = () => {
    console.info('[LogView] realtime log websocket connected')
    wsStatus.value = 'connected'
    sendLevelFilter()
    startHeartbeat()
  }

  ws.onmessage = (event: MessageEvent) => {
    console.debug('[LogView] realtime log websocket message', event.data)
    handleWsMessage(event.data)
  }

  ws.onclose = (event: CloseEvent) => {
    console.warn('[LogView] realtime log websocket closed', {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
    })
    wsStatus.value = 'disconnected'
    stopHeartbeat()
    ws = null
  }

  ws.onerror = (event: Event) => {
    console.error('[LogView] realtime log websocket error', {
      apiBaseUrl: API_BASE_URL,
      origin,
      url,
      readyState: ws?.readyState,
      event,
    })
    wsStatus.value = 'disconnected'
    toastStore.show(t('log.toast.wsError'), 'error')
  }
}

function disconnectWs(): void {
  stopHeartbeat()
  if (ws) {
    ws.close()
    ws = null
  }
  wsStatus.value = 'disconnected'
}

function startHeartbeat(): void {
  stopHeartbeat()
  heartbeatTimer = window.setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }, 30000)
}

function stopHeartbeat(): void {
  if (heartbeatTimer !== null) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function handleWsMessage(rawData: unknown): void {
  try {
    const msg = typeof rawData === 'string' ? JSON.parse(rawData) : rawData
    if (!msg || typeof msg !== 'object') return

    const typedMsg = msg as { type?: string; data?: unknown }
    if (typedMsg.type === 'pong') return

    if (typedMsg.type === 'history_batch' && Array.isArray(typedMsg.data)) {
      const entries = typedMsg.data.map(normalizeLogEntry).filter(Boolean) as RealtimeLogEntry[]
      realtimeLogs.value = mergeRealtimeLogs(entries, realtimeLogs.value)
      if (autoScroll.value) scrollToBottom()
      return
    }

    if (typedMsg.type === 'realtime_log' && typedMsg.data) {
      appendRealtimeLog(typedMsg.data)
      return
    }

    if (typedMsg.type === undefined && 'message' in typedMsg) {
      appendRealtimeLog(typedMsg)
    }
  } catch {
    if (typeof rawData === 'string' && rawData.trim()) {
      appendRealtimeLog({ message: rawData, level: 'INFO' })
    }
  }
}

function normalizeLogEntry(value: unknown): RealtimeLogEntry | null {
  if (!value || typeof value !== 'object') return null

  const raw = value as Partial<RealtimeLogEntry> & Record<string, unknown>
  const message = String(raw.message ?? raw.msg ?? raw.text ?? '')
  if (!message) return null

  return {
    timestamp: String(raw.timestamp ?? raw.time ?? new Date().toLocaleTimeString()),
    level: String(raw.level ?? 'INFO').toUpperCase(),
    logger_name: String(raw.logger_name ?? raw.name ?? ''),
    display: String(raw.display ?? raw.logger_name ?? raw.name ?? ''),
    color: String(raw.color ?? ''),
    message,
    metadata: typeof raw.metadata === 'object' && raw.metadata !== null
      ? raw.metadata as Record<string, unknown>
      : {},
  }
}

function mergeRealtimeLogs(prefix: RealtimeLogEntry[], current: RealtimeLogEntry[]): RealtimeLogEntry[] {
  return [...prefix, ...current].slice(-maxLogEntries)
}

function appendRealtimeLog(value: unknown): void {
  const entry = normalizeLogEntry(value)
  if (!entry) return

  realtimeLogs.value.push(entry)
  lastRealtimeAt.value = entry.timestamp

  if (realtimeLogs.value.length > maxLogEntries) {
    realtimeLogs.value = realtimeLogs.value.slice(-maxLogEntries)
  }

  if (autoScroll.value) {
    scrollToBottom()
  }
}

function sendLevelFilter(): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    const levels = selectedLevels.value.length > 0 ? [...selectedLevels.value] : null
    ws.send(JSON.stringify({ type: 'set_level_filter', levels }))
  }
}

function toggleLevel(level: string): void {
  const idx = selectedLevels.value.indexOf(level)
  if (idx === -1) {
    selectedLevels.value = [...selectedLevels.value, level]
  } else {
    selectedLevels.value = selectedLevels.value.filter((l) => l !== level)
  }
  sendLevelFilter()
}

function clearLevelFilter(): void {
  selectedLevels.value = []
  sendLevelFilter()
}

function toggleLevelDropdown(): void {
  levelDropdownOpen.value = !levelDropdownOpen.value
}

function closeLevelDropdown(event: MouseEvent): void {
  if (levelDropdownRef.value && !levelDropdownRef.value.contains(event.target as Node)) {
    levelDropdownOpen.value = false
  }
}

function clearLogs(): void {
  realtimeLogs.value = []
  lastRealtimeAt.value = ''
}

function scrollToBottom(): void {
  nextTick(() => {
    const container = logContainerRef.value
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}

function handleRealtimeScroll(): void {
  const container = logContainerRef.value
  if (!container) return
  const nearBottom = isNearBottom(container)
  atBottom.value = nearBottom
  autoScroll.value = nearBottom
}

function isNearTop(container: HTMLElement, threshold = 72): boolean {
  return container.scrollTop < threshold
}

function isNearBottom(container: HTMLElement, threshold = 72): boolean {
  return container.scrollHeight - container.scrollTop - container.clientHeight < threshold
}

function levelColor(level: string): string {
  switch (level.toUpperCase()) {
    case 'DEBUG': return 'var(--md-sys-color-on-surface-variant)'
    case 'INFO': return 'var(--md-sys-color-primary)'
    case 'WARNING': return '#dd5b00'
    case 'ERROR': return 'var(--md-sys-color-error)'
    case 'CRITICAL': return '#d32f2f'
    default: return 'var(--md-sys-color-on-surface)'
  }
}

function levelBg(level: string): string {
  switch (level.toUpperCase()) {
    case 'DEBUG': return 'color-mix(in srgb, var(--md-sys-color-on-surface-variant) 10%, transparent)'
    case 'INFO': return 'color-mix(in srgb, var(--md-sys-color-primary) 13%, transparent)'
    case 'WARNING': return 'color-mix(in srgb, #dd5b00 14%, transparent)'
    case 'ERROR': return 'color-mix(in srgb, var(--md-sys-color-error) 13%, transparent)'
    case 'CRITICAL': return 'color-mix(in srgb, #d32f2f 17%, transparent)'
    default: return 'transparent'
  }
}

async function loadLogFiles(): Promise<void> {
  try {
    const data = await getLogFiles()
    logFiles.value = data.files
  } catch {
    toastStore.show(t('log.toast.fileListFailed'), 'error')
  }
}

async function loadFileContent(
  filename: string,
  offset = 0,
  mode: HistoryLoadMode = 'replace',
): Promise<void> {
  if (!filename) return
  if (mode !== 'replace' && loadedHistoryOffsets.value.has(offset)) return

  const container = historyContainerRef.value
  const previousScrollHeight = container?.scrollHeight ?? 0
  const previousScrollTop = container?.scrollTop ?? 0

  setHistoryLoading(mode, true)

  try {
    const data = await getLogContent(
      filename,
      offset,
      historyChunkLimit,
      historySearchText.value.trim(),
      historyFilterLevels(),
    )
    applyHistoryChunk(data, mode)

    await nextTick()
    if (!historyContainerRef.value) return

    if (mode === 'prepend') {
      historyContainerRef.value.scrollTop = historyContainerRef.value.scrollHeight - previousScrollHeight + previousScrollTop
    } else if (mode === 'replace') {
      historyContainerRef.value.scrollTop = 0
    }
  } catch {
    toastStore.show(t('log.toast.contentFailed'), 'error')
  } finally {
    setHistoryLoading(mode, false)
  }
}

function setHistoryLoading(mode: HistoryLoadMode, value: boolean): void {
  if (mode === 'replace') historyLoading.value = value
  if (mode === 'prepend') historyLoadingPrev.value = value
  if (mode === 'append') historyLoadingNext.value = value
}

function applyHistoryChunk(data: LogContentResponse, mode: HistoryLoadMode): void {
  const meta = extractHistoryMeta(data)
  historyMeta.value = meta
  loadedHistoryOffsets.value = new Set(loadedHistoryOffsets.value).add(data.offset)

  if (mode === 'replace') {
    historyLines.value = data.content
    historyEntries.value = data.entries?.length ? data.entries : fallbackHistoryEntries(data.content)
    historyStartOffset.value = data.offset
    historyEndOffset.value = data.next_offset
  } else if (mode === 'prepend') {
    historyLines.value = [...data.content, ...historyLines.value]
    historyEntries.value = [
      ...(data.entries?.length ? data.entries : fallbackHistoryEntries(data.content)),
      ...historyEntries.value,
    ]
    historyStartOffset.value = data.offset
  } else {
    historyLines.value = [...historyLines.value, ...data.content]
    historyEntries.value = [
      ...historyEntries.value,
      ...(data.entries?.length ? data.entries : fallbackHistoryEntries(data.content)),
    ]
    historyEndOffset.value = data.next_offset
  }

  historyHasPrev.value = historyStartOffset.value > 0
  historyHasNext.value = historyEndOffset.value < data.total_size
}

function extractHistoryMeta(data: LogContentResponse): HistoryMeta {
  return {
    offset: data.offset,
    size: data.size,
    total_size: data.total_size,
    has_prev: data.has_prev,
    has_next: data.has_next,
    next_offset: data.next_offset,
    prev_offset: data.prev_offset,
  }
}

function selectLogFile(filename: string): void {
  selectedFile.value = filename
  isMobileFileMenuOpen.value = false
  historyLines.value = []
  historyEntries.value = []
  historyMeta.value = null
  historyStartOffset.value = 0
  historyEndOffset.value = 0
  historyHasPrev.value = false
  historyHasNext.value = false
  loadedHistoryOffsets.value = new Set()
  loadFileContent(filename)
}

function refreshHistorySearch(): void {
  if (!selectedFile.value) return
  historyLines.value = []
  historyEntries.value = []
  historyMeta.value = null
  historyStartOffset.value = 0
  historyEndOffset.value = 0
  historyHasPrev.value = false
  historyHasNext.value = false
  loadedHistoryOffsets.value = new Set()
  loadFileContent(selectedFile.value)
}

function handleHistoryScroll(): void {
  const container = historyContainerRef.value
  if (!container || historyLoading.value) return

  if (isNearTop(container) && historyHasPrev.value && !historyLoadingPrev.value) {
    loadFileContent(selectedFile.value, Math.max(0, historyStartOffset.value - historyChunkLimit), 'prepend')
  }

  if (isNearBottom(container) && historyHasNext.value && !historyLoadingNext.value) {
    loadFileContent(selectedFile.value, historyEndOffset.value, 'append')
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function formatTimestamp(ts: string): string {
  const normalized = ts.trim()
  if (!normalized) return ''

  const parsed = new Date(normalized)
  if (Number.isNaN(parsed.getTime())) return normalized

  return new Intl.DateTimeFormat(locale.value, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(parsed)
}

watch(activeTab, (tab) => {
  if (tab === 'realtime') {
    connectWs()
  } else {
    loadLogFiles()
  }
})

onMounted(() => {
  connectWs()
  document.addEventListener('click', closeLevelDropdown)
})

onUnmounted(() => {
  disconnectWs()
  document.removeEventListener('click', closeLevelDropdown)
})
</script>

<template>
  <AppShell no-padding>
    <section class="log-page" :aria-label="t('routes.log')">
      <div class="tab-bar" role="tablist" :aria-label="t('log.tabs.aria')">
        <button class="tab-item" :class="{ active: activeTab === 'realtime' }" @click="activeTab = 'realtime'">
          <Icon icon="material-symbols:stream-rounded" width="18" height="18" />
          <span>{{ t('log.tabs.realtime') }}</span>
        </button>
        <button class="tab-item" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
          <Icon icon="material-symbols:folder-open-outline-rounded" width="18" height="18" />
          <span>{{ t('log.tabs.history') }}</span>
        </button>
      </div>

      <div v-if="activeTab === 'realtime'" class="realtime-section">
        <section class="realtime-panel">
          <div class="control-card">
            <label class="search-field">
              <Icon icon="material-symbols:search-rounded" width="19" height="19" />
              <input v-model="searchText" :placeholder="t('log.realtime.searchPlaceholder')" />
            </label>

            <div class="level-multiselect" ref="levelDropdownRef">
              <button
                type="button"
                class="level-multiselect-trigger"
                :class="{ open: levelDropdownOpen, active: selectedLevels.length > 0 }"
                :aria-expanded="levelDropdownOpen"
                @click.stop="toggleLevelDropdown"
              >
                <span class="level-multiselect-label">{{ t('log.realtime.levelLabel') }}</span>
                <span class="level-multiselect-value">
                  <template v-if="selectedLevels.length === 0">{{ t('log.realtime.allLevels') }}</template>
                  <template v-else>{{ t('log.realtime.selectedCount', { count: String(selectedLevels.length) }) }}</template>
                </span>
                <Icon
                  icon="material-symbols:keyboard-arrow-down-rounded"
                  width="20"
                  height="20"
                  class="level-multiselect-chevron"
                  :class="{ open: levelDropdownOpen }"
                />
              </button>

              <transition name="level-dropdown">
                <div v-if="levelDropdownOpen" class="level-multiselect-panel" role="listbox" aria-multiselectable="true">
                  <button
                    type="button"
                    class="level-multiselect-option"
                    :class="{ checked: selectedLevels.length === 0 }"
                    role="option"
                    :aria-selected="selectedLevels.length === 0"
                    @click="clearLevelFilter"
                  >
                    <span class="level-multiselect-check">
                      <Icon
                        v-if="selectedLevels.length === 0"
                        icon="material-symbols:check-rounded"
                        width="16"
                        height="16"
                      />
                    </span>
                    <span class="level-multiselect-option-text">{{ t('log.realtime.allLevels') }}</span>
                    <span class="level-multiselect-count">{{ realtimeLogs.length }}</span>
                  </button>

                  <button
                    v-for="level in LOG_LEVELS"
                    :key="level"
                    type="button"
                    class="level-multiselect-option"
                    :class="{ checked: selectedLevels.includes(level) }"
                    role="option"
                    :aria-selected="selectedLevels.includes(level)"
                    :style="{ '--option-level-color': levelColor(level) }"
                    @click="toggleLevel(level)"
                  >
                    <span class="level-multiselect-check">
                      <Icon
                        v-if="selectedLevels.includes(level)"
                        icon="material-symbols:check-rounded"
                        width="16"
                        height="16"
                      />
                    </span>
                    <span class="level-multiselect-option-text">{{ level }}</span>
                    <span class="level-multiselect-count">{{ logStats[level] || 0 }}</span>
                  </button>

                  <div v-if="selectedLevels.length > 0" class="level-multiselect-footer">
                    <button type="button" class="level-multiselect-clear" @click="clearLevelFilter">
                      <Icon icon="material-symbols:filter-alt-off-outline-rounded" width="16" height="16" />
                      {{ t('log.realtime.clearFilter') }}
                    </button>
                  </div>
                </div>
              </transition>
            </div>

            <div class="toolbar-right">
              <div class="inline-status-group">
                <div class="hero-metric compact">
                  <span>{{ t('log.realtime.currentBuffer') }}</span>
                  <strong>{{ realtimeLogs.length }}</strong>
                </div>
                <div class="ws-status" :class="wsStatus">
                  <span class="ws-dot"></span>
                  <span>{{ wsStatusText }}</span>
                </div>
              </div>
              <div class="scroll-action-row">
                <button class="pill-action" :class="{ active: autoScroll }" @click="autoScroll = !autoScroll">
                  <Icon icon="material-symbols:vertical-align-bottom-rounded" width="18" height="18" />
                  {{ t('log.realtime.autoScroll') }}
                </button>
                <button
                  class="pill-action scroll-to-bottom-action"
                  :disabled="autoScroll || atBottom || filteredLogs.length === 0"
                  @click="autoScroll = true; scrollToBottom()"
                >
                  <Icon icon="material-symbols:arrow-downward-rounded" width="16" height="16" />
                  {{ t('log.realtime.backToBottom') }}
                </button>
              </div>
              <button class="icon-button" @click="clearLogs" :title="t('log.realtime.clearTitle')">
                <Icon icon="material-symbols:delete-outline-rounded" width="20" height="20" />
              </button>
              <button
                class="icon-button"
                @click="wsStatus === 'connected' ? disconnectWs() : connectWs()"
                :title="wsStatus === 'connected' ? t('log.realtime.disconnectTitle') : t('log.realtime.connectTitle')"
              >
                <Icon
                  :icon="wsStatus === 'connected' ? 'material-symbols:link-off-rounded' : 'material-symbols:link-rounded'"
                  width="20"
                  height="20"
                />
              </button>
            </div>
          </div>

          <div class="log-container" ref="logContainerRef" @scroll="handleRealtimeScroll">
            <div v-if="filteredLogs.length === 0" class="empty-state">
              <Icon icon="material-symbols:terminal-rounded" width="48" height="48" />
              <p>{{ wsStatus === 'connected' ? t('log.realtime.waitingLogs') : t('log.realtime.serviceDisconnected') }}</p>
            </div>
            <div v-else class="log-entries">
              <div
                v-for="(entry, idx) in filteredLogs"
                :key="`${entry.timestamp}-${idx}`"
                class="log-entry"
                :style="{ '--entry-level-color': levelColor(entry.level), '--entry-level-bg': levelBg(entry.level) }"
              >
                <span class="shell-prompt">❯</span>
                <span class="log-time">{{ formatTimestamp(entry.timestamp) }}</span>
                <span class="log-level-badge">{{ entry.level }}</span>
                <span class="log-logger">{{ entry.display || entry.logger_name || 'core' }}</span>
                <span class="log-message">{{ entry.message }}</span>
              </div>
            </div>
          </div>

          <div class="status-bar">
            <span>{{ t('log.realtime.totalSummary', { total: String(realtimeLogs.length), visible: String(filteredLogs.length) }) }}</span>
            <span v-if="lastRealtimeAt">{{ t('log.realtime.lastUpdated', { time: formatTimestamp(lastRealtimeAt) }) }}</span>
          </div>
        </section>
      </div>

      <div v-else class="history-section">
        <header class="history-mobile-top-bar">
          <div class="history-mobile-title">
            <button class="history-file-title-btn" type="button" @click="isMobileFileMenuOpen = !isMobileFileMenuOpen">
              <h3>{{ selectedFile || t('log.history.filesTitle') }}</h3>
              <Icon icon="material-symbols:expand-more-rounded" width="20" height="20" class="history-file-chevron" :class="{ open: isMobileFileMenuOpen }" />
            </button>
            <p>{{ historyProgressText }}</p>
          </div>
          <button class="icon-button" @click="loadLogFiles" :title="t('log.history.refreshTitle')">
            <Icon icon="material-symbols:refresh-rounded" width="18" height="18" />
          </button>
        </header>

        <button v-if="isMobileFileMenuOpen" class="history-mobile-menu-backdrop" type="button" aria-label="Close history file list" @click="isMobileFileMenuOpen = false"></button>
        <aside class="history-mobile-file-menu" :class="{ open: isMobileFileMenuOpen }" aria-label="history log files">
          <div class="panel-header">
            <div>
              <span class="panel-kicker">{{ t('log.history.archives') }}</span>
              <h3>{{ t('log.history.filesTitle') }}</h3>
            </div>
          </div>
          <label class="history-search-field file-search-field">
            <Icon icon="material-symbols:search-rounded" width="18" height="18" />
            <input v-model="fileSearchText" :placeholder="t('log.history.fileSearchPlaceholder')" />
          </label>
          <div v-if="filteredLogFiles.length === 0" class="empty-state small">
            <p>{{ logFiles.length === 0 ? t('log.history.emptyFiles') : t('log.history.noMatchedFiles') }}</p>
          </div>
          <div v-else class="file-list">
            <button
              v-for="file in filteredLogFiles"
              :key="file.filename"
              class="file-item"
              :class="{ active: selectedFile === file.filename }"
              @click="selectLogFile(file.filename)"
            >
              <div class="file-item-main">
                <Icon icon="material-symbols:description-outline-rounded" width="18" height="18" />
                <span class="file-name" :title="file.filename">{{ file.filename }}</span>
              </div>
              <div class="file-item-meta">
                <span>{{ formatFileSize(file.size) }}</span>
                <span>{{ formatTimestamp(file.modified_time) }}</span>
              </div>
            </button>
          </div>
        </aside>

        <div class="history-layout">
          <aside class="file-list-panel">
            <div class="panel-header">
              <div>
                <span class="panel-kicker">{{ t('log.history.archives') }}</span>
                <h3>{{ t('log.history.filesTitle') }}</h3>
              </div>
              <button class="icon-button" @click="loadLogFiles" :title="t('log.history.refreshTitle')">
                <Icon icon="material-symbols:refresh-rounded" width="18" height="18" />
              </button>
            </div>
            <label class="history-search-field file-search-field">
              <Icon icon="material-symbols:search-rounded" width="18" height="18" />
              <input v-model="fileSearchText" :placeholder="t('log.history.fileSearchPlaceholder')" />
            </label>
            <div v-if="filteredLogFiles.length === 0" class="empty-state small">
              <p>{{ logFiles.length === 0 ? t('log.history.emptyFiles') : t('log.history.noMatchedFiles') }}</p>
            </div>
            <div v-else class="file-list">
              <button
                v-for="file in filteredLogFiles"
                :key="file.filename"
                class="file-item"
                :class="{ active: selectedFile === file.filename }"
                @click="selectLogFile(file.filename)"
              >
                <div class="file-item-main">
                  <Icon icon="material-symbols:description-outline-rounded" width="18" height="18" />
                  <span class="file-name" :title="file.filename">{{ file.filename }}</span>
                </div>
                <div class="file-item-meta">
                  <span>{{ formatFileSize(file.size) }}</span>
                  <span>{{ formatTimestamp(file.modified_time) }}</span>
                </div>
              </button>
            </div>
          </aside>

          <main class="content-panel">
            <div v-if="!selectedFile" class="empty-state hero-empty">
              <Icon icon="material-symbols:folder-open-outline-rounded" width="54" height="54" />
              <p>{{ t('log.history.selectFileTitle') }}</p>
              <span>{{ t('log.history.selectFileHint') }}</span>
            </div>
            <template v-else>
              <div class="content-header">
                <div class="content-title-block">
                  <span class="panel-kicker">{{ t('log.history.viewer') }}</span>
                  <h3 :title="selectedFile">{{ selectedFile }}</h3>
                </div>
                <span class="content-meta">{{ historyProgressText }}</span>
              </div>

              <div class="history-toolbar">
                <label class="history-search-field">
                  <Icon icon="material-symbols:find_in_page-outline-rounded" width="18" height="18" />
                  <input v-model="historySearchText" :placeholder="t('log.history.contentSearchPlaceholder')" @keyup.enter="refreshHistorySearch" />
                </label>
                <button class="pill-action" @click="refreshHistorySearch">
                  <Icon icon="material-symbols:manage-search-rounded" width="18" height="18" />
                  {{ t('log.history.searchContent') }}
                </button>
              </div>

              <div class="history-content-wrap" ref="historyContainerRef" @scroll="handleHistoryScroll">
                <div v-if="historyLoading" class="empty-state">
                  <Icon icon="material-symbols:progress-activity-rounded" width="36" height="36" />
                  <p>{{ t('log.history.loadingContent') }}</p>
                </div>
                <template v-else>
                  <div v-if="historyLoadingPrev" class="load-sentinel">{{ t('log.history.loadingPrev') }}</div>
                  <div v-else-if="!historyHasPrev && historyLines.length > 0" class="load-sentinel muted">{{ t('log.history.fileStart') }}</div>

                  <div class="history-content">
                    <article
                      v-for="(entry, index) in historyEntries"
                      :key="`${entry.raw}-${index}`"
                      class="history-entry log-entry"
                      :class="`tone-${entry.tone}`"
                      :style="historyEntryStyle(entry)"
                    >
                      <span class="shell-prompt">❯</span>
                      <span class="log-time history-time">{{ entry.timestamp ? formatTimestamp(entry.timestamp) : '——:——:——' }}</span>
                      <span class="log-level-badge history-level">{{ entry.level }}</span>
                      <span class="log-logger history-source" :title="entry.source || 'core'">{{ entry.source || 'core' }}</span>
                      <code class="log-message history-message">
                        <template v-for="(part, partIndex) in visibleHistoryLineParts(entry)" :key="partIndex">
                          <mark v-if="part.hit">{{ part.text }}</mark>
                          <span v-else>{{ part.text }}</span>
                        </template>
                      </code>
                      <span v-for="badge in visibleHistoryBadges(entry)" :key="badge" class="history-badge">{{ badge }}</span>
                    </article>
                    <div v-if="historyEntries.length === 0" class="empty-state small">
                      <p>{{ t('log.history.noMatchedContent') }}</p>
                    </div>
                  </div>

                  <div v-if="historyLoadingNext" class="load-sentinel">{{ t('log.history.loadingNext') }}</div>
                  <div v-else-if="!historyHasNext && historyLines.length > 0" class="load-sentinel muted">{{ t('log.history.fileEnd') }}</div>
                </template>
              </div>
            </template>
          </main>
        </div>
      </div>
    </section>
  </AppShell>
</template>

<style scoped>
.log-page {
  --page-shadow: 0 18px 48px rgba(0, 0, 0, .08), 0 4px 18px rgba(0, 0, 0, .045), 0 1px 4px rgba(0, 0, 0, .035);
  --soft-border: color-mix(in srgb, var(--md-sys-color-outline-variant) 72%, transparent);
  --glass-surface: color-mix(in srgb, var(--md-sys-color-surface-container-lowest) 72%, transparent);
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
  min-height: 0;
  overflow: hidden;
  background: transparent;
}

h1,
h2,
h3,
p {
  margin: 0;
}

button,
input {
  font: inherit;
}

button:focus-visible,
input:focus-visible {
  outline: 2px solid var(--md-sys-color-primary);
  outline-offset: 2px;
}

.realtime-panel,
.history-layout {
  border: 0;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  box-shadow: none;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.panel-kicker {
  color: var(--md-sys-color-primary);
  font-size: .66rem;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.hero-metric,
.ws-status {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--soft-border);
  background: color-mix(in srgb, var(--md-sys-color-surface-container-lowest) 76%, transparent);
  box-shadow: 0 6px 14px rgba(0, 0, 0, .04);
}

.hero-metric {
  flex-direction: column;
  align-items: flex-start;
  gap: .02rem;
  padding: .38rem .56rem;
  border-radius: 13px;
}

.hero-metric span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: .64rem;
  font-weight: 700;
}

.hero-metric strong {
  color: var(--md-sys-color-on-surface);
  font-size: 1rem;
  line-height: 1;
}

.ws-status {
  gap: .38rem;
  padding: .44rem .62rem;
  border-radius: var(--md-sys-shape-corner-full);
  color: var(--md-sys-color-on-surface-variant);
  font-size: .74rem;
  font-weight: 700;
}

.ws-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--md-sys-color-outline);
  transition: background .25s, box-shadow .25s;
}

.ws-status.connected .ws-dot {
  background: #1aae39;
  box-shadow: 0 0 0 6px rgba(26, 174, 57, .12), 0 0 12px rgba(26, 174, 57, .6);
}

.ws-status.connecting .ws-dot {
  background: #dd5b00;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .45; transform: scale(.82); }
}

.tab-bar {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  flex-shrink: 0;
  z-index: 10;
  overflow-x: auto;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: .42rem;
  border: 0;
  border-radius: var(--md-sys-shape-corner-full);
  padding: .62rem 1.05rem;
  color: var(--md-sys-color-on-surface-variant);
  background: transparent;
  font-size: .9rem;
  font-weight: 800;
  cursor: pointer;
  transition: transform .18s ease, background .18s ease, color .18s ease;
}

.tab-item:hover {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--md-sys-color-primary) 8%, transparent);
}

.tab-item.active {
  color: var(--md-sys-color-on-primary);
  background: var(--md-sys-color-primary);
  box-shadow: 0 8px 18px color-mix(in srgb, var(--md-sys-color-primary) 26%, transparent);
}

.realtime-section,
.history-section {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  padding: 0;
}

.realtime-panel {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  gap: .6rem;
  padding: .65rem;
  border-radius: 0;
  overflow: hidden;
}

.control-card {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(160px, 220px) auto;
  align-items: center;
  gap: .55rem;
  padding: .1rem;
  flex-shrink: 0;
}

.search-field {
  display: flex;
  align-items: center;
  gap: .5rem;
  width: 100%;
  min-height: 42px;
  padding: .55rem .8rem;
  border: 1px solid var(--soft-border);
  border-radius: 14px;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--glass-surface);
  backdrop-filter: blur(6px);
}

.level-multiselect {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 42px;
}

.level-multiselect-trigger {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  min-height: 42px;
  width: 100%;
  padding: .35rem .72rem;
  border: 1px solid var(--soft-border);
  border-radius: 14px;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--glass-surface);
  backdrop-filter: blur(6px);
  cursor: pointer;
  transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
}

.level-multiselect-trigger:hover {
  border-color: color-mix(in srgb, var(--md-sys-color-primary) 38%, var(--soft-border));
  background: color-mix(in srgb, var(--md-sys-color-primary) 6%, var(--glass-surface));
}

.level-multiselect-trigger.open {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--md-sys-color-primary) 16%, transparent);
}

.level-multiselect-trigger.active {
  border-color: color-mix(in srgb, var(--md-sys-color-primary) 48%, var(--soft-border));
  background: color-mix(in srgb, var(--md-sys-color-primary-container) 42%, transparent);
}

.level-multiselect-label {
  flex: 0 0 auto;
  color: var(--md-sys-color-primary);
  font-size: .72rem;
  font-weight: 900;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.level-multiselect-value {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  color: var(--md-sys-color-on-surface);
  font-size: .9rem;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.level-multiselect-chevron {
  flex: 0 0 auto;
  color: var(--md-sys-color-on-surface-variant);
  transition: transform .18s ease;
}

.level-multiselect-chevron.open {
  transform: rotate(180deg);
}

.level-multiselect-panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 60;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 220px;
  padding: .42rem;
  border: 1px solid var(--soft-border);
  border-radius: 16px;
  background: var(--md-sys-color-surface-container-lowest);
  box-shadow: 0 12px 32px rgba(0, 0, 0, .12), 0 4px 12px rgba(0, 0, 0, .06);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.level-multiselect-option {
  display: flex;
  align-items: center;
  gap: .5rem;
  width: 100%;
  padding: .5rem .58rem;
  border: 0;
  border-radius: 10px;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  font-size: .86rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  transition: background .14s ease, color .14s ease;
}

.level-multiselect-option:hover {
  background: color-mix(in srgb, var(--md-sys-color-primary) 10%, transparent);
}

.level-multiselect-option.checked {
  color: var(--md-sys-color-on-surface);
  background: color-mix(in srgb, var(--md-sys-color-primary) 14%, transparent);
}

.level-multiselect-check {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: var(--md-sys-color-primary);
}

.level-multiselect-option-text {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.level-multiselect-option:not(:first-child) .level-multiselect-option-text {
  color: var(--option-level-color, var(--md-sys-color-on-surface));
  font-weight: 900;
}

.level-multiselect-count {
  flex: 0 0 auto;
  padding: .04rem .42rem;
  border-radius: 999px;
  color: var(--md-sys-color-on-surface-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 72%, transparent);
  font-size: .72rem;
  font-weight: 800;
}

.level-multiselect-footer {
  display: flex;
  justify-content: flex-end;
  padding: .32rem .2rem .12rem;
  margin-top: .2rem;
  border-top: 1px solid var(--soft-border);
}

.level-multiselect-clear {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  padding: .32rem .58rem;
  border: 0;
  border-radius: 999px;
  color: var(--md-sys-color-primary);
  background: color-mix(in srgb, var(--md-sys-color-primary) 10%, transparent);
  font-size: .76rem;
  font-weight: 800;
  cursor: pointer;
  transition: background .14s ease;
}

.level-multiselect-clear:hover {
  background: color-mix(in srgb, var(--md-sys-color-primary) 18%, transparent);
}

.level-dropdown-enter-active,
.level-dropdown-leave-active {
  transition: opacity .16s ease, transform .16s ease;
}

.level-dropdown-enter-from,
.level-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(.98);
}

.search-field input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  font-size: .9rem;
}

.search-field input::placeholder {
  color: color-mix(in srgb, var(--md-sys-color-on-surface-variant) 72%, transparent);
}

.toolbar-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: .45rem;
  flex-wrap: nowrap;
}

.inline-status-group {
  display: inline-flex;
  align-items: center;
  gap: .38rem;
  flex: 0 0 auto;
}

.hero-metric.compact {
  min-height: 40px;
  padding: .32rem .58rem;
}

.scroll-action-row {
  display: inline-flex;
  align-items: center;
  gap: .38rem;
  flex: 0 0 auto;
}

.icon-button,
.pill-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  cursor: pointer;
  transition: transform .16s ease, background .16s ease, color .16s ease;
}

.icon-button {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  color: var(--md-sys-color-on-surface-variant);
  background: transparent;
}

.icon-button:hover,
.pill-action:hover:not(:disabled) {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--md-sys-color-primary) 10%, transparent);
}

.icon-button.active,
.pill-action.active {
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
}

.pill-action {
  gap: .4rem;
  min-height: 40px;
  padding: 0 .85rem;
  border-radius: var(--md-sys-shape-corner-full);
  color: var(--md-sys-color-on-surface-variant);
  background: transparent;
  font-size: .82rem;
  font-weight: 800;
}

.pill-action:disabled {
  color: color-mix(in srgb, var(--md-sys-color-on-surface-variant) 48%, transparent);
  background: color-mix(in srgb, var(--md-sys-color-outline-variant) 28%, transparent);
  cursor: not-allowed;
  opacity: .72;
}

.scroll-to-bottom-action {
  white-space: nowrap;
}

.log-container {
  flex: 1 1 0;
  min-height: 0;
  height: 100%;
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid color-mix(in srgb, var(--md-sys-color-primary) 18%, var(--soft-border));
  border-radius: 22px;
  background:
    radial-gradient(circle at 12% 0%, color-mix(in srgb, var(--md-sys-color-primary) 16%, transparent), transparent 32%),
    linear-gradient(180deg, color-mix(in srgb, var(--md-sys-color-surface-container-lowest) 62%, transparent), color-mix(in srgb, var(--md-sys-color-surface-container-low) 54%, transparent));
  color: var(--md-sys-color-on-surface);
  scroll-behavior: smooth;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .2), 0 10px 28px rgba(0, 0, 0, .05);
  backdrop-filter: blur(10px) saturate(1.08);
  -webkit-backdrop-filter: blur(10px) saturate(1.08);
}

.log-entry {
  display: flex;
  align-items: baseline;
  gap: .5rem;
  font-family: Inter, 'Noto Sans SC', system-ui, sans-serif;
  font-size: 12.5px;
  line-height: 1.32;
}

.shell-prompt {
  color: var(--md-sys-color-primary);
  font-weight: 900;
}

.log-entries {
  display: flex;
  flex-direction: column;
  gap: .15rem;
  padding: .55rem;
}

.log-entry {
  padding: .22rem .42rem;
  border-radius: 12px;
  background: var(--entry-level-bg);
  transition: background .12s ease, transform .12s ease;
}

.log-entry:hover {
  transform: translateX(2px);
  background: color-mix(in srgb, var(--entry-level-color) 13%, transparent);
}

.shell-prompt {
  flex: 0 0 auto;
}

.log-time {
  flex: 0 0 auto;
  color: color-mix(in srgb, var(--md-sys-color-on-surface-variant) 74%, transparent);
  font-size: 11.5px;
  font-weight: 700;
  white-space: nowrap;
}

.log-level-badge {
  flex: 0 0 66px;
  width: 66px;
  color: var(--entry-level-color);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .04em;
  white-space: nowrap;
}

.log-logger {
  flex: 0 0 160px;
  width: 160px;
  min-width: 0;
  color: var(--md-sys-color-primary);
  font-size: 11.5px;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-message {
  min-width: 0;
  color: var(--md-sys-color-on-surface);
  word-break: break-word;
  white-space: pre-wrap;
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .65rem;
  min-height: 26px;
  padding: 0 .28rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: .76rem;
  flex-shrink: 0;
}

.scroll-hint {
  gap: .3rem;
  padding: .38rem .7rem;
  border-radius: 999px;
  color: var(--md-sys-color-primary);
  background: transparent;
  font-weight: 800;
}

.empty-state {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .65rem;
  padding: 2rem;
  color: var(--md-sys-color-on-surface-variant);
  text-align: center;
}

.log-container .empty-state {
  color: var(--md-sys-color-on-surface-variant);
}

.empty-state.small {
  min-height: 90px;
  padding: 1rem;
}

.hero-empty span {
  max-width: 24rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: .86rem;
}

.history-mobile-top-bar,
.history-mobile-menu-backdrop,
.history-mobile-file-menu {
  display: none;
}

.history-layout {
  display: grid;
  grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
  flex: 1;
  min-height: 0;
  border-radius: 0;
  overflow: hidden;
}

.file-list-panel {
  border-right: 1px solid var(--soft-border);
  padding: .85rem;
  overflow-y: auto;
  min-height: 0;
}

.panel-header,
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-width: 0;
}

.panel-header {
  margin-bottom: .85rem;
}

.content-title-block {
  flex: 1 1 auto;
  min-width: 0;
  max-width: 100%;
}

.panel-header h3,
.content-header h3 {
  color: var(--md-sys-color-on-surface);
  font-size: 1.08rem;
  font-weight: 900;
  letter-spacing: -.02em;
}

.content-header h3 {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: .45rem;
}

.file-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: .35rem;
  padding: .82rem;
  border: 1px solid transparent;
  border-radius: 16px;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: transform .16s ease, background .16s ease, border-color .16s ease;
}

.file-item:hover,
.file-item.active {
  border-color: color-mix(in srgb, var(--md-sys-color-primary) 28%, var(--soft-border));
  background: color-mix(in srgb, var(--md-sys-color-primary-container) 44%, transparent);
}

.file-item:hover {
  transform: translateY(-1px);
}

.file-item-main {
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: .5rem;
}

.file-item-main .iconify {
  flex: 0 0 auto;
}

.file-name {
  min-width: 0;
  overflow: hidden;
  font-size: .86rem;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: .45rem .8rem;
  padding-left: 1.65rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: .72rem;
}

.content-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: .7rem;
  padding: .85rem;
}

.content-meta {
  flex-shrink: 0;
  padding: .32rem .68rem;
  border-radius: 999px;
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
  font-size: .78rem;
  font-weight: 800;
}

.history-toolbar {
  display: flex;
  align-items: center;
  gap: .55rem;
}

.history-search-field {
  display: flex;
  align-items: center;
  gap: .5rem;
  min-height: 40px;
  padding: .48rem .72rem;
  border: 1px solid var(--soft-border);
  border-radius: 14px;
  color: var(--md-sys-color-on-surface-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface-container-lowest) 68%, transparent);
}

.file-search-field {
  margin-bottom: .75rem;
}

.history-search-field input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  font-size: .86rem;
}

.history-content-wrap {
  flex: 1 1 0;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid color-mix(in srgb, var(--md-sys-color-primary) 16%, var(--soft-border));
  border-radius: 20px;
  background:
    radial-gradient(circle at 14% 0%, color-mix(in srgb, var(--md-sys-color-primary) 12%, transparent), transparent 34%),
    color-mix(in srgb, var(--md-sys-color-surface-container-lowest) 66%, transparent);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .2), 0 10px 28px rgba(0, 0, 0, .045);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.history-content {
  min-height: 100%;
  margin: 0;
  padding: .55rem;
  color: var(--md-sys-color-on-surface);
  font-family: Inter, 'Noto Sans SC', system-ui, sans-serif;
  font-size: 12.5px;
  line-height: 1.32;
}

.history-entry {
  border-left: 3px solid var(--history-entry-color);
}

.history-entry + .history-entry {
  margin-top: .22rem;
}

.history-level,
.history-badge,
.history-source {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  padding: .12rem .42rem;
  border-radius: 999px;
  font-family: Inter, 'Noto Sans SC', system-ui, sans-serif;
  font-size: .68rem;
  font-weight: 900;
  line-height: 1.4;
  white-space: nowrap;
}

.history-level {
  justify-content: center;
}

.history-source {
  justify-content: flex-start;
}

.history-level {
  color: var(--history-entry-color);
  background: color-mix(in srgb, var(--history-entry-color) 12%, transparent);
}

.history-badge {
  flex: 0 0 auto;
  color: var(--md-sys-color-on-surface-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 72%, transparent);
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-time {
  color: color-mix(in srgb, var(--md-sys-color-on-surface-variant) 78%, transparent);
  font-family: Inter, 'Noto Sans SC', system-ui, sans-serif;
  font-size: .7rem;
  font-weight: 700;
}

.history-message {
  min-width: 0;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  font: inherit;
  white-space: pre-wrap;
  word-break: break-word;
}

.history-message mark {
  border-radius: 5px;
  padding: .02rem .12rem;
  color: var(--md-sys-color-on-tertiary-container);
  background: var(--md-sys-color-tertiary-container);
}

.load-sentinel {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  color: var(--md-sys-color-primary);
  background: color-mix(in srgb, var(--md-sys-color-primary) 8%, transparent);
  font-size: .78rem;
  font-weight: 800;
}

.load-sentinel.muted {
  color: var(--md-sys-color-on-surface-variant);
  background: transparent;
}

@media (max-width: 1180px) {
  .control-card {
    grid-template-columns: minmax(220px, 1fr) minmax(160px, 220px);
  }

  .toolbar-right {
    grid-column: 1 / -1;
    justify-content: space-between;
  }
}

@media (max-width: 1100px) {
  .history-mobile-top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 10px 16px;
    border-bottom: 1px solid var(--soft-border);
    background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    flex-shrink: 0;
    z-index: 10;
  }

  .history-mobile-title {
    min-width: 0;
  }

  .history-file-title-btn {
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

  .history-file-title-btn h3 {
    overflow: hidden;
    margin: 0;
    font-size: 1rem;
    font-weight: 900;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .history-file-chevron {
    color: var(--md-sys-color-on-surface-variant);
    transition: transform .18s ease;
    flex: 0 0 auto;
  }

  .history-file-chevron.open {
    transform: rotate(180deg);
  }

  .history-mobile-title p {
    overflow: hidden;
    margin: 0;
    color: var(--md-sys-color-on-surface-variant);
    font-size: .76rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .history-mobile-menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 70;
    display: block;
    border: 0;
    background: rgba(0, 0, 0, .32);
    animation: fade-in .15s ease;
  }

  .history-mobile-file-menu {
    position: fixed;
    top: 4.5rem;
    left: .75rem;
    right: .75rem;
    z-index: 80;
    display: block;
    max-height: min(76vh, 620px);
    overflow: auto;
    padding: 1rem;
    border: 1px solid var(--soft-border);
    border-radius: 20px;
    background: var(--md-sys-color-surface);
    box-shadow: 0 8px 32px rgba(0, 0, 0, .12), 0 2px 8px rgba(0, 0, 0, .08);
    transform: translateY(-12px) scale(.98);
    opacity: 0;
    pointer-events: none;
    transition: transform .18s ease, opacity .18s ease;
  }

  .history-mobile-file-menu.open {
    transform: translateY(0) scale(1);
    opacity: 1;
    pointer-events: auto;
  }

  .history-layout {
    display: flex;
    overflow: hidden;
  }

  .file-list-panel {
    display: none;
  }

  .content-panel {
    flex: 1 1 0;
    min-height: 0;
    max-height: none;
  }
}

@media (max-width: 820px) {
  .control-card {
    grid-template-columns: 1fr;
    gap: .4rem;
  }

  .search-field,
  .level-multiselect {
    min-height: 38px;
  }

  .search-field {
    padding-inline: .58rem;
    border-radius: 12px;
  }

  .level-multiselect-trigger {
    min-height: 38px;
    padding-inline: .58rem;
    border-radius: 12px;
    gap: .38rem;
  }

  .level-multiselect-label {
    font-size: .66rem;
  }

  .level-multiselect-value,
  .search-field input {
    font-size: .82rem;
  }

  .toolbar-right,
  .scroll-action-row {
    gap: .28rem;
  }

  .pill-action {
    min-height: 36px;
    padding-inline: .58rem;
    font-size: .74rem;
  }

  .icon-button {
    width: 36px;
    height: 36px;
    border-radius: 12px;
  }
}

@media (max-width: 760px) {
  .log-page {
    height: auto;
    min-height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
    overflow: visible;
  }

  .realtime-section,
  .history-section {
    padding: 0;
  }

  .hero-metric,
  .ws-status {
    flex: 0 0 auto;
  }

  .tab-bar {
    padding: 12px;
  }

  .tab-item {
    flex: 1;
    justify-content: center;
    padding-inline: .7rem;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .65rem;
  }

  .control-card {
    grid-template-columns: 1fr;
    align-items: stretch;
    gap: .45rem;
  }

  .search-field,
  .level-multiselect {
    width: auto;
    min-height: 38px;
  }

  .toolbar-right {
    justify-content: stretch;
    width: 100%;
    flex-wrap: wrap;
  }

  .inline-status-group {
    width: 100%;
  }

  .scroll-action-row {
    flex: 1 1 auto;
    min-width: 0;
  }

  .toolbar-right .pill-action,
  .toolbar-right .icon-button {
    background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 72%, transparent);
  }

  .toolbar-right .pill-action {
    flex: 1 1 0;
    min-width: 0;
    padding-inline: .48rem;
    font-size: .72rem;
  }

  .toolbar-right .icon-button {
    flex: 0 0 38px;
    width: 38px;
    height: 38px;
  }

  .icon-button:hover,
  .pill-action:hover:not(:disabled),
  .scroll-action-row .pill-action:hover:not(:disabled),
  .file-item:hover,
  .tab-item:hover,
  .log-entry:hover {
    transform: none;
  }

  .toolbar-right .pill-action:hover:not(:disabled),
  .toolbar-right .icon-button:hover {
    background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 72%, transparent);
  }

  .toolbar-right .pill-action:disabled:hover {
    background: color-mix(in srgb, var(--md-sys-color-outline-variant) 28%, transparent);
  }

  .toolbar-right .pill-action.active:hover:not(:disabled) {
    background: var(--md-sys-color-primary-container);
  }

  .realtime-panel {
    min-height: 0;
  }

  .log-container {
    min-height: 0;
    flex: 1;
    border-radius: 18px;
  }

  .shell-command-line,
  .log-entry {
    flex-wrap: wrap;
    gap: .18rem .5rem;
  }

  .log-entry {
    padding: .28rem .2rem;
  }

  .log-logger {
    max-width: 100%;
  }

  .log-entry .log-logger,
  .history-entry .history-source {
    flex: 0 1 8rem;
    width: auto;
    max-width: min(100%, 12rem);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .content-header,
  .history-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .history-entry {
    display: flex;
    flex-direction: row;
    align-items: baseline;
    flex-wrap: wrap;
    gap: .12rem .38rem;
    padding: .22rem .34rem;
    border-left-width: 2px;
  }

  .history-entry .history-badge {
    display: none;
  }

  .history-entry .log-time {
    max-width: 5.6rem;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .history-entry .log-level-badge {
    min-width: 4.25rem;
  }

  .history-entry .history-source {
    flex: 0 1 7.2rem;
    max-width: 7.2rem;
  }

  .history-entry .history-message {
    flex: 1 1 100%;
    padding-left: .2rem;
    line-height: 1.38;
  }

  .history-content-wrap {
    min-height: 54dvh;
    max-height: none;
  }

  .status-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .history-layout {
    min-height: 0;
    border-radius: 0;
  }

  .content-panel,
  .file-list-panel {
    padding: .85rem;
  }

  .content-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .history-content-wrap {
    height: 440px;
    min-height: 0;
    flex: 0 0 auto;
  }
}

@media (max-width: 460px) {
  .toolbar-right {
    width: 100%;
  }

  .hero-metric,
  .ws-status {
    flex: 1;
  }

  .realtime-panel,
  .history-layout {
    border-radius: 0;
  }

  .realtime-panel,
  .content-panel,
  .file-list-panel {
    padding: .6rem;
  }

  .history-content-wrap {
    height: 360px;
  }
}

@media (max-width: 425px) {
  .log-container {
    height: clamp(260px, 46dvh, 340px);
    min-height: 0;
    flex: 0 0 auto;
  }
}

@media (max-width: 360px) {
  .toolbar-right .pill-action {
    padding-inline: .34rem;
    font-size: .68rem;
  }

  .toolbar-right .icon-button {
    flex-basis: 34px;
    width: 34px;
    height: 34px;
  }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>

