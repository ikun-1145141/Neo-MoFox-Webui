<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import Icon from '../common/Icon.vue'
import { commitPluginImport, discardPluginImport, getPluginImportOperation, preparePluginImport } from '../../api/modules/plugin-import'
import type { PluginImportCommit, PluginImportOperation, PluginImportPreview } from '../../api/types/plugin-import'
import { useI18n } from '../../utils/i18n'
import { useToastStore } from '../../utils/toast'

const emit = defineEmits<{ finished: [] }>()
const { t, locale } = useI18n()
const toast = useToastStore()
const text = (key: string) => t('plugins.import.' + key)
const open = ref(false)
const dialog = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const file = ref<File | null>(null)
const fileKey = ref(0)
const preview = ref<PluginImportPreview | null>(null)
const operation = ref<PluginImportOperation | null>(null)
const operationId = ref<string | null>(null)
const pendingCommit = ref<PluginImportCommit | null>(null)
const uploading = ref(false)
const committing = ref(false)
const polling = ref(false)
const deleting = ref(false)
const overwrite = ref(false)
const uploadProgress = ref(0)
const errorMessage = ref('')
const now = ref(Date.now())
const storageKey = 'neo-mofox-plugin-import-pending'
let clock: ReturnType<typeof setInterval> | undefined
let pollTimer: ReturnType<typeof setTimeout> | undefined
let uploadController: AbortController | undefined
let pollController: AbortController | undefined
let disposed = false

const terminal = computed(() => operation.value?.status === 'succeeded' || operation.value?.status === 'failed')
const busy = computed(() => uploading.value || committing.value || deleting.value || polling.value)
const pending = computed(() => !terminal.value && Boolean(operationId.value || pendingCommit.value))
const expired = computed(() => preview.value ? now.value >= Date.parse(preview.value.expires_at) : false)
const canCommit = computed(() => Boolean(preview.value?.can_import && !expired.value && !busy.value && !pending.value && (!preview.value.overwrite_required || overwrite.value)))
const outcome = computed(() => {
  if (operation.value?.status === 'failed') return text('failed')
  const result = operation.value?.result
  if (result?.restart_required) return text('restart')
  return result?.loaded ? text('loaded') : text('written')
})
const formatSize = (bytes: number) => (bytes / 1024 / 1024).toFixed(2) + ' MiB'
const formatTime = (value: string) => new Date(value).toLocaleString(locale.value)

function savePending() {
  // Session-only task recovery, not UI settings or credentials.
  try {
    if (operationId.value || pendingCommit.value) {
      sessionStorage.setItem(storageKey, JSON.stringify({ operationId: operationId.value, request: pendingCommit.value }))
    } else sessionStorage.removeItem(storageKey)
  } catch { /* Storage-disabled browsers can still complete the current dialog. */ }
}

function errorText(error: unknown): string {
  const value = error as { message?: string; response?: { data?: { message?: string; detail?: string } } }
  return value.response?.data?.message || value.response?.data?.detail || value.message || text('network')
}

function show() {
  open.value = true
  nextTick(() => dialog.value?.focus())
  if (operationId.value && !terminal.value) void poll()
}

function selectFile(event: Event) {
  const selected = (event.target as HTMLInputElement).files?.[0] ?? null
  errorMessage.value = ''
  if (selected && (!/\.(zip|mfp)$/i.test(selected.name) || selected.size === 0 || selected.size > 50 * 1024 * 1024)) {
    file.value = null
    errorMessage.value = text('invalid')
    toast.show(errorMessage.value, 'error')
    return
  }
  file.value = selected
}

async function prepare() {
  if (!file.value || busy.value || pending.value) return
  uploading.value = true
  errorMessage.value = ''
  uploadProgress.value = 0
  uploadController = new AbortController()
  try {
    preview.value = await preparePluginImport(file.value, value => { uploadProgress.value = value }, uploadController.signal)
    overwrite.value = false
  } catch (error) {
    if (!uploadController.signal.aborted) errorMessage.value = errorText(error)
  } finally {
    uploading.value = false
  }
}

async function confirm() {
  if (busy.value || operationId.value) return
  if (!pendingCommit.value) {
    if (!canCommit.value || !preview.value) return
    pendingCommit.value = { upload_id: preview.value.upload_id, confirm_overwrite: overwrite.value }
    savePending()
  }
  committing.value = true
  errorMessage.value = ''
  try {
    const result = await commitPluginImport(pendingCommit.value)
    operation.value = result
    operationId.value = result.operation_id
    pendingCommit.value = null
    savePending()
  } catch (error) {
    errorMessage.value = errorText(error)
    const status = (error as { response?: { status?: number } }).response?.status
    // Definite client rejection: no install was accepted. Network/5xx results are ambiguous.
    if (status && [400, 409, 410, 422, 429].includes(status)) {
      pendingCommit.value = null
      savePending()
    }
  } finally {
    committing.value = false
  }
  if (operationId.value && !disposed) void poll()
}

async function poll() {
  if (!operationId.value || polling.value || disposed) return
  if (pollTimer) clearTimeout(pollTimer)
  polling.value = true
  errorMessage.value = ''
  pollController = new AbortController()
  try {
    operation.value = await getPluginImportOperation(operationId.value, pollController.signal)
    if (terminal.value) {
      operationId.value = null
      pendingCommit.value = null
      savePending()
      emit('finished')
    } else if (!disposed) {
      pollTimer = setTimeout(() => { void poll() }, 1200)
    }
  } catch (error) {
    if (!pollController.signal.aborted) errorMessage.value = errorText(error)
    // Pause after an error; only resume status queries, never resubmit an operation.
  } finally {
    polling.value = false
  }
}

async function reset() {
  if (busy.value || pending.value) return
  deleting.value = true
  try {
    if (preview.value && !operation.value) await discardPluginImport(preview.value.upload_id)
    preview.value = null
    operation.value = null
    file.value = null
    fileKey.value++
    overwrite.value = false
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = errorText(error)
  } finally {
    deleting.value = false
  }
}

async function close() {
  if (uploading.value || committing.value || deleting.value) return
  if (!pending.value) {
    await reset()
    if (preview.value) return
  }
  open.value = false
  nextTick(() => trigger.value?.focus())
}

function forget() {
  if (busy.value) return
  if (pollTimer) clearTimeout(pollTimer)
  operationId.value = null
  pendingCommit.value = null
  operation.value = null
  preview.value = null
  errorMessage.value = ''
  savePending()
  emit('finished')
}

function trapFocus(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); void close(); return }
  if (event.key !== 'Tab' || !dialog.value) return
  const controls = [...dialog.value.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), [tabindex="0"]')]
  const first = controls[0], last = controls[controls.length - 1]
  if (!first || !last) { event.preventDefault(); return }
  if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.value)) {
    event.preventDefault(); last.focus()
  } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialog.value)) {
    event.preventDefault(); first.focus()
  }
}

onMounted(() => {
  clock = setInterval(() => { now.value = Date.now() }, 1000)
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null')
    if (typeof saved?.operationId === 'string' && /^[a-f0-9]{32}$/.test(saved.operationId)) operationId.value = saved.operationId
    else if (typeof saved?.request?.upload_id === 'string' && /^[a-f0-9]{32}$/.test(saved.request.upload_id)) {
      pendingCommit.value = { upload_id: saved.request.upload_id, confirm_overwrite: saved.request.confirm_overwrite === true }
    }
  } catch { /* Ignore corrupt local reminder data. */ }
})
onBeforeRouteLeave(() => {
  // Prevent navigation only while the upload/confirmation response is in flight.
  if (uploading.value || committing.value || deleting.value) return false
})
onBeforeUnmount(() => {
  disposed = true
  if (clock) clearInterval(clock)
  if (pollTimer) clearTimeout(pollTimer)
  uploadController?.abort()
  pollController?.abort()
  if (preview.value && !pending.value && !operation.value) {
    void discardPluginImport(preview.value.upload_id).catch(() => { /* Also expires server-side. */ })
  }
})
</script>

<template>
  <button ref="trigger" class="import-trigger" type="button" @click="show">
    <Icon icon="material-symbols:upload-file-outline-rounded" width="20" height="20" />
    {{ pending ? text('pending') : text('button') }}
  </button>
  <Teleport to="body">
    <div v-if="open" class="import-backdrop" @click.self="close">
      <section ref="dialog" class="import-dialog" role="dialog" aria-modal="true" aria-labelledby="plugin-import-title" aria-describedby="plugin-import-trust" tabindex="-1" @keydown="trapFocus">
        <header>
          <div class="heading-icon"><Icon icon="material-symbols:upload-file-outline-rounded" width="28" height="28" /></div>
          <div><h2 id="plugin-import-title">{{ text('title') }}</h2><p>{{ text('subtitle') }}</p></div>
        </header>
        <div class="import-body">
          <p id="plugin-import-trust" class="notice"><Icon icon="material-symbols:warning-outline-rounded" width="20" height="20" />{{ text('trust') }}</p>
          <template v-if="!preview && !operation && !pending">
            <label class="file-picker">{{ text('choose') }}<input :key="fileKey" type="file" accept=".zip,.mfp" :disabled="busy" @change="selectFile" /></label>
            <p class="hint">{{ text('structure') }}</p>
            <p v-if="file" class="filename">{{ file.name }} · {{ formatSize(file.size) }}</p>
          </template>
          <div v-if="uploading" class="progress" role="status" aria-live="polite">
            <span>{{ uploadProgress === 100 ? text('validating') : text('uploading') }} · {{ uploadProgress }}%</span>
            <progress :value="uploadProgress" max="100" :aria-label="text('uploading')" />
          </div>
          <template v-if="preview && !operation">
            <dl class="metadata">
              <dt>{{ text('file') }}</dt><dd>{{ preview.filename }} · {{ formatSize(preview.size_bytes) }}</dd>
              <dt>{{ text('plugin') }}</dt><dd>{{ preview.plugin_name }}</dd>
              <dt>{{ text('version') }}</dt><dd>{{ preview.version }}</dd>
              <template v-if="preview.installed_version"><dt>{{ text('installed') }}</dt><dd>{{ preview.installed_version }}</dd></template>
              <dt>{{ text('expires') }}</dt><dd>{{ formatTime(preview.expires_at) }}</dd>
            </dl>
            <p v-if="preview.description" class="description">{{ preview.description }}</p>
            <p v-if="preview.self_update" class="notice">{{ text('selfUpdate') }}</p>
            <ul v-if="preview.warnings.length" class="warning-list"><li v-for="warning in preview.warnings" :key="warning">{{ warning }}</li></ul>
            <ul v-if="preview.blocking_reasons.length" class="error-list"><li v-for="reason in preview.blocking_reasons" :key="reason">{{ reason }}</li></ul>
            <label v-if="preview.overwrite_required && preview.can_import" class="overwrite"><input v-model="overwrite" type="checkbox" :disabled="busy || pending" />{{ text('overwrite') }}</label>
            <p v-if="expired" class="error-text">{{ text('expired') }}</p>
          </template>
          <p v-if="pending && !operation" class="hint">{{ text('pendingHint') }}</p>
          <div v-if="operation" class="operation" role="status" aria-live="polite">
            <template v-if="!terminal">
              <p>{{ text('stages.' + operation.stage) }} · {{ operation.progress }}%</p>
              <progress :value="operation.progress" max="100" :aria-label="text('stages.' + operation.stage)" />
            </template>
            <template v-else>
              <h3 :class="operation.result?.loaded ? 'success-text' : 'warning-text'">{{ outcome }}</h3>
              <p class="filename">{{ operation.plugin_name }} <span v-if="operation.result">· {{ operation.result.version }}</span></p>
              <p v-if="operation.error_message" class="error-text">{{ operation.error_message }}</p>
              <p v-if="!operation.result?.written">{{ text('notWritten') }}</p>
              <template v-else-if="operation.result.restart_required"><p>{{ text('selfUpdate') }}</p></template>
              <template v-else-if="!operation.result.loaded"><p class="error-text">{{ operation.result.load_error }}</p><p>{{ text('loadHint') }}</p></template>
              <p class="hint">{{ text('refreshHint') }}</p>
            </template>
          </div>
          <p v-if="errorMessage" class="error-text" role="alert">{{ errorMessage }}</p>
          <template v-if="pending && errorMessage"><p class="hint">{{ text('network') }}</p><p class="hint">{{ text('forgetHint') }}</p></template>
        </div>
        <footer>
          <button class="secondary" :disabled="uploading || committing || deleting" @click="close">{{ pending || terminal ? text('close') : text('cancel') }}</button>
          <button v-if="pending && errorMessage" class="secondary" :disabled="busy" @click="forget">{{ text('forget') }}</button>
          <button v-if="operationId && errorMessage" class="primary" :disabled="busy" @click="poll">{{ text('resume') }}</button>
          <button v-else-if="pendingCommit" class="primary" :disabled="busy" @click="confirm">{{ committing ? text('committing') : text('retryCommit') }}</button>
          <button v-else-if="terminal || (preview && (expired || !preview.can_import))" class="primary" :disabled="busy" @click="reset">{{ text('another') }}</button>
          <button v-else-if="preview && !operation" class="primary" :disabled="!canCommit" @click="confirm">{{ text('commit') }}</button>
          <button v-else-if="!operation && !pending" class="primary" :disabled="!file || busy" @click="prepare">{{ text('prepare') }}</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.import-trigger, button { font: inherit; cursor: pointer; }
.import-trigger { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 16px; border: 0; border-radius: 24px; background: var(--md-sys-color-primary); color: var(--md-sys-color-on-primary); font-size: 14px; font-weight: 600; }
.import-backdrop { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px; background: #0006; backdrop-filter: blur(4px); }
.import-dialog { width: min(100%, 620px); max-height: calc(100dvh - 40px); display: flex; flex-direction: column; border: 1px solid var(--md-sys-color-outline-variant); border-radius: 24px; background: var(--md-sys-color-surface); color: var(--md-sys-color-on-surface); box-shadow: 0 16px 64px #0003; outline: none; }
header { display: flex; gap: 16px; align-items: center; padding: 24px 24px 16px; }
.heading-icon { display: flex; padding: 12px; border-radius: 16px; background: var(--md-sys-color-primary-container); color: var(--md-sys-color-on-primary-container); }
h2 { margin: 0 0 6px; font-size: 21px; } header p { margin: 0; font-size: 13px; color: var(--md-sys-color-on-surface-variant); }
.import-body { padding: 0 24px 20px; overflow-y: auto; overflow-wrap: anywhere; line-height: 1.6; }
.notice { display: flex; gap: 10px; align-items: flex-start; padding: 14px; border-radius: 12px; background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container); font-size: 13px; }
.notice :deep(span) { flex-shrink: 0; }
.file-picker { display: flex; flex-direction: column; gap: 12px; padding: 20px; margin-top: 20px; border: 1px dashed var(--md-sys-color-outline); border-radius: 16px; font-weight: 600; }
input[type=file] { width: 100%; font: inherit; font-size: 13px; } input::file-selector-button { border: 0; border-radius: 8px; padding: 8px 12px; margin-right: 12px; background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface); cursor: pointer; }
.hint { font-size: 12px; color: var(--md-sys-color-on-surface-variant); }.filename { font-weight: 600; }.metadata { display: grid; grid-template-columns: auto 1fr; gap: 10px 20px; font-size: 14px; }.metadata dt { color: var(--md-sys-color-on-surface-variant); }.metadata dd { margin: 0; font-weight: 600; }.description { white-space: pre-wrap; font-size: 14px; }
.warning-list, .error-list { padding: 12px 12px 12px 28px; border-radius: 12px; font-size: 13px; }.warning-list { background: var(--md-sys-color-tertiary-container); color: var(--md-sys-color-on-tertiary-container); }.error-list { background: var(--md-sys-color-error-container); color: var(--md-sys-color-on-error-container); }.error-text { color: var(--md-sys-color-error); }.success-text { color: var(--md-sys-color-primary); }.warning-text { color: var(--md-sys-color-tertiary); }
.overwrite { display: flex; align-items: flex-start; gap: 10px; font-size: 14px; padding: 12px 0; }.overwrite input { margin-top: 5px; accent-color: var(--md-sys-color-primary); }
.progress, .operation { margin-top: 16px; }progress { display: block; width: 100%; height: 8px; margin-top: 12px; accent-color: var(--md-sys-color-primary); }
footer { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; padding: 16px 24px; border-top: 1px solid var(--md-sys-color-outline-variant); }footer button { border: 0; border-radius: 24px; padding: 10px 18px; font-size: 14px; font-weight: 600; }.primary { background: var(--md-sys-color-primary); color: var(--md-sys-color-on-primary); }.secondary { background: transparent; color: var(--md-sys-color-on-surface-variant); }button:disabled { opacity: .5; cursor: not-allowed; }button:focus-visible, input:focus-visible { outline: 2px solid var(--md-sys-color-primary); outline-offset: 3px; }
@media (max-width: 520px) { .import-backdrop { padding: 10px; }.import-dialog { max-height: calc(100dvh - 20px); border-radius: 18px; }header { padding: 18px 16px 12px; }.import-body { padding: 0 16px 16px; }footer { padding: 12px 16px; }.metadata { gap: 8px 12px; grid-template-columns: 1fr; }.metadata dd { margin-bottom: 6px; }h2 { font-size: 18px; }.import-trigger { padding: 9px 12px; } }
</style>
