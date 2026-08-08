<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Icon from '../common/Icon.vue'
import {
  getMarketCapabilities,
  getMarketInstallPlan,
  getMarketOperation,
  getMarketPluginDetail,
  getMarketPluginReadme,
  startMarketInstall,
} from '../../api/modules/plugin-market'
import type {
  InstallPlan,
  MarketCapabilities,
  MarketOperation,
  MarketPluginDetail,
  MarketPluginReadme,
  MarketVersion,
} from '../../api/types/plugin-market'
import { useDialogStore } from '../../utils/dialog'
import { useI18n } from '../../utils/i18n'
import { useToastStore } from '../../utils/toast'

type ReadmeTheme = {
  mode: 'light' | 'dark'
  background: string
  foreground: string
  muted: string
  primary: string
  container: string
  outline: string
}

const props = defineProps<{
  pluginId: string
}>()

const emit = defineEmits<{
  close: []
  changed: [pluginId: string]
  configure: [pluginId: string]
  manage: [pluginId: string]
}>()

const dialogStore = useDialogStore()
const toastStore = useToastStore()
const { t } = useI18n()

const detail = ref<MarketPluginDetail | null>(null)
const readme = ref<MarketPluginReadme | null>(null)
const capabilities = ref<MarketCapabilities | null>(null)
const selectedVersion = ref('')
const activeTab = ref<'info' | 'docs'>('info')
const operation = ref<MarketOperation | null>(null)
const isLoading = ref(true)
const isReadmeLoading = ref(true)
const isPlanning = ref(false)
const errorMessage = ref('')
const readmeErrorMessage = ref('')
const imageFailed = ref(false)
const isDescriptionExpanded = ref(false)
const isDescriptionTruncated = ref(false)
let descriptionResizeTimer: number | null = null
const readmeTheme = ref<ReadmeTheme>({
  mode: 'light',
  background: '#fef7ff',
  foreground: '#1d1b20',
  muted: '#49454f',
  primary: '#6750a4',
  container: '#f3edf7',
  outline: '#cac4d0',
})
let pollTimer: number | null = null
let themeObserver: MutationObserver | null = null

const plugin = computed(() => detail.value?.plugin ?? null)

const readmeDocument = computed(() => {
  if (!readme.value?.exists || !readme.value.html) return ''
  const theme = readmeTheme.value
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; font-src https: data:;"
  >
  <base target="_blank">
  <style>
    :root {
      color-scheme: ${theme.mode};
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
    }
    body {
      margin: 0;
      padding: 1.1rem;
      color: ${theme.foreground};
      background: ${theme.background};
      line-height: 1.7;
      overflow-wrap: anywhere;
    }
    h1, h2, h3, h4 { margin: 1.4em 0 0.6em; line-height: 1.3; }
    h1:first-child, h2:first-child { margin-top: 0; }
    p, ul, ol, blockquote, pre, table { margin: 0.8rem 0; }
    a { color: ${theme.primary}; }
    img { max-width: 100%; height: auto; border-radius: 8px; }
    code { padding: 0.12em 0.35em; border-radius: 5px; background: ${theme.container}; }
    pre { overflow: auto; padding: 0.9rem; border-radius: 8px; background: ${theme.container}; }
    pre code { padding: 0; background: transparent; }
    blockquote {
      margin-left: 0;
      padding-left: 0.9rem;
      color: ${theme.muted};
      border-left: 4px solid ${theme.primary};
    }
    table { display: block; width: 100%; overflow-x: auto; border-collapse: collapse; }
    th, td { padding: 0.55rem 0.7rem; border: 1px solid ${theme.outline}; text-align: left; }
  </style>
</head>
<body>${readme.value.html}</body>
</html>`
})

const selectedVersionInfo = computed<MarketVersion | null>(() => {
  return detail.value?.versions.find((item) => item.version === selectedVersion.value) ?? null
})

const isOperationActive = computed(() => {
  return operation.value?.status === 'queued' || operation.value?.status === 'running'
})

const primaryActionLabel = computed(() => {
  if (isOperationActive.value) return operation.value?.message ?? t('pluginMarket.detail.processing')
  if (plugin.value?.local_state.update_available) return t('pluginMarket.detail.update')
  return t('pluginMarket.detail.install')
})

const primaryActionIcon = computed(() => {
  if (isOperationActive.value) return 'material-symbols:progress-activity'
  if (plugin.value?.local_state.update_available) return 'material-symbols:update-rounded'
  return 'material-symbols:download-rounded'
})

const canStartInstall = computed(() => {
  if (!plugin.value || !capabilities.value?.install_enabled || isOperationActive.value) return false
  if (!selectedVersionInfo.value) return false
  return canInstallVersion(selectedVersionInfo.value)
})

function canInstallVersion(version: MarketVersion): boolean {
  if (!plugin.value || !capabilities.value?.install_enabled || isOperationActive.value) return false
  if (version.is_yanked || version.status !== 'published') return false
  if (version.compatibility.status === 'incompatible') return false
  return !(
    plugin.value.local_state.installed
    && plugin.value.local_state.installed_version === version.version
  )
}

const isLatestSelected = computed(() => {
  const versions = detail.value?.versions ?? []
  if (!versions.length || !selectedVersion.value) return false
  const latest = versions.find((item) => item.status === 'published' && !item.is_yanked)
    ?? versions[0]
  return latest?.version === selectedVersion.value
})

const pluginInitial = computed(() => {
  const value = plugin.value?.display_name || plugin.value?.plugin_id || 'P'
  return value.trim().slice(0, 1).toUpperCase()
})

const descriptionText = computed(() => {
  return plugin.value?.description || plugin.value?.summary || ''
})

const MOBILE_DESCRIPTION_LIMIT = 20

function checkDescriptionTruncation(): void {
  const isMobile = window.innerWidth <= 560
  if (!isMobile) {
    isDescriptionTruncated.value = false
    isDescriptionExpanded.value = false
    return
  }
  isDescriptionTruncated.value = descriptionText.value.length > MOBILE_DESCRIPTION_LIMIT
}

function handleDescriptionResize(): void {
  if (descriptionResizeTimer !== null) {
    window.clearTimeout(descriptionResizeTimer)
  }
  descriptionResizeTimer = window.setTimeout(() => {
    checkDescriptionTruncation()
  }, 150)
}

async function loadDetail(): Promise<void> {
  if (!props.pluginId) return
  isLoading.value = true
  errorMessage.value = ''
  imageFailed.value = false
  try {
    const [nextDetail, nextCapabilities] = await Promise.all([
      getMarketPluginDetail(props.pluginId),
      getMarketCapabilities(),
    ])
    detail.value = nextDetail
    capabilities.value = nextCapabilities
    const currentSelection = nextDetail.versions.some((item) => item.version === selectedVersion.value)
    if (!currentSelection) {
      selectedVersion.value = nextDetail.recommended_version?.version
        ?? nextDetail.versions.find((item) => item.status === 'published' && !item.is_yanked)?.version
        ?? nextDetail.versions[0]?.version
        ?? ''
      activeTab.value = 'info'
    }
    isDescriptionExpanded.value = false
    checkDescriptionTruncation()
  } catch (error: unknown) {
    errorMessage.value = errorText(error)
  } finally {
    isLoading.value = false
  }
}

async function loadReadme(): Promise<void> {
  if (!props.pluginId) return
  isReadmeLoading.value = true
  readmeErrorMessage.value = ''
  try {
    readme.value = await getMarketPluginReadme(props.pluginId)
  } catch (error: unknown) {
    readme.value = null
    readmeErrorMessage.value = errorText(error)
  } finally {
    isReadmeLoading.value = false
  }
}

async function refreshDetail(): Promise<void> {
  await Promise.all([loadDetail(), loadReadme()])
}

function syncReadmeTheme(): void {
  const root = document.documentElement
  const styles = getComputedStyle(root)
  const readColor = (name: string, fallback: string): string => {
    return styles.getPropertyValue(name).trim() || fallback
  }
  const isDark = root.getAttribute('data-theme') === 'dark'
  readmeTheme.value = {
    mode: isDark ? 'dark' : 'light',
    background: readColor('--md-sys-color-surface', isDark ? '#141218' : '#fef7ff'),
    foreground: readColor('--md-sys-color-on-surface', isDark ? '#e6e0e9' : '#1d1b20'),
    muted: readColor('--md-sys-color-on-surface-variant', isDark ? '#cac4d0' : '#49454f'),
    primary: readColor('--md-sys-color-primary', isDark ? '#d0bcff' : '#6750a4'),
    container: readColor('--md-sys-color-surface-container-high', isDark ? '#2b292f' : '#ece6f0'),
    outline: readColor('--md-sys-color-outline-variant', isDark ? '#49454f' : '#cac4d0'),
  }
}

async function beginInstall(versionOverride?: string): Promise<void> {
  if (!plugin.value) return
  const targetVersion = versionOverride ?? selectedVersion.value
  if (!targetVersion) return
  const versionInfo = detail.value?.versions.find((item) => item.version === targetVersion) ?? null
  if (!versionInfo || !canInstallVersion(versionInfo)) {
    if (versionOverride) selectedVersion.value = targetVersion
    return
  }
  if (versionOverride && selectedVersion.value !== versionOverride) {
    selectedVersion.value = versionOverride
  }
  isPlanning.value = true
  try {
    const plan = await getMarketInstallPlan(plugin.value.plugin_id, targetVersion || null)
    if (!plan.can_install) {
      await dialogStore.alert(plan.blocking_reasons.join('\n'), t('pluginMarket.detail.blockedTitle'))
      return
    }
    const confirmed = await dialogStore.confirm(
      planMessage(plan),
      plan.action === 'update'
        ? t('pluginMarket.detail.updateConfirmTitle')
        : t('pluginMarket.detail.installConfirmTitle'),
      plan.action === 'update' ? t('pluginMarket.detail.update') : t('pluginMarket.detail.install'),
      t('pluginMarket.detail.cancel'),
    )
    if (!confirmed) return
    operation.value = await startMarketInstall(plugin.value.plugin_id, plan.version.version)
    schedulePoll()
  } catch (error: unknown) {
    toastStore.show(errorText(error), 'error', 6000)
  } finally {
    isPlanning.value = false
  }
}

function schedulePoll(): void {
  stopPolling()
  pollTimer = window.setTimeout(() => {
    void pollOperation()
  }, 700)
}

async function pollOperation(): Promise<void> {
  if (!operation.value) return
  try {
    operation.value = await getMarketOperation(operation.value.operation_id)
    if (operation.value.status === 'queued' || operation.value.status === 'running') {
      schedulePoll()
      return
    }
    if (operation.value.status === 'succeeded') {
      const message = operation.value.result?.restart_required
        ? t('pluginMarket.detail.operationRestartRequired')
        : t('pluginMarket.detail.operationSucceeded')
      toastStore.show(message, 'success', 6000)
      await loadDetail()
      emit('changed', props.pluginId)
    } else {
      toastStore.show(
        operation.value.error_message || t('pluginMarket.detail.operationFailed'),
        'error',
        7000,
      )
    }
  } catch (error: unknown) {
    operation.value = operation.value
      ? { ...operation.value, status: 'failed', error_message: errorText(error), message: errorText(error) }
      : null
    toastStore.show(errorText(error), 'error', 6000)
  }
}

function stopPolling(): void {
  if (pollTimer !== null) {
    window.clearTimeout(pollTimer)
    pollTimer = null
  }
}

function openConfig(): void {
  if (!plugin.value) return
  emit('configure', plugin.value.plugin_id)
}

function openManage(): void {
  if (!plugin.value) return
  emit('manage', plugin.value.plugin_id)
}

function downloadVersion(version: MarketVersion): void {
  if (!version.asset_download_url) return
  const link = document.createElement('a')
  link.href = version.asset_download_url
  link.download = version.asset_name || ''
  link.target = '_blank'
  link.rel = 'noopener noreferrer'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function isVersionInstalled(version: MarketVersion): boolean {
  return Boolean(plugin.value?.local_state.installed
    && plugin.value.local_state.installed_version === version.version)
}

function installVersionLabel(version: MarketVersion): string {
  if (isVersionInstalled(version)) return t('pluginMarket.detail.installed')
  if (plugin.value?.local_state.installed) {
    return plugin.value.local_state.update_available
      ? t('pluginMarket.detail.update')
      : t('pluginMarket.detail.switchVersion')
  }
  return t('pluginMarket.detail.install')
}

function installVersionIcon(version: MarketVersion): string {
  if (isVersionInstalled(version)) return 'material-symbols:check-circle-outline-rounded'
  if (plugin.value?.local_state.installed) return 'material-symbols:swap-vert-rounded'
  return 'material-symbols:download-rounded'
}

function planMessage(plan: InstallPlan): string {
  const lines = [
    `${plan.plugin.display_name} @ ${plan.version.version}`,
    t('pluginMarket.detail.planSource', { source: plan.plugin.repository_url || plan.plugin.homepage || '—' }),
    t('pluginMarket.detail.planSize', { size: formatBytes(plan.version.file_size) }),
  ]
  if (plan.dependencies.length) {
    lines.push(t('pluginMarket.detail.planDependencies', { count: String(plan.dependencies.length) }))
  }
  if (plan.warnings.length) {
    lines.push('', t('pluginMarket.detail.planWarnings'), ...plan.warnings.map((item) => `• ${item}`))
  }
  lines.push('', t('pluginMarket.detail.planRestart'))
  return lines.join('\n')
}

function formatBytes(value: number | null): string {
  if (value === null) return t('pluginMarket.detail.unknown')
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
  }).format(date)
}

function errorText(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error !== null && 'message' in error) return String(error.message)
  return t('pluginMarket.error.fallback')
}

onMounted(() => {
  syncReadmeTheme()
  themeObserver = new MutationObserver(syncReadmeTheme)
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme', 'style'],
  })
  window.addEventListener('resize', handleDescriptionResize)
  void refreshDetail()
})

onBeforeUnmount(() => {
  stopPolling()
  themeObserver?.disconnect()
  themeObserver = null
  window.removeEventListener('resize', handleDescriptionResize)
  if (descriptionResizeTimer !== null) {
    window.clearTimeout(descriptionResizeTimer)
    descriptionResizeTimer = null
  }
})
</script>

<template>
  <section class="detail-page">
      <header class="detail-toolbar">
        <button class="back-button" type="button" @click="emit('close')">
          <Icon icon="material-symbols:arrow-back-rounded" width="20" height="20" />
          {{ t('pluginMarket.detail.back') }}
        </button>
        <button
          class="icon-button"
          type="button"
          :title="t('pluginMarket.refresh')"
          :aria-label="t('pluginMarket.refresh')"
          :disabled="isLoading || isOperationActive"
          @click="refreshDetail"
        >
          <Icon icon="material-symbols:refresh-rounded" width="21" height="21" />
        </button>
      </header>

      <div class="detail-scroll">
        <div v-if="isLoading" class="state-panel" aria-busy="true">
          <Icon icon="material-symbols:progress-activity" width="46" height="46" class="spinning" />
          <p>{{ t('pluginMarket.detail.loading') }}</p>
        </div>

        <div v-else-if="errorMessage" class="state-panel error-state">
          <Icon icon="material-symbols:error-outline-rounded" width="48" height="48" />
          <h2>{{ t('pluginMarket.detail.errorTitle') }}</h2>
          <p>{{ errorMessage }}</p>
          <button class="primary-button" type="button" @click="loadDetail">
            <Icon icon="material-symbols:refresh-rounded" width="19" height="19" />
            {{ t('pluginMarket.retry') }}
          </button>
        </div>

        <template v-else-if="plugin && detail">
          <div class="detail-layout">
            <main class="detail-main">
              <section class="plugin-overview">
                <div class="overview-body">
                  <div class="overview-head">
                    <div class="plugin-icon" aria-hidden="true">
                      <img
                        v-if="plugin.icon_url && !imageFailed"
                        :src="plugin.icon_url"
                        alt=""
                        @error="imageFailed = true"
                      />
                      <span v-else>{{ pluginInitial }}</span>
                    </div>
                    <div class="overview-copy">
                      <div class="title-row">
                        <div>
                          <h1>{{ plugin.display_name }}</h1>
                          <code>{{ plugin.plugin_id }}</code>
                        </div>
                        <span class="trust-badge">{{ plugin.trust_level }}</span>
                      </div>
                      <div class="overview-desc-wrapper" :class="{ expanded: isDescriptionExpanded }">
                        <p class="overview-desc">{{ descriptionText || t('pluginMarket.card.noSummary') }}</p>
                        <button
                          v-if="isDescriptionTruncated || isDescriptionExpanded"
                          class="desc-toggle-btn"
                          type="button"
                          @click="isDescriptionExpanded = !isDescriptionExpanded"
                        >
                          {{ isDescriptionExpanded ? t('pluginMarket.detail.collapse') : t('pluginMarket.detail.expand') }}
                          <Icon
                            :icon="isDescriptionExpanded ? 'material-symbols:expand-less-rounded' : 'material-symbols:expand-more-rounded'"
                            width="18"
                            height="18"
                          />
                        </button>
                      </div>
                      <div class="overview-meta">
                        <span>
                          <Icon icon="material-symbols:person-outline-rounded" width="18" height="18" />
                          {{ plugin.owner_display_name || plugin.owner_login || t('pluginMarket.detail.unknown') }}
                        </span>
                        <span>
                          <Icon icon="material-symbols:download-rounded" width="18" height="18" />
                          {{ plugin.downloads_count }}
                        </span>
                        <span>
                          <Icon icon="material-symbols:update-rounded" width="18" height="18" />
                          {{ formatDate(plugin.updated_at) }}
                        </span>
                      </div>
                      <div v-if="plugin.tags.length" class="tag-list">
                        <span v-for="tag in plugin.tags" :key="tag">{{ tag }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="source-links">
                    <a
                      v-if="plugin.repository_url"
                      :href="plugin.repository_url"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Icon icon="material-symbols:code-rounded" width="18" height="18" />
                      {{ t('pluginMarket.detail.repository') }}
                    </a>
                    <a
                      v-if="plugin.homepage && plugin.homepage !== plugin.repository_url"
                      :href="plugin.homepage"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Icon icon="material-symbols:open-in-new-rounded" width="18" height="18" />
                      {{ t('pluginMarket.detail.homepage') }}
                    </a>
                  </div>
                </div>
              </section>

              <div v-if="plugin.risk_notice" class="notice error-notice">
                <Icon icon="material-symbols:warning-outline-rounded" width="22" height="22" />
                <span>{{ plugin.risk_notice }}</span>
              </div>

              <div v-if="operation" class="operation-panel" :class="operation.status">
                <div class="operation-heading">
                  <Icon
                    :icon="operation.status === 'failed' ? 'material-symbols:error-outline-rounded' : 'material-symbols:sync-rounded'"
                    width="22"
                    height="22"
                    :class="{ spinning: isOperationActive }"
                  />
                  <div>
                    <strong>{{ operation.message }}</strong>
                    <span>{{ operation.error_message || operation.stage }}</span>
                  </div>
                  <em>{{ operation.progress }}%</em>
                </div>
                <div class="progress-track" role="progressbar" :aria-valuenow="operation.progress" aria-valuemin="0" aria-valuemax="100">
                  <span :style="{ width: `${operation.progress}%` }"></span>
                </div>
              </div>

              <div class="tab-bar" role="tablist">
                <button
                  type="button"
                  role="tab"
                  :aria-selected="activeTab === 'info'"
                  class="tab-button"
                  :class="{ active: activeTab === 'info' }"
                  @click="activeTab = 'info'"
                >
                  <Icon icon="material-symbols:info-outline-rounded" width="18" height="18" />
                  {{ t('pluginMarket.detail.about') }}
                </button>
                <button
                  type="button"
                  role="tab"
                  :aria-selected="activeTab === 'docs'"
                  class="tab-button"
                  :class="{ active: activeTab === 'docs' }"
                  @click="activeTab = 'docs'"
                >
                  <Icon icon="material-symbols:description-outline-rounded" width="18" height="18" />
                  {{ t('pluginMarket.detail.readme') }}
                </button>
              </div>

              <section v-show="activeTab === 'info'" class="tab-panel">
                <section class="section-block">
                  <h2>{{ t('pluginMarket.detail.dependencies') }}</h2>
                  <div v-if="detail.dependencies.length" class="dependency-list">
                    <article v-for="dependency in detail.dependencies" :key="dependency.plugin_id">
                      <div>
                        <strong>{{ dependency.plugin_id }}</strong>
                        <code>{{ dependency.version_constraint || dependency.required_version || '—' }}</code>
                      </div>
                      <span :class="{ satisfied: dependency.satisfied }">
                        {{ dependency.satisfied ? t('pluginMarket.detail.satisfied') : t('pluginMarket.detail.missing') }}
                      </span>
                    </article>
                  </div>
                  <p v-else class="muted-text">{{ t('pluginMarket.detail.noDependencies') }}</p>
                </section>

                <section class="section-block">
                  <h2>{{ t('pluginMarket.detail.versionHistory') }}</h2>
                  <div class="version-list">
                    <article
                      v-for="version in detail.versions"
                      :key="version.version"
                      class="version-row"
                      :class="{ 'version-yanked': version.is_yanked || version.status !== 'published' }"
                    >
                      <div class="version-info">
                        <div class="version-title">
                          <strong>v{{ version.version }}</strong>
                          <span v-if="version.is_prerelease" class="version-badge prerelease">
                            {{ t('pluginMarket.detail.prerelease') }}
                          </span>
                          <span v-if="version.is_yanked || version.status !== 'published'" class="version-badge yanked">
                            {{ t('pluginMarket.detail.yanked') }}
                          </span>
                          <span v-if="version.compatibility.status === 'incompatible'" class="version-badge incompatible">
                            {{ t('pluginMarket.detail.incompatible') }}
                          </span>
                        </div>
                        <span class="compatibility" :class="version.compatibility.status">
                          {{ version.compatibility.summary }}
                        </span>
                      </div>
                      <div class="version-actions">
                        <span class="version-meta">
                          {{ formatDate(version.published_at) }} · {{ formatBytes(version.file_size) }}
                        </span>
                        <button
                          v-if="version.asset_download_url"
                          type="button"
                          class="secondary-button version-download"
                          :title="t('pluginMarket.detail.downloadVersion')"
                          @click="downloadVersion(version)"
                        >
                          <Icon icon="material-symbols:download-rounded" width="18" height="18" />
                          {{ t('pluginMarket.detail.download') }}
                        </button>
                        <button
                          type="button"
                          class="primary-button version-install"
                          :disabled="!canInstallVersion(version) || isPlanning"
                          :title="installVersionLabel(version)"
                          @click="beginInstall(version.version)"
                        >
                          <Icon
                            :icon="isPlanning && selectedVersion === version.version
                              ? 'material-symbols:progress-activity'
                              : installVersionIcon(version)"
                            width="18"
                            height="18"
                            :class="{ spinning: isPlanning && selectedVersion === version.version }"
                          />
                          {{ installVersionLabel(version) }}
                        </button>
                      </div>
                    </article>
                  </div>
                </section>
              </section>

              <section v-show="activeTab === 'docs'" class="tab-panel documentation-block">
                <section class="section-block documentation-section">
                  <h2>{{ t('pluginMarket.detail.readme') }}</h2>
                  <div v-if="isReadmeLoading" class="documentation-state" aria-busy="true">
                    <Icon icon="material-symbols:progress-activity" width="24" height="24" class="spinning" />
                    <span>{{ t('pluginMarket.detail.documentationLoading') }}</span>
                  </div>
                  <div v-else-if="readmeErrorMessage" class="documentation-state documentation-error">
                    <Icon icon="material-symbols:error-outline-rounded" width="24" height="24" />
                    <div>
                      <strong>{{ t('pluginMarket.detail.documentationError') }}</strong>
                      <span>{{ readmeErrorMessage }}</span>
                    </div>
                    <button class="secondary-button" type="button" @click="loadReadme">
                      <Icon icon="material-symbols:refresh-rounded" width="18" height="18" />
                      {{ t('pluginMarket.retry') }}
                    </button>
                  </div>
                  <iframe
                    v-else-if="readmeDocument"
                    class="documentation-frame"
                    :srcdoc="readmeDocument"
                    :title="t('pluginMarket.detail.documentationFrameTitle', { name: plugin.display_name })"
                    sandbox="allow-popups allow-popups-to-escape-sandbox"
                    referrerpolicy="no-referrer"
                  ></iframe>
                  <p v-else class="muted-text">{{ t('pluginMarket.detail.documentationEmpty') }}</p>
                </section>
              </section>
            </main>

            <aside class="install-panel">
              <h2>{{ t('pluginMarket.detail.installation') }}</h2>
              <div class="local-state">
                <span>{{ t('pluginMarket.detail.localState') }}</span>
                <strong>
                  {{ plugin.local_state.installed
                    ? t('pluginMarket.detail.installedVersion', { version: plugin.local_state.installed_version || '—' })
                    : t('pluginMarket.card.notInstalled') }}
                </strong>
              </div>

              <div v-if="selectedVersionInfo" class="selected-version-meta">
                <span>
                  <Icon
                    :icon="selectedVersionInfo.compatibility.status === 'compatible'
                      ? 'material-symbols:check-circle-outline-rounded'
                      : selectedVersionInfo.compatibility.status === 'incompatible'
                        ? 'material-symbols:cancel-outline-rounded'
                        : 'material-symbols:help-outline-rounded'"
                    width="19"
                    height="19"
                  />
                  {{ selectedVersionInfo.compatibility.summary }}
                </span>
                <small>
                  {{ t('pluginMarket.detail.hostRange', {
                    min: selectedVersionInfo.min_host_version || '—',
                    max: selectedVersionInfo.max_host_version || '∞',
                  }) }}
                </small>
                <small>{{ t('pluginMarket.detail.apiVersion', { version: selectedVersionInfo.plugin_api_version || '—' }) }}</small>
                <small>{{ t('pluginMarket.detail.packageSize', { size: formatBytes(selectedVersionInfo.file_size) }) }}</small>
              </div>

              <button
                class="primary-button full-width"
                type="button"
                :disabled="!canStartInstall || isPlanning"
                @click="beginInstall()"
              >
                <Icon
                  :icon="isPlanning ? 'material-symbols:progress-activity' : primaryActionIcon"
                  width="20"
                  height="20"
                  :class="{ spinning: isPlanning || isOperationActive }"
                />
                {{ primaryActionLabel }}
              </button>

              <p v-if="!isLatestSelected && selectedVersionInfo" class="action-hint">
                {{ t('pluginMarket.detail.notLatestHint') }}
              </p>

              <button
                v-if="plugin.local_state.has_config"
                class="secondary-button full-width"
                type="button"
                :disabled="isOperationActive"
                @click="openConfig"
              >
                <Icon icon="material-symbols:settings-outline-rounded" width="20" height="20" />
                {{ t('pluginMarket.detail.configure') }}
              </button>

              <button
                v-if="plugin.local_state.installed"
                class="secondary-button full-width"
                type="button"
                :disabled="isOperationActive"
                @click="openManage"
              >
                <Icon icon="material-symbols:extension-outline-rounded" width="20" height="20" />
                {{ t('pluginMarket.detail.manage') }}
              </button>

              <p v-if="!capabilities?.install_enabled" class="action-hint">
                {{ t('pluginMarket.detail.installDisabled') }}
              </p>
            </aside>
          </div>
        </template>
      </div>
  </section>
</template>

<style scoped>
.detail-page {
  height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-toolbar {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 1.5rem;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface) 84%, transparent);
  backdrop-filter: blur(12px);
}

.back-button,
.icon-button,
.primary-button,
.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 40px;
  border-radius: 8px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.back-button {
  padding: 0 12px;
  border: 0;
  color: var(--md-sys-color-on-surface);
  background: transparent;
}

.back-button:hover,
.icon-button:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-high);
}

.icon-button {
  width: 40px;
  padding: 0;
  border: 1px solid var(--md-sys-color-outline-variant);
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container-low);
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.detail-scroll {
  flex: 1;
  min-height: 0;
  padding: 1.5rem;
  overflow: auto;
  background: color-mix(in srgb, var(--md-sys-color-surface) 72%, transparent);
}

.plugin-overview {
  position: relative;
  margin: 0 0 1.25rem;
  overflow: hidden;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 16px;
  background: var(--md-sys-color-surface-container-low);
}

.overview-body {
  padding: 1.4rem;
}

.overview-head {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  gap: 18px;
  align-items: center;
}

.plugin-icon {
  width: 84px;
  height: 84px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 14px;
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
  font-size: 1.9rem;
  font-weight: 700;
}

.plugin-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overview-copy,
.title-row > div {
  min-width: 0;
}

.overview-copy {
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.title-row h1 {
  margin: 0;
  color: var(--md-sys-color-on-surface);
  font-size: 1.75rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.title-row code {
  display: block;
  margin-top: 4px;
  color: var(--md-sys-color-on-surface-variant);
  overflow-wrap: anywhere;
}

.trust-badge,
.dependency-list article > span,
.compatibility {
  padding: 4px 8px;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 700;
}

.trust-badge {
  flex: 0 0 auto;
  color: var(--md-sys-color-on-tertiary-container);
  background: var(--md-sys-color-tertiary-container);
}

.overview-desc-wrapper {
  max-width: 850px;
  margin: 12px 0 0;
}

.overview-desc {
  margin: 0;
  color: var(--md-sys-color-on-surface-variant);
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.desc-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-top: 6px;
  padding: 2px 0;
  border: 0;
  background: transparent;
  color: var(--md-sys-color-primary);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.desc-toggle-btn:hover {
  text-decoration: underline;
}

.overview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8rem;
}

.overview-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.notice,
.operation-panel {
  margin: 0 0 1rem;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
}

.notice {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 12px 14px;
}

.error-notice {
  color: var(--md-sys-color-on-error-container);
  background: var(--md-sys-color-error-container);
}

.operation-panel {
  padding: 13px 14px;
  background: var(--md-sys-color-surface-container-low);
}

.operation-panel.failed {
  color: var(--md-sys-color-on-error-container);
  background: var(--md-sys-color-error-container);
}

.operation-heading {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
}

.operation-heading div {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.operation-heading span,
.operation-heading em {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.76rem;
  font-style: normal;
  overflow-wrap: anywhere;
}

.progress-track {
  height: 5px;
  margin-top: 10px;
  border-radius: 9999px;
  overflow: hidden;
  background: var(--md-sys-color-surface-container-highest);
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--md-sys-color-primary);
  transition: width 0.25s ease;
}

.detail-layout {
  max-width: 1240px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 400px);
  align-items: start;
  gap: 1rem;
  margin: 0 auto;
}

.detail-main {
  min-width: 0;
  display: grid;
  gap: 1rem;
}

.section-block,
.install-panel {
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 92%, transparent);
}

.section-block {
  padding: 1.1rem;
}

.section-block h2,
.install-panel h2 {
  margin: 0 0 0.9rem;
  color: var(--md-sys-color-on-surface);
  font-size: 1rem;
}

.muted-text {
  margin: 0;
  color: var(--md-sys-color-on-surface-variant);
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.tag-list span {
  padding: 4px 8px;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container-high);
  white-space: nowrap;
}

.documentation-block {
  min-width: 0;
}

.documentation-state {
  min-height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--md-sys-color-on-surface-variant);
}

.documentation-error {
  justify-content: flex-start;
  flex-wrap: wrap;
}

.documentation-error > div {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 0.2rem;
}

.documentation-error span {
  overflow-wrap: anywhere;
}

.documentation-frame {
  display: block;
  width: 100%;
  height: clamp(480px, 72vh, 820px);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  background: var(--md-sys-color-surface);
}

.dependency-list,
.version-list {
  display: grid;
  gap: 8px;
}

.version-list {
  max-height: 480px;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: var(--md-sys-color-outline-variant) transparent;
}

.version-list::-webkit-scrollbar {
  width: 6px;
}

.version-list::-webkit-scrollbar-track {
  background: transparent;
}

.version-list::-webkit-scrollbar-thumb {
  border-radius: 9999px;
  background: var(--md-sys-color-outline-variant);
}

.dependency-list article,
.version-row {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 10px 0;
  border-top: 1px solid var(--md-sys-color-outline-variant);
}

.dependency-list article:first-child,
.version-row:first-child {
  border-top: 0;
}

.dependency-list article > div,
.version-info {
  min-width: 0;
  display: grid;
  gap: 5px;
}

.version-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.version-title > strong {
  color: var(--md-sys-color-on-surface);
  font-size: 0.92rem;
}

.version-badge {
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container-high);
}

.version-badge.prerelease {
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
}

.version-badge.yanked {
  color: var(--md-sys-color-on-error-container);
  background: var(--md-sys-color-error-container);
}

.version-badge.incompatible {
  color: var(--md-sys-color-on-error-container);
  background: var(--md-sys-color-error-container);
}

.version-yanked .version-title > strong {
  color: var(--md-sys-color-on-surface-variant);
  text-decoration: line-through;
}

.version-meta {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.74rem;
  white-space: nowrap;
}

.dependency-list code,
.version-row span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.76rem;
  overflow-wrap: anywhere;
}

.version-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-download,
.version-install {
  min-height: 34px;
  padding: 0 10px;
  border-radius: 9999px;
  font-size: 0.78rem;
}

.version-install {
  min-width: 124px;
  justify-content: center;
}

.dependency-list article > span {
  flex: 0 0 auto;
  color: var(--md-sys-color-on-error-container);
  background: var(--md-sys-color-error-container);
}

.dependency-list article > span.satisfied,
.compatibility.compatible {
  color: var(--md-sys-color-on-tertiary-container);
  background: var(--md-sys-color-tertiary-container);
}

.compatibility {
  justify-self: start;
  max-width: 100%;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container-high);
  text-align: left;
  overflow-wrap: anywhere;
}

.compatibility.incompatible {
  color: var(--md-sys-color-on-error-container);
  background: var(--md-sys-color-error-container);
}

.tab-bar {
  display: flex;
  gap: 4px;
  padding: 6px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 9999px;
  background: var(--md-sys-color-surface-container-low);
}

.tab-button {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 14px;
  border: 0;
  border-radius: 9999px;
  font: inherit;
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--md-sys-color-on-surface-variant);
  background: transparent;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease;
}

.tab-button:hover:not(.active) {
  background: var(--md-sys-color-surface-container-high);
}

.tab-button.active {
  color: var(--md-sys-color-on-primary);
  background: var(--md-sys-color-primary);
}

.tab-panel {
  display: grid;
  gap: 1rem;
}

.install-panel {
  position: sticky;
  top: 0;
  display: grid;
  gap: 12px;
  padding: 1rem;
}

.install-panel h2 {
  margin-bottom: 0;
}

.local-state,
.selected-version-meta {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--md-sys-color-surface-container);
}

.local-state span,
.selected-version-meta small {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.75rem;
}

.selected-version-meta > span {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  color: var(--md-sys-color-on-surface);
  font-size: 0.82rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.primary-button,
.secondary-button {
  padding: 0 14px;
  border: 1px solid transparent;
}

.primary-button {
  color: var(--md-sys-color-on-primary);
  background: var(--md-sys-color-primary);
}

.secondary-button {
  color: var(--md-sys-color-on-secondary-container);
  background: var(--md-sys-color-secondary-container);
}

.full-width {
  width: 100%;
}

.action-hint {
  margin: 0;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.75rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.source-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 4px;
}

.source-links a {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--md-sys-color-primary);
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: none;
}

.state-panel {
  min-height: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--md-sys-color-on-surface-variant);
  text-align: center;
}

.state-panel h2,
.state-panel p {
  max-width: 650px;
  margin: 0;
  overflow-wrap: anywhere;
}

.state-panel h2 {
  color: var(--md-sys-color-on-surface);
  font-size: 1.1rem;
}

.error-state > :first-child {
  color: var(--md-sys-color-error);
}

.spinning {
  display: inline-grid;
  flex: 0 0 auto;
  place-items: center;
  line-height: 1;
  vertical-align: middle;
  transform-origin: 50% 50%;
  will-change: transform;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1175px) {
  .detail-layout {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .detail-main {
    display: contents;
  }

  .plugin-overview {
    order: 1;
    width: 100%;
  }

  .notice {
    order: 2;
    width: 100%;
  }

  .operation-panel {
    order: 3;
    width: 100%;
  }

  .install-panel {
    position: static;
    order: 4;
    width: 100%;
  }

  .tab-bar {
    order: 5;
    width: 100%;
  }

  .tab-panel {
    order: 6;
    width: 100%;
  }
}

@media (max-width: 560px) {
  .detail-toolbar {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }

  .detail-scroll {
    padding: 1rem;
  }

  .overview-body {
    padding: 1rem;
  }

  .overview-head {
    grid-template-columns: 64px minmax(0, 1fr);
    gap: 12px;
  }

  .plugin-icon {
    width: 64px;
    height: 64px;
    font-size: 1.4rem;
  }

  .documentation-frame {
    height: 65vh;
    min-height: 420px;
  }

  .title-row {
    flex-direction: column;
    gap: 7px;
  }

  .title-row h1 {
    font-size: 1.4rem;
  }

  .overview-desc-wrapper:not(.expanded) .overview-desc {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    max-height: 3.2em;
  }

  .tag-list {
    flex-wrap: nowrap;
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    margin-left: -1rem;
    margin-right: -1rem;
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .tag-list::-webkit-scrollbar {
    display: none;
  }

  .dependency-list article,
  .version-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 9px;
  }

  .version-info {
    grid-template-columns: 1fr;
  }

  .version-actions {
    width: 100%;
    flex-wrap: wrap;
    align-items: stretch;
  }

  .version-meta {
    width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
  }

  .version-download,
  .version-install {
    flex: 1 1 0;
    min-width: 0;
    justify-content: center;
  }

  .compatibility {
    max-width: 100%;
    text-align: left;
  }
}
</style>
