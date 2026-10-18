<script setup lang="ts">
import { computed, ref, shallowReactive, watch } from 'vue'
import InspectorMessages from './InspectorMessages.vue'
import InspectorTools from './InspectorTools.vue'
import InspectorResponse from './InspectorResponse.vue'
import InspectorJsonTree from './InspectorJsonTree.vue'
import InspectorRawJson from './InspectorRawJson.vue'
import InspectorText from './InspectorText.vue'
import { useI18n } from '../../utils/i18n'
import type { InspectorRecordDetail } from '../../api/types/request-inspector'
const props = defineProps<{ record: InspectorRecordDetail | null; loading: boolean; exporting: boolean; filteredOut?: boolean }>()
const emit = defineEmits<{ copy: [text: string]; export: [value: unknown, scope: string] }>()
const { t } = useI18n()
const tabs = ['request', 'response', 'tools', 'raw'] as const
const tab = ref<(typeof tabs)[number]>('request')
const requestMode = ref('messages')
const panels = shallowReactive<Record<string, InspectorRecordDetail | null>>({})
const recordKey = computed(() => props.record ? `${props.record.instance_id}:${props.record.id}` : '')
// Keep at most four visited panels. Inactive panels retain DOM/scroll/state, not live updates.
watch(recordKey, () => {
  for (const name of tabs) panels[name] = null
  tab.value = 'request'
  requestMode.value = 'messages'
}, { flush: 'sync' })
watch([() => props.record, tab], () => {
  if (props.record) panels[tab.value] = props.record
}, { immediate: true, flush: 'sync' })
const metadata = computed(() => props.record ? [
  ['provider', props.record.api_provider || '—'],
  ['trace', props.record.logical_request_id || '—'],
  ['attempt', props.record.attempt],
  ['stream', t(props.record.stream ? 'requestMonitor.yes' : 'requestMonitor.no')],
  ['duration', props.record.duration_ms === null ? '—' : `${(props.record.duration_ms / 1000).toFixed(3)} s`],
  ['firstToken', props.record.first_token_ms === null ? '—' : `${(props.record.first_token_ms / 1000).toFixed(3)} s`],
  ['tokensIn', props.record.tokens_in ?? '—'], ['tokensOut', props.record.tokens_out ?? '—'],
  ['estimated', props.record.estimated_input_tokens ?? '—'],
] : [])
function moveTab(event: KeyboardEvent) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (tabs.indexOf(tab.value) + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
  tab.value = tabs[index]!
  ;(event.currentTarget as HTMLElement).querySelectorAll<HTMLButtonElement>('[role="tab"]')[index]?.focus()
}
</script>
<template>
  <section class="rm-detail-panel" :aria-label="t('requestMonitor.detail')" :aria-busy="loading">
    <div v-if="!record" class="rm-welcome">
      <h2>{{ t(loading ? 'requestMonitor.loading' : 'requestMonitor.selectRecord') }}</h2>
      <p>{{ t('requestMonitor.selectHint') }}</p>
      <span class="rm-muted">{{ t('requestMonitor.memoryOnly') }}</span>
    </div>
    <template v-else>
      <header class="rm-detail-header">
        <div class="rm-detail-header-main">
          <div class="rm-detail-meta-top">
            <span class="rm-mono rm-detail-id-tag">#{{ record.id }}</span>
            <span class="rm-detail-time-tag">{{ new Date(record.ts * 1000).toLocaleString() }}</span>
            <span class="rm-status-badge" :class="`rm-status-${record.status}`">{{ t(`requestMonitor.status.${record.status}`) }}</span>
          </div>
          <h2 class="rm-detail-title">{{ record.request_name || record.model }}</h2>
          <div class="rm-detail-subline">
            <span class="rm-model-tag">{{ record.model }}</span>
            <span class="rm-detail-sep">·</span>
            <span class="rm-mono rm-detail-api">{{ record.api_provider }} · {{ record.api_name }}</span>
          </div>
        </div>
        <button class="rm-btn rm-btn-tonal rm-detail-export-btn" :disabled="exporting || loading" @click="emit('export', record, 'record')">
          <Icon icon="material-symbols:download-rounded" width="16" height="16" />
          <span>{{ t('requestMonitor.export') }}</span>
        </button>
      </header>
      <details class="rm-record-meta">
        <summary>{{ t('requestMonitor.requestInfo') }}</summary>
        <dl class="rm-overview"><template v-for="[name, value] in metadata" :key="name"><dt>{{ t(`requestMonitor.${name}`) }}</dt><dd class="rm-mono">{{ value }}</dd></template></dl>
      </details>
      <p v-if="filteredOut" class="rm-info rm-inline-notice">{{ t('requestMonitor.filteredSelection') }}</p>
      <div v-if="record.error" class="rm-error rm-record-error" role="alert"><strong>{{ record.error.type }} {{ record.error.status_code ?? '' }}</strong><InspectorText :text="record.error.message" @copy="emit('copy', $event)" /></div>
      <div class="rm-integrity">
        <span v-if="record.capture_info.redacted">{{ t('requestMonitor.redacted') }}</span>
        <span v-if="record.capture_info.raw_truncated" class="rm-warning">{{ t('requestMonitor.truncated') }}</span>
        <span v-if="record.capture_info.raw_unavailable" class="rm-warning">{{ t('requestMonitor.rawUnavailable') }}</span>
        <span v-if="record.capture_info.request_unavailable" class="rm-warning">{{ t('requestMonitor.requestUnavailable') }}</span>
        <span v-if="record.capture_info.metadata_unavailable" class="rm-warning">{{ t('requestMonitor.metadataUnavailable') }}</span>
      </div>
      <div class="rm-tabs" role="tablist" :aria-label="t('requestMonitor.detail')" @keydown="moveTab">
        <button v-for="name in tabs" :id="`rm-tab-${name}`" :key="name" type="button" role="tab" :aria-selected="tab === name" :aria-controls="`rm-panel-${name}`" :tabindex="tab === name ? 0 : -1" class="rm-tab-btn" :class="{ active: tab === name }" @click="tab = name">{{ t(`requestMonitor.${name}`) }}</button>
        <span v-if="loading" class="rm-muted" style="margin-left: auto; align-self: center; font-size: 0.72rem;">{{ t('requestMonitor.updating') }}</span>
      </div>
      <template v-for="name in tabs" :key="`${recordKey}:${name}`">
        <div v-if="panels[name]" v-show="tab === name" :id="`rm-panel-${name}`" class="rm-detail-content" role="tabpanel" :aria-labelledby="`rm-tab-${name}`" tabindex="0">
          <template v-if="name === 'request'">
            <div class="rm-mode-toolbar">
              <div class="rm-segmented-control">
                <button class="rm-seg-btn" :class="{ active: requestMode === 'messages' }" :aria-pressed="requestMode === 'messages'" @click="requestMode = 'messages'">{{ t('requestMonitor.messages') }}</button>
                <button class="rm-seg-btn" :class="{ active: requestMode === 'tree' }" :aria-pressed="requestMode === 'tree'" @click="requestMode = 'tree'">{{ t('requestMonitor.tree') }}</button>
              </div>
              <button class="rm-btn rm-btn-tonal" @click="emit('copy', JSON.stringify(panels[name]!.params, null, 2))">
                <Icon icon="material-symbols:content-copy-rounded" width="15" height="15" />
                <span>{{ t('requestMonitor.copy') }}</span>
              </button>
            </div>
            <p class="rm-muted rm-note">{{ t('requestMonitor.requestHint') }}</p>
            <InspectorJsonTree v-show="requestMode === 'tree'" :value="panels[name]!.params" :scope="`${recordKey}:params`" path-prefix="/params" @copy="emit('copy', $event)" />
            <div v-show="requestMode === 'messages'"><InspectorMessages :messages="panels[name]!.rendered.messages" :record-key="recordKey" @copy="emit('copy', $event)" /></div>
            <details class="rm-block rm-metadata-block"><summary>{{ t('requestMonitor.metadata') }}</summary><InspectorJsonTree :value="panels[name]!.metadata" :scope="`${recordKey}:metadata`" path-prefix="/metadata" @copy="emit('copy', $event)" /></details>
          </template>
          <InspectorResponse v-else-if="name === 'response'" :record="panels[name]!" @copy="emit('copy', $event)" />
          <InspectorTools v-else-if="name === 'tools'" :record="panels[name]!" @copy="emit('copy', $event)" />
          <InspectorRawJson v-else :record="panels[name]!" @copy="emit('copy', $event)" @export="(value, scope) => emit('export', value, scope)" />
        </div>
      </template>
      <p class="rm-privacy">{{ t('requestMonitor.privacyHint') }}</p>
    </template>
  </section>
</template>
