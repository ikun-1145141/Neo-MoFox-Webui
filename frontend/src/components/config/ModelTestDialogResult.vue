<!--
  @file ModelTestDialogResult.vue
  @description 单个模型测试项的结果展示（等待/运行中/成功/失败）
-->

<template>
  <div class="test-result" :class="`status-${test.status}`">
    <template v-if="test.status === 'idle'">
      <Icon icon="material-symbols:schedule-outline-rounded" :size="18" />
      <span>{{ t('modelTestDialog.status.idle') }}</span>
    </template>

    <template v-else-if="test.status === 'running'">
      <Icon icon="material-symbols:progress-activity" :size="18" class="spinning" />
      <span>{{ t('modelTestDialog.status.running') }}</span>
    </template>

    <template v-else-if="test.status === 'success' && test.result">
      <Icon icon="material-symbols:check-circle-outline-rounded" :size="18" />
      <div class="result-content">
        <p class="result-line">
          <span class="status-label">{{ t('modelTestDialog.status.success') }}</span>
          <span v-if="hasLatency(test.result)" class="latency">
            {{ t('modelTestDialog.result.latency', { ms: String(test.result.latency_ms!.toFixed(0)) }) }}
          </span>
        </p>

        <p v-if="test.result.response_text" class="result-detail">
          {{ truncate(test.result.response_text, 120) }}
        </p>

        <p v-if="test.key === 'embedding' && test.result.dimensions" class="result-detail">
          {{ t('modelTestDialog.result.dimensions', { dim: String(test.result.dimensions) }) }}
          <template v-if="test.result.embedding_preview?.length">
            · {{ t('modelTestDialog.result.embeddingPreview') }}
            <code>{{ formatPreview(test.result.embedding_preview) }}</code>
          </template>
        </p>

        <template v-if="test.key === 'rerank'">
          <p class="result-detail">
            {{ t('modelTestDialog.result.rerankCount', { count: String(test.result.rerank_results?.length || 0) }) }}
          </p>
          <ol v-if="test.result.rerank_results?.length" class="rerank-list">
            <li v-for="(item, idx) in test.result.rerank_results.slice(0, 3)" :key="idx">
              <span class="score">{{ (item.score * 100).toFixed(1) }}%</span>
              <span class="doc">{{ truncate(item.document, 60) }}</span>
            </li>
          </ol>
        </template>

        <p v-if="test.key === 'tool_call' && test.result.tool_calls?.length" class="result-detail">
          {{ t('modelTestDialog.result.toolCalls') }}: <code>{{ test.result.tool_calls.join(', ') }}</code>
        </p>
      </div>
    </template>

    <template v-else>
      <Icon icon="material-symbols:error-outline-rounded" :size="18" />
      <div class="result-content">
        <p class="result-line">
          <span class="status-label">{{ t('modelTestDialog.status.fail') }}</span>
          <span v-if="test.result && hasLatency(test.result)" class="latency">
            {{ t('modelTestDialog.result.latency', { ms: String(test.result.latency_ms!.toFixed(0)) }) }}
          </span>
        </p>
        <p class="result-detail">{{ test.error || test.result?.error_message || t('modelTestDialog.status.fail') }}</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '@/utils/i18n'
import Icon from '../common/Icon.vue'
import type { TestItem } from './modelTestDialogTypes'
import type { ModelTestResult } from '@/api/types/config'

const { t } = useI18n()

defineProps<{
  test: TestItem
  isRunning: boolean
}>()

function hasLatency(result: ModelTestResult): boolean {
  return result.latency_ms !== undefined && result.latency_ms !== null
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text
  return text.slice(0, max) + '…'
}

function formatPreview(values: number[]): string {
  return values.map(v => v.toFixed(4)).join(', ')
}
</script>

<style scoped>
.test-result {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface-variant);
}

.test-result.status-success {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.test-result.status-fail {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.status-success .status-label {
  color: var(--md-sys-color-on-tertiary-container);
}

.status-fail .status-label {
  color: var(--md-sys-color-on-error-container);
}

.status-success .latency,
.status-fail .latency {
  font-weight: 400;
  font-size: 12px;
  opacity: 0.75;
}

.status-success .result-detail,
.status-fail .result-detail {
  color: inherit;
}

.result-content {
  flex: 1;
  min-width: 0;
}

.result-line {
  margin: 0 0 4px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: inherit;
}

.latency {
  font-weight: 400;
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.75;
}

.result-detail {
  margin: 0;
  color: var(--md-sys-color-on-surface-variant);
  word-break: break-word;
  white-space: pre-wrap;
}

.result-detail code {
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--md-sys-color-surface-container);
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.rerank-list {
  margin: 6px 0 0 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rerank-list li {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
}

.rerank-list .score {
  font-weight: 600;
  color: var(--md-sys-color-primary);
  flex-shrink: 0;
}

.rerank-list .doc {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>