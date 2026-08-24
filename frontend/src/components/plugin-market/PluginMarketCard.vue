<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from '../../utils/i18n'
import type { MarketPlugin } from '../../api/types/plugin-market'
import Icon from '../common/Icon.vue'

const props = defineProps<{
  plugin: MarketPlugin
  busy?: boolean
}>()

const emit = defineEmits<{
  action: [plugin: MarketPlugin]
}>()

const { t } = useI18n()
const imageFailed = ref(false)

const detailRoute = computed(() => ({
  name: 'plugin-market',
  query: { plugin: props.plugin.plugin_id },
  state: { fromPluginMarketList: true },
}))

const initial = computed(() => {
  const label = props.plugin.display_name || props.plugin.plugin_id
  return label.trim().slice(0, 1).toUpperCase() || 'P'
})

const statusLabel = computed(() => {
  if (props.plugin.local_state.update_available) return t('pluginMarket.card.updateAvailable')
  if (props.plugin.local_state.installed) return t('pluginMarket.card.installed')
  return t('pluginMarket.card.notInstalled')
})

const actionKind = computed<'install' | 'update' | 'configure' | 'manage'>(() => {
  if (props.plugin.local_state.update_available) return 'update'
  if (!props.plugin.local_state.installed) return 'install'
  if (props.plugin.local_state.has_config) return 'configure'
  return 'manage'
})

const actionLabel = computed(() => {
  if (props.busy) return t('pluginMarket.card.processing')
  return t('pluginMarket.card.' + actionKind.value)
})

const actionIcon = computed(() => {
  if (props.busy) return 'material-symbols:progress-activity'
  if (actionKind.value === 'update') return 'material-symbols:update-rounded'
  if (actionKind.value === 'install') return 'material-symbols:download-rounded'
  if (actionKind.value === 'configure') return 'material-symbols:settings-outline-rounded'
  return 'material-symbols:extension-outline-rounded'
})

const isPrimaryAction = computed(() => actionKind.value === 'install' || actionKind.value === 'update')

function formatCount(value: number): string {
  return new Intl.NumberFormat(undefined, {
    notation: value >= 10_000 ? 'compact' : 'standard',
    maximumFractionDigits: 1,
  }).format(value)
}
</script>

<template>
  <article class="market-card">
    <RouterLink
      class="card-main"
      :to="detailRoute"
      :aria-label="t('pluginMarket.card.details')"
    >
      <header class="card-header">
        <div class="plugin-icon" aria-hidden="true">
          <img
            v-if="plugin.icon_url && !imageFailed"
            :src="plugin.icon_url"
            alt=""
            loading="lazy"
            @error="imageFailed = true"
          />
          <span v-else>{{ initial }}</span>
        </div>
        <div class="title-block">
          <h2 :title="plugin.display_name">{{ plugin.display_name }}</h2>
          <code :title="plugin.plugin_id">{{ plugin.plugin_id }}</code>
        </div>
        <span
          class="local-status"
          :class="{
            installed: plugin.local_state.installed,
            update: plugin.local_state.update_available,
          }"
        >
          {{ statusLabel }}
        </span>
      </header>

      <p class="summary">
        {{ plugin.summary || plugin.description || t('pluginMarket.card.noSummary') }}
      </p>

      <div class="tag-row" aria-label="Tags">
        <span v-for="tag in plugin.tags.slice(0, 3)" :key="tag" class="tag" :title="tag">
          {{ tag }}
        </span>
        <span v-if="plugin.tags.length > 3" class="tag">+{{ plugin.tags.length - 3 }}</span>
      </div>
    </RouterLink>

    <footer class="card-footer">
      <div class="metrics">
        <span :title="t('pluginMarket.card.downloads')">
          <Icon icon="material-symbols:download-rounded" width="17" height="17" />
          {{ formatCount(plugin.downloads_count) }}
        </span>
        <span v-if="plugin.rating_count > 0" :title="t('pluginMarket.card.rating')">
          <Icon icon="material-symbols:star-rounded" width="17" height="17" />
          {{ plugin.rating_avg.toFixed(1) }}
        </span>
        <span class="version">v{{ plugin.latest_version || '—' }}</span>
      </div>

      <button
        type="button"
        class="card-action"
        :class="{ primary: isPrimaryAction }"
        :disabled="busy"
        @click="emit('action', plugin)"
      >
        <Icon
          :icon="actionIcon"
          width="18"
          height="18"
          :class="{ spinning: busy }"
        />
        {{ actionLabel }}
      </button>
    </footer>
  </article>
</template>

<style scoped>
.market-card {
  min-width: 0;
  min-height: 250px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 92%, transparent);
  overflow: hidden;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
}

.market-card:hover {
  border-color: var(--md-sys-color-outline);
  box-shadow: var(--md-sys-elevation-1);
  transform: translateY(-2px);
}

.card-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 17px 17px 0;
  color: inherit;
  text-decoration: none;
}

.card-main:focus-visible {
  outline: 2px solid var(--md-sys-color-primary);
  outline-offset: -3px;
}

.card-header {
  min-width: 0;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.plugin-icon {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 8px;
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
  font-size: 1.05rem;
  font-weight: 700;
}

.plugin-icon img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.title-block {
  min-width: 0;
}

.title-block h2,
.title-block code {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.title-block h2 {
  margin: 0;
  color: var(--md-sys-color-on-surface);
  font-size: 1rem;
  line-height: 1.35;
}

.title-block code {
  margin-top: 3px;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.74rem;
}

.local-status {
  max-width: 116px;
  padding: 4px 8px;
  border-radius: 9999px;
  overflow: hidden;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container-high);
  font-size: 0.7rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.local-status.installed {
  color: var(--md-sys-color-on-tertiary-container);
  background: var(--md-sys-color-tertiary-container);
}

.local-status.update {
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
}

.summary {
  min-height: 63px;
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.86rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.tag-row {
  min-height: 26px;
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

.tag {
  max-width: 116px;
  padding: 4px 8px;
  border-radius: 6px;
  overflow: hidden;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container);
  font-size: 0.72rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-footer {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: auto 17px 17px;
  padding-top: 13px;
  border-top: 1px solid var(--md-sys-color-outline-variant);
}

.metrics,
.metrics span,
.card-action {
  display: inline-flex;
  align-items: center;
}

.metrics {
  min-width: 0;
  gap: 10px;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.76rem;
}

.metrics span {
  gap: 3px;
}

.metrics .version {
  color: var(--md-sys-color-primary);
  font-weight: 700;
}

.card-action {
  flex: 0 0 auto;
  min-height: 36px;
  justify-content: center;
  gap: 6px;
  padding: 0 13px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  color: var(--md-sys-color-primary);
  background: var(--md-sys-color-surface-container);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.16s, border-color 0.16s, color 0.16s;
}

.card-action:hover:not(:disabled) {
  border-color: var(--md-sys-color-outline);
  background: var(--md-sys-color-surface-container-high);
}

.card-action.primary {
  border-color: transparent;
  color: var(--md-sys-color-on-primary);
  background: var(--md-sys-color-primary);
}

.card-action.primary:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-primary) 90%, black);
}

.card-action:disabled {
  opacity: 0.68;
  cursor: wait;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 420px) {
  .card-header {
    grid-template-columns: 46px minmax(0, 1fr);
  }

  .local-status {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
