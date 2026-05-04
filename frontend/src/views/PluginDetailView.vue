<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import Icon from '../components/common/Icon.vue'
import { getPluginDetail, reloadPlugin } from '../api/modules/plugin'
import type { PluginDetail, PluginComponentInfo } from '../api/types/plugin'
import { useDialogStore } from '../utils/dialog'
import { useToastStore } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const dialogStore = useDialogStore()
const toastStore = useToastStore()

const pluginName = computed(() => route.params.name as string)
const plugin = ref<PluginDetail | null>(null)
const isLoading = ref(true)
const isReloading = ref(false)
const selectedType = ref<string>('all')

// 获取插件详情
const fetchPluginDetail = async () => {
  isLoading.value = true
  try {
    plugin.value = await getPluginDetail(pluginName.value)
  } catch (error) {
    console.error('获取插件详情失败:', error)
    toastStore.error('获取插件详情失败')
    router.push({ name: 'plugins' })
  } finally {
    isLoading.value = false
  }
}

// 按类型分组组件
const componentsByType = computed(() => {
  if (!plugin.value) return {}
  
  const grouped: Record<string, PluginComponentInfo[]> = {}
  plugin.value.components.forEach(comp => {
    if (!grouped[comp.component_type]) {
      grouped[comp.component_type] = []
    }
    grouped[comp.component_type].push(comp)
  })
  
  return grouped
})

// 过滤后的组件
const filteredComponents = computed(() => {
  if (!plugin.value) return []
  if (selectedType.value === 'all') return plugin.value.components
  return plugin.value.components.filter(comp => comp.component_type === selectedType.value)
})

// 获取所有组件类型
const componentTypes = computed(() => {
  if (!plugin.value) return []
  return [...new Set(plugin.value.components.map(c => c.component_type))]
})

// 重载插件
const handleReload = async () => {
  const confirmed = await dialogStore.confirm(
    '确认重载插件',
    `是否重载插件 "${pluginName.value}"？这将卸载并重新加载该插件。`,
    { confirmText: '重载', cancelText: '取消' }
  )
  
  if (!confirmed) return
  
  isReloading.value = true
  try {
    const result = await reloadPlugin(pluginName.value)
    if (result.success) {
      toastStore.success(`插件 "${pluginName.value}" 重载成功`)
      await fetchPluginDetail()
    } else {
      toastStore.error(`插件重载失败: ${result.error_message}`)
    }
  } catch (error) {
    console.error('重载插件失败:', error)
  } finally {
    isReloading.value = false
  }
}

// 跳转到配置页面
const goToConfig = () => {
  if (!plugin.value?.has_config) return
  router.push({
    name: 'config-plugins',
    query: { plugin: pluginName.value }
  })
}

// 返回列表
const goBack = () => {
  router.push({ name: 'plugins' })
}

// 获取组件状态颜色类
const getStatusClass = (status: string): string => {
  const classMap: Record<string, string> = {
    'active': 'status-active',
    'inactive': 'status-inactive',
    'error': 'status-error'
  }
  return classMap[status] || 'status-inactive'
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

onMounted(async () => {
  await fetchPluginDetail()
})
</script>

<template>
  <AppShell>
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <Icon icon="material-symbols:progress-activity" width="48" height="48" class="loading-spinner" />
      <p>加载插件详情...</p>
    </div>

    <!-- 插件详情 -->
    <div v-else-if="plugin" class="plugin-detail">
      <!-- 返回按钮 -->
      <button class="back-btn" @click="goBack">
        <Icon icon="material-symbols:arrow-back-rounded" width="20" height="20" />
        <span>返回列表</span>
      </button>

      <!-- 插件头部信息卡片 -->
      <div class="plugin-header-card">
        <div class="plugin-header-main">
          <div class="plugin-icon-large">
            <Icon icon="material-symbols:extension-rounded" width="48" height="48" />
          </div>
          <div class="plugin-header-info">
            <h1 class="plugin-title">{{ plugin.plugin_name }}</h1>
            <div class="plugin-meta">
              <span class="plugin-version">v{{ plugin.plugin_version }}</span>
              <span class="plugin-status-badge" :class="{ loaded: plugin.is_loaded }">
                {{ plugin.is_loaded ? '已加载' : '未加载' }}
              </span>
            </div>
            <p class="plugin-description">{{ plugin.plugin_description || '暂无描述' }}</p>
            <p class="plugin-path">
              <Icon icon="material-symbols:folder-outline-rounded" width="16" height="16" />
              {{ plugin.plugin_path }}
            </p>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="plugin-actions">
          <button
            v-if="plugin.has_config"
            class="action-btn action-btn-primary"
            @click="goToConfig"
          >
            <Icon icon="material-symbols:settings-outline-rounded" width="20" height="20" />
            <span>配置</span>
          </button>
          <button
            class="action-btn action-btn-secondary"
            @click="handleReload"
            :disabled="isReloading"
          >
            <Icon icon="material-symbols:refresh-rounded" width="20" height="20" />
            <span>{{ isReloading ? '重载中...' : '重载' }}</span>
          </button>
        </div>
      </div>

      <!-- 统计信息卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">
            <Icon icon="material-symbols:extension-outline-rounded" width="24" height="24" />
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ plugin.component_count }}</div>
            <div class="stat-label">组件总数</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">
            <Icon icon="material-symbols:category-outline-rounded" width="24" height="24" />
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ componentTypes.length }}</div>
            <div class="stat-label">组件类型</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">
            <Icon icon="material-symbols:account-tree-outline-rounded" width="24" height="24" />
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ plugin.dependencies.length }}</div>
            <div class="stat-label">依赖数量</div>
          </div>
        </div>
      </div>

      <!-- 组件列表 -->
      <div class="components-section">
        <div class="section-header">
          <h2 class="section-title">组件列表</h2>
          
          <!-- 类型筛选 -->
          <div class="type-filter">
            <button
              class="filter-btn"
              :class="{ active: selectedType === 'all' }"
              @click="selectedType = 'all'"
            >
              全部 ({{ plugin.components.length }})
            </button>
            <button
              v-for="type in componentTypes"
              :key="type"
              class="filter-btn"
              :class="{ active: selectedType === type }"
              @click="selectedType = type"
            >
              {{ type }} ({{ componentsByType[type].length }})
            </button>
          </div>
        </div>

        <!-- 组件卡片 -->
        <div class="component-grid">
          <div
            v-for="component in filteredComponents"
            :key="component.signature"
            class="component-card"
          >
            <div class="component-card-header">
              <div class="component-type-icon">
                <Icon :icon="getComponentTypeIcon(component.component_type)" width="24" height="24" />
              </div>
              <span class="component-status-dot" :class="getStatusClass(component.status)"></span>
            </div>
            
            <div class="component-card-body">
              <div class="component-type-badge">{{ component.component_type }}</div>
              <h3 class="component-name">{{ component.component_name }}</h3>
              <p class="component-description">{{ component.description || '暂无描述' }}</p>
              
              <!-- 扩展属性 -->
              <div v-if="component.extra && Object.keys(component.extra).length > 0" class="component-extra">
                <div
                  v-for="(value, key) in component.extra"
                  :key="key"
                  class="extra-item"
                >
                  <span class="extra-key">{{ key }}:</span>
                  <span class="extra-value">{{ typeof value === 'object' ? JSON.stringify(value) : value }}</span>
                </div>
              </div>
            </div>

            <div class="component-card-footer">
              <code class="component-signature">{{ component.signature }}</code>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="filteredComponents.length === 0" class="empty-components">
          <Icon icon="material-symbols:filter-list-off-rounded" width="48" height="48" />
          <p>该类型下暂无组件</p>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
/* ====== 加载状态 ====== */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 1rem;
  color: var(--md-sys-color-on-surface-variant);
}

.loading-spinner {
  animation: spin 1s linear infinite;
  color: var(--md-sys-color-primary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ====== 返回按钮 ====== */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  margin-bottom: 1.5rem;
  border: none;
  border-radius: 20px;
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.94rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  background: var(--md-sys-color-surface-container-high);
  transform: translateX(-4px);
}

/* ====== 插件头部卡片 ====== */
.plugin-header-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 2rem;
  padding: 2rem;
  margin-bottom: 1.5rem;
  border-radius: 20px;
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 95%, transparent);
  backdrop-filter: blur(12px);
  border: 1px solid var(--md-sys-color-outline-variant);
  box-shadow: 
    rgba(0, 0, 0, 0.04) 0px 4px 18px,
    rgba(0, 0, 0, 0.027) 0px 2.025px 7.84688px;
}

.plugin-header-main {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}

.plugin-icon-large {
  width: 80px;
  height: 80px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.plugin-header-info {
  flex: 1;
}

.plugin-title {
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 2rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface);
  margin: 0 0 0.5rem;
  letter-spacing: -0.02em;
}

.plugin-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.plugin-version {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--md-sys-color-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.plugin-status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.75rem;
  font-weight: 600;
}

.plugin-status-badge.loaded {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.plugin-description {
  font-size: 1rem;
  line-height: 1.6;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0 0 0.75rem;
}

.plugin-path {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
  font-family: 'Consolas', 'Monaco', monospace;
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.8;
}

/* ====== 操作按钮 ====== */
.plugin-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border: none;
  border-radius: 28px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.94rem;
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

.action-btn-secondary {
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
}

.action-btn-secondary:hover {
  background: var(--md-sys-color-surface-container-highest);
  transform: scale(1.02);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

/* ====== 统计卡片网格 ====== */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 16px;
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 95%, transparent);
  backdrop-filter: blur(12px);
  border: 1px solid var(--md-sys-color-outline-variant);
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface);
  line-height: 1;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
}

/* ====== 组件列表部分 ====== */
.components-section {
  margin-top: 2rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.section-title {
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

/* ====== 类型筛选 ====== */
.type-filter {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 20px;
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface-variant);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover {
  background: var(--md-sys-color-surface-container-high);
}

.filter-btn.active {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

/* ====== 组件卡片网格 ====== */
.component-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.component-card {
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  border-radius: 16px;
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 92%, transparent);
  backdrop-filter: blur(12px);
  border: 1px solid var(--md-sys-color-outline-variant);
  transition: all 0.2s;
}

.component-card:hover {
  border-color: var(--md-sys-color-primary);
  box-shadow: 
    rgba(0, 0, 0, 0.04) 0px 4px 12px,
    rgba(0, 0, 0, 0.02) 0px 2px 6px;
}

/* ====== 组件卡片头部 ====== */
.component-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.component-type-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.component-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: background 0.2s;
}

.component-status-dot.status-active {
  background: var(--md-sys-color-tertiary);
  box-shadow: 0 0 8px var(--md-sys-color-tertiary);
}

.component-status-dot.status-inactive {
  background: var(--md-sys-color-outline);
}

.component-status-dot.status-error {
  background: var(--md-sys-color-error);
  box-shadow: 0 0 8px var(--md-sys-color-error);
}

/* ====== 组件卡片内容 ====== */
.component-card-body {
  flex: 1;
  margin-bottom: 0.75rem;
}

.component-type-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  margin-bottom: 0.5rem;
  border-radius: 6px;
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.component-name {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  margin: 0 0 0.5rem;
}

.component-description {
  font-size: 0.88rem;
  line-height: 1.5;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0 0 0.5rem;
}

/* ====== 扩展属性 ====== */
.component-extra {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.5rem;
  padding: 0.5rem;
  border-radius: 8px;
  background: var(--md-sys-color-surface-container);
}

.extra-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.75rem;
  font-family: 'Consolas', 'Monaco', monospace;
}

.extra-key {
  font-weight: 600;
  color: var(--md-sys-color-primary);
}

.extra-value {
  color: var(--md-sys-color-on-surface-variant);
  word-break: break-all;
}

/* ====== 组件卡片底部 ====== */
.component-card-footer {
  padding-top: 0.75rem;
  border-top: 1px solid var(--md-sys-color-outline-variant);
}

.component-signature {
  display: block;
  font-size: 0.75rem;
  font-family: 'Consolas', 'Monaco', monospace;
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.8;
  word-break: break-all;
}

/* ====== 空状态 ====== */
.empty-components {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem 1rem;
  color: var(--md-sys-color-on-surface-variant);
}

.empty-components p {
  margin-top: 1rem;
  font-size: 1rem;
}

/* ====== 响应式 ====== */
@media (max-width: 900px) {
  .plugin-header-card {
    flex-direction: column;
  }
  
  .plugin-actions {
    width: 100%;
    flex-direction: row;
  }
  
  .component-grid {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
