<script setup lang="ts">
/**
 * 日志查看器视图。
 *
 * 提供实时日志 WebSocket 推送和历史日志文件浏览功能，
 * 支持日志级别过滤、关键词搜索、自动滚动等。
 */

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import Icon from '../components/common/Icon.vue'
import { useI18n } from '../utils/i18n'
import { useToastStore } from '../utils/toast'
import { getLogFiles, getLogContent } from '../api/modules/log'
import { API_BASE_URL } from '../api/config'
import type { RealtimeLogEntry, LogFileInfo, LogContentResponse } from '../api/types/log'

const { t } = useI18n()
const toastStore = useToastStore()

// ========== 状态 ==========
const activeTab = ref<'realtime' | 'history'>('realtime')

// 实时日志
const realtimeLogs = ref<RealtimeLogEntry[]>([])
const wsStatus = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
const autoScroll = ref(true)
const searchText = ref('')
const selectedLevels = ref<Set<string>>(new Set())
const logContainerRef = ref<HTMLElement | null>(null)
const maxLogEntries = 2000

// 历史日志
const logFiles = ref<LogFileInfo[]>([])
const selectedFile = ref<string>('')
const historyContent = ref('')
const historyLoading = ref(false)
const historyMeta = ref<Omit<LogContentResponse, 'content'> | null>(null)

// WebSocket
let ws: WebSocket | null = null
let heartbeatTimer: number | null = null

const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const

// ========== 计算属性 ==========
const filteredLogs = computed(() => {
  const keyword = searchText.value.trim().toLowerCase()
  return realtimeLogs.value.filter((entry) => {
    // 级别过滤
    if (selectedLevels.value.size > 0 && !selectedLevels.value.has(entry.level)) {
      return false
    }
    // 关键词搜索
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
    stats[entry.level] = (stats[entry.level] || 0) + 1
  }
  return stats
})

// ========== WebSocket ==========
function connectWs(): void {
  if (ws && ws.readyState === WebSocket.OPEN) return

  wsStatus.value = 'connecting'
  const origin = API_BASE_URL.replace(/^http/, 'ws')
  const token = sessionStorage.getItem('neo_token')
  const url = token
    ? `${origin}/webui/api/log/ws?token=${encodeURIComponent(token)}`
    : `${origin}/webui/api/log/ws`

  ws = new WebSocket(url)

  ws.onopen = () => {
    wsStatus.value = 'connected'
    startHeartbeat()
  }

  ws.onmessage = (event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data as string)
      if (msg.type === 'history_batch' && Array.isArray(msg.data)) {
        realtimeLogs.value = [...msg.data, ...realtimeLogs.value].slice(-maxLogEntries)
        scrollToBottom()
      } else if (msg.type === 'realtime_log' && msg.data) {
        realtimeLogs.value.push(msg.data)
        if (realtimeLogs.value.length > maxLogEntries) {
          realtimeLogs.value = realtimeLogs.value.slice(-maxLogEntries)
        }
        if (autoScroll.value) {
          scrollToBottom()
        }
      }
    } catch {
      // 忽略非 JSON 消息
    }
  }

  ws.onclose = () => {
    wsStatus.value = 'disconnected'
    stopHeartbeat()
  }

  ws.onerror = () => {
    wsStatus.value = 'disconnected'
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

function sendLevelFilter(): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    const levels = selectedLevels.value.size > 0 ? Array.from(selectedLevels.value) : null
    ws.send(JSON.stringify({ type: 'set_level_filter', levels }))
  }
}

// ========== 实时日志操作 ==========
function toggleLevel(level: string): void {
  if (selectedLevels.value.has(level)) {
    selectedLevels.value.delete(level)
  } else {
    selectedLevels.value.add(level)
  }
  // 触发响应式更新
  selectedLevels.value = new Set(selectedLevels.value)
  sendLevelFilter()
}

function clearLogs(): void {
  realtimeLogs.value = []
}

function scrollToBottom(): void {
  nextTick(() => {
    const container = logContainerRef.value
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}

function handleScroll(): void {
  const container = logContainerRef.value
  if (!container) return
  const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50
  autoScroll.value = atBottom
}

function levelColor(level: string): string {
  switch (level.toUpperCase()) {
    case 'DEBUG': return 'var(--md-sys-color-on-surface-variant)'
    case 'INFO': return 'var(--md-sys-color-primary)'
    case 'WARNING': return '#e09000'
    case 'ERROR': return 'var(--md-sys-color-error)'
    case 'CRITICAL': return '#d32f2f'
    default: return 'var(--md-sys-color-on-surface)'
  }
}

function levelBg(level: string): string {
  switch (level.toUpperCase()) {
    case 'DEBUG': return 'color-mix(in srgb, var(--md-sys-color-on-surface-variant) 10%, transparent)'
    case 'INFO': return 'color-mix(in srgb, var(--md-sys-color-primary) 12%, transparent)'
    case 'WARNING': return 'color-mix(in srgb, #e09000 12%, transparent)'
    case 'ERROR': return 'color-mix(in srgb, var(--md-sys-color-error) 12%, transparent)'
    case 'CRITICAL': return 'color-mix(in srgb, #d32f2f 15%, transparent)'
    default: return 'transparent'
  }
}

// ========== 历史日志 ==========
async function loadLogFiles(): Promise<void> {
  try {
    const data = await getLogFiles()
    logFiles.value = data.files
  } catch {
    toastStore.show('获取日志文件列表失败', 'error')
  }
}

async function loadFileContent(filename: string, offset = 0): Promise<void> {
  historyLoading.value = true
  try {
    const data = await getLogContent(filename, offset)
    historyContent.value = data.content.join('\n')
    historyMeta.value = {
      offset: data.offset,
      size: data.size,
      total_size: data.total_size,
      has_prev: data.has_prev,
      has_next: data.has_next,
      next_offset: data.next_offset,
      prev_offset: data.prev_offset,
    }
  } catch {
    toastStore.show('获取日志内容失败', 'error')
  } finally {
    historyLoading.value = false
  }
}

function selectLogFile(filename: string): void {
  selectedFile.value = filename
  loadFileContent(filename)
}

function loadPrev(): void {
  if (historyMeta.value?.has_prev && selectedFile.value) {
    loadFileContent(selectedFile.value, historyMeta.value.prev_offset)
  }
}

function loadNext(): void {
  if (historyMeta.value?.has_next && selectedFile.value) {
    loadFileContent(selectedFile.value, historyMeta.value.next_offset)
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

// ========== 生命周期 ==========
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
      <!-- Hero Card -->
      <header class="hero-card">
        <div class="hero-copy">
          <span class="eyebrow">SYSTEM LOGS</span>
          <h1>日志查看器</h1>
          <p>实时监控系统日志输出，支持级别过滤与历史浏览</p>
        </div>
        <div class="hero-actions">
          <div class="ws-status" :class="wsStatus">
            <span class="ws-dot"></span>
            <span class="ws-label">{{ wsStatus === 'connected' ? '已连接' : wsStatus === 'connecting' ? '连接中' : '已断开' }}</span>
          </div>
        </div>
      </header>

      <!-- Tab 切换 -->
      <div class="tab-bar">
        <button class="tab-item" :class="{ active: activeTab === 'realtime' }" @click="activeTab = 'realtime'">
          <Icon icon="material-symbols:stream-rounded" width="18" height="18" />
          <span>实时日志</span>
        </button>
        <button class="tab-item" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
          <Icon icon="material-symbols:folder-open-outline-rounded" width="18" height="18" />
          <span>历史日志</span>
        </button>
      </div>

      <!-- 实时日志面板 -->
      <div v-if="activeTab === 'realtime'" class="realtime-section">
        <!-- 统计条 -->
        <div class="stat-grid">
          <article v-for="level in LOG_LEVELS" :key="level" class="stat-card mini"
            :class="{ selected: selectedLevels.has(level) }" @click="toggleLevel(level)">
            <span class="stat-level" :style="{ color: levelColor(level) }">{{ level }}</span>
            <strong>{{ logStats[level] || 0 }}</strong>
          </article>
        </div>

        <!-- 工具栏 -->
        <div class="toolbar">
          <div class="toolbar-left">
            <input v-model="searchText" class="search-input" placeholder="搜索日志内容..." />
          </div>
          <div class="toolbar-right">
            <button class="icon-button" :class="{ active: autoScroll }" @click="autoScroll = !autoScroll"
              title="自动滚动">
              <Icon icon="material-symbols:vertical-align-bottom-rounded" width="20" height="20" />
            </button>
            <button class="icon-button" @click="clearLogs" title="清空日志">
              <Icon icon="material-symbols:delete-outline-rounded" width="20" height="20" />
            </button>
            <button class="icon-button" @click="wsStatus === 'connected' ? disconnectWs() : connectWs()"
              :title="wsStatus === 'connected' ? '断开' : '连接'">
              <Icon :icon="wsStatus === 'connected' ? 'material-symbols:link-off-rounded' : 'material-symbols:link-rounded'"
                width="20" height="20" />
            </button>
          </div>
        </div>

        <!-- 日志输出区域 -->
        <div class="log-container" ref="logContainerRef" @scroll="handleScroll">
          <div v-if="filteredLogs.length === 0" class="empty-state">
            <Icon icon="material-symbols:terminal-rounded" width="48" height="48" />
            <p>{{ wsStatus === 'connected' ? '等待日志输出...' : '未连接到日志服务' }}</p>
          </div>
          <div v-else class="log-entries">
            <div v-for="(entry, idx) in filteredLogs" :key="idx" class="log-entry"
              :style="{ '--entry-level-color': levelColor(entry.level), '--entry-level-bg': levelBg(entry.level) }">
              <span class="log-time">{{ entry.timestamp }}</span>
              <span class="log-level-badge" :style="{ color: levelColor(entry.level), background: levelBg(entry.level) }">
                {{ entry.level }}
              </span>
              <span class="log-logger">{{ entry.display || entry.logger_name }}</span>
              <span class="log-message">{{ entry.message }}</span>
            </div>
          </div>
        </div>

        <!-- 底部状态栏 -->
        <div class="status-bar">
          <span>共 {{ realtimeLogs.length }} 条 · 显示 {{ filteredLogs.length }} 条</span>
          <span v-if="!autoScroll" class="scroll-hint" @click="autoScroll = true; scrollToBottom()">
            <Icon icon="material-symbols:arrow-downward-rounded" width="14" height="14" />
            回到底部
          </span>
        </div>
      </div>

      <!-- 历史日志面板 -->
      <div v-else class="history-section">
        <div class="history-layout">
          <!-- 文件列表 -->
          <aside class="file-list-panel">
            <div class="panel-header">
              <h3>日志文件</h3>
              <button class="icon-button" @click="loadLogFiles" title="刷新">
                <Icon icon="material-symbols:refresh-rounded" width="18" height="18" />
              </button>
            </div>
            <div v-if="logFiles.length === 0" class="empty-state small">
              <p>暂无日志文件</p>
            </div>
            <div v-else class="file-list">
              <button v-for="file in logFiles" :key="file.filename" class="file-item"
                :class="{ active: selectedFile === file.filename }" @click="selectLogFile(file.filename)">
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

          <!-- 内容面板 -->
          <main class="content-panel">
            <div v-if="!selectedFile" class="empty-state">
              <Icon icon="material-symbols:folder-open-outline-rounded" width="48" height="48" />
              <p>选择一个日志文件查看内容</p>
            </div>
            <template v-else>
              <div class="content-header">
                <h3>{{ selectedFile }}</h3>
                <span v-if="historyMeta" class="content-meta">
                  {{ formatFileSize(historyMeta.total_size) }}
                </span>
              </div>
              <div v-if="historyLoading" class="empty-state">
                <p>加载中...</p>
              </div>
              <pre v-else class="history-content">{{ historyContent }}</pre>
              <div v-if="historyMeta" class="pagination">
                <button class="tonal-button" :disabled="!historyMeta.has_prev" @click="loadPrev">
                  <Icon icon="material-symbols:chevron-left-rounded" width="18" height="18" />
                  上一页
                </button>
                <span class="pagination-info">
                  {{ formatFileSize(historyMeta.size) }} / {{ formatFileSize(historyMeta.total_size) }}
                </span>
                <button class="tonal-button" :disabled="!historyMeta.has_next" @click="loadNext">
                  下一页
                  <Icon icon="material-symbols:chevron-right-rounded" width="18" height="18" />
                </button>
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
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ===== Hero Card ===== */
.hero-card,
.log-container,
.history-layout,
.stat-card {
  border: 1px solid var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 78%, transparent);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(18px) saturate(1.08);
  -webkit-backdrop-filter: blur(18px) saturate(1.08);
}

.hero-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 28px;
}

.eyebrow {
  color: var(--md-sys-color-primary);
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

h1, h2, h3, p { margin: 0; }

h1 {
  margin-top: .35rem;
  color: var(--md-sys-color-on-surface);
  font-size: clamp(1.8rem, 4vw, 3rem);
  letter-spacing: -.04em;
}

.hero-copy p {
  color: var(--md-sys-color-on-surface-variant);
  margin-top: .25rem;
}

/* WS 状态指示 */
.ws-status {
  display: flex;
  align-items: center;
  gap: .5rem;
  padding: .5rem .9rem;
  border-radius: 999px;
  background: var(--md-sys-color-surface-container);
  border: 1px solid var(--md-sys-color-outline-variant);
  font-size: .85rem;
  font-weight: 600;
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--md-sys-color-outline);
  transition: background .3s;
}

.ws-status.connected .ws-dot {
  background: #1aae39;
  box-shadow: 0 0 6px #1aae39;
}

.ws-status.connecting .ws-dot {
  background: #e09000;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .4; }
}

/* ===== Tab Bar ===== */
.tab-bar {
  display: inline-flex;
  padding: .3rem;
  border-radius: 999px;
  background: var(--md-sys-color-surface-container-high);
  border: 1px solid var(--md-sys-color-outline-variant);
  gap: .25rem;
  align-self: flex-start;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  border: 0;
  border-radius: 999px;
  padding: .6rem 1rem;
  font-weight: 600;
  font-size: .9rem;
  cursor: pointer;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  transition: all .2s;
}

.tab-item.active {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

/* ===== Stat Grid ===== */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: .75rem;
}

.stat-card.mini {
  padding: .75rem;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  gap: .2rem;
  cursor: pointer;
  transition: all .2s;
  user-select: none;
}

.stat-card.mini:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-card.mini.selected {
  border-color: var(--md-sys-color-primary);
  background: color-mix(in srgb, var(--md-sys-color-primary-container) 55%, transparent);
  backdrop-filter: blur(12px);
}

.stat-level {
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .06em;
}

.stat-card.mini strong {
  font-size: 1.4rem;
  color: var(--md-sys-color-on-surface);
}

/* ===== Toolbar ===== */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
}

.toolbar-left {
  flex: 1;
  min-width: 0;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: .4rem;
}

.search-input {
  width: 100%;
  max-width: 360px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 14px;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  padding: .65rem .9rem;
  outline: none;
  font-size: .9rem;
  transition: border-color .2s;
}

.search-input:focus {
  border-color: var(--md-sys-color-primary);
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  cursor: pointer;
  transition: all .15s;
}

.icon-button:hover {
  background: var(--md-sys-color-surface-container-high);
}

.icon-button.active {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

/* ===== Log Container ===== */
.log-container {
  border-radius: 22px;
  padding: .5rem;
  min-height: 420px;
  max-height: calc(100vh - 420px);
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
}

.log-entries {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.log-entry {
  display: grid;
  grid-template-columns: auto auto auto 1fr;
  gap: .6rem;
  align-items: baseline;
  padding: .4rem .7rem;
  border-radius: 10px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: .8rem;
  line-height: 1.5;
  transition: background .15s;
}

.log-entry:hover {
  background: var(--entry-level-bg);
}

.log-time {
  color: var(--md-sys-color-on-surface-variant);
  opacity: .7;
  font-size: .72rem;
  white-space: nowrap;
}

.log-level-badge {
  font-size: .68rem;
  font-weight: 700;
  padding: .1rem .4rem;
  border-radius: 6px;
  text-align: center;
  min-width: 52px;
  white-space: nowrap;
}

.log-logger {
  color: var(--md-sys-color-tertiary);
  font-weight: 600;
  font-size: .75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.log-message {
  color: var(--md-sys-color-on-surface);
  word-break: break-word;
  white-space: pre-wrap;
}

/* ===== Status Bar ===== */
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: .5rem .75rem;
  font-size: .78rem;
  color: var(--md-sys-color-on-surface-variant);
}

.scroll-hint {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  cursor: pointer;
  color: var(--md-sys-color-primary);
  font-weight: 600;
}

/* ===== Empty State ===== */
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

.empty-state.small {
  min-height: 80px;
}

/* ===== History Section ===== */
.history-layout {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  min-height: 55vh;
  border-radius: 28px;
  overflow: hidden;
}

.file-list-panel {
  border-right: 1px solid var(--md-sys-color-outline-variant);
  padding: 1rem;
  overflow-y: auto;
  max-height: calc(100vh - 320px);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: .75rem;
}

.panel-header h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface);
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: .4rem;
}

.file-item {
  width: 100%;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: .3rem;
  padding: .75rem;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: var(--md-sys-color-on-surface);
  cursor: pointer;
  transition: all .15s;
}

.file-item:hover,
.file-item.active {
  background: var(--md-sys-color-secondary-container);
  border-color: var(--md-sys-color-outline-variant);
}

.file-item-main {
  display: flex;
  align-items: center;
  gap: .5rem;
}

.file-name {
  font-weight: 600;
  font-size: .85rem;
  word-break: break-all;
}

.file-item-meta {
  display: flex;
  gap: .75rem;
  padding-left: 1.6rem;
  font-size: .72rem;
  color: var(--md-sys-color-on-surface-variant);
}

/* ===== Content Panel ===== */
.content-panel {
  padding: 1.25rem;
  overflow-y: auto;
  max-height: calc(100vh - 320px);
  display: flex;
  flex-direction: column;
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.content-header h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface);
}

.content-meta {
  font-size: .78rem;
  color: var(--md-sys-color-on-surface-variant);
  padding: .25rem .6rem;
  border-radius: 999px;
  background: var(--md-sys-color-surface-container);
}

.history-content {
  flex: 1;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 1rem;
  border-radius: 16px;
  background: var(--md-sys-color-surface-container-lowest);
  border: 1px solid var(--md-sys-color-outline-variant);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: .8rem;
  line-height: 1.6;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

/* ===== Pagination ===== */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
}

.pagination-info {
  font-size: .8rem;
  color: var(--md-sys-color-on-surface-variant);
}

.tonal-button {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  border: 0;
  border-radius: 999px;
  padding: .55rem .9rem;
  font-weight: 600;
  font-size: .82rem;
  cursor: pointer;
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
  transition: opacity .15s;
}

.tonal-button:disabled {
  cursor: not-allowed;
  opacity: .45;
}

/* ===== 响应式 ===== */
@media (max-width: 1100px) {
  .stat-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .history-layout {
    display: flex;
    flex-direction: column;
  }

  .file-list-panel {
    border-right: 0;
    border-bottom: 1px solid var(--md-sys-color-outline-variant);
    max-height: 200px;
  }

  .content-panel {
    max-height: none;
  }
}

@media (max-width: 720px) {
  .hero-card {
    flex-direction: column;
    align-items: stretch;
    border-radius: 20px;
    padding: 1.2rem;
  }

  .hero-actions {
    display: flex;
    justify-content: flex-end;
  }

  .stat-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .5rem;
  }

  .stat-card.mini {
    padding: .55rem;
    border-radius: 14px;
  }

  .stat-card.mini strong {
    font-size: 1.1rem;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: .5rem;
  }

  .toolbar-left {
    order: 2;
  }

  .toolbar-right {
    order: 1;
    justify-content: flex-end;
  }

  .search-input {
    max-width: 100%;
  }

  .log-container {
    border-radius: 16px;
    max-height: calc(100vh - 480px);
    min-height: 300px;
  }

  .log-entry {
    grid-template-columns: 1fr;
    gap: .15rem;
    padding: .5rem .6rem;
    border-bottom: 1px solid var(--md-sys-color-outline-variant);
    border-radius: 0;
  }

  .log-entry:last-child {
    border-bottom: none;
  }

  .log-time {
    font-size: .65rem;
  }

  .log-logger {
    max-width: 100%;
    font-size: .7rem;
  }

  .log-message {
    font-size: .78rem;
  }

  .history-layout {
    border-radius: 20px;
  }

  .file-list-panel {
    max-height: 180px;
    padding: .85rem;
  }

  .content-panel {
    padding: .85rem;
  }

  .history-content {
    font-size: .72rem;
  }

  .tab-bar {
    align-self: stretch;
  }

  .tab-item {
    flex: 1;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat-card.mini:last-child {
    grid-column: span 2;
  }

  h1 {
    font-size: 1.6rem;
  }
}
</style>
