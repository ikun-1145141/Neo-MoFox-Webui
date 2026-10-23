<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useI18n } from '../../utils/i18n'
import type {
  InspectorRecordSummary,
  InspectorStatus,
} from '../../api/types/request-inspector'
const { t } = useI18n()
const props = defineProps<{
  records: InspectorRecordSummary[]
  selectedId: number | null
  models: string[]
  search: string
  status: InspectorStatus | ''
  model: string
  loading: boolean
  active?: boolean
}>()
const emit = defineEmits<{
  select: [id: number]
  'update:search': [value: string]
  'update:status': [value: InspectorStatus | '']
  'update:model': [value: string]
}>()
const recordsElement = ref<HTMLElement | null>(null)
let savedScroll = 0
let scrollGeneration = 0
watch(() => props.active, async (active, previous) => {
  const generation = ++scrollGeneration
  if (previous !== false && recordsElement.value) savedScroll = recordsElement.value.scrollTop
  await nextTick()
  if (generation === scrollGeneration && active !== false && recordsElement.value) recordsElement.value.scrollTop = savedScroll
})
const statuses: InspectorStatus[] = [
  'pending',
  'running',
  'streaming',
  'succeeded',
  'failed',
  'cancelled',
  'captured',
]
</script>
<template>
  <aside class="rm-list-panel" :aria-label="t('requestMonitor.records')">
    <div class="rm-list-toolbar">
      <div class="rm-toolbar-top">
        <h2 class="rm-toolbar-title">{{ t('requestMonitor.records') }}</h2>
        <span class="rm-count-pill">{{ records.length }}</span>
      </div>
      <input
        class="rm-search-input"
        type="search"
        :value="search"
        :placeholder="t('requestMonitor.search')"
        :aria-label="t('requestMonitor.search')"
        @input="
          emit('update:search', ($event.target as HTMLInputElement).value)
        "
      />
      <div class="rm-filter-row">
        <select
          class="rm-select"
          :value="status"
          :aria-label="t('requestMonitor.filterStatus')"
          @change="
            emit(
              'update:status',
              ($event.target as HTMLSelectElement).value as
                | InspectorStatus
                | '',
            )
          "
        >
          <option value="">{{ t('requestMonitor.allStatuses') }}</option>
          <option v-for="value in statuses" :key="value" :value="value">
            {{ t(`requestMonitor.status.${value}`) }}
          </option>
        </select>
        <select
          class="rm-select"
          :value="model"
          :aria-label="t('requestMonitor.filterModel')"
          @change="
            emit('update:model', ($event.target as HTMLSelectElement).value)
          "
        >
          <option value="">{{ t('requestMonitor.allModels') }}</option>
          <option v-if="model && !models.includes(model)" :value="model">
            {{ model }}
          </option>
          <option v-for="value in models" :key="value" :value="value">
            {{ value }}
          </option>
        </select>
      </div>
    </div>
    <div ref="recordsElement" class="rm-records" :aria-busy="loading">
      <p v-if="!records.length" class="rm-empty">
        {{ t(loading ? 'requestMonitor.loading' : 'requestMonitor.noRecords') }}
      </p>
      <button
        v-for="record in records"
        :key="record.id"
        class="rm-record"
        :class="{ selected: record.id === selectedId }"
        type="button"
        :aria-pressed="record.id === selectedId"
        @click="emit('select', record.id)"
      >
        <span class="rm-record-top"
          ><span class="rm-mono">#{{ record.id }}</span
          ><span class="rm-status-badge" :class="`rm-status-${record.status}`">{{
            t(`requestMonitor.status.${record.status}`)
          }}</span></span
        >
        <strong class="rm-record-name">{{
          record.request_name || record.model
        }}</strong>
        <span class="rm-record-model">{{ record.model }}</span>
        <span class="rm-record-api rm-mono">{{ record.api_provider }} · {{ record.api_name }}</span>
        <span class="rm-record-api">{{ t(record.stream ? 'requestMonitor.stream' : 'requestMonitor.nonStreaming') }} · {{ t('requestMonitor.attempt') }} {{ record.attempt }}</span>
        <span class="rm-record-bottom"
          ><time>{{ new Date(record.ts * 1000).toLocaleTimeString() }}</time
          ><span>{{
            record.duration_ms === null
              ? '—'
              : `${(record.duration_ms / 1000).toFixed(2)} s`
          }}</span></span
        >
      </button>
    </div>
  </aside>
</template>
