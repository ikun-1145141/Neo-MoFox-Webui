<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { isAxiosError } from 'axios'
import Icon from '../common/Icon.vue'
import { testModel } from '../../api/modules/config'
import type { ModelTestModel, ModelTestProvider, ModelTestRequest, ModelTestResult, ModelTestStatus, ModelTestType } from '../../api/types/config'
import { useI18n } from '../../utils/i18n'

const props = defineProps<{ model: ModelTestModel; provider: ModelTestProvider | null }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()
type RowStatus = ModelTestStatus | 'idle' | 'queued' | 'running'
interface TestRow {
  type: ModelTestType
  icon: string
  selected: boolean
  status: RowStatus
  result: ModelTestResult | null
  error: string
  expanded: boolean
  startedAt: number | null
}
const definitions: { type: ModelTestType; icon: string }[] = [
  { type: 'vlm', icon: 'material-symbols:image-outline-rounded' },
  { type: 'embedding', icon: 'material-symbols:grain-rounded' },
  { type: 'stream', icon: 'material-symbols:stream-rounded' },
  { type: 'non_stream', icon: 'material-symbols:chat-bubble-outline-rounded' },
  { type: 'tools', icon: 'material-symbols:construction-outline-rounded' },
]
const rows = ref<TestRow[]>(definitions.map(item => ({ ...item, selected: false, status: 'idle', result: null, error: '', expanded: false, startedAt: null })))
const dialog = ref<HTMLDialogElement | null>(null)
const running = ref(false)
const now = ref(Date.now())
const selectedCount = computed(() => rows.value.filter(row => row.selected).length)
const configError = computed(() => !props.provider ? t('modelTestDialog.providerMissing') : !props.model.model_identifier.trim() ? t('modelTestDialog.modelMissing') : '')
const protocol = computed(() => {
  const type = props.provider?.client_type ?? 'openai'
  const names: Record<string, string> = { openai: 'OpenAI', openai_response: 'OpenAI Responses', anthropic: 'Anthropic', gemini: 'Gemini', aiohttp_gemini: 'Gemini (aiohttp)', bedrock: 'Bedrock' }
  return names[type] ?? type
})
let generation = 0
let controller: AbortController | null = null
let clock: ReturnType<typeof setInterval> | null = null
let previousFocus: HTMLElement | null = null
let previousOverflow = ''

function duration(milliseconds: number): string {
  return milliseconds < 1000 ? `${Math.round(milliseconds)} ms` : `${(milliseconds / 1000).toFixed(2)} s`
}
function rowTime(row: TestRow): string {
  if (row.status === 'running' && row.startedAt !== null) return duration(now.value - row.startedAt)
  return row.result?.latency_ms != null ? duration(row.result.latency_ms) : ''
}
function clearClock() {
  if (clock !== null) clearInterval(clock)
  clock = null
}
function stop() {
  // 每次停止都作废旧代次，防止取消后的迟到结果覆盖下一轮测试。
  generation++
  controller?.abort()
  controller = null
  for (const row of rows.value) {
    if (row.status === 'running' || row.status === 'queued') row.status = 'cancelled'
  }
  running.value = false
  clearClock()
}
function close() {
  stop()
  dialog.value?.close()
  emit('close')
}
function backdrop(event: MouseEvent) {
  if (event.target !== dialog.value || !dialog.value) return
  const rect = dialog.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close()
}
function errorMessage(error: unknown, snapshot: ModelTestRequest): string {
  let message = t('modelTestDialog.requestFailed')
  if (isAxiosError(error)) {
    if (error.response?.status === 401 || error.response?.status === 403) return t('modelTestDialog.authFailed')
    const payload = error.response?.data
    const detail = payload?.message ?? payload?.detail
    if (typeof detail === 'string') message = detail
  }
  const keys = snapshot.provider?.api_key ?? []
  for (const key of Array.isArray(keys) ? keys : [keys]) {
    if (key) message = message.split(key).join('[已隐藏]')
  }
  return message.slice(0, 2000)
}
async function start() {
  if (running.value || !selectedCount.value || configError.value || !props.provider) return
  const current = ++generation
  // 固定本轮使用的页面快照；请求过程不会修改表单或持久化任何凭据。
  const snapshot: ModelTestRequest = JSON.parse(JSON.stringify({
    provider_name: props.provider.name,
    model_name: props.model.name,
    provider: props.provider,
    model: props.model,
    test_prompt: '请简短回复：连接成功。',
    timeout: 30,
  }))
  const queue = rows.value.filter(row => row.selected)
  for (const row of queue) {
    row.status = 'queued'
    row.result = null
    row.error = ''
    row.expanded = false
    row.startedAt = null
  }
  running.value = true
  now.value = Date.now()
  clock = setInterval(() => { now.value = Date.now() }, 200)
  try {
    for (const row of queue) {
      if (current !== generation) return
      row.status = 'running'
      row.startedAt = Date.now()
      now.value = row.startedAt
      const active = new AbortController()
      controller = active
      try {
        const result = await testModel({ ...snapshot, test_type: row.type }, active.signal)
        if (current !== generation) return
        row.result = result
        row.status = result.status ?? (result.success ? 'succeeded' : 'failed')
      } catch (error: unknown) {
        if (current !== generation) return
        row.status = isAxiosError(error) && error.code === 'ERR_CANCELED' ? 'cancelled' : 'failed'
        row.error = errorMessage(error, snapshot)
      } finally {
        if (controller === active) controller = null
      }
    }
  } finally {
    if (current === generation) {
      running.value = false
      clearClock()
    }
  }
}

onMounted(async () => {
  previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  await nextTick()
  dialog.value?.showModal()
  dialog.value?.focus()
})
onBeforeUnmount(() => {
  stop()
  dialog.value?.close()
  document.body.style.overflow = previousOverflow
  if (previousFocus?.isConnected) previousFocus.focus()
})
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="model-test-dialog" aria-labelledby="model-test-title" aria-describedby="model-test-hint" tabindex="-1" @cancel.prevent="close" @click="backdrop">
      <header class="test-header">
        <h2 id="model-test-title">{{ t('modelTestDialog.title') }}</h2>
        <button type="button" class="test-icon-button" :aria-label="t('modelTestDialog.close')" @click="close">
          <Icon icon="material-symbols:close-rounded" :size="22" />
        </button>
      </header>
      <section class="test-identity">
        <div class="test-model-pill">
          <span class="test-model-mark"><Icon icon="material-symbols:auto-awesome-rounded" :size="25" /></span>
          <div class="test-model-names"><strong>{{ model.name || model.model_identifier }}</strong><span v-if="model.name !== model.model_identifier">{{ model.model_identifier }}</span></div>
        </div>
        <div class="test-provider-line"><span>{{ t('modelTestDialog.provider') }} · {{ provider?.name || model.api_provider }}</span><span>{{ t('modelTestDialog.protocol') }} · {{ protocol }}</span></div>
      </section>
      <div class="test-body">
        <p id="model-test-hint" class="test-hint">{{ t('modelTestDialog.hint') }}</p>
        <p v-if="configError" class="test-config-error" role="alert">{{ configError }}</p>
        <div class="test-rows" :aria-busy="running">
          <section v-for="row in rows" :key="row.type" class="test-item" :class="`test-item-${row.status}`">
            <div class="test-row">
              <label class="test-name" :for="`model-test-select-${row.type}`"><Icon :icon="row.icon" :size="20" /><span>{{ t(`modelTestDialog.${row.type}`) }}</span></label>
              <button type="button" class="test-result-button" :class="`result-${row.status}`" :disabled="!row.result && !row.error" :aria-label="t('modelTestDialog.expand', { name: t(`modelTestDialog.${row.type}`) })" :aria-expanded="row.expanded" :aria-controls="`model-test-result-${row.type}`" @click="row.expanded = !row.expanded">
                <span v-if="row.status === 'running'" class="test-wave" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
                <Icon v-else-if="row.status === 'succeeded'" icon="material-symbols:check-circle-rounded" :size="18" />
                <Icon v-else-if="row.status === 'failed'" icon="material-symbols:error-outline-rounded" :size="18" />
                <span class="test-result-label"><span>{{ t(`modelTestDialog.${row.status}`) }}</span><small v-if="rowTime(row)">{{ rowTime(row) }}</small></span>
                <Icon v-if="row.result || row.error" :icon="row.expanded ? 'material-symbols:expand-less-rounded' : 'material-symbols:expand-more-rounded'" :size="16" />
              </button>
              <label class="test-checkbox-area"><input :id="`model-test-select-${row.type}`" v-model="row.selected" type="checkbox" :disabled="running" :aria-label="t('modelTestDialog.select', { name: t(`modelTestDialog.${row.type}`) })" /></label>
            </div>
            <div v-if="row.expanded && (row.result || row.error)" :id="`model-test-result-${row.type}`" class="test-result-details">
              <p class="test-result-summary">{{ row.error || row.result?.summary || row.result?.error_message }}</p>
              <p v-if="row.result?.first_token_ms != null" class="test-first-token">{{ t('modelTestDialog.firstToken', { time: duration(row.result.first_token_ms) }) }}</p>
              <template v-if="row.result?.response_text"><h3>{{ t('modelTestDialog.response') }}</h3><pre>{{ row.result.response_text }}</pre></template>
              <template v-if="row.result?.details && Object.keys(row.result.details).length"><h3>{{ t('modelTestDialog.details') }}</h3><pre>{{ JSON.stringify(row.result.details, null, 2) }}</pre></template>
            </div>
          </section>
        </div>
        <p class="test-snapshot-note">{{ t('modelTestDialog.snapshot') }}</p>
      </div>
      <footer class="test-footer">
        <span class="test-selection-count" aria-live="polite">{{ t('modelTestDialog.selected', { count: String(selectedCount) }) }}</span>
        <button type="button" class="test-action test-action-secondary" @click="running ? stop() : close()">{{ t(running ? 'modelTestDialog.stop' : 'modelTestDialog.cancel') }}</button>
        <button type="button" class="test-action test-action-primary" :disabled="running || !selectedCount || !!configError" @click="start">{{ t(running ? 'modelTestDialog.running' : 'modelTestDialog.start') }}</button>
      </footer>
    </dialog>
  </Teleport>
</template>

<style scoped>
.model-test-dialog {
  box-sizing: border-box;
  width: min(500px, calc(100vw - 32px));
  max-width: 100%;
  max-height: min(780px, calc(100dvh - 32px));
  margin: auto;
  padding: 0;
  overflow: hidden;
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container-high);
  border: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 55%, transparent);
  border-radius: 28px;
  box-shadow: 0 24px 80px rgb(0 0 0 / .3);
  font-family: inherit;
}
.model-test-dialog[open] { display: flex; flex-direction: column; }
.model-test-dialog::backdrop { background: rgb(0 0 0 / .46); backdrop-filter: blur(3px); }
.test-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex: none; padding: 22px 24px 6px; }
.test-header h2 { margin: 0; font-size: 1.45rem; font-weight: 550; letter-spacing: -.02em; }
.test-icon-button { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; padding: 0; border: 0; border-radius: 50%; color: var(--md-sys-color-on-surface-variant); background: transparent; cursor: pointer; }
.test-icon-button:hover { background: var(--md-sys-color-surface-container-highest); }
.test-identity { flex: none; min-width: 0; padding: 12px 28px 8px; }
.test-model-pill { display: flex; align-items: center; justify-content: center; gap: 12px; min-width: 0; padding: 14px 18px; border-radius: 20px; color: var(--md-sys-color-primary); background: color-mix(in srgb, var(--md-sys-color-primary-container) 55%, transparent); }
.test-model-mark { display: inline-flex; flex: none; }
.test-model-names { display: flex; flex-direction: column; gap: 4px; min-width: 0; overflow-wrap: anywhere; }
.test-model-names strong { font-size: 1rem; font-weight: 600; line-height: 1.4; }
.test-model-names > span { font-family: ui-monospace, monospace; font-size: .72rem; opacity: .8; }
.test-provider-line { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px 14px; padding: 10px 0 0; color: var(--md-sys-color-on-surface-variant); font-size: .72rem; overflow-wrap: anywhere; }
.test-body { flex: 1; min-height: 0; min-width: 0; overflow-y: auto; overscroll-behavior: contain; padding: 4px 28px 12px; scrollbar-gutter: stable; }
.test-hint, .test-snapshot-note { margin: 8px 0 14px; color: var(--md-sys-color-on-surface-variant); font-size: .76rem; line-height: 1.7; overflow-wrap: anywhere; }
.test-snapshot-note { margin: 16px 0 4px; font-size: .71rem; }
.test-config-error { padding: 10px 12px; border-radius: 10px; color: var(--md-sys-color-on-error-container); background: var(--md-sys-color-error-container); font-size: .8rem; line-height: 1.6; }
.test-item { min-width: 0; border-bottom: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 55%, transparent); }
.test-item:last-child { border-bottom: 0; }
.test-row { display: grid; grid-template-columns: minmax(100px, 1fr) minmax(0, auto) 44px; align-items: center; min-height: 64px; gap: 8px; }
.test-name { display: flex; align-items: center; gap: 10px; min-height: 44px; min-width: 0; cursor: pointer; font-size: .88rem; overflow-wrap: anywhere; }
.test-name > :first-child { flex: none; color: var(--md-sys-color-on-surface-variant); }
.test-result-button { display: inline-flex; justify-content: flex-end; align-items: center; flex-wrap: wrap; gap: 6px; min-width: 0; min-height: 44px; max-width: 170px; padding: 4px 0; color: var(--md-sys-color-on-surface-variant); border: 0; border-radius: 8px; background: transparent; font: inherit; font-size: .73rem; cursor: pointer; }
.test-result-button:disabled { cursor: default; }
.test-result-button:not(:disabled):hover { background: color-mix(in srgb, var(--md-sys-color-on-surface) 5%, transparent); }
.test-result-label { display: flex; flex-direction: column; gap: 3px; align-items: flex-end; }
.test-result-label small { font-family: ui-monospace, monospace; font-size: .65rem; font-variant-numeric: tabular-nums; }
.result-succeeded { color: var(--md-sys-color-primary); }
.result-failed { color: var(--md-sys-color-error); }
.result-running { color: var(--md-sys-color-primary); }
.test-checkbox-area { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; cursor: pointer; }
.test-checkbox-area input { width: 21px; height: 21px; margin: 0; accent-color: var(--md-sys-color-primary); cursor: pointer; }
.test-checkbox-area input:disabled { cursor: default; }
.test-result-details { min-width: 0; margin: 2px 0 14px; padding: 12px; border-radius: 12px; background: var(--md-sys-color-surface-container-low); font-size: .76rem; line-height: 1.65; overflow-wrap: anywhere; }
.test-result-details h3 { margin: 12px 0 6px; font-size: .75rem; font-weight: 600; }
.test-result-details p { margin: 0 0 6px; }
.test-result-details pre { box-sizing: border-box; max-width: 100%; min-width: 0; margin: 0; padding: 10px; border-radius: 8px; color: var(--md-sys-color-on-surface); background: var(--md-sys-color-surface-container-lowest); font-size: .7rem; font-family: ui-monospace, monospace; white-space: pre-wrap; overflow-wrap: anywhere; word-break: normal; }
.test-first-token { color: var(--md-sys-color-on-surface-variant); }
.test-footer { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 8px; flex: none; padding: 14px 24px 20px; border-top: 1px solid color-mix(in srgb, var(--md-sys-color-outline-variant) 55%, transparent); }
.test-selection-count { margin-right: auto; color: var(--md-sys-color-on-surface-variant); font-size: .74rem; }
.test-action { display: inline-flex; justify-content: center; align-items: center; min-height: 44px; min-width: 76px; padding: 10px 18px; border: 0; border-radius: 24px; font-family: inherit; font-size: .84rem; font-weight: 600; cursor: pointer; }
.test-action-secondary { color: var(--md-sys-color-primary); background: transparent; }
.test-action-primary { color: var(--md-sys-color-on-primary); background: var(--md-sys-color-primary); }
.test-action:disabled { opacity: .38; cursor: not-allowed; }
.test-action-secondary:hover { background: var(--md-sys-color-surface-container-highest); }
.test-action-primary:not(:disabled):hover { filter: brightness(.94); }
.test-wave { display: inline-flex; align-items: center; gap: 3px; height: 22px; }
.test-wave i { display: block; width: 3px; height: 14px; border-radius: 4px; background: currentColor; animation: test-wave-motion .85s ease-in-out infinite alternate; }
.test-wave i:nth-child(2) { animation-delay: -.2s; }
.test-wave i:nth-child(3) { animation-delay: -.4s; }
.test-wave i:nth-child(4) { animation-delay: -.6s; }
@keyframes test-wave-motion { from { transform: scaleY(.35); opacity: .5; } to { transform: scaleY(1); opacity: 1; } }
@media (max-width: 380px) {
  .model-test-dialog { width: calc(100vw - 20px); max-height: calc(100dvh - 20px); border-radius: 24px; }
  .test-header { padding: 16px 16px 4px; }
  .test-header h2 { font-size: 1.25rem; }
  .test-identity { padding: 10px 18px 6px; }
  .test-body { padding: 4px 18px 8px; }
  .test-row { gap: 4px; grid-template-columns: minmax(92px, 1fr) minmax(0, auto) 44px; }
  .test-name { gap: 6px; font-size: .8rem; }
  .test-result-button { gap: 3px; font-size: .68rem; max-width: 110px; }
  .test-footer { padding: 12px 14px 16px; gap: 4px; }
  .test-action { min-width: 66px; padding: 10px 12px; }
}
@media (prefers-reduced-motion: reduce) { .test-wave i { animation: none; } }
</style>
