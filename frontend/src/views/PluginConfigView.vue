<!--
  @file PluginConfigView.vue
  @description 插件配置管理视图
  
  功能：
  - 左侧插件列表
  - 右侧配置编辑器
  - 搜索过滤插件
-->
<template>
  <AppShell no-padding>
    <div class="plugin-config-view">
      <!-- 移动端顶部插件选择器 -->
      <div class="mobile-top-selector">
        <MdSelect
          v-model="selectedPluginName"
          :options="pluginOptions"
          placeholder="选择要配置的插件..."
        />
      </div>

      <!-- 左侧插件列表 -->
      <div class="plugin-list">
        <!-- 搜索框 -->
        <div class="search-box">
          <Icon icon="material-symbols:search-rounded" :size="20" />
          <input
            type="text"
            v-model="searchQuery"
            placeholder="搜索插件..."
            class="search-input"
          />
        </div>

        <!-- 插件列表 -->
        <div v-if="isLoadingList" class="list-loading">
          <Icon icon="material-symbols:progress-activity" :size="32" class="spinning" />
          <p>加载插件列表...</p>
        </div>

        <div v-else-if="filteredPlugins.length === 0" class="list-empty">
          <Icon icon="material-symbols:inbox-outline-rounded" :size="48" />
          <p>{{ searchQuery ? '未找到匹配的插件' : '暂无可配置的插件' }}</p>
        </div>

        <div v-else class="list-items">
          <button
            v-for="plugin in filteredPlugins"
            :key="plugin.plugin_name"
            type="button"
            class="plugin-item"
            :class="{ active: selectedPlugin?.plugin_name === plugin.plugin_name }"
            @click="selectPlugin(plugin)"
          >
            <div class="plugin-item-content">
              <h3 class="plugin-name">{{ plugin.config_name }}</h3>
              <p v-if="plugin.config_description" class="plugin-description">
                {{ plugin.config_description }}
              </p>
            </div>
            <Icon
              icon="material-symbols:chevron-right-rounded"
              :size="20"
              class="chevron-icon"
            />
          </button>
        </div>
      </div>

      <!-- 右侧配置编辑器 -->
      <div class="plugin-editor">
        <!-- 未选择插件 -->
        <div v-if="!selectedPlugin" class="editor-empty">
          <Icon icon="material-symbols:settings-outline-rounded" :size="64" />
          <p class="empty-text-desktop">请从左侧选择一个插件以编辑配置</p>
          <p class="empty-text-mobile">请从上方选择一个插件以编辑配置</p>
        </div>

        <!-- 加载配置 -->
        <div v-else-if="isLoadingConfig" class="editor-loading">
          <Icon icon="material-symbols:progress-activity" :size="48" class="spinning" />
          <p>加载配置中...</p>
        </div>

        <!-- 配置编辑器 -->
        <ConfigEditor
          v-else-if="currentPluginConfig"
          :title="currentPluginConfig.config_name"
          :config-path="currentPluginConfig.config_path"
          :config-type="'plugin'"
          :plugin-name="selectedPlugin.plugin_name"
          :schema="currentPluginConfig.schema"
          :model-value="currentPluginConfig.data"
          @save="handleSave"
        />

        <!-- 配置加载失败 -->
        <div v-else-if="configErrorMessage" class="editor-error">
          <Icon icon="material-symbols:error-outline-rounded" :size="48" />
          <p>{{ configErrorMessage }}</p>
          <button type="button" class="retry-btn" @click="loadPluginConfig(selectedPlugin!)">
            <Icon icon="material-symbols:refresh-rounded" :size="20" />
            <span>重试</span>
          </button>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppShell from '@/components/common/AppShell.vue'
import Icon from '@/components/common/Icon.vue'
import MdSelect from '@/components/common/MdSelect.vue'
import ConfigEditor from '@/components/config/ConfigEditor.vue'
import {
  listPluginConfigs,
  getConfig,
  fullWriteConfig,
} from '@/api/modules/config'
import type { PluginConfigEntry, EnhancedConfigResponse } from '@/api/types/config'

// 插件列表
const plugins = ref<PluginConfigEntry[]>([])
const isLoadingList = ref(false)
const searchQuery = ref('')

// 选中的插件
const selectedPlugin = ref<PluginConfigEntry | null>(null)

// 当前插件配置
const currentPluginConfig = ref<EnhancedConfigResponse | null>(null)
const isLoadingConfig = ref(false)
const configErrorMessage = ref('')

// 过滤后的插件列表
const filteredPlugins = computed(() => {
  if (!searchQuery.value) return plugins.value

  const query = searchQuery.value.toLowerCase()
  return plugins.value.filter(
    (p) =>
      p.config_name.toLowerCase().includes(query) ||
      p.plugin_name.toLowerCase().includes(query) ||
      p.config_description.toLowerCase().includes(query)
  )
})

// 加载插件列表
async function loadPluginList() {
  try {
    isLoadingList.value = true
    plugins.value = await listPluginConfigs()
  } catch (error: any) {
    console.error('加载插件列表失败:', error)
  } finally {
    isLoadingList.value = false
  }
}

// 选择插件
function selectPlugin(plugin: PluginConfigEntry) {
  selectedPlugin.value = plugin
  loadPluginConfig(plugin)
}

// 移动端顶栏选择器的双向绑定与选项
const pluginOptions = computed(() => {
  return plugins.value.map(p => ({
    label: p.config_name,
    value: p.plugin_name
  }))
})

const selectedPluginName = computed({
  get: () => selectedPlugin.value?.plugin_name || null,
  set: (val) => {
    if (val) {
      const plugin = plugins.value.find((p) => p.plugin_name === val)
      if (plugin) selectPlugin(plugin)
    }
  }
})

// 加载插件配置
async function loadPluginConfig(plugin: PluginConfigEntry) {
  try {
    isLoadingConfig.value = true
    configErrorMessage.value = ''
    currentPluginConfig.value = null

    const response = await getConfig('plugin', plugin.plugin_name)
    currentPluginConfig.value = response
  } catch (error: any) {
    configErrorMessage.value = error.message || '加载配置失败'
  } finally {
    isLoadingConfig.value = false
  }
}

// 保存配置
async function handleSave(data: Record<string, any>) {
  if (!selectedPlugin.value) return

  try {
    const response = await fullWriteConfig(
      'plugin',
      data,
      selectedPlugin.value.plugin_name
    )

    currentPluginConfig.value = response
    alert('保存成功！')
  } catch (error: any) {
    alert(`保存失败: ${error.message}`)
  }
}

// 组件挂载时加载插件列表
onMounted(() => {
  loadPluginList()
})
</script>

<style scoped>
.plugin-config-view {
  display: flex;
  align-items: stretch;
  height: calc(100dvh - 64px);
  min-height: 0;
  overflow: hidden;
}

/* 左侧插件列表 */
.plugin-list {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: color-mix(in srgb, var(--md-sys-color-surface) 90%, transparent);
  backdrop-filter: blur(12px);
  border-right: 1px solid var(--md-sys-color-outline-variant);
  height: 100%;
  min-height: 0;
  z-index: 5;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  background: transparent;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  font-size: 14px;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  border: none;
  outline: none;
  font-family: inherit;
}

.search-input::placeholder {
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.6;
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

.list-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.plugin-item {
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

.plugin-item:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.plugin-item.active {
  background: var(--md-sys-color-secondary-container);
}

.plugin-item-content {
  flex: 1;
  min-width: 0;
}

.plugin-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plugin-item.active .plugin-name {
  color: var(--md-sys-color-on-secondary-container);
}

.plugin-description {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.plugin-item.active .plugin-description {
  color: var(--md-sys-color-on-secondary-container);
  opacity: 0.8;
}

.chevron-icon {
  color: var(--md-sys-color-on-surface-variant);
  flex-shrink: 0;
}

.plugin-item.active .chevron-icon {
  color: var(--md-sys-color-on-secondary-container);
}

/* 右侧编辑器区域 */
.plugin-editor {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: transparent;
}

.editor-empty,
.editor-loading,
.editor-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px;
  color: var(--md-sys-color-on-surface-variant);
}

.editor-empty p,
.editor-loading p,
.editor-error p {
  font-size: 16px;
  text-align: center;
  margin: 0;
}

.empty-text-mobile {
  display: none;
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
  background: color-mix(in srgb, var(--md-sys-color-surface) 90%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

/* 响应式布局 */
@media (max-width: 768px) {
  .plugin-config-view {
    flex-direction: column;
  }
  
  .mobile-top-selector {
    display: block;
  }

  .plugin-list {
    display: none;
  }
  
  .plugin-editor {
    min-height: calc(100dvh - 180px);
  }

  .empty-text-desktop {
    display: none;
  }

  .empty-text-mobile {
    display: block;
  }
}
</style>
