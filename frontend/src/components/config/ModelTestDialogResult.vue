<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/utils/i18n'
import Icon from '../common/Icon.vue'
import type { TestItem } from './modelTestDialogTypes'

const props = defineProps<{ test: TestItem }>()
const { t } = useI18n()
const tr = (key: string, params?: Record<string, string>) => t(`modelTestDialog.${key}`, params)
const result = computed(() => props.test.result)
</script>

<template>
  <div class="inline-result" role="group" :aria-label="tr('outputTitle')">
    <p v-if="test.status === 'fail'" class="error-line"><strong>{{ tr('result.error') }}</strong>
      <span class="verbatim">{{ test.error || tr('errors.failed') }}</span></p>
    <div v-if="result?.response_text" class="part"><strong>{{ tr('result.response') }}</strong>
      <p class="verbatim">{{ result.response_text }}</p></div>
    <div v-if="result?.tool_calls?.length" class="part"><strong>{{ tr('result.toolCalls') }}</strong>
      <ul class="tools"><li v-for="(name, index) in result.tool_calls" :key="index"><code>{{ name }}</code></li></ul></div>
    <div v-if="test.key === 'embedding' && result?.dimensions != null" class="part">
      <strong>{{ tr('result.dimensions', { dim: String(result.dimensions) }) }}</strong>
      <p v-if="result.embedding_preview?.length" class="vector">{{ tr('result.embeddingPreview') }} <code>[{{ result.embedding_preview.join(', ') }}]</code></p>
    </div>
    <div v-if="test.key === 'rerank' && result?.rerank_results" class="part">
      <strong>{{ tr('result.rerankCount', { count: String(result.rerank_results.length) }) }}</strong>
      <ol v-if="result.rerank_results.length" class="ranks"><li v-for="(item, index) in result.rerank_results" :key="index">
        <span class="score">{{ tr('result.score', { score: String(item.score) }) }}</span><p class="verbatim">{{ item.document }}</p></li></ol>
    </div>
    <p v-if="result?.latency_ms != null" class="latency"><Icon icon="timer-outline-rounded" :width="14" :height="14" />{{ tr('result.latency', { ms: String(Math.round(result.latency_ms)) }) }}</p>
  </div>
</template>

<style scoped>
.inline-result { min-width: 0; display: grid; gap: 8px; margin: 0 14px; padding: 10px 0 12px; border-block-start: 1px solid var(--mt-line); font-size: 13px; line-height: 1.55; overflow-wrap: anywhere; }
.inline-result:empty { display: none; }
.inline-result :is(p, ul, ol) { margin: 0; }
.part, .error-line { min-width: 0; display: grid; gap: 2px; }
.inline-result strong, .score, .latency { color: var(--md-sys-color-on-surface-variant); font-size: 12px; }
.inline-result strong { font-weight: 600; }
.verbatim { white-space: pre-wrap; }
.error-line { border-inline-start: 2px solid var(--md-sys-color-error); padding-inline-start: 9px; }
.error-line strong { color: var(--md-sys-color-error); }
.latency { display: flex; align-items: center; gap: 5px; font-variant-numeric: tabular-nums; }
.tools { list-style: none; display: flex; flex-wrap: wrap; gap: 5px; padding: 0; }
.tools li { min-width: 0; padding: 2px 6px; border-radius: var(--md-sys-shape-corner-extra-small); background: var(--md-sys-color-surface-container-low); }
.vector code, .tools code { font: 12px/1.55 ui-monospace, Consolas, monospace; }
.ranks { padding-inline-start: 22px; }
.ranks li + li { margin-top: 6px; }
.ranks li::marker { color: var(--md-sys-color-on-surface-variant); font-size: 12px; }
</style>
