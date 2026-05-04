<script setup lang="ts">
import { ref, onMounted, computed, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
import Icon from '../components/common/Icon.vue'
import { getPluginDetail, reloadPlugin, loadPlugin, unloadPlugin } from '../api/modules/plugin'
import type { PluginDetail, PluginComponentInfo } from '../api/types/plugin'
import { useDialogStore } from '../utils/dialog'
import { useToastStore } from '../utils/toast'
import { useI18n } from '../utils/i18n'

const route = useRoute()
const router = useRouter()
const dialogStore = useDialogStore()
const toastStore = useToastStore()
const { t } = useI18n()

const pluginName = computed(() => route.params.name as string)
const plugin = ref<PluginDetail | null>(null)
const isLoading = ref(true)
const isReloading = ref(false)
const isLoadingPlugin = ref(false)
const isUnloadingPlugin = ref(false)
const selectedType = ref<string>('all')
const isDescriptionExpanded = ref(false)
const descriptionRef = ref<HTMLElement | null>(null)
const isTextTruncated = ref(false)

const checkTruncation = () => {
  if (!plugin.value?.plugin_description) {
    isTextTruncated.value = false
    return
  }
  
  const isMobile = window.innerWidth <= 768
  const description = plugin.value.plugin_description || ''
  
  if (isMobile) {
    // 移动端：检查字数是否超过20字
    isTextTruncated.value = description.length > 20
  } else {
    // 桌面端：不显示展开按钮
    isTextTruncated.value = false
  }
}

// 监听窗口大小变化以重新计算是否截断
let resizeTimeout: number | null = null
const handleResize = () => {
  if (resizeTimeout) {
    window.clearTimeout(resizeTimeout)
  }
  resizeTimeout = window.setTimeout(() => {
    checkTruncation()
  }, 150)
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (resizeTimeout) {
    window.clearTimeout(resizeTimeout)
  }
})

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

// 获取插件详情
const fetchPluginDetail = async () => {
  isLoading.value = true
  try {
    plugin.value = await getPluginDetail(pluginName.value)
    nextTick(() => {
      checkTruncation()
    })
  } catch (error) {
    console.error('获取插件详情失败:', error)
    toastStore.show(t('plugins.detail.toast.fetchFailed'), 'error')
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

// 加载插件
const handleLoad = async () => {
  if (!plugin.value) return
  
  const confirmed = await dialogStore.confirm(
    tr('plugins.detail.dialogs.loadMessage', { name: pluginName.value }),
    t('plugins.detail.dialogs.loadTitle'),
    t('plugins.detail.dialogs.loadConfirm'),
    t('plugins.detail.dialogs.cancel')
  )
  
  if (!confirmed) return
  
  isLoadingPlugin.value = true
  try {
    const result = await loadPlugin(plugin.value.plugin_path)
    if (result.success) {
      toastStore.show(tr('plugins.detail.toast.loadSuccess', { name: pluginName.value }), 'success')
      await fetchPluginDetail()
    } else {
      toastStore.show(tr('plugins.detail.toast.loadFailed', { error: result.error_message }), 'error')
    }
  } catch (error) {
    console.error('加载插件失败:', error)
  } finally {
    isLoadingPlugin.value = false
  }
}

// 卸载插件
const handleUnload = async () => {
  const confirmed = await dialogStore.confirm(
    tr('plugins.detail.dialogs.unloadMessage', { name: pluginName.value }),
    t('plugins.detail.dialogs.unloadTitle'),
    t('plugins.detail.dialogs.unloadConfirm'),
    t('plugins.detail.dialogs.cancel')
  )
  
  if (!confirmed) return
  
  isUnloadingPlugin.value = true
  try {
    const result = await unloadPlugin(pluginName.value)
    if (result.success) {
      toastStore.show(tr('plugins.detail.toast.unloadSuccess', { name: pluginName.value }), 'success')
      // 卸载成功后返回插件列表页面，避免用户再次点击卸载按钮
      router.push({ name: 'plugins' })
    } else {
      toastStore.show(tr('plugins.detail.toast.unloadFailed', { error: result.error_message }), 'error')
    }
  } catch (error) {
    console.error('卸载插件失败:', error)
  } finally {
    isUnloadingPlugin.value = false
  }
}

// 重载插件
const handleReload = async () => {
  const confirmed = await dialogStore.confirm(
    tr('plugins.detail.dialogs.reloadMessage', { name: pluginName.value }),
    t('plugins.detail.dialogs.reloadTitle'),
    t('plugins.detail.dialogs.reloadConfirm'),
    t('plugins.detail.dialogs.cancel')
  )
  
  if (!confirmed) return
  
  isReloading.value = true
  try {
    const result = await reloadPlugin(pluginName.value)
    if (result.success) {
      toastStore.show(tr('plugins.detail.toast.reloadSuccess', { name: pluginName.value }), 'success')
      await fetchPluginDetail()
    } else {
      toastStore.show(tr('plugins.detail.toast.reloadFailed', { error: result.error_message }), 'error')
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

// 获取组件类型显示名称
const getComponentTypeName = (type: string): string => {
  const key = `plugins.detail.componentTypes.${type.toLowerCase()}`
  const translated = t(key)
  return translated !== key ? translated : type
}

// 获取平台图标
const getPlatformIcon = (platform: string | undefined): string => {
  if (!platform) return 'material-symbols:device-unknown'
  const iconMap: Record<string, string> = {
    'qq': 'material-symbols:chat-bubble-outline-rounded',
    'wechat': 'material-symbols:wechat',
    'discord': 'material-symbols:discord',
    'telegram': 'material-symbols:send-outline-rounded',
    'web': 'material-symbols:language-rounded',
  }
  return iconMap[platform.toLowerCase()] || 'material-symbols:hub-outline-rounded'
}

// 获取权限等级颜色
const getPermissionLevelClass = (level: string | undefined): string => {
  if (!level) return 'permission-user'
  // 处理 "PermissionLevel.XXX" 格式
  const levelStr = level.includes('.') ? level.split('.').pop() || level : level
  const classMap: Record<string, string> = {
    'OWNER': 'permission-owner',
    'OPERATOR': 'permission-operator',
    'USER': 'permission-user',
    'GUEST': 'permission-guest',
  }
  return classMap[levelStr.toUpperCase()] || 'permission-user'
}

// 获取权限等级显示文本
const getPermissionLevelText = (level: string | undefined): string => {
  if (!level) return t('plugins.detail.metadata.permissions.user')
  // 处理 "PermissionLevel.XXX" 格式
  const levelStr = level.includes('.') ? level.split('.').pop() || level : level
  const key = `plugins.detail.metadata.permissions.${levelStr.toLowerCase()}`
  const translated = t(key)
  return translated !== key ? translated : levelStr
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
      <p>{{ t('plugins.loading') }}</p>
    </div>

    <!-- 插件详情 -->
    <div v-else-if="plugin" class="plugin-detail">
      <!-- 返回按钮 -->
      <button class="back-btn" @click="goBack">
        <Icon icon="material-symbols:arrow-back-rounded" width="20" height="20" />
        <span>{{ t('plugins.detail.backToList') }}</span>
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
              <span class="plugin-version">{{ tr('plugins.version', { version: plugin.plugin_version }) }}</span>
              <span class="plugin-status-badge" :class="{ loaded: plugin.is_loaded }">
                {{ plugin.is_loaded ? t('plugins.detail.loaded') : t('plugins.detail.notLoaded') }}
              </span>
            </div>
            <div class="plugin-description-wrapper" :class="{ expanded: isDescriptionExpanded }">
              <p class="plugin-description" ref="descriptionRef">{{ plugin.plugin_description || t('plugins.noDescription') }}</p>
              <button 
                class="description-toggle-btn" 
                @click="isDescriptionExpanded = !isDescriptionExpanded"
                v-show="isTextTruncated || isDescriptionExpanded"
              >
                {{ isDescriptionExpanded ? t('plugins.detail.collapse') : t('plugins.detail.expand') }}
              </button>
            </div>
            <p class="plugin-path">
              <Icon icon="material-symbols:folder-outline-rounded" width="16" height="16" />
              {{ plugin.plugin_path }}
            </p>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="plugin-actions">
          <!-- 未加载状态：只显示加载按钮 -->
          <template v-if="!plugin.is_loaded">
            <button
              class="action-btn action-btn-primary"
              @click="handleLoad"
              :disabled="isLoadingPlugin"
            >
              <Icon icon="material-symbols:play-circle-outline-rounded" width="20" height="20" />
              <span>{{ isLoadingPlugin ? t('plugins.detail.actions.loading') : t('plugins.detail.actions.load') }}</span>
            </button>
          </template>
          
          <!-- 已加载状态：显示配置、重载、卸载按钮 -->
          <template v-else>
            <button
              v-if="plugin.has_config"
              class="action-btn action-btn-primary"
              @click="goToConfig"
            >
              <Icon icon="material-symbols:settings-outline-rounded" width="20" height="20" />
              <span>{{ t('plugins.detail.actions.config') }}</span>
            </button>
            <button
              class="action-btn action-btn-secondary"
              @click="handleReload"
              :disabled="isReloading"
            >
              <Icon icon="material-symbols:refresh-rounded" width="20" height="20" />
              <span>{{ isReloading ? t('plugins.detail.actions.reloading') : t('plugins.detail.actions.reload') }}</span>
            </button>
            <button
              class="action-btn action-btn-danger"
              @click="handleUnload"
              :disabled="isUnloadingPlugin"
            >
              <Icon icon="material-symbols:stop-circle-outline-rounded" width="20" height="20" />
              <span>{{ isUnloadingPlugin ? t('plugins.detail.actions.unloading') : t('plugins.detail.actions.unload') }}</span>
            </button>
          </template>
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
            <div class="stat-label">{{ t('plugins.detail.stats.totalComponents') }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">
            <Icon icon="material-symbols:category-outline-rounded" width="24" height="24" />
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ componentTypes.length }}</div>
            <div class="stat-label">{{ t('plugins.detail.stats.componentTypes') }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">
            <Icon icon="material-symbols:account-tree-outline-rounded" width="24" height="24" />
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ plugin.dependencies.length }}</div>
            <div class="stat-label">{{ t('plugins.detail.stats.dependencies') }}</div>
          </div>
        </div>
      </div>

      <!-- 组件列表 -->
      <div class="components-section" :class="{ disabled: !plugin.is_loaded }">
        <div class="section-header">
          <h2 class="section-title">
            {{ t('plugins.detail.components.title') }}
            <span v-if="!plugin.is_loaded" class="disabled-hint">{{ t('plugins.detail.components.disabledHint') }}</span>
          </h2>
          
          <!-- 类型筛选 -->
          <div class="type-filter" v-if="plugin.is_loaded">
            <button
              class="filter-btn"
              :class="{ active: selectedType === 'all' }"
              @click="selectedType = 'all'"
            >
              {{ t('plugins.detail.components.all') }} ({{ plugin.components.length }})
            </button>
            <button
              v-for="type in componentTypes"
              :key="type"
              class="filter-btn"
              :class="{ active: selectedType === type }"
              @click="selectedType = type"
            >
              {{ getComponentTypeName(type) }} ({{ componentsByType[type].length }})
            </button>
          </div>
        </div>

        <!-- 组件卡片 -->
        <div class="component-grid">
          <div
            v-for="component in filteredComponents"
            :key="component.signature"
            class="component-card"
            :class="{ disabled: !plugin.is_loaded }"
          >
            <div class="component-card-header">
              <div class="component-type-icon">
                <Icon :icon="getComponentTypeIcon(component.component_type)" width="24" height="24" />
              </div>
              <span class="component-status-dot" :class="getStatusClass(component.status)"></span>
            </div>
            
            <div class="component-card-body">
              <div class="component-type-badge">{{ getComponentTypeName(component.component_type) }}</div>
              <h3 class="component-name">{{ component.component_name }}</h3>
              <p class="component-description">{{ component.description || t('plugins.noDescription') }}</p>
              
              <!-- 组件元数据标签 -->
              <div v-if="component.extra && Object.keys(component.extra).length > 0" class="component-metadata">
                <!-- Adapter 组件 -->
                <template v-if="component.component_type === 'adapter'">
                  <div v-if="component.extra.platform" class="metadata-tag metadata-platform">
                    <Icon :icon="getPlatformIcon(component.extra.platform)" width="16" height="16" />
                    <span>{{ component.extra.platform }}</span>
                  </div>
                </template>
                
                <!-- Router 组件 -->
                <template v-if="component.component_type === 'router'">
                  <div v-if="component.extra.custom_route_path" class="metadata-tag metadata-path">
                    <Icon icon="material-symbols:route-rounded" width="16" height="16" />
                    <span>{{ component.extra.custom_route_path }}</span>
                  </div>
                  <div v-if="component.extra.cors_origins && component.extra.cors_origins.length > 0" class="metadata-tag metadata-info">
                    <Icon icon="material-symbols:shield-outline-rounded" width="16" height="16" />
                    <span>CORS: {{ component.extra.cors_origins.length }} {{ t('plugins.detail.metadata.origins') }}</span>
                  </div>
                </template>
                
                <!-- Command 组件 -->
                <template v-if="component.component_type === 'command'">
                  <div v-if="component.extra.command_name" class="metadata-tag metadata-command">
                    <Icon icon="material-symbols:terminal-rounded" width="16" height="16" />
                    <span>/{{ component.extra.command_name }}</span>
                  </div>
                  <div v-if="component.extra.permission_level" class="metadata-tag metadata-permission" :class="getPermissionLevelClass(component.extra.permission_level)">
                    <Icon icon="material-symbols:shield-person-outline-rounded" width="16" height="16" />
                    <span>{{ getPermissionLevelText(component.extra.permission_level) }}</span>
                  </div>
                </template>
                
                <!-- Action 组件 -->
                <template v-if="component.component_type === 'action'">
                  <div v-if="component.extra.primary_action" class="metadata-tag metadata-primary">
                    <Icon icon="material-symbols:star-outline-rounded" width="16" height="16" />
                    <span>{{ t('plugins.detail.metadata.primaryAction') }}</span>
                  </div>
                </template>
                
                <!-- Agent 组件 -->
                <template v-if="component.component_type === 'agent'">
                  <div v-if="component.extra.usables && component.extra.usables.length > 0" class="metadata-tag metadata-info">
                    <Icon icon="material-symbols:extension-outline-rounded" width="16" height="16" />
                    <span>{{ component.extra.usables.length }} {{ t('plugins.detail.metadata.usables') }}</span>
                  </div>
                </template>
                
                <!-- Tool 组件 -->
                <template v-if="component.component_type === 'tool'">
                  <div class="metadata-tag metadata-tool">
                    <Icon icon="material-symbols:build-rounded" width="16" height="16" />
                    <span>{{ t('plugins.detail.metadata.toolComponent') }}</span>
                  </div>
                </template>
                
                <!-- Chatter 组件 -->
                <template v-if="component.component_type === 'chatter'">
                  <div class="metadata-tag metadata-chatter">
                    <Icon icon="material-symbols:chat-outline-rounded" width="16" height="16" />
                    <span>{{ t('plugins.detail.metadata.chatterComponent') }}</span>
                  </div>
                </template>
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
          <p>{{ t('plugins.detail.components.empty') }}</p>
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
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
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
  word-break: break-word;
  overflow-wrap: break-word;
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

.plugin-description-wrapper {
  margin: 0 0 0.75rem;
  position: relative;
}

.plugin-description {
  font-size: 1rem;
  line-height: 1.6;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0;
  word-break: break-word;
  overflow-wrap: break-word;
  white-space: pre-line;
}

.description-toggle-btn {
  display: none;
  background: transparent;
  border: none;
  color: var(--md-sys-color-primary);
  font-size: 0.88rem;
  font-weight: 600;
  padding: 0;
  margin-top: 0.25rem;
  cursor: pointer;
}

.description-toggle-btn:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .plugin-header-card {
    flex-direction: column;
    padding: 1.5rem;
    gap: 1.5rem;
  }

  .plugin-header-main {
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 1rem;
    width: 100%;
  }

  .plugin-meta {
    justify-content: center;
  }

  .plugin-path {
    justify-content: center;
    word-break: break-all;
  }

  .plugin-actions {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: center;
  }

  .action-btn {
    flex: 1;
    justify-content: center;
  }

  .plugin-title {
    font-size: 1.5rem;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .plugin-description-wrapper:not(.expanded) .plugin-description {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: pre-line;
    max-height: 3.2em;
    line-height: 1.6em;
  }

  .plugin-description-wrapper.expanded .plugin-description {
    max-height: none;
  }

  .plugin-description-wrapper .description-toggle-btn {
    display: inline-block;
  }
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

.action-btn-danger {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.action-btn-danger:hover {
  background: var(--md-sys-color-error);
  color: var(--md-sys-color-on-error);
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
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 88%, transparent);
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

.components-section.disabled {
  opacity: 0.6;
  pointer-events: none;
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

.disabled-hint {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.7;
  margin-left: 0.5rem;
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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.component-card {
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  border-radius: 16px;
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 85%, transparent);
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

.component-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.component-card.disabled:hover {
  border-color: var(--md-sys-color-outline-variant);
  box-shadow: none;
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

/* ====== 组件元数据标签 ====== */
.component-metadata {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.metadata-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 12px;
  font-size: 0.81rem;
  font-weight: 500;
  transition: all 0.2s;
  white-space: nowrap;
}

.metadata-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 平台标签 */
.metadata-platform {
  background: linear-gradient(135deg, var(--md-sys-color-primary-container) 0%, color-mix(in srgb, var(--md-sys-color-primary-container) 80%, var(--md-sys-color-tertiary-container)) 100%);
  color: var(--md-sys-color-on-primary-container);
  border: 1px solid var(--md-sys-color-primary);
}

/* 路径标签 */
.metadata-path {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  font-family: 'Consolas', 'Monaco', monospace;
  border: 1px solid var(--md-sys-color-secondary);
}

/* 命令标签 */
.metadata-command {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
  font-family: 'Consolas', 'Monaco', monospace;
  border: 1px solid var(--md-sys-color-tertiary);
}

/* 权限标签 */
.metadata-permission {
  border: 1px solid;
  font-weight: 600;
}

.metadata-permission.permission-owner {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
  color: white;
  border-color: #ff6b6b;
  box-shadow: 0 2px 8px rgba(255, 107, 107, 0.3);
}

.metadata-permission.permission-operator {
  background: linear-gradient(135deg, #ffa94d 0%, #ff8c42 100%);
  color: white;
  border-color: #ffa94d;
  box-shadow: 0 2px 8px rgba(255, 169, 77, 0.3);
}

.metadata-permission.permission-user {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  border-color: var(--md-sys-color-primary);
}

.metadata-permission.permission-guest {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface-variant);
  border-color: var(--md-sys-color-outline);
}

/* 动作标签 */
.metadata-action {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
  border: 1px solid var(--md-sys-color-tertiary);
}

/* 主动作标签 */
.metadata-primary {
  background: linear-gradient(135deg, #ffd93d 0%, #ffb33d 100%);
  color: #1a1a1a;
  border: 1px solid #ffd93d;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(255, 217, 61, 0.3);
}

/* Agent 标签 */
.metadata-agent {
  background: linear-gradient(135deg, var(--md-sys-color-tertiary-container) 0%, color-mix(in srgb, var(--md-sys-color-tertiary-container) 80%, var(--md-sys-color-primary-container)) 100%);
  color: var(--md-sys-color-on-tertiary-container);
  border: 1px solid var(--md-sys-color-tertiary);
}

/* Tool 标签 */
.metadata-tool {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  border: 1px solid var(--md-sys-color-secondary);
}

/* Chatter 标签 */
.metadata-chatter {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  border: 1px solid var(--md-sys-color-primary);
}

/* 通用信息标签 */
.metadata-info {
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
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
