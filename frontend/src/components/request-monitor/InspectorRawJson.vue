<script setup lang="ts">
import Icon from '../common/Icon.vue'
import { computed, ref } from 'vue'
import type { InspectorRecordDetail, JsonValue } from '../../api/types/request-inspector'
import InspectorJsonTree from './InspectorJsonTree.vue'
import InspectorText from './InspectorText.vue'
import { useI18n } from '../../utils/i18n'
const props = defineProps<{ record: InspectorRecordDetail }>()
const emit = defineEmits<{ copy: [text: string]; export: [value: unknown, scope: string] }>()
const { t } = useI18n()
const source = ref<'params' | 'raw_response' | 'raw_events' | 'metadata' | 'record'>('params')
const mode = ref('json')
const sources = { params: 'rawRequest', raw_response: 'rawResponse', raw_events: 'rawEvents', metadata: 'metadata', record: 'fullRecord' }
const value = computed(() => source.value === 'record' ? props.record : props.record[source.value])
// 接口详情仅包含 JSON 数据，不进行供应商专用格式转换。
const treeValue = computed(() => value.value as unknown as JsonValue)
// 文本视图关闭时不计算格式化内容，流式记录更新时也不例外。
const formatted = computed(() => mode.value === 'json' ? JSON.stringify(value.value, null, 2) : '')
const key = computed(() => `${props.record.instance_id}:${props.record.id}:${source.value}`)
</script>
<template>
  <div class="rm-mode-toolbar">
    <div class="rm-toolbar-group">
      <select v-model="source" class="rm-select" :aria-label="t('requestMonitor.rawSource')">
        <option v-for="(label, name) in sources" :key="name" :value="name">{{ t(`requestMonitor.${label}`) }}</option>
      </select>
      <div class="rm-segmented-control">
        <button class="rm-seg-btn" :class="{ active: mode === 'json' }" :aria-pressed="mode === 'json'" @click="mode = 'json'">JSON</button>
        <button class="rm-seg-btn" :class="{ active: mode === 'tree' }" :aria-pressed="mode === 'tree'" @click="mode = 'tree'">{{ t('requestMonitor.tree') }}</button>
      </div>
    </div>
    <div class="rm-toolbar-group">
      <button class="rm-btn rm-btn-tonal" @click="emit('copy', JSON.stringify(value, null, 2))">
        <Icon icon="material-symbols:content-copy-rounded" width="15" height="15" />
        <span>{{ t('requestMonitor.copy') }}</span>
      </button>
      <button class="rm-btn rm-btn-tonal" @click="emit('export', value, source)">
        <Icon icon="material-symbols:download-rounded" width="15" height="15" />
        <span>{{ t('requestMonitor.downloadJson') }}</span>
      </button>
    </div>
  </div>
  <p class="rm-muted rm-note">{{ t('requestMonitor.rawHint') }}</p>
  <p class="rm-muted rm-note">{{ t('requestMonitor.rawBudget') }}: {{ record.capture_info.raw_bytes }} / {{ record.capture_info.raw_limit_bytes }} B · {{ t('requestMonitor.rawEvents') }}: {{ record.raw_events.length }}</p>
  <InspectorJsonTree v-show="mode === 'tree'" :value="treeValue" :scope="key" :path-prefix="source === 'record' ? '' : `/${source}`" @copy="emit('copy', $event)" />
  <InspectorText v-if="mode === 'json'" :text="formatted" @copy="emit('copy', $event)" />
  <p v-if="mode === 'json'" class="rm-muted rm-note">{{ t('requestMonitor.previewHint') }}</p>
</template>
