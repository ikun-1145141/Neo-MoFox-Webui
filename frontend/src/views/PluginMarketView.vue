<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import Icon from '../components/common/Icon.vue'
import MdSelect from '../components/common/MdSelect.vue'
import PageHeader from '../components/common/PageHeader.vue'
import PluginMarketCard from '../components/plugin-market/PluginMarketCard.vue'
import { getMarketPlugins } from '../api/modules/plugin-market'
import type { MarketPlugin } from '../api/types/plugin-market'
import { useI18n } from '../utils/i18n'

type SelectOption = { label: string; value: string }
type MarketStateFilter = 'all' | 'installed' | 'updates' | 'not-installed'
type MarketSort = 'updated' | 'downloads' | 'rating' | 'name'

const { t } = useI18n()
const plugins = ref<MarketPlugin[]>([])
const isLoading = ref(true)
const isRefreshing = ref(false)
const errorMessage = ref('')
const searchQuery = ref('')
const category = ref('')
const stateFilter = ref<MarketStateFilter>('all')
const sortBy = ref<MarketSort>('updated')

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
    <section class="market-page">
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
  .market-header,
  .market-content {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .filter-bar {
    grid-template-columns: 1fr 1fr;
  }

  .search-field {
    grid-column: 1 / -1;
  }
}

@media (max-width: 480px) {
  .market-header {
    padding-top: 1rem;
  }

  .header-row :deep(.page-header-title) {
    font-size: 1.45rem;
  }

  .filter-bar {
    grid-template-columns: 1fr;
  }

  .search-field {
    grid-column: auto;
  }

  .result-summary {
    align-items: flex-start;
    flex-direction: column;
    gap: 3px;
    padding-bottom: 8px;
  }
}
</style>
