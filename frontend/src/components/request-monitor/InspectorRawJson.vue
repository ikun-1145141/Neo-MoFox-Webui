<script setup lang="ts">
import { computed, ref } from 'vue'
import type { InspectorRecordDetail, JsonValue } from '../../api/types/request-inspector'
import InspectorJsonTree from './InspectorJsonTree.vue'
import InspectorText from './InspectorText.vue'
import { useI18n } from '../../utils/i18n'
const props = defineProps<{ record: InspectorRecordDetail }>()
const emit = defineEmits<{ copy: [text: string]; export: [value: unknown, scope: string] }>()
const { t } = useI18n()
const source = ref<'params' | 'raw_response' | 'raw_events' | 'metadata' | 'record'>('params')
const mode = ref('tree')
const sources = { params: 'rawRequest', raw_response: 'rawResponse', raw_events: 'rawEvents', metadata: 'metadata', record: 'fullRecord' }
const value = computed(() => source.value === 'record' ? props.record : props.record[source.value])
// API details consist exclusively of JSON data; no provider-specific conversion.
const treeValue = computed(() => value.value as unknown as JsonValue)
// Not evaluated while the text view is closed, even for an actively streaming record.
const formatted = computed(() => mode.value === 'json' ? JSON.stringify(value.value, null, 2) : '')
const key = computed(() => `${props.record.instance_id}:${props.record.id}:${source.value}`)
</script>
<template>
  <div class="rm-section-heading rm-wrap">
    <select v-model="source" class="rm-input rm-raw-source" :aria-label="t('requestMonitor.rawSource')">
      <option v-for="(label, name) in sources" :key="name" :value="name">{{ t(`requestMonitor.${label}`) }}</option>
    </select>
    <div class="rm-inline-actions">
      <button class="rm-button" :aria-pressed="mode === 'tree'" @click="mode = 'tree'">{{ t('requestMonitor.tree') }}</button>
      <button class="rm-button" :aria-pressed="mode === 'json'" @click="mode = 'json'">JSON</button>
      <button class="rm-button" @click="emit('copy', JSON.stringify(value, null, 2))">{{ t('requestMonitor.copy') }}</button>
      <button class="rm-button" @click="emit('export', value, source)">{{ t('requestMonitor.downloadJson') }}</button>
    </div>
  </div>
  <p class="rm-muted rm-note">{{ t('requestMonitor.rawHint') }}</p>
  <p class="rm-muted rm-note">{{ t('requestMonitor.rawBudget') }}: {{ record.capture_info.raw_bytes }} / {{ record.capture_info.raw_limit_bytes }} B · {{ t('requestMonitor.rawEvents') }}: {{ record.raw_events.length }}</p>
  <InspectorJsonTree v-show="mode === 'tree'" :value="treeValue" :scope="key" :path-prefix="source === 'record' ? '' : `/${source}`" @copy="emit('copy', $event)" />
  <InspectorText v-if="mode === 'json'" :text="formatted" @copy="emit('copy', $event)" />
  <p v-if="mode === 'json'" class="rm-muted rm-note">{{ t('requestMonitor.previewHint') }}</p>
</template>
