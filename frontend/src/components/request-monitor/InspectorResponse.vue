<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '../../utils/i18n'
import type { InspectorRecordDetail } from '../../api/types/request-inspector'
import InspectorJsonTree from './InspectorJsonTree.vue'
import InspectorText from './InspectorText.vue'
const props = defineProps<{ record: InspectorRecordDetail }>()
const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()
const key = computed(() => `${props.record.instance_id}:${props.record.id}`)
const pending = computed(() => ['pending', 'running', 'streaming'].includes(props.record.status))
</script>
<template>
  <p v-if="pending" class="rm-info rm-note">{{ t('requestMonitor.partialResponse') }}</p>
  <p v-else-if="record.status === 'captured'" class="rm-info rm-note">{{ t('requestMonitor.capturedOnly') }}</p>
  <section v-if="record.response.kind === 'chat'" class="rm-response-sections">
    <section v-if="record.response.message !== null" class="rm-block">
      <h3>{{ t('requestMonitor.responseText') }}</h3>
      <InspectorText :text="record.response.message" @copy="emit('copy', $event)" />
    </section>
    <p v-else class="rm-empty">{{ t(pending ? 'requestMonitor.waitingContent' : record.response.tool_calls.length ? 'requestMonitor.toolOnlyResponse' : 'requestMonitor.noResponseText') }}</p>
    <section v-if="record.response.reasoning_content !== null" class="rm-block">
      <h3>{{ t('requestMonitor.reasoning') }}</h3>
      <InspectorText :text="record.response.reasoning_content" @copy="emit('copy', $event)" />
    </section>
    <section v-if="record.response.reasoning_parts.length" class="rm-block">
      <h3>{{ t('requestMonitor.reasoningParts') }}</h3>
      <InspectorJsonTree :value="record.response.reasoning_parts" :scope="`${key}:reasoning`" path-prefix="/response/reasoning_parts" @copy="emit('copy', $event)" />
    </section>
    <p v-if="record.response.tool_calls.length" class="rm-muted rm-note">{{ t('requestMonitor.callsInTools') }}: {{ record.response.tool_calls.length }}</p>
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
</template>
