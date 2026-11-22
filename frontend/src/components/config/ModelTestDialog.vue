<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from 'vue'
import type { ModelTestModel, ModelTestProvider } from '@/api/types/config'
import { useI18n } from '@/utils/i18n'
import Icon from '../common/Icon.vue'
import ModelTestDialogResult from './ModelTestDialogResult.vue'
import { statusIcons } from './modelTestDialogTypes'
import { modelKinds, useModelTestSession } from './useModelTestSession'

const props = withDefaults(defineProps<{
  isOpen: boolean
  model: ModelTestModel | null
  providers: ModelTestProvider[]
  timeout?: number
}>(), { timeout: 30 })
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
const tr = (key: string, params?: Record<string, string>) => t(`modelTestDialog.${key}`, params)
const { activeKind, tests, checkedCount, blocked, batch, isRunning, dimensions, query, topN,
  reset, switchKind, normalizeDimensions, normalizeTopN, run } = useModelTestSession(props)

const id = useId()
const dialog = ref<HTMLDialogElement | null>(null)
const panel = ref<HTMLElement | null>(null)
const pressedBackdrop = ref(false)

watch([() => props.isOpen, dialog], ([open, el]) => {
  if (!el) return
  if (open && !el.open) {
    reset()
    el.showModal()
  } else if (!open && el.open) el.close()
}, { flush: 'post', immediate: true })

const summary = computed(() => {
  if (blocked.value) {
    const provider = blocked.value === 'errors.providerNotFound' && props.model?.api_provider
    return tr(blocked.value) + (provider ? ` · ${provider}` : '')
  }
  const { done, total, passed, failed } = batch.value
  if (isRunning.value) return tr('summary.running', { done: String(done), total: String(total) })
  if (!total) return ''
  return failed ? tr('summary.done', { success: String(passed), fail: String(failed) })
    : tr('summary.allPassed', { count: String(passed) })
})
const summaryState = computed(() => blocked.value ? 'blocked' : isRunning.value ? 'running'
  : batch.value.failed ? 'fail' : 'success')
const summaryIcons = { ...statusIcons, blocked: 'info-outline-rounded' }

function close() { if (!isRunning.value) emit('close') }
function start() {
  if (blocked.value || isRunning.value) return
  void run()
  // The run button becomes disabled. The scrollable list stays available to keyboard users.
  void nextTick(() => panel.value?.focus({ preventScroll: true }))
}
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="model-test" :aria-labelledby="`${id}-title`" @cancel.prevent="close"
      @pointerdown="pressedBackdrop = $event.target === dialog" @click.self="pressedBackdrop && close()">
      <div v-if="isOpen" class="shell">
        <header class="dialog-head">
          <div class="identity">
            <h2 :id="`${id}-title`" tabindex="-1" autofocus>{{ tr('title') }}</h2>
            <p class="model-meta"><span class="model-name">{{ model?.name || tr('unknownModel') }}</span>
              <template v-if="model?.api_provider"><span aria-hidden="true" class="meta-dot">·</span><span>{{ model.api_provider }}</span></template></p>
          </div>
          <button type="button" class="icon-button" :aria-label="tr('close')" :title="tr('close')" :disabled="isRunning" @click="close">
            <Icon icon="close-rounded" :width="21" :height="21" />
          </button>
        </header>

        <div class="dialog-body">
          <aside class="rail">
            <fieldset :disabled="isRunning" class="kind-list">
              <legend>{{ tr('kindLabel') }}</legend>
              <label v-for="kind in modelKinds" :key="kind.key" class="kind">
                <input class="sr-only" type="radio" :name="`${id}-kind`" :checked="activeKind === kind.key" @change="switchKind(kind.key)" />
                <span class="kind-face"><Icon :icon="kind.icon" :width="19" :height="19" />{{ tr(`types.${kind.key}`) }}</span>
              </label>
            </fieldset>
          </aside>

          <section :key="activeKind" ref="panel" class="test-panel" :aria-labelledby="`${id}-checks`" tabindex="0">
            <div class="panel-heading">
              <h3 :id="`${id}-checks`">{{ tr('listTitle') }}</h3>
              <span>{{ tr('countSelected', { count: String(checkedCount), total: String(tests.length) }) }}</span>
            </div>
            <ul class="cards">
              <li v-for="test in tests" :key="test.key" class="test-card">
                <label class="test-row">
                  <input v-model="test.checked" type="checkbox" class="sr-only" :disabled="isRunning"
                    :aria-labelledby="`${id}-${test.key}`" :aria-describedby="`${id}-${test.key}-desc`" />
                  <span class="check-face"><Icon icon="check-rounded" :width="14" :height="14" /></span>
                  <span class="test-glyph"><Icon :icon="test.icon" :width="19" :height="19" /></span>
                  <span class="test-info">
                    <span :id="`${id}-${test.key}`" class="test-name">{{ tr(test.message) }}</span>
                    <span :id="`${id}-${test.key}-desc`" class="test-desc">{{ tr(`${test.message}Desc`) }}</span>
                  </span>
                  <span class="state" :data-state="test.status"><Icon :icon="statusIcons[test.status]" :width="14" :height="14" :class="{ spinning: test.status === 'running' }" />{{ tr(`status.${test.status}`) }}</span>
                </label>
                <p v-if="test.key === 'vlm'" class="image-note"><Icon icon="info-outline-rounded" :width="14" :height="14" />{{ tr('llm.vlmImageHint') }}</p>
                <ModelTestDialogResult v-if="test.status === 'success' || test.status === 'fail'" :test="test" />
              </li>
            </ul>

            <div v-if="activeKind === 'embedding'" class="parameters">
              <label class="field"><span>{{ tr('embedding.dimensionLabel') }}</span>
                <input v-model.number="dimensions" type="number" min="1" max="65536" step="1" :disabled="isRunning"
                  :aria-describedby="`${id}-dim-hint`" :placeholder="tr('embedding.dimensionPlaceholder')" @change="normalizeDimensions" /></label>
              <p :id="`${id}-dim-hint`" class="field-hint">{{ tr('embedding.dimensionHint') }}</p>
            </div>
            <div v-else-if="activeKind === 'rerank'" class="parameters rerank-fields">
              <label class="field"><span>{{ tr('rerank.queryLabel') }}</span><input v-model="query" type="text" :disabled="isRunning" :placeholder="tr('rerank.queryPlaceholder')" /></label>
              <label class="field"><span>{{ tr('rerank.topNLabel') }}</span><input v-model.number="topN" type="number" min="1" max="100" step="1" :disabled="isRunning" @change="normalizeTopN" /></label>
            </div>
          </section>
        </div>

        <footer class="dialog-foot">
          <div class="feedback" role="status" aria-atomic="true" :data-state="summaryState">
            <template v-if="summary"><div class="feedback-line"><Icon :icon="summaryIcons[summaryState]" :width="17" :height="17" :class="{ spinning: isRunning }" /><span>{{ summary }}</span></div>
              <progress v-if="isRunning" :value="batch.done" :max="batch.total" :aria-label="summary" /></template>
          </div>
          <div class="actions">
            <button type="button" class="cancel" :disabled="isRunning" @click="close">{{ tr('close') }}</button>
            <button type="button" class="run" :disabled="isRunning || !!blocked" @click="start"><Icon :icon="isRunning ? statusIcons.running : 'play-arrow-rounded'" :width="19" :height="19" :class="{ spinning: isRunning }" />{{ tr(isRunning ? 'running' : batch.total ? 'runAgain' : 'testButton') }}</button>
          </div>
        </footer>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.model-test {
  --mt-line: color-mix(in srgb, var(--md-sys-color-outline-variant) 68%, transparent);
  --mt-muted: var(--md-sys-color-on-surface-variant);
  --mt-card: var(--md-sys-color-surface-container-lowest);
  box-sizing: border-box; width: min(92vw, 860px); height: clamp(532px, 50dvh, 620px);
  max-width: none; max-height: calc(100dvh - 32px); margin: auto; padding: 0; overflow: hidden;
  border: 0; border-radius: var(--md-sys-shape-corner-extra-large); box-shadow: var(--md-sys-elevation-3);
  background: var(--md-sys-color-surface); color: var(--md-sys-color-on-surface); font-family: inherit;
}
.model-test::backdrop { background: color-mix(in srgb, var(--md-sys-color-scrim) 38%, transparent); }
.model-test[open] { animation: mt-enter 160ms ease-out; }
.shell { height: 100%; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; }
.shell :is(h2, h3, p, ul, fieldset) { margin: 0; }
.shell button, .shell input { font: inherit; }
.shell button { border: 0; cursor: pointer; }
.shell button:disabled { cursor: default; }
.shell :is(button, .field input):focus-visible, .sr-only:focus-visible + span { outline: 2px solid var(--md-sys-color-primary); outline-offset: 3px; }
.test-panel:focus-visible { outline: 2px solid var(--md-sys-color-primary); outline-offset: -3px; }
.sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip-path: inset(50%); border: 0; white-space: nowrap; }
.dialog-head, .dialog-foot { display: flex; align-items: center; justify-content: space-between; gap: 16px; background: var(--md-sys-color-surface); }
.dialog-head { padding: 17px 22px 16px 24px; border-block-end: 1px solid var(--mt-line); }
.identity { min-width: 0; }
.identity h2 { font-size: 23px; line-height: 1.3; font-weight: 600; letter-spacing: -.025em; }
.identity h2:focus { outline: none; }
.identity .model-meta { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0 7px; margin-top: 3px; max-height: 3em; overflow: auto; overflow-wrap: anywhere; color: var(--mt-muted); font-size: 12px; line-height: 1.5; }
.model-meta span { min-width: 0; }
.model-name { font-family: ui-monospace, Consolas, monospace; }
.meta-dot { color: var(--md-sys-color-outline); }
.icon-button { flex: none; display: grid; place-items: center; width: 42px; height: 42px; padding: 0; border-radius: 50%; color: var(--mt-muted); background: transparent; }

/* The rail chooses a model family, never an individual check. */
.dialog-body { display: grid; grid-template-columns: 180px minmax(0, 1fr); min-height: 0; }
.rail { min-width: 0; overflow: auto; padding: 16px 12px; background: var(--md-sys-color-surface-container-low); border-inline-end: 1px solid var(--mt-line); }
.kind-list { min-width: 0; padding: 0; border: 0; }
.kind-list legend, .panel-heading h3 { padding: 0; color: var(--mt-muted); font-size: 13px; line-height: 20px; font-weight: 600; }
.kind-list legend { margin: 0 0 10px 12px; }
.kind { position: relative; display: block; cursor: pointer; }
.kind + .kind { margin-top: 4px; }
.kind-face { display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 8px 12px; border-radius: var(--md-sys-shape-corner-medium); color: var(--mt-muted); font-size: 14px; line-height: 20px; }
.kind-face > span, .image-note > span { flex: none; }
.kind input:checked + .kind-face { background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container); font-weight: 600; }
.kind-list:disabled .kind, .test-row:has(input:disabled) { cursor: default; }
.kind-list:disabled .kind input:not(:checked) + .kind-face { opacity: .6; }

.test-panel { min-width: 0; min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 16px 20px 18px; }
.panel-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 10px; }
.panel-heading > span { color: var(--mt-muted); font-size: 12px; line-height: 18px; font-variant-numeric: tabular-nums; }
.cards { display: grid; gap: 8px; list-style: none; padding: 0; }
.test-card { min-width: 0; border: 1px solid var(--mt-line); border-radius: var(--md-sys-shape-corner-medium); background: var(--mt-card); }
.test-row { position: relative; display: grid; grid-template-columns: 18px 30px minmax(0, 1fr) auto; align-items: center; gap: 10px; min-height: 61px; padding: 9px 14px; border-radius: inherit; cursor: pointer; }
.check-face { box-sizing: border-box; display: grid; place-items: center; width: 18px; height: 18px; border: 2px solid var(--md-sys-color-outline); border-radius: var(--md-sys-shape-corner-extra-small); }
.check-face > span { visibility: hidden; }
.test-row input:checked + .check-face { background: var(--md-sys-color-primary); border-color: var(--md-sys-color-primary); color: var(--md-sys-color-on-primary); }
.test-row input:checked + .check-face > span { visibility: visible; }
.test-row input:disabled + .check-face { opacity: .5; }
.test-glyph { display: grid; place-items: center; width: 30px; height: 30px; border-radius: var(--md-sys-shape-corner-small); color: var(--mt-muted); background: var(--md-sys-color-surface-container-low); }
.test-row input:checked ~ .test-glyph { color: var(--md-sys-color-primary); background: color-mix(in srgb, var(--md-sys-color-primary-container) 44%, var(--mt-card)); }
.test-info { min-width: 0; display: grid; gap: 2px; overflow-wrap: anywhere; }
.test-name { font-size: 15px; font-weight: 600; line-height: 20px; }
.test-desc, .field-hint { font-size: 12px; line-height: 18px; color: var(--mt-muted); }
.state { display: inline-flex; align-items: center; justify-self: end; gap: 4px; white-space: nowrap; padding: 2px 7px; border-radius: var(--md-sys-shape-corner-full); font-size: 12px; line-height: 18px; color: var(--mt-muted); }
.state[data-state='running'] { color: var(--md-sys-color-on-primary-container); background: var(--md-sys-color-primary-container); }
.state[data-state='success'] { color: var(--md-sys-color-on-tertiary-container); background: var(--md-sys-color-tertiary-container); }
.state[data-state='fail'] { color: var(--md-sys-color-on-error-container); background: var(--md-sys-color-error-container); }
.test-card .image-note { display: flex; align-items: baseline; gap: 5px; padding: 0 14px 10px 82px; color: var(--mt-muted); font-size: 12px; line-height: 17px; }
.image-note > span { align-self: flex-start; margin-top: 1px; }

.parameters { display: grid; gap: 6px; margin: 16px 0 0; }
.rerank-fields { grid-template-columns: minmax(0, 1fr) minmax(105px, .38fr); gap: 12px; align-items: end; }
.field { display: grid; min-width: 0; gap: 6px; }
.field > span { color: var(--md-sys-color-on-surface); font-size: 13px; font-weight: 550; }
.field input { box-sizing: border-box; width: 100%; min-width: 0; min-height: 44px; padding: 8px 12px; border: 1px solid var(--md-sys-color-outline); border-radius: var(--md-sys-shape-corner-small); color: var(--md-sys-color-on-surface); background: var(--mt-card); font-size: 14px; }
.field input::placeholder { color: var(--mt-muted); }
.field input:disabled { opacity: .65; }
.dialog-foot { justify-content: flex-end; padding: 12px 22px; border-block-start: 1px solid var(--mt-line); }
.feedback { min-width: 0; margin-inline-end: auto; color: var(--mt-muted); }
.feedback-line { display: flex; align-items: center; gap: 7px; font-size: 13px; line-height: 19px; overflow-wrap: anywhere; }
.feedback-line > span:first-child { flex: none; }
.feedback[data-state='fail'], .feedback[data-state='blocked'] { color: var(--md-sys-color-error); }
.feedback[data-state='success'] { color: var(--md-sys-color-tertiary); }
.feedback progress { display: block; width: min(160px, 100%); height: 4px; margin-top: 5px; accent-color: var(--md-sys-color-primary); }
.actions { flex: none; display: flex; align-items: center; gap: 8px; }
.actions button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 42px; padding: 0 17px; border-radius: var(--md-sys-shape-corner-full); font-size: 14px; font-weight: 600; }
.cancel { background: transparent; color: var(--mt-muted); }
.actions .run { padding: 0 21px 0 16px; background: var(--md-sys-color-primary); color: var(--md-sys-color-on-primary); }
.actions .run:disabled { color: var(--mt-muted); background: color-mix(in srgb, var(--md-sys-color-on-surface) 12%, transparent); }
.icon-button:disabled, .cancel:disabled { opacity: .45; }
@media (hover: hover) {
  .icon-button:hover:not(:disabled), .cancel:hover:not(:disabled), .kind-list:not(:disabled) .kind:hover input:not(:checked) + span { background: color-mix(in srgb, var(--md-sys-color-on-surface) 8%, transparent); }
  .test-card:has(.test-row:hover input:not(:disabled)) { border-color: var(--md-sys-color-outline); }
  .actions .run:hover:not(:disabled) { background: color-mix(in srgb, var(--md-sys-color-primary) 92%, var(--md-sys-color-on-primary)); box-shadow: var(--md-sys-elevation-1); }
}
@media (max-width: 768px) {
  .model-test { width: 95vw; height: 78dvh; max-height: calc(100dvh - 16px); border-radius: var(--md-sys-shape-corner-large); }
  .dialog-body { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
  .rail { padding: 6px 12px; border-inline-end: 0; border-block-end: 1px solid var(--mt-line); }
  .kind-list { display: flex; gap: 4px; }
  .kind-list legend { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
  .kind { flex: 1; min-width: 0; }
  .kind + .kind { margin: 0; }
  .kind-face { justify-content: center; gap: 6px; padding-inline: 5px; text-align: center; }
  .test-panel { padding: 12px 14px 16px; }
  .dialog-head { padding: 13px 15px 12px 18px; }
  .identity h2 { font-size: 21px; }
  .dialog-foot { flex-wrap: wrap; gap: 5px 12px; padding: 10px 14px; }
  .actions { margin-inline-start: auto; }
  .rerank-fields { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 480px) {
  .kind-face { font-size: 13px; }
  .test-row { grid-template-columns: 18px 24px minmax(0, 1fr) auto; gap: 7px; padding: 10px; }
  .test-glyph { width: 24px; height: 27px; }
  .state { gap: 3px; padding-inline: 4px; font-size: 11px; }
  .test-card .image-note { padding-inline: 10px; }
}
@media (max-width: 359px) { .kind-face > span { display: none; } }
.spinning { animation: mt-spin 1s linear infinite; }
@keyframes mt-spin { to { transform: rotate(360deg); } }
@keyframes mt-enter { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .model-test[open], .spinning { animation: none; } }
</style>
