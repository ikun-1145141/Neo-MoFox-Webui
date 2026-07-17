<!--
  @file PluginPagesView.vue
  @description 插件页面视图

  功能：
  - 挂载时调用 getUiDiscovery() 获取所有已注册的插件页面
  - 左侧按插件分组展示页面列表
  - 点击页面时通过 getUiSchema() 加载其 XML，用 parseUiPage() 校验后交由 SchemaRenderer 渲染
  - 每个页面持有独立的 createDataStore() 状态
-->
<template>
  <AppShell no-padding>
    <div class="plugin-pages-view">
      <!-- 移动端顶部页面选择器 -->
      <div class="mobile-top-selector">
        <MdSelect
          v-model="selectedKey"
          :options="pageOptions"
          :placeholder="t('plugins.pages.selectPlaceholder')"
        />
      </div>

      <!-- 左侧页面列表 -->
      <div class="page-list">
        <div v-if="isLoadingList" class="list-loading">
          <Icon icon="material-symbols:progress-activity" :size="32" class="spinning" />
          <p>{{ t('plugins.pages.loading') }}</p>
        </div>

        <div v-else-if="pages.length === 0" class="list-empty">
          <Icon icon="material-symbols:web-asset-off-rounded" :size="48" />
          <p>{{ t('plugins.pages.empty') }}</p>
        </div>

        <div v-else class="list-groups">
          <div v-for="group in pageGroups" :key="group.pluginName" class="page-group">
            <h3 class="group-title">{{ group.pluginName }}</h3>
            <button
              v-for="page in group.pages"
              :key="pageKey(page)"
              type="button"
              class="page-item"
              :class="{ active: selectedKey === pageKey(page) }"
              @click="selectPage(page)"
            >
              <Icon
                v-if="page.icon"
                :icon="page.icon"
                :size="20"
                class="page-icon"
              />
              <div class="page-item-content">
                <span class="page-title">{{ page.title }}</span>
                <span v-if="page.description" class="page-description">
                  {{ page.description }}
                </span>
              </div>
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧页面内容 -->
      <div class="page-content">
        <!-- 未选择页面 -->
        <div v-if="!selectedPage" class="content-empty">
          <Icon icon="material-symbols:web-rounded" :size="64" />
          <p>{{ t('plugins.pages.selectPage') }}</p>
        </div>

        <!-- 加载中 -->
        <div v-else-if="isLoadingSchema" class="content-loading">
          <Icon icon="material-symbols:progress-activity" :size="48" class="spinning" />
          <p>{{ t('plugins.pages.loadingPage') }}</p>
        </div>

        <!-- 加载失败 -->
        <div v-else-if="loadError" class="content-error">
          <Icon icon="material-symbols:error-outline-rounded" :size="48" />
          <p>{{ loadError }}</p>
          <button type="button" class="retry-btn" @click="loadSchema(selectedPage!)">
            <Icon icon="material-symbols:refresh-rounded" :size="20" />
            <span>{{ t('plugins.pages.retry') }}</span>
          </button>
        </div>

        <!-- 渲染页面 -->
        <div v-else-if="pageXml" class="content-render">
          <SchemaRenderer :xml="pageXml" :store="store" :plugin-name="selectedPage!.plugin_name" />
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from '@/utils/i18n'
import AppShell from '@/components/common/AppShell.vue'
import Icon from '@/components/common/Icon.vue'
import MdSelect from '@/components/common/MdSelect.vue'
import SchemaRenderer from '@/components/ui-schema/SchemaRenderer.vue'
import { getUiDiscovery, getUiSchema } from '@/api/modules/ui'
import { parseUiPage } from '@/utils/xmlParser'
import { createDataStore } from '@/utils/dataStore'
import type { UiPageMeta } from '@/api/types/ui'

const { t } = useI18n()

// 页面列表
const pages = ref<UiPageMeta[]>([])
const isLoadingList = ref(false)

// 选中的页面
const selectedPage = ref<UiPageMeta | null>(null)
const pageXml = ref<string>('')
const isLoadingSchema = ref(false)
const loadError = ref('')

// 当前页面的独立状态存储
const store = ref<Record<string, any>>(createDataStore())

// 页面唯一键
function pageKey(page: UiPageMeta): string {
  return `${page.plugin_name}::${page.page_id}`
}

// 选中页面的键（用于高亮和移动端选择器双向绑定）
const selectedKey = computed<string | null>({
  get: () => (selectedPage.value ? pageKey(selectedPage.value) : null),
  set: (val) => {
    if (val) {
      const page = pages.value.find((p) => pageKey(p) === val)
      if (page) selectPage(page)
    }
  },
})

// 按插件分组（保持后端返回的 order 顺序）
const pageGroups = computed(() => {
  const groups = new Map<string, UiPageMeta[]>()
  for (const page of pages.value) {
    if (!groups.has(page.plugin_name)) {
      groups.set(page.plugin_name, [])
    }
    groups.get(page.plugin_name)!.push(page)
  }
  return Array.from(groups.entries()).map(([pluginName, groupPages]) => ({
    pluginName,
    pages: groupPages,
  }))
})

// 移动端选择器选项
const pageOptions = computed(() =>
  pages.value.map((p) => ({
    label: `${p.plugin_name} · ${p.title}`,
    value: pageKey(p),
  })),
)

// 加载页面列表
async function loadPageList() {
  try {
    isLoadingList.value = true
    const list = await getUiDiscovery()
    // 按 order 升序排序，保证分组内顺序稳定
    pages.value = [...list].sort((a, b) => a.order - b.order)
  } catch (error: any) {
    console.error('加载插件页面列表失败:', error)
  } finally {
    isLoadingList.value = false
  }
}

// 选择页面
function selectPage(page: UiPageMeta) {
  selectedPage.value = page
  loadSchema(page)
}

// 加载并校验页面 Schema
async function loadSchema(page: UiPageMeta) {
  try {
    isLoadingSchema.value = true
    loadError.value = ''
    pageXml.value = ''

    const response = await getUiSchema(page.plugin_name, page.page_id)

    // 校验 XML（解析失败会抛出 XmlParseError）
    parseUiPage(response.page_xml)

    // 每个页面使用独立的状态存储
    store.value = createDataStore()
    pageXml.value = response.page_xml
  } catch (error: any) {
    loadError.value = error?.message || t('plugins.pages.loadFailed')
  } finally {
    isLoadingSchema.value = false
  }
}

onMounted(() => {
  loadPageList()
  connectWebSocket()
})

onUnmounted(() => {
  closeWebSocket()
})

// ========== WebSocket 页面热更新（设计文档 3.2） ==========

let ws: WebSocket | null = null
let heartbeatTimer: ReturnType<typeof setInterval> | null = null

function connectWebSocket() {
  const token = sessionStorage.getItem('neo_token')
  if (!token) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${window.location.host}/webui/api/ui/ws?token=${encodeURIComponent(token)}`

  ws = new WebSocket(url)

  ws.onopen = () => {
    console.log('[PluginPages] WS 已连接')
    // 30s 心跳
    heartbeatTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'page_updated') {
        console.log('[PluginPages] 收到页面更新通知:', msg)
        // 刷新页面列表
        loadPageList()
        // 若当前正查看被更新的页面，重载其 Schema
        const current = selectedPage.value
        if (
          current &&
          current.plugin_name === msg.plugin_name &&
          current.page_id === msg.page_id
        ) {
          loadSchema(current)
        }
      }
    } catch (e) {
      console.error('[PluginPages] WS 消息解析失败:', e)
    }
  }

  ws.onerror = (e) => console.error('[PluginPages] WS 错误:', e)
  ws.onclose = () => console.log('[PluginPages] WS 已关闭')
}

function closeWebSocket() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
  ws?.close()
  ws = null
}
</script>

<style scoped>
.plugin-pages-view {
  display: flex;
  align-items: stretch;
  height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
  min-height: 0;
  overflow: hidden;
}

/* 左侧页面列表 */
.page-list {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  border-right: 1px solid var(--md-sys-color-outline-variant);
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  z-index: 5;
}

.list-loading,
.list-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
  color: var(--md-sys-color-on-surface-variant);
}

.list-loading p,
.list-empty p {
  font-size: 14px;
  text-align: center;
  margin: 0;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.list-groups {
  flex: 1;
  padding: 8px;
}

.page-group {
  margin-bottom: 12px;
}

.group-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--md-sys-color-on-surface-variant);
  padding: 8px 16px 4px;
  margin: 0;
}

.page-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: transparent;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  margin-bottom: 4px;
}

.page-item:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.page-item.active {
  background: var(--md-sys-color-secondary-container);
}

.page-icon {
  color: var(--md-sys-color-on-surface-variant);
  flex-shrink: 0;
}

.page-item.active .page-icon {
  color: var(--md-sys-color-on-secondary-container);
}

.page-item-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-item.active .page-title {
  color: var(--md-sys-color-on-secondary-container);
}

.page-description {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.page-item.active .page-description {
  color: var(--md-sys-color-on-secondary-container);
  opacity: 0.8;
}

/* 右侧内容区域 */
.page-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.content-empty,
.content-loading,
.content-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px;
  color: var(--md-sys-color-on-surface-variant);
}

.content-empty p,
.content-loading p,
.content-error p {
  font-size: 16px;
  text-align: center;
  margin: 0;
}

.content-render {
  padding: 24px;
}

.retry-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.retry-btn:hover {
  box-shadow: 0 2px 8px rgba(0, 88, 189, 0.3);
  transform: translateY(-1px);
}

/* 移动端顶部选择器 */
.mobile-top-selector {
  display: none;
  padding: 16px;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

/* 响应式布局 */
@media (max-width: 768px) {
  .plugin-pages-view {
    flex-direction: column;
  }

  .mobile-top-selector {
    display: block;
  }

  .page-list {
    display: none;
  }

  .page-content {
    min-height: calc(100dvh - 180px - var(--app-bottom-nav-height, 0px));
  }
}
</style>
