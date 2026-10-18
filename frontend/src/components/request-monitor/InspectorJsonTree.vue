<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import type { JsonValue } from '../../api/types/request-inspector'
import { JSON_PAGE_SIZE, JSON_ROW_LIMIT, TEXT_PAGE_SIZE, hasJsonPath, previewJson, visibleJsonRows } from '../../utils/request-monitor-json'
import type { JsonNodeState, JsonRow } from '../../utils/request-monitor-json'
import { useI18n } from '../../utils/i18n'
const props = withDefaults(defineProps<{ value: JsonValue; scope: string; pathPrefix?: string }>(), { pathPrefix: '' })
const emit = defineEmits<{ copy: [text: string] }>()
const { t } = useI18n()
const state = reactive(new Map<string, JsonNodeState>())
watch(() => props.scope, () => state.clear())
watch(() => props.value, value => {
  for (const path of state.keys()) if (!hasJsonPath(value, path)) state.delete(path)
})
const view = computed(() => visibleJsonRows(props.value, state))
function update(path: string, patch: JsonNodeState) {
  if (!state.has(path) && state.size >= JSON_ROW_LIMIT * 2) state.delete(state.keys().next().value!)
  state.set(path, { ...state.get(path), ...patch })
}
function toggle(row: JsonRow) { update(row.path, { expanded: !row.expanded }) }
function copy(row: JsonRow) { emit('copy', JSON.stringify(row.value, null, 2)) }
</script>
<template>
  <div class="rm-json-tree" :aria-label="t('requestMonitor.tree')">
    <div v-for="row in view.rows" :key="`${row.more ? 'more:' : 'node:'}${row.path}`" class="rm-json-node" :style="{ '--rm-depth': Math.min(row.depth, 12) }" :data-json-path="row.path">
      <div v-if="row.more" class="rm-inline-actions">
        <button class="rm-button rm-small" :disabled="row.offset === 0" @click="update(row.path, { offset: Math.max(0, row.offset - JSON_PAGE_SIZE) })">{{ t('requestMonitor.previousPage') }}</button>
        <span class="rm-muted">{{ row.offset + 1 }}–{{ row.shown }} / {{ row.size }}</span>
        <button class="rm-button rm-small" :disabled="row.shown >= row.size" @click="update(row.path, { offset: row.shown })">{{ t('requestMonitor.moreChildren') }}</button>
      </div>
      <template v-else>
        <div class="rm-json-row">
          <button v-if="row.type === 'object' || row.type === 'array'" class="rm-json-toggle" :aria-expanded="row.expanded" :aria-label="`${t(row.expanded ? 'requestMonitor.collapse' : 'requestMonitor.expand')} ${row.key}`" @click="toggle(row)">{{ row.expanded ? '−' : '+' }}</button>
          <span v-else class="rm-json-toggle rm-muted" aria-hidden="true">·</span>
          <span class="rm-json-key">{{ row.key }}</span>
          <span class="rm-json-type">{{ row.type }}{{ ['object', 'array', 'string'].includes(row.type) ? ` (${row.size})` : '' }}</span>
          <span class="rm-json-value">{{ previewJson(row.value, state.get(row.path)?.textLength ?? 160) }}</span>
          <span class="rm-json-actions">
            <button class="rm-button rm-small" :aria-label="`${t('requestMonitor.copyPath')} ${row.key}`" @click="emit('copy', pathPrefix + row.path)">{{ t('requestMonitor.path') }}</button>
            <button class="rm-button rm-small" :aria-label="`${t('requestMonitor.copyNode')} ${row.key}`" @click="copy(row)">{{ t('requestMonitor.copyNode') }}</button>
          </span>
        </div>
        <button v-if="row.type === 'string' && row.size > (state.get(row.path)?.textLength ?? 160)" class="rm-button rm-small rm-json-more-text" @click="update(row.path, { textLength: (state.get(row.path)?.textLength ?? 160) + TEXT_PAGE_SIZE })">{{ t('requestMonitor.moreText') }}</button>
      </template>
    </div>
    <p v-if="view.limited" class="rm-info">{{ t('requestMonitor.treeLimit') }}</p>
  </div>
</template>
