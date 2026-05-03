<!--
  @file ConfigView.vue
  @description 配置管理主视图（机器人配置 + 模型配置）
  
  功能：
  - Tab 切换（机器人配置 / 模型配置）
  - 使用 ConfigEditor 和 ModelConfigEditor
  - 数据加载、保存、错误处理
-->
<template>
  <AppShell no-padding>
    <template #title>
      <Icon icon="material-symbols:settings-outline-rounded" :size="24" />
      <span>配置管理</span>
    </template>

    <div class="config-view">
      <!-- Tab 切换 -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === tab.value }"
          @click="switchTab(tab.value)"
        >
          <Icon :icon="tab.icon" :size="20" />
          <span>{{ tab.label }}</span>
        </button>
      </div>

      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-container">
        <Icon icon="material-symbols:progress-activity" :size="48" class="spinning" />
        <p>加载配置中...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="errorMessage" class="error-container">
        <Icon icon="material-symbols:error-outline-rounded" :size="48" />
        <p>{{ errorMessage }}</p>
        <button type="button" class="retry-btn" @click="loadConfig">
          <Icon icon="material-symbols:refresh-rounded" :size="20" />
          <span>重试</span>
        </button>
      </div>

      <!-- 配置编辑器 -->
      <div v-else class="config-content">
        <!-- 机器人配置 -->
        <ConfigEditor
          v-if="activeTab === 'bot' && botConfig"
          :title="botConfig?.config_name"
          :config-path="botConfig?.config_path"
          :config-type="'bot'"
          :schema="botConfig?.schema"
          :model-value="botConfig?.data"
          @save="handleSave('bot', $event)"
        />

        <!-- 模型配置 -->
        <ModelConfigEditor
          v-else-if="activeTab === 'model' && modelConfig"
          :title="modelConfig?.config_name"
          :config-path="modelConfig?.config_path"
          :schema="modelConfig?.schema"
          :model-value="modelConfig?.data"
          @save="handleSave('model', $event)"
        />
      </div>
    </div>
  </AppShell>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/common/AppShell.vue'
import Icon from '@/components/common/Icon.vue'
import ConfigEditor from '@/components/config/ConfigEditor.vue'
import ModelConfigEditor from '@/components/config/ModelConfigEditor.vue'
import { getConfig, fullWriteConfig } from '@/api/modules/config'
import type { EnhancedConfigResponse } from '@/api/types/config'

// 路由
const router = useRouter()

// Tab 定义
const tabs = [
  { value: 'bot' as const, label: '机器人配置', icon: 'material-symbols:smart-toy-outline-rounded' },
  { value: 'model' as const, label: '模型配置', icon: 'material-symbols:model-training-outline-rounded' },
]

// 当前激活的 Tab
const activeTab = ref<'bot' | 'model'>('bot')

// 配置数据
const botConfig = ref<EnhancedConfigResponse | null>(null)
const modelConfig = ref<EnhancedConfigResponse | null>(null)

// 加载状态
const isLoading = ref(false)
const errorMessage = ref('')

// 切换 Tab
function switchTab(tab: 'bot' | 'model') {
  activeTab.value = tab
  // 更新 URL 查询参数
  router.replace({ query: { tab } })
}

// 加载配置
async function loadConfig() {
  console.log('[ConfigView] 开始加载配置...')
  try {
    isLoading.value = true
    errorMessage.value = ''

    // 并行加载两个配置
    console.log('[ConfigView] 发起 API 请求...')
    const [botResponse, modelResponse] = await Promise.all([
      getConfig('bot'),
      getConfig('model'),
    ])

    console.log('[ConfigView] Bot 配置:', botResponse)
    console.log('[ConfigView] Model 配置:', modelResponse)

    botConfig.value = botResponse
    modelConfig.value = modelResponse
    
    console.log('[ConfigView] 配置加载成功')
  } catch (error: any) {
    console.error('[ConfigView] 配置加载失败:', error)
    errorMessage.value = error.message || '加载配置失败'
  } finally {
    isLoading.value = false
  }
}

// 保存配置
async function handleSave(configType: 'bot' | 'model', data: Record<string, any>) {
  console.log(`[ConfigView] handleSave 被调用:`, { configType, dataKeys: Object.keys(data) })
  try {
    const response = await fullWriteConfig(configType, data)

    // 更新本地数据（会触发子组件的 watch，更新 originalData）
    if (configType === 'bot') {
      botConfig.value = response
      console.log('[ConfigView] Bot 配置保存成功，已更新 botConfig')
    } else {
      modelConfig.value = response
      console.log('[ConfigView] Model 配置保存成功，已更新 modelConfig')
    }

    // 显示成功提示（可以集成 Toast 组件）
  } catch (error: any) {
    console.error(`[ConfigView] 保存 ${configType} 配置失败:`, error)
    // 显示错误提示（可以集成 Toast 组件）
  }
}

// 组件挂载时加载配置
onMounted(() => {
  // 从 URL 查询参数恢复 Tab 状态
  const tabParam = router.currentRoute.value.query.tab as string
  if (tabParam === 'model') {
    activeTab.value = 'model'
  }

  loadConfig()
})
</script>

<style scoped>
.config-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--md-sys-color-background);
}

/* Tab 栏 */
.tab-bar {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  background: var(--md-sys-color-surface);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  flex-shrink: 0;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.tab-btn:hover {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
}

.tab-btn.active {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  font-weight: 600;
}

/* 加载和错误状态 */
.loading-container,
.error-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--md-sys-color-on-surface-variant);
}

.loading-container p,
.error-container p {
  font-size: 16px;
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

/* 配置内容区 */
.config-content {
  flex: 1;
  overflow: hidden;
  /* 移除 padding，让 ModelConfigEditor 自己管理布局 */
}
</style>
