<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import Icon from '../components/common/Icon.vue'
import { getPluginList, loadPlugin } from '../api/modules/plugin'
import type { PluginSummary } from '../api/types/plugin'
import { useDialogStore } from '../utils/dialog'
import { useToastStore } from '../utils/toast'
import { useI18n } from '../utils/i18n'

const router = useRouter()
const dialogStore = useDialogStore()
const toastStore = useToastStore()
const { t } = useI18n()

const plugins = ref<PluginSummary[]>([])
const isLoading = ref(true)
const searchQuery = ref('')

// 获取插件列表
const fetchPlugins = async () => {
  isLoading.value = true
  try {
    plugins.value = await getPluginList()
  } catch (error) {
    console.error('获取插件列表失败:', error)
  } finally {
    isLoading.value = false
  }
}

// 加载插件
const isLoadingPlugin = ref(false)
const handleLoad = async (plugin: PluginSummary) => {
  // 检查插件路径是否存在
  if (!plugin.plugin_path) {
    toastStore.show(tr('plugins.detail.toast.loadFailed', { error: '插件路径未找到' }), 'error')
    return
  }
  
  const confirmed = await dialogStore.confirm(
    tr('plugins.detail.dialogs.loadMessage', { name: plugin.plugin_name }),
    t('plugins.detail.dialogs.loadTitle'),
    t('plugins.detail.dialogs.loadConfirm'),
    t('plugins.detail.dialogs.cancel')
  )
  
  if (!confirmed) return
  
  isLoadingPlugin.value = true
  try {
    const result = await loadPlugin(plugin.plugin_path)
    if (result.success) {
      toastStore.show(tr('plugins.detail.toast.loadSuccess', { name: plugin.plugin_name }), 'success')
      await fetchPlugins()
      filterPlugins()
    } else {
      toastStore.show(tr('plugins.detail.toast.loadFailed', { error: result.error_message }), 'error')
    }
  } catch (error) {
    console.error('加载插件失败:', error)
    toastStore.show(tr('plugins.detail.toast.loadFailed', { error: 'Unknown Error' }), 'error')
  } finally {
    isLoadingPlugin.value = false
  }
}

// 搜索过滤
const filteredPlugins = ref<PluginSummary[]>([])
const filterPlugins = () => {
  const query = searchQuery.value.toLowerCase().trim()
  if (!query) {
    filteredPlugins.value = plugins.value
    return
  }
  
  filteredPlugins.value = plugins.value.filter(plugin => 
    plugin.plugin_name.toLowerCase().includes(query) ||
    plugin.plugin_description?.toLowerCase().includes(query)
  )
}

// 按加载状态分类
const loadedPlugins = computed(() => 
  filteredPlugins.value.filter(p => p.is_loaded)
)

const unloadedPlugins = computed(() => 
  filteredPlugins.value.filter(p => !p.is_loaded)
)

// 导航到插件详情
const goToDetail = (pluginName: string) => {
  router.push({ name: 'plugin-detail', params: { name: pluginName } })
}

// 获取组件类型图标
const getComponentTypeIcon = (type: string): string => {
  const iconMap: Record<string, string> = {
    'action': 'material-symbols:play-circle-outline-rounded',
    'adapter': 'material-symbols:link-rounded',
    'command': 'material-symbols:terminal-rounded',
    'router': 'material-symbols:route-rounded',
    'agent': 'material-symbols:smart-toy-outline-rounded',
    'tool': 'material-symbols:build-rounded',
    'chatter': 'material-symbols:chat-outline-rounded',
    'config': 'material-symbols:settings-outline-rounded',
    'service': 'material-symbols:cloud-outline-rounded',
  }
  return iconMap[type.toLowerCase()] || 'material-symbols:extension-outline-rounded'
}

// 获取组件类型显示名称
const getComponentTypeName = (type: string): string => {
  const key = `plugins.detail.componentTypes.${type.toLowerCase()}`
  const translated = t(key)
  return translated !== key ? translated : type
}

// 翻译工具函数：替换带参数的文本
const tr = (key: string, params?: Record<string, any>): string => {
  let text = t(key)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      text = text.replace(`{${k}}`, String(v))
    })
  }
  return text
}

onMounted(async () => {
  await fetchPlugins()
  filteredPlugins.value = plugins.value
})

// 监听搜索变化
const handleSearch = () => {
  filterPlugins()
}
</script>

<template>
  <AppShell>
    <PageHeader 
      :title="t('plugins.title')" 
      icon="material-symbols:extension-outline-rounded"
      :subtitle="t('plugins.subtitle')"
    >
      <template #actions>
        <button class="icon-btn" @click="fetchPlugins" :disabled="isLoading" :title="t('plugins.refresh')">
          <Icon icon="material-symbols:refresh-rounded" width="20" height="20" />
        </button>
      </template>
    </PageHeader>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <div class="search-input-wrapper">
        <Icon icon="material-symbols:search-rounded" width="20" height="20" class="search-icon" />
        <input
          v-model="searchQuery"
          @input="handleSearch"
          type="text"
          :placeholder="t('plugins.searchPlaceholder')"
          class="search-input"
        />
      </div>
      <div class="plugin-count">
        {{ tr('plugins.pluginCount', { count: filteredPlugins.length }) }}
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <Icon icon="material-symbols:progress-activity" width="48" height="48" class="loading-spinner" />
      <p>{{ t('plugins.loading') }}</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="filteredPlugins.length === 0" class="empty-state">
      <Icon icon="material-symbols:extension-off-outline-rounded" width="64" height="64" />
      <p>{{ searchQuery ? t('plugins.noMatch') : t('plugins.empty') }}</p>
    </div>

    <!-- 插件卡片网格 -->
    <div v-else class="plugin-lists">
      <!-- 已加载的插件 -->
      <div v-if="loadedPlugins.length > 0" class="plugin-section">
        <h3 class="section-title">
          <Icon icon="material-symbols:check-circle-outline-rounded" width="20" height="20" />
          {{ t('plugins.sections.loaded') }} ({{ loadedPlugins.length }})
        </h3>
        <div class="plugin-grid">
          <div
            v-for="plugin in loadedPlugins"
            :key="plugin.plugin_name"
            class="plugin-card"
            @click="goToDetail(plugin.plugin_name)"
          >
        <!-- 插件头部 -->
        <div class="plugin-card-header">
          <div class="plugin-icon">
            <Icon icon="material-symbols:extension-rounded" width="32" height="32" />
          </div>
          <div class="plugin-status">
            <span class="status-dot" :class="{ loaded: plugin.is_loaded }"></span>
          </div>
        </div>

        <!-- 插件信息 -->
        <div class="plugin-card-body">
          <h3 class="plugin-name">{{ plugin.plugin_name }}</h3>
          <p class="plugin-version">{{ tr('plugins.version', { version: plugin.plugin_version }) }}</p>
          <p class="plugin-description">
            {{ plugin.plugin_description || t('plugins.noDescription') }}
          </p>
        </div>

        <!-- 插件组件信息 -->
        <div class="plugin-card-footer">
          <div class="component-badges">
            <div
              v-for="type in plugin.component_types.slice(0, 2)"
              :key="type"
              class="component-badge"
              :title="getComponentTypeName(type)"
            >
              <Icon :icon="getComponentTypeIcon(type)" width="16" height="16" />
              <span>{{ getComponentTypeName(type) }}</span>
            </div>
            <div v-if="plugin.component_types.length > 2" class="component-badge more">
              +{{ plugin.component_types.length - 2 }}
            </div>
          </div>
          <div class="component-count">
            {{ plugin.component_count }} {{ t('plugins.components') }}
          </div>
        </div>

        <!-- 配置标识 -->
        <div v-if="plugin.has_config" class="config-indicator">
          <Icon icon="material-symbols:settings-outline-rounded" width="16" height="16" />
        </div>
      </div>
        </div>
      </div>

      <!-- 未加载的插件 -->
      <div v-if="unloadedPlugins.length > 0" class="plugin-section">
        <h3 class="section-title">
          <Icon icon="material-symbols:cancel-outline-rounded" width="20" height="20" />
          {{ t('plugins.sections.unloaded') }} ({{ unloadedPlugins.length }})
        </h3>
        <div class="plugin-grid">
          <div
            v-for="plugin in unloadedPlugins"
            :key="plugin.plugin_name"
            class="plugin-card plugin-card-unloaded"
          >
            <!-- 插件头部 -->
            <div class="plugin-card-header">
              <div class="plugin-icon">
                <Icon icon="material-symbols:extension-rounded" width="32" height="32" />
              </div>
              <div class="plugin-actions-unloaded">
                <button
                  class="action-btn action-btn-primary"
                  @click="handleLoad(plugin)"
                  :disabled="isLoadingPlugin"
                >
                  <Icon icon="material-symbols:play-arrow-rounded" width="20" height="20" />
                  <span>{{ t('plugins.detail.load') }}</span>
                </button>
              </div>
            </div>

            <!-- 插件信息 -->
            <div class="plugin-card-body">
              <h3 class="plugin-name">{{ plugin.plugin_name }}</h3>
              <p class="plugin-version">{{ tr('plugins.version', { version: plugin.plugin_version }) }}</p>
              <p class="plugin-description">
                {{ plugin.plugin_description || t('plugins.noDescription') }}
              </p>
            </div>

            <!-- 插件组件信息 -->
            <div class="plugin-card-footer">
              <div class="component-badges">
                <div
                  v-for="type in plugin.component_types.slice(0, 2)"
                  :key="type"
                  class="component-badge"
                  :title="getComponentTypeName(type)"
                >
                  <Icon :icon="getComponentTypeIcon(type)" width="16" height="16" />
                  <span>{{ getComponentTypeName(type) }}</span>
                </div>
                <div v-if="plugin.component_types.length > 2" class="component-badge more">
                  +{{ plugin.component_types.length - 2 }}
                </div>
              </div>
              <div class="component-count">
                {{ plugin.component_count }} {{ t('plugins.components') }}
              </div>
            </div>

            <!-- 配置标识 -->
            <div v-if="plugin.has_config" class="config-indicator">
              <Icon icon="material-symbols:settings-outline-rounded" width="16" height="16" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
/* ====== 搜索栏 ====== */
.search-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.search-input-wrapper {
  position: relative;
  flex: 1;
  min-width: 250px;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--md-sys-color-on-surface-variant);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.75rem 0.75rem 0.75rem 2.75rem;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 28px;
  background: var(--md-sys-color-surface-container-low);
  color: var(--md-sys-color-on-surface);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.94rem;
  transition: all 0.2s;
}

.search-input::placeholder {
  color: var(--md-sys-color-on-surface-variant);
}

.search-input:focus {
  outline: none;
  border-color: var(--md-sys-color-primary);
  background: var(--md-sys-color-surface);
  box-shadow: 0 0 0 3px rgba(var(--md-sys-color-primary-rgb, 0, 117, 222), 0.12);
}

.plugin-count {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
  padding: 0.5rem 1rem;
  background: var(--md-sys-color-surface-container);
  border-radius: 16px;
}

/* ====== 加载和空状态 ====== */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 1rem;
  color: var(--md-sys-color-on-surface-variant);
  text-align: center;
}

.loading-spinner {
  animation: spin 1s linear infinite;
  color: var(--md-sys-color-primary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-state p {
  margin-top: 1rem;
  font-size: 1rem;
  font-weight: 500;
}

/* ====== 插件卡片网格 ====== */
.plugin-lists {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
}

.plugin-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  margin: 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--md-sys-color-outline-variant);
}

.plugin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.plugin-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  border-radius: 16px;
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
  backdrop-filter: blur(12px);
  border: 1px solid var(--md-sys-color-outline-variant);
  cursor: pointer;
  transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 
    rgba(0, 0, 0, 0.04) 0px 4px 18px,
    rgba(0, 0, 0, 0.027) 0px 2.025px 7.84688px,
    rgba(0, 0, 0, 0.02) 0px 0.8px 2.925px;
}

.plugin-card:hover {
  transform: translateY(-4px);
  box-shadow: 
    rgba(0, 0, 0, 0.06) 0px 8px 24px,
    rgba(0, 0, 0, 0.04) 0px 4px 12px;
  border-color: var(--md-sys-color-primary);
  background: color-mix(in srgb, var(--md-sys-color-surface-container-highest) 92%, transparent);
}

.plugin-card-unloaded {
  opacity: 0.7;
  cursor: default;
}

.plugin-card-unloaded:hover {
  opacity: 1;
  transform: translateY(-4px);
  box-shadow: 
    rgba(0, 0, 0, 0.06) 0px 8px 24px,
    rgba(0, 0, 0, 0.04) 0px 4px 12px;
  border-color: var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
}

/* ====== 卡片头部 ====== */
.plugin-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.plugin-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.plugin-status {
  display: flex;
  align-items: center;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--md-sys-color-outline);
  transition: background 0.2s;
}

.status-dot.loaded {
  background: var(--md-sys-color-tertiary);
  box-shadow: 0 0 8px var(--md-sys-color-tertiary);
}

/* ====== 未加载的插件操作按钮 ====== */
.plugin-actions-unloaded {
  display: flex;
  align-items: center;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 20px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.action-btn-primary {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.action-btn-primary:hover {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  transform: scale(1.02);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

/* ====== 卡片内容 ====== */
.plugin-card-body {
  flex: 1;
  margin-bottom: 1rem;
}

.plugin-name {
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface);
  margin: 0 0 0.25rem;
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plugin-version {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--md-sys-color-primary);
  margin: 0 0 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.plugin-description {
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  height: 2.64rem; /* 固定两行高度保持卡片底部对齐 */
}

/* ====== 卡片底部 ====== */
.plugin-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--md-sys-color-outline-variant);
}

.component-badges {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: nowrap;
  overflow: hidden;
  min-height: 32px;
}

.component-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 8px;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}

.component-badge.more {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.component-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface-variant);
  white-space: nowrap;
}

/* ====== 配置指示器 ====== */
.config-indicator {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  transition: transform 0.2s;
}

.plugin-card:hover .config-indicator {
  transform: scale(1.1);
}

/* ====== 响应式 ====== */
@media (max-width: 640px) {
  .plugin-grid {
    grid-template-columns: 1fr;
  }
  
  .search-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-input-wrapper {
    min-width: auto;
  }
}
</style>
