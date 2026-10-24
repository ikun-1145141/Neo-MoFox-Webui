<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Icon from '../common/Icon.vue'
import { useI18n } from '../../utils/i18n'
import type { InspectorMessageBlock, InspectorMessageView, InspectorRecordDetail, JsonValue } from '../../api/types/request-inspector'
import InspectorJsonTree from './InspectorJsonTree.vue'
import InspectorMessages from './InspectorMessages.vue'
const props = defineProps<{ record: InspectorRecordDetail }>()
const emit = defineEmits<{ copy: [text: string]; tools: [] }>()
const { t } = useI18n()
const key = computed(() => `${props.record.instance_id}:${props.record.id}`)
const mode = ref<'messages' | 'tree'>('messages')
watch(key, () => { mode.value = 'messages' })
const treeValue = computed(() => props.record.response as unknown as JsonValue)
const hasMessage = computed(() => !!props.record.response.message?.trim())
const pending = computed(() => ['pending', 'running', 'streaming'].includes(props.record.status))

function block(type: string, label: string, text: string | null): InspectorMessageBlock {
  return { type, label, text, media_type: null, title: null, meta: null, call_id: null, name: null, arguments_text: null }
}
function field(call: JsonValue, name: string): JsonValue | undefined {
  return call !== null && typeof call === 'object' && !Array.isArray(call) && Object.hasOwn(call, name) ? call[name] : undefined
}
// Render only the public normalized response, without guessing provider protocols or tool semantics.
const messages = computed<InspectorMessageView[]>(() => {
  const response = props.record.response
  const result: InspectorMessageView[] = []
  const blocks: InspectorMessageBlock[] = []
  if (hasMessage.value) blocks.push(block('markdown', t('requestMonitor.responseText'), response.message))
  if (response.reasoning_content?.trim()) blocks.push(block('markdown', t('requestMonitor.reasoning'), response.reasoning_content))
  if (blocks.length) result.push({ index: 0, role: 'assistant', label: 'Assistant', meta: props.record.model, blocks })
  for (const [index, call] of response.tool_calls.entries()) {
    const tool = block('tool_call', t('requestMonitor.toolCall'), null)
    const name = field(call, 'name')
    const id = field(call, 'id')
    const args = field(call, 'args')
    tool.name = typeof name === 'string' ? name : null
    tool.call_id = typeof id === 'string' ? id : null
    tool.arguments_text = typeof args === 'string' ? args : JSON.stringify(args === undefined ? call : args, null, 2)
    result.push({ index: index + 1, role: 'assistant', label: 'Assistant', meta: `${t('requestMonitor.toolCall')} · #${index + 1}`, blocks: [tool] })
  }
  return result
})
</script>
<template>
  <div class="rm-mode-toolbar">
    <div class="rm-segmented-control">
      <button class="rm-seg-btn" :class="{ active: mode === 'messages' }" :aria-pressed="mode === 'messages'" @click="mode = 'messages'">{{ t('requestMonitor.responseMessages') }}</button>
      <button class="rm-seg-btn" :class="{ active: mode === 'tree' }" :aria-pressed="mode === 'tree'" @click="mode = 'tree'">{{ t('requestMonitor.tree') }}</button>
    </div>
    <button class="rm-btn rm-btn-tonal" @click="emit('copy', JSON.stringify(record.response, null, 2))">
      <Icon icon="material-symbols:content-copy-rounded" width="15" height="15" />
      <span>{{ t('requestMonitor.copy') }}</span>
    </button>
  </div>
  <p v-if="pending" class="rm-info rm-note">{{ t('requestMonitor.partialResponse') }}</p>
  <p v-else-if="record.status === 'captured'" class="rm-info rm-note">{{ t('requestMonitor.capturedOnly') }}</p>
  <InspectorJsonTree v-show="mode === 'tree'" :value="treeValue" :scope="`${key}:response`" path-prefix="/response" @copy="emit('copy', $event)" />
  <div v-show="mode === 'messages'">
    <section v-if="record.response.kind === 'chat'" class="rm-response-sections">
      <p v-if="!hasMessage" class="rm-info rm-note">{{ t(record.response.tool_calls.length ? 'requestMonitor.toolOnlyResponse' : pending ? 'requestMonitor.waitingContent' : 'requestMonitor.noResponseText') }}</p>
      <InspectorMessages v-if="messages.length" :messages="messages" :record-key="`${key}:response`" :title="t('requestMonitor.responseMessages')" @copy="emit('copy', $event)" />
      <section v-if="record.response.reasoning_parts.length" class="rm-block">
        <h3>{{ t('requestMonitor.reasoningParts') }}</h3>
        <InspectorJsonTree :value="record.response.reasoning_parts" :scope="`${key}:reasoning`" path-prefix="/response/reasoning_parts" @copy="emit('copy', $event)" />
      </section>
      <p v-if="record.response.tool_calls.length" class="rm-note">
        <button class="rm-btn rm-btn-tonal" @click="emit('tools')">{{ t('requestMonitor.viewToolCalls') }}</button>
      </p>
      <p v-if="record.response.stop_reason !== null" class="rm-muted rm-note">{{ t('requestMonitor.stopReason') }}: {{ record.response.stop_reason }}</p>
    </section>
    <section v-else-if="record.response.kind === 'embedding'" class="rm-block">
      <h3>{{ t('requestMonitor.embeddings') }} · {{ record.response.embeddings.length }}</h3>
      <p class="rm-muted rm-note">{{ t('requestMonitor.vectorHint') }}</p>
      <InspectorJsonTree :value="record.response.embeddings" :scope="`${key}:embeddings`" path-prefix="/response/embeddings" @copy="emit('copy', $event)" />
    </section>
    <section v-else-if="record.response.kind === 'rerank'" class="rm-block">
      <h3>{{ t('requestMonitor.rerank') }} · {{ record.response.results.length }}</h3>
      <InspectorJsonTree :value="record.response.results" :scope="`${key}:results`" path-prefix="/response/results" @copy="emit('copy', $event)" />
    </section>
    <p v-else class="rm-empty">{{ t(pending ? 'requestMonitor.waitingContent' : 'requestMonitor.noResponse') }}</p>
    <section v-if="record.response.usage !== null" class="rm-block">
      <h3>{{ t('requestMonitor.usage') }}</h3>
      <InspectorJsonTree :value="record.response.usage" :scope="`${key}:usage`" path-prefix="/response/usage" @copy="emit('copy', $event)" />
    </section>
    <p v-else class="rm-muted rm-note">{{ t('requestMonitor.usageUnavailable') }}</p>
  </div>
</template>
