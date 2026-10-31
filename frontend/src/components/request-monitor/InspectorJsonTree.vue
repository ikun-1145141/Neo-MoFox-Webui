<script setup lang="ts">
import { computed, reactive, watch, type PropType } from 'vue'
import Icon from '../common/Icon.vue'
import type { JsonValue } from '../../api/types/request-inspector'
import { JSON_PAGE_SIZE, JSON_ROW_LIMIT, hasJsonPath, previewJson, visibleJsonRows } from '../../utils/request-monitor-json'
import type { JsonNodeState, JsonRow } from '../../utils/request-monitor-json'
import { useI18n } from '../../utils/i18n'

const props = defineProps({
  // 禁止布尔属性转换，避免根节点的空字符串被转换成 true。
  value: { type: null as unknown as PropType<JsonValue>, required: true },
  scope: { type: String, required: true },
  pathPrefix: { type: String, default: '' },
})
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
  <div class="rm-tree-container" :aria-label="t('requestMonitor.tree')">
    <div
      v-for="row in view.rows"
      :key="`${row.more ? 'more:' : 'node:'}${row.path}`"
      class="rm-tree-item"
      :style="{ '--rm-depth': Math.min(row.depth, 14) }"
      :data-json-path="row.path"
    >
      <div v-if="row.more" class="rm-tree-pagination">
        <button
          class="rm-tree-btn"
          :disabled="row.offset === 0"
          @click="update(row.path, { offset: Math.max(0, row.offset - JSON_PAGE_SIZE) })"
        >
          <Icon icon="material-symbols:chevron-left-rounded" width="16" height="16" />
          {{ t('requestMonitor.previousPage') }}
        </button>
        <span class="rm-tree-page-info">{{ row.offset + 1 }}–{{ row.shown }} / {{ row.size }}</span>
        <button
          class="rm-tree-btn"
          :disabled="row.shown >= row.size"
          @click="update(row.path, { offset: row.shown })"
        >
          {{ t('requestMonitor.moreChildren') }}
          <Icon icon="material-symbols:chevron-right-rounded" width="16" height="16" />
        </button>
      </div>

      <template v-else>
        <div class="rm-tree-row" :class="{ 'is-expandable': row.type === 'object' || row.type === 'array' }">
          <!-- 展开/折叠按钮 -->
          <button
            v-if="row.type === 'object' || row.type === 'array'"
            class="rm-tree-toggle"
            :aria-expanded="row.expanded"
            :aria-label="`${t(row.expanded ? 'requestMonitor.collapse' : 'requestMonitor.expand')} ${row.key}`"
            @click="toggle(row)"
          >
            <Icon
              :icon="row.expanded ? 'material-symbols:keyboard-arrow-down-rounded' : 'material-symbols:keyboard-arrow-right-rounded'"
              width="18"
              height="18"
            />
          </button>
          <span v-else class="rm-tree-bullet" aria-hidden="true"></span>

          <!-- 字段 Key -->
          <span class="rm-tree-key">{{ row.key }}</span>
          <span class="rm-tree-colon">:</span>

          <!-- 类型徽标 -->
          <span class="rm-tree-type-pill" :class="`type-${row.type}`">
            {{ row.type }}{{ ['object', 'array', 'string'].includes(row.type) ? ` (${row.size})` : '' }}
          </span>

          <!-- 非字符串节点的缩略值 -->
          <span v-if="row.type !== 'string'" class="rm-tree-val" :class="`val-${row.type}`">
            {{ previewJson(row.value) }}
          </span>

          <!-- 悬浮/操作动作 -->
          <div class="rm-tree-actions">
            <button
              class="rm-action-pill"
              :title="`${t('requestMonitor.copyPath')} ${row.key}`"
              :aria-label="`${t('requestMonitor.copyPath')} ${row.key}`"
              @click="emit('copy', pathPrefix + row.path)"
            >
              <Icon icon="material-symbols:link-rounded" width="13" height="13" />
              <span>{{ t('requestMonitor.path') }}</span>
            </button>
            <button
              class="rm-action-pill"
              :title="`${t('requestMonitor.copyNode')} ${row.key}`"
              :aria-label="`${t('requestMonitor.copyNode')} ${row.key}`"
              @click="copy(row)"
            >
              <Icon icon="material-symbols:content-copy-rounded" width="13" height="13" />
              <span>{{ t('requestMonitor.copyNode') }}</span>
            </button>
          </div>
        </div>

        <!-- 字符串完整显示在只读文本框内，长内容在框内滚动。 -->
        <textarea
          v-if="typeof row.value === 'string'"
          class="rm-tree-text"
          :value="row.value"
          :rows="row.size > 160 || /[\r\n]/.test(row.value) ? 6 : 2"
          :aria-label="`${t('requestMonitor.tree')} ${pathPrefix + row.path || '$'}`"
          readonly
          :spellcheck="false"
          wrap="soft"
        ></textarea>
      </template>
    </div>

    <p v-if="view.limited" class="rm-tree-limit-hint">
      <Icon icon="material-symbols:info-outline-rounded" width="16" height="16" />
      {{ t('requestMonitor.treeLimit') }}
    </p>
  </div>
</template>
