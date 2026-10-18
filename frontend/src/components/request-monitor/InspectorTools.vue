<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from '../../utils/i18n'
import { parseJsonText } from '../../utils/request-monitor-json'
import type { InspectorRecordDetail, JsonValue } from '../../api/types/request-inspector'
import InspectorJsonTree from './InspectorJsonTree.vue'
import InspectorMessages from './InspectorMessages.vue'
const props = defineProps<{ record: InspectorRecordDetail }>()
const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()
const opened = reactive(new Set<string>())
const definitionLimit = ref(100)
const callLimit = ref(100)
const key = computed(() => `${props.record.instance_id}:${props.record.id}`)
const results = computed(() => props.record.rendered.messages
  .map(message => ({ ...message, blocks: message.blocks.filter(block => block.type === 'tool_result') }))
  .filter(message => message.blocks.length))
function toggle(id: string, event: Event) {
  if ((event.target as HTMLDetailsElement).open) opened.add(id)
  else opened.delete(id)
}
function field(call: JsonValue, name: string): JsonValue | undefined {
  return call !== null && !Array.isArray(call) && typeof call === 'object' && Object.hasOwn(call, name) ? call[name] : undefined
}
function label(call: JsonValue): string {
  const name = field(call, 'name')
  return typeof name === 'string' ? name : t('requestMonitor.toolCall')
}
function argumentText(call: JsonValue): string | null {
  const args = field(call, 'args')
  return typeof args === 'string' ? args : null
}
</script>
<template>
  <p class="rm-muted rm-note">{{ t('requestMonitor.toolsHint') }}</p>
  <section class="rm-tool-section">
    <h3>{{ t('requestMonitor.toolDefinitions') }} · {{ record.rendered.tools.length }}</h3>
    <p v-if="!record.rendered.tools.length" class="rm-empty">{{ t('requestMonitor.noTools') }}</p>
    <details v-for="tool in record.rendered.tools.slice(0, definitionLimit)" :key="tool.index" class="rm-block" @toggle="toggle(`definition:${tool.index}`, $event)">
      <summary><strong class="rm-mono">{{ tool.name }}</strong> <span class="rm-muted">{{ tool.kind }}</span></summary>
      <template v-if="opened.has(`definition:${tool.index}`)">
        <p class="rm-note">{{ tool.description || '—' }}</p>
        <p v-if="tool.required.length" class="rm-muted rm-note">{{ t('requestMonitor.required') }}: {{ tool.required.join(', ') }}</p>
        <InspectorJsonTree :value="parseJsonText(tool.raw_json).value" :scope="`${key}:definition:${tool.index}`" @copy="emit('copy', $event)" />
      </template>
    </details>
    <button v-if="record.rendered.tools.length > definitionLimit" class="rm-button" @click="definitionLimit += 100">{{ t('requestMonitor.moreChildren') }}</button>
  </section>
  <section class="rm-tool-section">
    <h3>{{ t('requestMonitor.modelToolCalls') }} · {{ record.response.tool_calls.length }}</h3>
    <p v-if="!record.response.tool_calls.length" class="rm-empty">{{ t('requestMonitor.noToolCalls') }}</p>
    <details v-for="(call, index) in record.response.tool_calls.slice(0, callLimit)" :key="index" class="rm-block" @toggle="toggle(`call:${index}`, $event)">
      <summary>{{ label(call) }} · #{{ index + 1 }} <span v-if="typeof field(call, 'id') === 'string'" class="rm-muted rm-mono">{{ field(call, 'id') }}</span></summary>
      <template v-if="opened.has(`call:${index}`)">
        <InspectorJsonTree :value="call" :scope="`${key}:call:${index}`" :path-prefix="`/response/tool_calls/${index}`" @copy="emit('copy', $event)" />
        <template v-if="argumentText(call) !== null">
          <p class="rm-muted rm-note">{{ t(parseJsonText(argumentText(call)!).parsed ? 'requestMonitor.parsedArguments' : 'requestMonitor.partialArguments') }}</p>
          <InspectorJsonTree v-if="parseJsonText(argumentText(call)!).parsed" :value="parseJsonText(argumentText(call)!).value" :scope="`${key}:args:${index}`" @copy="emit('copy', $event)" />
        </template>
      </template>
    </details>
    <button v-if="record.response.tool_calls.length > callLimit" class="rm-button" @click="callLimit += 100">{{ t('requestMonitor.moreChildren') }}</button>
  </section>
  <section class="rm-tool-section">
    <h3>{{ t('requestMonitor.toolResults') }}</h3>
    <p v-if="!results.length" class="rm-empty">{{ t('requestMonitor.noToolResults') }}</p>
    <InspectorMessages v-else :messages="results" :record-key="key" @copy="emit('copy', $event)" />
  </section>
</template>
