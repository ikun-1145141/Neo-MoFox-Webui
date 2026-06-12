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
import { getLogFiles, getLogContent } from '../api/modules/log'
import { API_BASE_URL } from '../api/config'
import type { RealtimeLogEntry, LogFileInfo, LogContentResponse } from '../api/types/log'

type WsStatus = 'disconnected' | 'connecting' | 'connected'
type HistoryLoadMode = 'replace' | 'prepend' | 'append'
type HistoryMeta = Omit<LogContentResponse, 'content'>

const toastStore = useToastStore()

const activeTab = ref<'realtime' | 'history'>('realtime')

const realtimeLogs = ref<RealtimeLogEntry[]>([])
const wsStatus = ref<WsStatus>('disconnected')
const autoScroll = ref(true)
const searchText = ref('')
const selectedLevels = ref<Set<string>>(new Set())
const logContainerRef = ref<HTMLElement | null>(null)
const lastRealtimeAt = ref<string>('')
const maxLogEntries = 2000

const logFiles = ref<LogFileInfo[]>([])
const selectedFile = ref<string>('')
const historyLines = ref<string[]>([])
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
  return realtimeLogs.value.filter((entry) => {
    if (selectedLevels.value.size > 0 && !selectedLevels.value.has(entry.level.toUpperCase())) {
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

const wsStatusText = computed(() => {
  if (wsStatus.value === 'connected') return '实时连接已建立'
  if (wsStatus.value === 'connecting') return '正在连接日志流'
  return '日志流已断开'
})

const historyProgressText = computed(() => {
  const meta = historyMeta.value
  if (!meta) return '未加载日志内容'
  const loadedSize = Math.max(0, historyEndOffset.value - historyStartOffset.value)
  return `${formatFileSize(loadedSize)} / ${formatFileSize(meta.total_size)}`
})

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
    toastStore.show('实时日志连接异常，请检查后端服务', 'error')
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
    const levels = selectedLevels.value.size > 0 ? Array.from(selectedLevels.value) : null
    ws.send(JSON.stringify({ type: 'set_level_filter', levels }))
  }
}

function toggleLevel(level: string): void {
  if (selectedLevels.value.has(level)) {
    selectedLevels.value.delete(level)
  } else {
    selectedLevels.value.add(level)
  }
  selectedLevels.value = new Set(selectedLevels.value)
  sendLevelFilter()
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
  autoScroll.value = isNearBottom(container)
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
    toastStore.show('获取日志文件列表失败', 'error')
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
    const data = await getLogContent(filename, offset, historyChunkLimit)
    applyHistoryChunk(data, mode)

    await nextTick()
    if (!historyContainerRef.value) return

    if (mode === 'prepend') {
      historyContainerRef.value.scrollTop = historyContainerRef.value.scrollHeight - previousScrollHeight + previousScrollTop
    } else if (mode === 'replace') {
      historyContainerRef.value.scrollTop = 0
    }
  } catch {
    toastStore.show('获取日志内容失败', 'error')
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
    historyStartOffset.value = data.offset
    historyEndOffset.value = data.next_offset
  } else if (mode === 'prepend') {
    historyLines.value = [...data.content, ...historyLines.value]
    historyStartOffset.value = data.offset
  } else {
    historyLines.value = [...historyLines.value, ...data.content]
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
  historyLines.value = []
  historyMeta.value = null
  historyStartOffset.value = 0
  historyEndOffset.value = 0
  historyHasPrev.value = false
  historyHasNext.value = false
  loadedHistoryOffsets.value = new Set()
  loadFileContent(filename)
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
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ts
  }
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
})

onUnmounted(() => {
  disconnectWs()
})
</script>

<template>
  <AppShell>
    <section class="log-page">
      <header class="hero-card">
        <div class="hero-copy">
          <span class="eyebrow">SYSTEM OBSERVABILITY</span>
          <h1>日志查看器</h1>
          <p>实时追踪运行状态，快速检索历史日志，并通过滚动无缝加载上下文。</p>
        </div>
        <div class="hero-actions">
          <div class="hero-metric">
            <span>当前缓冲</span>
            <strong>{{ realtimeLogs.length }}</strong>
          </div>
          <div class="ws-status" :class="wsStatus">
            <span class="ws-dot"></span>
            <span>{{ wsStatusText }}</span>
          </div>
        </div>
      </header>

      <div class="tab-bar" role="tablist" aria-label="日志模式">
        <button class="tab-item" :class="{ active: activeTab === 'realtime' }" @click="activeTab = 'realtime'">
          <Icon icon="material-symbols:stream-rounded" width="18" height="18" />
          <span>实时日志</span>
        </button>
        <button class="tab-item" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
          <Icon icon="material-symbols:folder-open-outline-rounded" width="18" height="18" />
          <span>历史日志</span>
        </button>
      </div>

      <div v-if="activeTab === 'realtime'" class="realtime-section">
        <div class="stat-grid">
          <button
            v-for="level in LOG_LEVELS"
            :key="level"
            class="stat-card mini"
            :class="{ selected: selectedLevels.has(level) }"
            :style="{ '--level-accent': levelColor(level), '--level-tint': levelBg(level) }"
            @click="toggleLevel(level)"
          >
            <span class="stat-level">{{ level }}</span>
            <strong>{{ logStats[level] || 0 }}</strong>
          </button>
        </div>

        <div class="control-card">
          <label class="search-field">
            <Icon icon="material-symbols:search-rounded" width="19" height="19" />
            <input v-model="searchText" placeholder="搜索消息、来源或显示名..." />
          </label>
          <div class="toolbar-right">
            <button class="pill-action" :class="{ active: autoScroll }" @click="autoScroll = !autoScroll">
              <Icon icon="material-symbols:vertical-align-bottom-rounded" width="18" height="18" />
              自动滚动
            </button>
            <button class="icon-button" @click="clearLogs" title="清空日志">
              <Icon icon="material-symbols:delete-outline-rounded" width="20" height="20" />
            </button>
            <button
              class="icon-button"
              @click="wsStatus === 'connected' ? disconnectWs() : connectWs()"
              :title="wsStatus === 'connected' ? '断开' : '连接'"
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
          <div class="terminal-topbar">
            <div class="traffic-lights">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>{{ wsStatus === 'connected' ? 'Live stream' : 'Stream paused' }}</span>
          </div>

          <div v-if="filteredLogs.length === 0" class="empty-state">
            <Icon icon="material-symbols:terminal-rounded" width="48" height="48" />
            <p>{{ wsStatus === 'connected' ? '等待新的日志输出...' : '实时日志服务未连接' }}</p>
          </div>
          <div v-else class="log-entries">
            <div
              v-for="(entry, idx) in filteredLogs"
              :key="`${entry.timestamp}-${idx}`"
              class="log-entry"
              :style="{ '--entry-level-color': levelColor(entry.level), '--entry-level-bg': levelBg(entry.level) }"
            >
              <span class="log-time">{{ entry.timestamp }}</span>
              <span class="log-level-badge">{{ entry.level }}</span>
              <span class="log-logger">{{ entry.display || entry.logger_name || 'core' }}</span>
              <span class="log-message">{{ entry.message }}</span>
            </div>
          </div>
        </div>

        <div class="status-bar">
          <span>共 {{ realtimeLogs.length }} 条 · 显示 {{ filteredLogs.length }} 条</span>
          <span v-if="lastRealtimeAt">最后更新 {{ lastRealtimeAt }}</span>
          <button v-if="!autoScroll" class="scroll-hint" @click="autoScroll = true; scrollToBottom()">
            <Icon icon="material-symbols:arrow-downward-rounded" width="14" height="14" />
            回到底部
          </button>
        </div>
      </div>

      <div v-else class="history-section">
        <div class="history-layout">
          <aside class="file-list-panel">
            <div class="panel-header">
              <div>
                <span class="panel-kicker">Archives</span>
                <h3>日志文件</h3>
              </div>
              <button class="icon-button" @click="loadLogFiles" title="刷新">
                <Icon icon="material-symbols:refresh-rounded" width="18" height="18" />
              </button>
            </div>
            <div v-if="logFiles.length === 0" class="empty-state small">
              <p>暂无日志文件</p>
            </div>
            <div v-else class="file-list">
              <button
                v-for="file in logFiles"
                :key="file.filename"
                class="file-item"
                :class="{ active: selectedFile === file.filename }"
                @click="selectLogFile(file.filename)"
              >
                <div class="file-item-main">
                  <Icon icon="material-symbols:description-outline-rounded" width="18" height="18" />
                  <span class="file-name">{{ file.filename }}</span>
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
              <p>选择一个日志文件查看内容</p>
              <span>选中文件后，在内容区域上下滚动即可自动加载更多。</span>
            </div>
            <template v-else>
              <div class="content-header">
                <div>
                  <span class="panel-kicker">History viewer</span>
                  <h3>{{ selectedFile }}</h3>
                </div>
                <span class="content-meta">{{ historyProgressText }}</span>
              </div>

              <div class="history-content-wrap" ref="historyContainerRef" @scroll="handleHistoryScroll">
                <div v-if="historyLoading" class="empty-state">
                  <Icon icon="material-symbols:progress-activity-rounded" width="36" height="36" />
                  <p>正在加载日志内容...</p>
                </div>
                <template v-else>
                  <div v-if="historyLoadingPrev" class="load-sentinel">正在加载上方内容...</div>
                  <div v-else-if="!historyHasPrev && historyLines.length > 0" class="load-sentinel muted">已到达文件开头</div>

                  <pre class="history-content">{{ historyLines.join('\n') }}</pre>

                  <div v-if="historyLoadingNext" class="load-sentinel">正在加载下方内容...</div>
                  <div v-else-if="!historyHasNext && historyLines.length > 0" class="load-sentinel muted">已到达文件末尾</div>
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
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
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

.hero-card,
.control-card,
.log-container,
.history-layout,
.stat-card {
  border: 1px solid var(--soft-border);
  background: linear-gradient(145deg, color-mix(in srgb, var(--md-sys-color-surface-container-lowest) 92%, transparent), color-mix(in srgb, var(--md-sys-color-surface-container-low) 88%, transparent));
  box-shadow: var(--page-shadow);
  backdrop-filter: blur(18px) saturate(1.08);
  -webkit-backdrop-filter: blur(18px) saturate(1.08);
}

.hero-card {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  gap: 1.2rem;
  padding: clamp(1.25rem, 3vw, 2rem);
  border-radius: var(--md-sys-shape-corner-extra-large);
  overflow: hidden;
}

.hero-card::before {
  content: '';
  position: absolute;
  inset: -40% auto auto 58%;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--md-sys-color-primary) 28%, transparent), transparent 68%);
  pointer-events: none;
}

.hero-copy,
.hero-actions {
  position: relative;
  z-index: 1;
}

.eyebrow,
.panel-kicker {
  color: var(--md-sys-color-primary);
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

h1 {
  margin-top: .35rem;
  color: var(--md-sys-color-on-surface);
  font-size: clamp(2rem, 4.6vw, 3.65rem);
  line-height: .98;
  letter-spacing: -.055em;
}

.hero-copy p {
  max-width: 38rem;
  margin-top: .7rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 1rem;
  line-height: 1.65;
}

.hero-actions {
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  gap: .75rem;
  flex-wrap: wrap;
  min-width: 220px;
}

.hero-metric,
.ws-status {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--soft-border);
  background: color-mix(in srgb, var(--md-sys-color-surface-container-lowest) 76%, transparent);
  box-shadow: 0 8px 20px rgba(0, 0, 0, .045);
}

.hero-metric {
  flex-direction: column;
  align-items: flex-start;
  gap: .1rem;
  padding: .7rem .9rem;
  border-radius: 18px;
}

.hero-metric span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: .72rem;
  font-weight: 700;
}

.hero-metric strong {
  color: var(--md-sys-color-on-surface);
  font-size: 1.6rem;
  line-height: 1;
}

.ws-status {
  gap: .5rem;
  padding: .62rem .9rem;
  border-radius: var(--md-sys-shape-corner-full);
  color: var(--md-sys-color-on-surface-variant);
  font-size: .86rem;
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
  display: inline-flex;
  align-self: flex-start;
  gap: .28rem;
  padding: .32rem;
  border: 1px solid var(--soft-border);
  border-radius: var(--md-sys-shape-corner-full);
  background: color-mix(in srgb, var(--md-sys-color-surface-container-high) 88%, transparent);
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
  flex-direction: column;
  gap: 1rem;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: .8rem;
}

.stat-card.mini {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: .3rem;
  min-height: 86px;
  padding: .85rem;
  border-radius: 20px;
  color: var(--md-sys-color-on-surface);
  cursor: pointer;
  overflow: hidden;
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}

.stat-card.mini::after {
  content: '';
  position: absolute;
  inset: auto .8rem .8rem auto;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: var(--level-tint);
}

.stat-card.mini:hover {
  transform: translateY(-2px);
}

.stat-card.mini.selected {
  border-color: var(--level-accent);
  background: linear-gradient(145deg, var(--level-tint), color-mix(in srgb, var(--md-sys-color-surface-container-lowest) 82%, transparent));
}

.stat-level {
  position: relative;
  z-index: 1;
  color: var(--level-accent);
  font-size: .72rem;
  font-weight: 900;
  letter-spacing: .08em;
}

.stat-card.mini strong {
  position: relative;
  z-index: 1;
  color: var(--md-sys-color-on-surface);
  font-size: 1.72rem;
  line-height: 1;
}

.control-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
  padding: .75rem;
  border-radius: 22px;
}

.search-field {
  display: flex;
  align-items: center;
  gap: .55rem;
  width: min(100%, 460px);
  padding: .72rem .9rem;
  border: 1px solid var(--soft-border);
  border-radius: 16px;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container-lowest);
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
  flex-wrap: wrap;
}

.icon-button,
.pill-action,
.scroll-hint {
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
.pill-action:hover,
.scroll-hint:hover {
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

.log-container {
  min-height: 430px;
  max-height: calc(100vh - 420px);
  overflow: auto;
  border-radius: 24px;
  background: linear-gradient(180deg, #111318, #17191f);
  color: #e8e8ef;
  scroll-behavior: smooth;
}

.terminal-topbar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: .62rem .85rem;
  border-bottom: 1px solid rgba(255, 255, 255, .08);
  background: rgba(17, 19, 24, .88);
  backdrop-filter: blur(14px);
  color: rgba(255, 255, 255, .56);
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.traffic-lights {
  display: inline-flex;
  gap: .4rem;
}

.traffic-lights span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.traffic-lights span:nth-child(1) { background: #ff5f56; }
.traffic-lights span:nth-child(2) { background: #ffbd2e; }
.traffic-lights span:nth-child(3) { background: #27c93f; }

.log-entries {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: .65rem;
}

.log-entry {
  display: grid;
  grid-template-columns: minmax(132px, auto) auto minmax(112px, 180px) minmax(0, 1fr);
  gap: .65rem;
  align-items: baseline;
  padding: .48rem .62rem;
  border-left: 3px solid transparent;
  border-radius: 12px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: .8rem;
  line-height: 1.55;
  transition: background .15s ease, border-color .15s ease;
}

.log-entry:hover {
  border-left-color: var(--entry-level-color);
  background: color-mix(in srgb, var(--entry-level-bg) 76%, rgba(255, 255, 255, .04));
}

.log-time {
  color: rgba(255, 255, 255, .46);
  font-size: .72rem;
  white-space: nowrap;
}

.log-level-badge {
  min-width: 58px;
  padding: .12rem .45rem;
  border-radius: 999px;
  color: var(--entry-level-color);
  background: var(--entry-level-bg);
  font-size: .68rem;
  font-weight: 900;
  text-align: center;
  white-space: nowrap;
}

.log-logger {
  color: #62aef0;
  font-size: .74rem;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-message {
  color: rgba(255, 255, 255, .9);
  word-break: break-word;
  white-space: pre-wrap;
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
  min-height: 34px;
  padding: 0 .3rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: .8rem;
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
  color: rgba(255, 255, 255, .58);
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

.history-layout {
  display: grid;
  grid-template-columns: minmax(260px, 340px) minmax(0, 1fr);
  min-height: 58vh;
  border-radius: var(--md-sys-shape-corner-extra-large);
  overflow: hidden;
}

.file-list-panel {
  border-right: 1px solid var(--soft-border);
  padding: 1rem;
  overflow-y: auto;
  max-height: calc(100vh - 310px);
}

.panel-header,
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.panel-header {
  margin-bottom: .85rem;
}

.panel-header h3,
.content-header h3 {
  color: var(--md-sys-color-on-surface);
  font-size: 1.08rem;
  font-weight: 900;
  letter-spacing: -.02em;
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
  display: flex;
  align-items: center;
  gap: .5rem;
}

.file-name {
  font-size: .86rem;
  font-weight: 800;
  word-break: break-all;
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
  display: flex;
  flex-direction: column;
  gap: .9rem;
  padding: 1.1rem;
  max-height: calc(100vh - 310px);
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

.history-content-wrap {
  flex: 1;
  min-height: 420px;
  overflow: auto;
  border: 1px solid var(--soft-border);
  border-radius: 20px;
  background: var(--md-sys-color-surface-container-lowest);
}

.history-content {
  min-height: 100%;
  margin: 0;
  padding: 1rem;
  color: var(--md-sys-color-on-surface);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: .8rem;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
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

@media (max-width: 1100px) {
  .history-layout {
    display: flex;
    flex-direction: column;
  }

  .file-list-panel {
    border-right: 0;
    border-bottom: 1px solid var(--soft-border);
    max-height: 220px;
  }

  .content-panel {
    max-height: none;
  }
}

@media (max-width: 760px) {
  .hero-card {
    flex-direction: column;
    border-radius: 22px;
  }

  .hero-actions {
    justify-content: flex-start;
  }

  .tab-bar {
    align-self: stretch;
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
    flex-direction: column;
    align-items: stretch;
  }

  .search-field {
    width: auto;
  }

  .toolbar-right {
    justify-content: flex-end;
  }

  .log-container {
    min-height: 330px;
    max-height: calc(100vh - 470px);
    border-radius: 18px;
  }

  .log-entry {
    grid-template-columns: 1fr;
    gap: .18rem;
    padding: .62rem .65rem;
  }

  .log-logger {
    max-width: 100%;
  }

  .status-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .history-layout {
    border-radius: 22px;
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
    min-height: 340px;
  }
}

@media (max-width: 460px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 2rem;
  }

  .hero-actions,
  .toolbar-right {
    width: 100%;
  }

  .hero-metric,
  .ws-status,
  .pill-action {
    flex: 1;
  }
}
</style>
