<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
import Icon from '../components/common/Icon.vue'
import MdSelect from '../components/common/MdSelect.vue'
import PageHeader from '../components/common/PageHeader.vue'
import PluginMarketCard from '../components/plugin-market/PluginMarketCard.vue'
import PluginMarketDetail from '../components/plugin-market/PluginMarketDetail.vue'
import {
  getMarketInstallPlan,
  getMarketOperation,
  getMarketPlugins,
  startMarketInstall,
} from '../api/modules/plugin-market'
import type { InstallPlan, MarketOperation, MarketPlugin } from '../api/types/plugin-market'
import { useDialogStore } from '../utils/dialog'
import { useI18n } from '../utils/i18n'
import { useToastStore } from '../utils/toast'

type SelectOption = { label: string; value: string }
type MarketStateFilter = 'all' | 'installed' | 'updates' | 'not-installed'
type MarketSort = 'updated' | 'downloads' | 'rating' | 'name'

const { t } = useI18n()
const dialogStore = useDialogStore()
const toastStore = useToastStore()
const route = useRoute()
const router = useRouter()
const plugins = ref<MarketPlugin[]>([])
const isLoading = ref(true)
const isRefreshing = ref(false)
const errorMessage = ref('')
const searchQuery = ref('')
const category = ref('')
const stateFilter = ref<MarketStateFilter>('all')
const sortBy = ref<MarketSort>('updated')
const busyPluginIds = ref<string[]>([])

const selectedPluginId = computed(() => {
  const value = route.query.plugin
  return typeof value === 'string' ? value : ''
})

const categoryOptions = computed<SelectOption[]>(() => [
  { label: t('pluginMarket.filters.allCategories'), value: '' },
  ...Array.from(new Set(plugins.value.flatMap((plugin) => plugin.categories)))
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right))
    .map((value) => ({ label: value, value })),
])

const stateOptions = computed<SelectOption[]>(() => [
  { label: t('pluginMarket.filters.allStates'), value: 'all' },
  { label: t('pluginMarket.filters.installed'), value: 'installed' },
  { label: t('pluginMarket.filters.updates'), value: 'updates' },
  { label: t('pluginMarket.filters.notInstalled'), value: 'not-installed' },
])

const sortOptions = computed<SelectOption[]>(() => [
  { label: t('pluginMarket.sort.updated'), value: 'updated' },
  { label: t('pluginMarket.sort.downloads'), value: 'downloads' },
  { label: t('pluginMarket.sort.rating'), value: 'rating' },
  { label: t('pluginMarket.sort.name'), value: 'name' },
])

const visiblePlugins = computed(() => {
  const tokens = searchQuery.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  const result = plugins.value.filter((plugin) => {
    if (category.value && !plugin.categories.includes(category.value)) return false
    if (stateFilter.value === 'installed' && !plugin.local_state.installed) return false
    if (stateFilter.value === 'updates' && !plugin.local_state.update_available) return false
    if (stateFilter.value === 'not-installed' && plugin.local_state.installed) return false
    const searchText = [
      plugin.plugin_id,
      plugin.display_name,
      plugin.summary,
      plugin.description,
      plugin.owner_login ?? '',
      plugin.owner_display_name ?? '',
      ...plugin.tags,
      ...plugin.categories,
    ].join(' ').toLocaleLowerCase()
    return tokens.every((token) => searchText.includes(token))
  })

  return result.sort((left, right) => {
    if (sortBy.value === 'downloads') return right.downloads_count - left.downloads_count
    if (sortBy.value === 'rating') return right.rating_avg - left.rating_avg
    if (sortBy.value === 'name') return left.display_name.localeCompare(right.display_name)
    return Date.parse(right.updated_at ?? '') - Date.parse(left.updated_at ?? '')
  })
})

async function loadPlugins(refresh = false): Promise<void> {
  errorMessage.value = ''
  if (refresh) isRefreshing.value = true
  else isLoading.value = true
  try {
    const result = await getMarketPlugins(refresh)
    plugins.value = result.plugins
  } catch (error: unknown) {
    errorMessage.value = errorText(error)
  } finally {
    isLoading.value = false
    isRefreshing.value = false
  }
}

function clearSearch(): void {
  searchQuery.value = ''
}

async function closeDetail(): Promise<void> {
  if (window.history.state?.fromPluginMarketList === true) {
    router.back()
    return
  }
  const query = { ...route.query }
  delete query.plugin
  await router.replace({ name: 'plugin-market', query })
}

async function openConfig(pluginId: string): Promise<void> {
  await router.push({
    name: 'config-plugins',
    query: { plugin: pluginId },
  })
}

async function openManage(pluginId: string): Promise<void> {
  await router.push({
    name: 'plugin-detail',
    params: { name: pluginId },
  })
}

function isPluginBusy(pluginId: string): boolean {
  return busyPluginIds.value.includes(pluginId)
}

function setPluginBusy(pluginId: string, busy: boolean): void {
  if (busy) {
    if (!busyPluginIds.value.includes(pluginId)) {
      busyPluginIds.value = [...busyPluginIds.value, pluginId]
    }
    return
  }
  busyPluginIds.value = busyPluginIds.value.filter((item) => item !== pluginId)
}

async function handleCardAction(plugin: MarketPlugin): Promise<void> {
  if (isPluginBusy(plugin.plugin_id)) return
  if (plugin.local_state.update_available || !plugin.local_state.installed) {
    await installOrUpdatePlugin(plugin)
    return
  }
  if (plugin.local_state.has_config) {
    await openConfig(plugin.plugin_id)
    return
  }
  await openManage(plugin.plugin_id)
}

async function installOrUpdatePlugin(plugin: MarketPlugin): Promise<void> {
  setPluginBusy(plugin.plugin_id, true)
  try {
    const plan = await getMarketInstallPlan(plugin.plugin_id, null)
    if (!plan.can_install) {
      await dialogStore.alert(plan.blocking_reasons.join('\n'), t('pluginMarket.detail.blockedTitle'))
      return
    }

    const confirmed = await dialogStore.confirm(
      planMessage(plan),
      plan.action === 'update'
        ? t('pluginMarket.detail.updateConfirmTitle')
        : t('pluginMarket.detail.installConfirmTitle'),
      plan.action === 'update'
        ? t('pluginMarket.detail.update')
        : t('pluginMarket.detail.install'),
      t('pluginMarket.detail.cancel'),
    )
    if (!confirmed) return

    const operation = await startMarketInstall(plugin.plugin_id, plan.version.version)
    const completed = await waitForOperation(operation)
    if (completed.status === 'succeeded') {
      const message = completed.result?.restart_required
        ? t('pluginMarket.detail.operationRestartRequired')
        : t('pluginMarket.detail.operationSucceeded')
      toastStore.show(message, 'success', 6000)
      await loadPlugins(true)
      return
    }
    toastStore.show(
      completed.error_message || t('pluginMarket.detail.operationFailed'),
      'error',
      7000,
    )
  } catch (error: unknown) {
    toastStore.show(errorText(error), 'error', 6000)
  } finally {
    setPluginBusy(plugin.plugin_id, false)
  }
}

async function waitForOperation(operation: MarketOperation): Promise<MarketOperation> {
  let current = operation
  while (current.status === 'queued' || current.status === 'running') {
    await new Promise<void>((resolve) => window.setTimeout(resolve, 700))
    current = await getMarketOperation(current.operation_id)
  }
  return current
}

function planMessage(plan: InstallPlan): string {
  const lines = [
    plan.plugin.display_name + ' @ ' + plan.version.version,
    t('pluginMarket.detail.planSource', {
      source: plan.plugin.repository_url || plan.plugin.homepage || '—',
    }),
    t('pluginMarket.detail.planSize', { size: formatBytes(plan.version.file_size) }),
  ]
  if (plan.dependencies.length) {
    lines.push(t('pluginMarket.detail.planDependencies', {
      count: String(plan.dependencies.length),
    }))
  }
  if (plan.warnings.length) {
    lines.push('', t('pluginMarket.detail.planWarnings'), ...plan.warnings.map((item) => '• ' + item))
  }
  lines.push('', t('pluginMarket.detail.planRestart'))
  return lines.join('\n')
}

function formatBytes(value: number | null): string {
  if (value === null) return t('pluginMarket.detail.unknown')
  if (value < 1024) return value + ' B'
  if (value < 1024 * 1024) return (value / 1024).toFixed(1) + ' KiB'
  return (value / (1024 * 1024)).toFixed(1) + ' MiB'
}

async function handlePluginChanged(): Promise<void> {
  await loadPlugins(true)
}

function errorText(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String(error.message)
  }
  return t('pluginMarket.error.fallback')
}

onMounted(() => {
  void loadPlugins()
})
</script>

<template>
  <AppShell no-padding>
    <PluginMarketDetail
      v-if="selectedPluginId"
      :key="selectedPluginId"
      :plugin-id="selectedPluginId"
      @close="closeDetail"
      @changed="handlePluginChanged"
      @configure="openConfig"
      @manage="openManage"
    />

    <section v-show="!selectedPluginId" class="market-page">
      <div class="market-header">
        <div class="header-row">
          <PageHeader
            :title="t('pluginMarket.title')"
            :subtitle="t('pluginMarket.subtitle')"
            icon="material-symbols:storefront-outline-rounded"
          />
          <button
            class="icon-button"
            type="button"
            :title="t('pluginMarket.refresh')"
            :aria-label="t('pluginMarket.refresh')"
            :disabled="isLoading || isRefreshing"
            @click="loadPlugins(true)"
          >
            <Icon
              icon="material-symbols:refresh-rounded"
              width="21"
              height="21"
              :class="{ spinning: isRefreshing }"
            />
          </button>
        </div>

        <div class="filter-bar">
          <label class="search-field">
            <span class="sr-only">{{ t('pluginMarket.searchPlaceholder') }}</span>
            <Icon icon="material-symbols:search-rounded" width="21" height="21" />
            <input v-model="searchQuery" type="search" :placeholder="t('pluginMarket.searchPlaceholder')" />
            <button
              v-if="searchQuery"
              type="button"
              :title="t('pluginMarket.clearSearch')"
              :aria-label="t('pluginMarket.clearSearch')"
              @click="clearSearch"
            >
              <Icon icon="material-symbols:close-rounded" width="19" height="19" />
            </button>
          </label>
          <div class="select-control">
            <span>{{ t('pluginMarket.filters.category') }}</span>
            <MdSelect
              v-model="category"
              :options="categoryOptions"
              :placeholder="t('pluginMarket.filters.allCategories')"
            />
          </div>
          <div class="select-control">
            <span>{{ t('pluginMarket.filters.state') }}</span>
            <MdSelect v-model="stateFilter" :options="stateOptions" />
          </div>
          <div class="select-control">
            <span>{{ t('pluginMarket.filters.sort') }}</span>
            <MdSelect v-model="sortBy" :options="sortOptions" />
          </div>
        </div>
      </div>

      <div class="market-content">
        <div v-if="isLoading" class="plugin-grid" aria-busy="true">
          <div v-for="index in 6" :key="index" class="skeleton-card">
            <span class="skeleton icon-skeleton"></span>
            <span class="skeleton title-skeleton"></span>
            <span class="skeleton line-skeleton"></span>
            <span class="skeleton line-skeleton short"></span>
          </div>
        </div>

        <div v-else-if="errorMessage" class="state-panel error-panel">
          <Icon icon="material-symbols:cloud-off-outline-rounded" width="48" height="48" />
          <h2>{{ t('pluginMarket.error.title') }}</h2>
          <p>{{ errorMessage }}</p>
          <button class="primary-button" type="button" @click="loadPlugins()">
            <Icon icon="material-symbols:refresh-rounded" width="19" height="19" />
            {{ t('pluginMarket.retry') }}
          </button>
        </div>

        <template v-else>
          <div class="result-summary">
            <strong>{{ t('pluginMarket.resultCount', { count: String(visiblePlugins.length) }) }}</strong>
            <span v-if="visiblePlugins.length !== plugins.length">
              {{ t('pluginMarket.totalCount', { count: String(plugins.length) }) }}
            </span>
          </div>

          <div v-if="visiblePlugins.length" class="plugin-grid">
            <PluginMarketCard
              v-for="plugin in visiblePlugins"
              :key="plugin.plugin_id"
              :plugin="plugin"
              :busy="isPluginBusy(plugin.plugin_id)"
              @action="handleCardAction"
            />
          </div>

          <div v-else class="state-panel">
            <Icon icon="material-symbols:search-off-rounded" width="52" height="52" />
            <h2>{{ t('pluginMarket.empty.title') }}</h2>
            <p>{{ t('pluginMarket.empty.description') }}</p>
          </div>
        </template>
      </div>
    </section>
  </AppShell>
</template>

<style scoped>
.market-page {
  height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.market-header {
  flex: 0 0 auto;
  padding: 1.5rem 1.5rem 1.25rem;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface) 82%, transparent);
  backdrop-filter: blur(12px);
}

.header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.header-row :deep(.page-header) {
  margin-bottom: 1.25rem;
}

.icon-button,
.search-field button {
  display: inline-grid;
  place-items: center;
  padding: 0;
  border: 0;
  cursor: pointer;
  color: var(--md-sys-color-on-surface-variant);
  background: transparent;
}

.icon-button {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  background: var(--md-sys-color-surface-container-low);
}

.icon-button:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-high);
}

.icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.filter-bar {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(150px, 190px) minmax(150px, 190px) minmax(150px, 190px);
  gap: 12px;
  align-items: end;
}

.search-field {
  height: 48px;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) 32px;
  align-items: center;
  gap: 8px;
  padding: 0 8px 0 14px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container-lowest);
}

.search-field:focus-within {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--md-sys-color-primary) 18%, transparent);
}

.search-field input {
  min-width: 0;
  height: 100%;
  padding: 0;
  border: 0;
  outline: 0;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  font: inherit;
}

.search-field button {
  width: 32px;
  height: 32px;
  border-radius: 50%;
}

.select-control {
  display: grid;
  gap: 5px;
}

.select-control > span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.76rem;
  font-weight: 700;
}

.market-content {
  flex: 1;
  min-height: 0;
  padding: 1.25rem 1.5rem 2rem;
  overflow: auto;
  background: color-mix(in srgb, var(--md-sys-color-surface) 72%, transparent);
}

.result-summary {
  min-height: 34px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.82rem;
}

.result-summary strong {
  color: var(--md-sys-color-on-surface);
}

.plugin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
  gap: 14px;
}

.skeleton-card {
  height: 250px;
  display: grid;
  grid-template-columns: 46px 1fr;
  align-content: start;
  gap: 14px 12px;
  padding: 17px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  background: var(--md-sys-color-surface-container-low);
}

.skeleton {
  border-radius: 6px;
  background: linear-gradient(
    90deg,
    var(--md-sys-color-surface-container) 20%,
    var(--md-sys-color-surface-container-high) 50%,
    var(--md-sys-color-surface-container) 80%
  );
  background-size: 220% 100%;
  animation: shimmer 1.25s linear infinite;
}

.icon-skeleton { width: 46px; height: 46px; }
.title-skeleton { height: 20px; align-self: center; }
.line-skeleton { grid-column: 1 / -1; height: 15px; margin-top: 10px; }
.line-skeleton.short { width: 66%; margin-top: 0; }

.state-panel {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 2rem;
  color: var(--md-sys-color-on-surface-variant);
  text-align: center;
}

.state-panel h2,
.state-panel p {
  margin: 0;
}

.state-panel h2 {
  color: var(--md-sys-color-on-surface);
  font-size: 1.1rem;
}

.state-panel p {
  max-width: 620px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.error-panel > :first-child {
  color: var(--md-sys-color-error);
}

.primary-button {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 8px;
  padding: 0 16px;
  border: 0;
  border-radius: 8px;
  color: var(--md-sys-color-on-primary);
  background: var(--md-sys-color-primary);
  font-weight: 700;
  cursor: pointer;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes shimmer { to { background-position: -220% 0; } }

@media (max-width: 1100px) {
  .filter-bar {
    grid-template-columns: minmax(260px, 1fr) repeat(3, minmax(130px, 1fr));
  }
}

@media (max-width: 780px) {
  /* 窄屏整页滚动，页头随内容滚走，不再固定占据大半屏幕 */
  .market-page {
    overflow-y: auto;
  }

  .market-content {
    flex: none;
    padding: 0.75rem 1rem 1.5rem;
    overflow: visible;
  }

  .market-header {
    padding: 1rem 1rem 0.75rem;
    backdrop-filter: none;
  }

  .header-row :deep(.page-header) {
    margin-bottom: 0.75rem;
  }

  .header-row :deep(.page-header-sub) {
    display: none;
  }

  /* 搜索独占一行，三个筛选并排一行 */
  .filter-bar {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .search-field {
    grid-column: 1 / -1;
    height: 42px;
  }

  .select-control > span {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }

  .result-summary {
    min-height: 0;
    padding-bottom: 8px;
  }

  .plugin-grid {
    gap: 10px;
  }

  .skeleton-card {
    height: 170px;
  }
}

@media (max-width: 480px) {
  .header-row :deep(.page-header-title) {
    font-size: 1.3rem;
  }

  .icon-button {
    width: 38px;
    height: 38px;
  }
}
</style>
