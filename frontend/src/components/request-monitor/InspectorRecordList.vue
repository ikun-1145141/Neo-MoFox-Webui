<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from '../../utils/i18n'
import MdSelect from '../common/MdSelect.vue'
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
const statusOptions = computed(() => [
  { label: t('requestMonitor.allStatuses'), value: '' },
  ...statuses.map((value) => ({
    label: t(`requestMonitor.status.${value}`),
    value,
  })),
])
const modelOptions = computed(() => {
  const models = props.model && !props.models.includes(props.model)
    ? [props.model, ...props.models]
    : props.models

  return [
    { label: t('requestMonitor.allModels'), value: '' },
    ...models.map((value) => ({ label: value, value })),
  ]
})
function updateStatus(value: string | number | null) {
  emit('update:status', String(value ?? '') as InspectorStatus | '')
}
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
        <MdSelect
          class="rm-md-select"
          :model-value="status"
          :options="statusOptions"
          :placeholder="t('requestMonitor.allStatuses')"
          :aria-label="t('requestMonitor.filterStatus')"
          @update:model-value="updateStatus"
        />
        <MdSelect
          class="rm-md-select"
          :model-value="model"
          :options="modelOptions"
          :placeholder="t('requestMonitor.allModels')"
          :aria-label="t('requestMonitor.filterModel')"
          @update:model-value="emit('update:model', String($event ?? ''))"
        />
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
