<!--
  @file McpConfigEditor.vue
  @description MCP 配置专用编辑器
-->
<template>
  <div class="mcp-config-editor">
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <h2 class="config-title">{{ title }}</h2>
        <span v-if="configPath" class="config-path">{{ configPath }}</span>
      </div>

      <div class="toolbar-right">
        <button
          type="button"
          class="mode-toggle-btn"
          @click="toggleEditMode"
          :title="isCodeMode ? t('configEditor.modeToggle.toForm') : t('configEditor.modeToggle.toCode')"
        >
          <Icon
            :icon="isCodeMode ? 'material-symbols:edit-note-rounded' : 'material-symbols:code-rounded'"
            :size="20"
          />
          <span>{{ isCodeMode ? t('configEditor.modeToggle.formLabel') : t('configEditor.modeToggle.codeLabel') }}</span>
        </button>

        <button
          type="button"
          class="save-btn"
          @click="handleSave"
          :disabled="isSaving || !hasChanges"
          :title="hasChanges ? t('configEditor.save.hasChanges') : t('configEditor.save.noChanges')"
        >
          <Icon
            v-if="!isSaving"
            icon="material-symbols:save-outline-rounded"
            :size="20"
          />
          <Icon
            v-else
            icon="material-symbols:progress-activity"
            :size="20"
            class="spinning"
          />
          <span>{{ isSaving ? t('configEditor.save.saving') : t('configEditor.save.button') }}</span>
        </button>
      </div>
    </div>

    <div class="editor-content">
      <TomlEditor
        v-if="isCodeMode"
        v-model="codeContent"
        :readonly="readonly"
      />

      <div v-else class="form-mode">
        <div class="tab-bar">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="tab-button"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            <Icon :icon="tab.icon" :size="20" />
            <span>{{ tab.label }}</span>
          </button>
        </div>

        <div class="tab-content">
          <div class="config-section">
            <div class="section-header">
              <h3>{{ activeTabConfig.title }}</h3>
            </div>
            <div class="sticky-action-row">
              <button type="button" class="add-btn" @click="addServer">
                <Icon icon="material-symbols:add-rounded" :size="20" />
                <span>{{ t('modelConfigEditor.actions.add') }}</span>
              </button>
            </div>

            <div v-if="serverEntries.length > 0" class="config-list">
              <div
                v-for="server in serverEntries"
                :key="server.name"
                class="config-card"
              >
                <div class="card-header">
                  <div class="card-title">
                    <Icon :icon="activeTabConfig.icon" :size="24" />
                    <span>{{ server.name }}</span>
                  </div>
                  <div class="card-actions">
                    <button type="button" class="icon-btn" @click="testServer(server.name)" :disabled="testingServers.has(server.name)" :title="t('modelConfigEditor.actions.test')">
                      <Icon v-if="!testingServers.has(server.name)" icon="material-symbols:play-arrow-rounded" :size="20" />
                      <Icon v-else icon="material-symbols:progress-activity" :size="20" class="spinning" />
                    </button>
                    <button type="button" class="icon-btn" @click="editServer(server.name)" :title="t('modelConfigEditor.actions.edit')">
                      <Icon icon="material-symbols:edit-outline-rounded" :size="20" />
                    </button>
                    <button type="button" class="icon-btn danger" @click="deleteServer(server.name)" :title="t('modelConfigEditor.actions.delete')">
                      <Icon icon="material-symbols:delete-outline-rounded" :size="20" />
                    </button>
                  </div>
                </div>

                <div class="card-body">
                  <div class="info-grid">
                    <div
                      v-for="field in server.fields"
                      :key="field.key"
                      class="info-item"
                    >
                      <span class="label">{{ field.key }}</span>
                      <span class="value">{{ field.value }}</span>
                    </div>
                  </div>
                  <div v-if="testResults.has(server.name)" class="test-result" :class="testResults.get(server.name)!.success ? 'success' : 'error'">
                    <Icon :icon="testResults.get(server.name)!.success ? 'material-symbols:check-circle-outline-rounded' : 'material-symbols:error-outline-rounded'" :size="18" />
                    <div class="result-content">
                      <p class="result-message">
                        {{ testResults.get(server.name)!.success ? t('modelConfigEditor.test.success') : t('modelConfigEditor.test.failed') }}: {{ testResults.get(server.name)!.message }}
                        <span v-if="testResults.get(server.name)!.latency_ms">（{{ t('modelConfigEditor.test.latency') }}: {{ testResults.get(server.name)!.latency_ms?.toFixed(0) }} ms）</span>
                      </p>
                      <p v-if="testResults.get(server.name)!.detail" class="result-detail">{{ testResults.get(server.name)!.detail }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="empty-state">
              <Icon icon="material-symbols:info-outline-rounded" :size="48" />
              <p>{{ t('mcpConfigEditor.empty') }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="errorMessage" class="error-banner">
      <Icon icon="material-symbols:error-outline-rounded" :size="20" />
      <span>{{ errorMessage }}</span>
      <button type="button" @click="errorMessage = ''" class="close-btn">
        <Icon icon="material-symbols:close-rounded" :size="16" />
      </button>
    </div>
    <McpEditDialog
      :is-open="dialog.isOpen"
      :type="activeTab"
      :mode="dialog.mode"
      :data="dialog.data"
      @close="closeDialog"
      @submit="handleDialogSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { parse as parseToml } from 'toml'
import { useI18n } from '@/utils/i18n'
import { useDialogStore } from '@/utils/dialog'
import Icon from '../common/Icon.vue'
import TomlEditor from './TomlEditor.vue'
import McpEditDialog from './McpEditDialog.vue'
import { getRawConfig, testMcpServer as apiTestMcpServer } from '@/api/modules/config'
import type { McpTestResult } from '@/api/types/config'

const { t } = useI18n()
const dialogStore = useDialogStore()

interface Props {
  title: string
  configPath?: string
  modelValue: Record<string, any>
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
  save: [data: Record<string, any>]
}>()

type McpTab = 'stdio' | 'sse' | 'streamable'

const isCodeMode = ref(false)
const activeTab = ref<McpTab>('stdio')
const localData = ref<Record<string, any>>({ ...props.modelValue })
const originalData = ref<Record<string, any>>({})
const codeContent = ref('')
const isSaving = ref(false)
const errorMessage = ref('')
const testingServers = ref(new Set<string>())
const testResults = ref(new Map<string, McpTestResult>())
const dialog = ref<{
  isOpen: boolean
  mode: 'add' | 'edit'
  data: Record<string, any>
}>({
  isOpen: false,
  mode: 'add',
  data: {},
})

const tabs = computed(() => [
  { key: 'stdio' as const, label: t('mcpConfigEditor.tabs.stdio'), title: t('mcpConfigEditor.sections.stdio'), icon: 'material-symbols:terminal-rounded' },
  { key: 'sse' as const, label: t('mcpConfigEditor.tabs.sse'), title: t('mcpConfigEditor.sections.sse'), icon: 'material-symbols:sync-alt-rounded' },
  { key: 'streamable' as const, label: t('mcpConfigEditor.tabs.streamable'), title: t('mcpConfigEditor.sections.streamable'), icon: 'material-symbols:http-rounded' },
])

const activeTabConfig = computed(() => tabs.value.find((tab) => tab.key === activeTab.value) ?? tabs.value[0])

const hasChanges = computed(() => JSON.stringify(localData.value) !== JSON.stringify(originalData.value))

const sectionMap: Record<McpTab, string> = {
  stdio: 'stdio_servers',
  sse: 'sse_servers',
  streamable: 'streamable_http_servers',
}

const serverEntries = computed(() => {
  const servers = getActiveServers()

  return Object.entries(servers).map(([name, value]) => ({
    name,
    fields: normalizeFields(value),
  }))
})

function normalizeFields(value: unknown) {
  if (typeof value === 'string') {
    return [{ key: 'url', value }]
  }
  if (!value || typeof value !== 'object') {
    return [{ key: 'value', value: String(value ?? '') }]
  }

  return Object.entries(value as Record<string, unknown>).map(([key, item]) => ({
    key,
    value: Array.isArray(item) ? item.join(' ') : typeof item === 'object' ? JSON.stringify(item) : String(item ?? ''),
  }))
}

onMounted(async () => {
  try {
    codeContent.value = await getRawConfig('mcp')
  } catch (error: any) {
    errorMessage.value = error.message
  }
})

watch(
  () => props.modelValue,
  (newValue) => {
    localData.value = JSON.parse(JSON.stringify(newValue || {}))
    // 规范化：确保 mcp 下的 server 字段为 dict 而非空字符串
    if (localData.value.mcp && typeof localData.value.mcp === 'object') {
      for (const key of ['stdio_servers', 'sse_servers', 'streamable_http_servers']) {
        if (key in localData.value.mcp && typeof localData.value.mcp[key] !== 'object') {
          localData.value.mcp[key] = {}
        }
      }
    }
    originalData.value = JSON.parse(JSON.stringify(localData.value))
  },
  { immediate: true, deep: true }
)

function getActiveServers() {
  const mcpConfig = localData.value.mcp || {}
  return mcpConfig[sectionMap[activeTab.value]] || {}
}

function ensureActiveSection() {
  if (!localData.value.mcp) {
    localData.value.mcp = {}
  }
  const sectionKey = sectionMap[activeTab.value]
  if (!localData.value.mcp[sectionKey]) {
    localData.value.mcp[sectionKey] = {}
  }
  return localData.value.mcp[sectionKey] as Record<string, any>
}

function addServer() {
  dialog.value = {
    isOpen: true,
    mode: 'add',
    data: {},
  }
}

function editServer(name: string) {
  const value = getActiveServers()[name]
  dialog.value = {
    isOpen: true,
    mode: 'edit',
    data: {
      name,
      ...(typeof value === 'object' && value !== null ? value : { value }),
    },
  }
}

async function deleteServer(name: string) {
  const confirmed = await dialogStore.confirm(`确定要删除 MCP 服务 ${name} 吗？`)
  if (confirmed) {
    const servers = ensureActiveSection()
    delete servers[name]
  }
}

async function testServer(name: string) {
  if (testingServers.value.has(name)) return

  try {
    testingServers.value.add(name)
    testResults.value.delete(name)
    const config = getActiveServers()[name]
    const result = await apiTestMcpServer({
      server_type: activeTab.value,
      name,
      config,
      timeout: 10,
    })
    testResults.value.set(name, result)
  } catch (error: any) {
    testResults.value.set(name, {
      success: false,
      message: '连接失败',
      detail: error.message || String(error),
    })
  } finally {
    testingServers.value.delete(name)
  }
}

function closeDialog() {
  dialog.value.isOpen = false
}

function handleDialogSubmit(data: Record<string, any>) {
  const servers = ensureActiveSection()
  const { name, ...serverValue } = data
  servers[name] = 'value' in serverValue && Object.keys(serverValue).length === 1
    ? serverValue.value
    : serverValue
  closeDialog()
}

async function toggleEditMode() {
  if (isCodeMode.value) {
    try {
      localData.value = parseToml(codeContent.value)
      errorMessage.value = ''
      isCodeMode.value = false
    } catch (error: any) {
      errorMessage.value = t('configEditor.errors.tomlParse', { error: error.message })
    }
  } else {
    try {
      codeContent.value = await getRawConfig('mcp')
      errorMessage.value = ''
      isCodeMode.value = true
    } catch (error: any) {
      errorMessage.value = t('configEditor.errors.loadRawToml', { error: error.message })
    }
  }
}

async function handleSave() {
  if (isSaving.value || !hasChanges.value) return

  try {
    isSaving.value = true
    errorMessage.value = ''
    const dataToSave = isCodeMode.value ? parseToml(codeContent.value) : localData.value
    emit('save', dataToSave)
    emit('update:modelValue', dataToSave)
    originalData.value = JSON.parse(JSON.stringify(dataToSave))
  } catch (error: any) {
    errorMessage.value = t('configEditor.save.failed', { error: error.message })
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.mcp-config-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.config-path {
  font-size: 12px;
  color: var(--md-sys-color-outline);
  padding: 4px 8px;
  background: var(--md-sys-color-surface-container);
  border-radius: 4px;
}

.toolbar-right {
  display: flex;
  gap: 12px;
}

.mode-toggle-btn,
.save-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.mode-toggle-btn {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.mode-toggle-btn:hover {
  background: var(--md-sys-color-secondary);
  color: var(--md-sys-color-on-secondary);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.save-btn {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.save-btn:hover:not(:disabled) {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.editor-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(16px);
}

.form-mode {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tab-bar {
  display: flex;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  padding: 0 24px;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  font-size: 14px;
  font-weight: 500;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  position: relative;
}

.tab-button:hover {
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
}

.tab-button.active {
  color: var(--md-sys-color-primary);
  border-bottom-color: var(--md-sys-color-primary);
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: color-mix(in srgb, var(--md-sys-color-surface) 80%, transparent);
  backdrop-filter: blur(16px);
}

.config-section {
  max-width: 1200px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.sticky-action-row {
  position: sticky;
  top: 8px;
  z-index: 1;
  display: flex;
  justify-content: flex-end;
  margin-top: -30px;
  margin-right: -100px;
  margin-bottom: 20px;
  pointer-events: none;
}

.sticky-action-row .add-btn {
  pointer-events: auto;
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.add-btn:hover {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.config-list {
  display: grid;
  gap: 16px;
}

.config-card {
  background: var(--md-sys-color-surface-container);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s;
}

.config-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.card-actions {
  display: flex;
  gap: 8px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  transform: scale(1.1);
}

.icon-btn.danger:hover {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 500;
}

.value {
  font-size: 14px;
  color: var(--md-sys-color-on-surface);
  word-break: break-all;
}

.test-result {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
}

.test-result.success {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.test-result.error {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-message,
.result-detail {
  margin: 0;
  white-space: pre-wrap;
}

.result-detail {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 24px;
  color: var(--md-sys-color-on-surface-variant);
}

.empty-state p {
  margin: 0;
  font-size: 15px;
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
  flex-shrink: 0;
}

.close-btn {
  margin-left: auto;
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
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

/* ===== 移动端适配 ===== */
@media screen and (max-width: 768px) {
  .editor-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
  }

  .toolbar-left {
    width: 100%;
  }

  .toolbar-right {
    width: 100%;
    justify-content: space-between;
  }

  .mode-toggle-btn,
  .save-btn {
    flex: 1;
    justify-content: center;
  }

  .tab-bar {
    padding: 0;
    overflow-x: auto;
    white-space: nowrap;
    scrollbar-width: none;
  }

  .tab-bar::-webkit-scrollbar {
    display: none;
  }

  .tab-button {
    padding: 12px 16px;
    flex-shrink: 0;
    white-space: nowrap;
  }

  .tab-content {
    padding: 16px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;
  }

  .sticky-action-row {
    position: static;
    margin-top: 0;
    margin-right: 0;
    margin-bottom: 16px;
    pointer-events: auto;
  }

  .sticky-action-row .add-btn {
    width: 100%;
    justify-content: center;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .card-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .info-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .config-card {
    padding: 16px;
  }

  .test-result {
    flex-direction: column;
    align-items: flex-start;
  }

  .empty-state {
    padding: 48px 16px;
  }
}
</style>
