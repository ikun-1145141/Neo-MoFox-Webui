<script setup lang="ts">
import { ref, computed } from 'vue'
import Icon from '../common/Icon.vue'
import { importPluginPackage } from '../../api/modules/plugin'
import type { PluginImportResult } from '../../api/types/plugin'
import { useDialogStore } from '../../utils/dialog'
import { useToastStore } from '../../utils/toast'
import { useI18n } from '../../utils/i18n'

const emit = defineEmits<{
  close: []
  imported: [result: PluginImportResult]
}>()

const dialogStore = useDialogStore()
const toastStore = useToastStore()
const { t } = useI18n()

// 与后端 MAX_PACKAGE_SIZE_MB 保持一致，后端为准
const MAX_PACKAGE_SIZE_MB = 50
const ACCEPTED_SUFFIXES = ['.zip', '.mfp']

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const isBusy = ref(false)
const stage = ref<'idle' | 'uploading' | 'installing'>('idle')
const progress = ref(0)

const stageText = computed(() => {
  if (stage.value === 'uploading') return t('plugins.import.uploading')
  if (stage.value === 'installing') return t('plugins.import.installing')
  return ''
})

function formatBytes(value: number): string {
  if (value < 1024) return value + ' B'
  if (value < 1024 * 1024) return (value / 1024).toFixed(1) + ' KiB'
  return (value / (1024 * 1024)).toFixed(1) + ' MiB'
}

// 前端预检：后缀与体积，失败返回 false
function acceptFile(file: File): boolean {
  const lowerName = file.name.toLowerCase()
  if (!ACCEPTED_SUFFIXES.some((suffix) => lowerName.endsWith(suffix))) {
    toastStore.show(t('plugins.import.invalidType'), 'error')
    return false
  }
  if (file.size > MAX_PACKAGE_SIZE_MB * 1024 * 1024) {
    toastStore.show(t('plugins.import.tooLarge', { size: String(MAX_PACKAGE_SIZE_MB) }), 'error')
    return false
  }
  selectedFile.value = file
  return true
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) acceptFile(file)
  // 清空以便重复选择同一文件也能触发 change
  input.value = ''
}

function handleDragOver() {
  if (!isBusy.value) isDragging.value = true
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(event: DragEvent) {
  isDragging.value = false
  if (isBusy.value) return
  const file = event.dataTransfer?.files?.[0]
  if (file) acceptFile(file)
}

function openFilePicker() {
  if (!isBusy.value) fileInputRef.value?.click()
}

function handleClose() {
  if (!isBusy.value) emit('close')
}

function conflictMessage(result: PluginImportResult): string {
  const lines = [
    t('plugins.import.conflictMessage', { name: result.plugin_name }),
    '',
    t('plugins.import.conflictExisting', {
      version: result.existing_version || '—',
      state: result.existing_loaded
        ? t('plugins.import.stateRunning')
        : t('plugins.import.stateStopped'),
    }),
    t('plugins.import.conflictIncoming', { version: result.plugin_version || '—' }),
  ]
  if (result.dependents.length) {
    lines.push(t('plugins.import.conflictDependents', { names: result.dependents.join(', ') }))
  }
  if (result.existing_loaded) {
    lines.push('', t('plugins.import.conflictReload'))
  }
  return lines.join('\n')
}

async function upload(file: File, overwrite: boolean): Promise<PluginImportResult> {
  stage.value = 'uploading'
  progress.value = 0
  return importPluginPackage(file, overwrite, (percent) => {
    progress.value = percent
    if (percent >= 100) stage.value = 'installing'
  })
}

async function handleImport() {
  const file = selectedFile.value
  if (!file || isBusy.value) return

  isBusy.value = true
  try {
    let result = await upload(file, false)

    if (result.conflict) {
      stage.value = 'idle'
      const confirmed = await dialogStore.confirm(
        conflictMessage(result),
        t('plugins.import.conflictTitle'),
        t('plugins.import.overwrite'),
        t('plugins.detail.dialogs.cancel'),
      )
      if (!confirmed) return
      result = await upload(file, true)
    }

    if (result.loaded) {
      toastStore.show(t('plugins.import.success', { name: result.plugin_name }), 'success', 6000)
    } else {
      const detail = result.error_message ? `\n${result.error_message}` : ''
      toastStore.show(t('plugins.import.restartRequired') + detail, 'error', 8000)
    }
    if (result.warnings.length) {
      await dialogStore.alert(
        result.warnings.map((item) => '• ' + item).join('\n'),
        t('plugins.import.warnings'),
      )
    }
    emit('imported', result)
  } catch {
    // 错误提示由全局拦截器处理
  } finally {
    isBusy.value = false
    stage.value = 'idle'
    progress.value = 0
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="import-backdrop" @click.self="handleClose">
      <div class="import-container" role="dialog" aria-modal="true">
        <div class="import-header">
          <h2 class="import-title">{{ t('plugins.import.title') }}</h2>
          <button
            class="close-btn"
            type="button"
            :disabled="isBusy"
            :title="t('plugins.detail.dialogs.cancel')"
            @click="handleClose"
          >
            <Icon icon="material-symbols:close-rounded" width="20" height="20" />
          </button>
        </div>

        <div
          class="drop-zone"
          :class="{ dragging: isDragging, disabled: isBusy }"
          @click="openFilePicker"
          @dragover.prevent="handleDragOver"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handleDrop"
        >
          <Icon icon="material-symbols:upload-file-outline-rounded" width="40" height="40" />
          <p class="drop-hint">{{ t('plugins.import.dropHint') }}</p>
          <p class="drop-sub">{{ t('plugins.import.fileType', { size: String(MAX_PACKAGE_SIZE_MB) }) }}</p>
          <input
            ref="fileInputRef"
            type="file"
            accept=".zip,.mfp"
            class="file-input"
            @change="handleFileChange"
          />
        </div>

        <div v-if="selectedFile" class="file-info">
          <Icon icon="material-symbols:folder-zip-outline-rounded" width="20" height="20" />
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">{{ formatBytes(selectedFile.size) }}</span>
        </div>

        <div v-if="stage !== 'idle'" class="operation-panel">
          <div class="operation-heading">
            <Icon icon="material-symbols:sync-rounded" width="18" height="18" class="spinning" />
            <strong>{{ stageText }}</strong>
            <em v-if="stage === 'uploading'">{{ progress }}%</em>
          </div>
          <div
            class="progress-track"
            role="progressbar"
            :aria-valuenow="stage === 'uploading' ? progress : 100"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <span
              :class="{ indeterminate: stage === 'installing' }"
              :style="{ width: stage === 'uploading' ? `${progress}%` : '100%' }"
            ></span>
          </div>
        </div>

        <div class="import-actions">
          <button class="text-btn" type="button" :disabled="isBusy" @click="handleClose">
            {{ t('plugins.detail.dialogs.cancel') }}
          </button>
          <button
            class="primary-btn"
            type="button"
            :disabled="!selectedFile || isBusy"
            @click="handleImport"
          >
            <Icon
              :icon="isBusy ? 'material-symbols:progress-activity' : 'material-symbols:upload-rounded'"
              width="18"
              height="18"
              :class="{ spinning: isBusy }"
            />
            {{ t('plugins.import.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* ===== 遮罩层（低于 dialogStore 的 10000 与 toast 的 9999，覆盖确认框可叠在上方） ===== */
.import-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: color-mix(in srgb, var(--md-sys-color-surface) 45%, transparent);
  backdrop-filter: blur(4px);
}

/* ===== 容器 ===== */
.import-container {
  position: relative;
  width: 100%;
  max-width: 480px;
  background: var(--md-sys-color-surface, #ffffff);
  border-radius: 16px;
  box-shadow:
    rgba(0, 0, 0, 0.04) 0px 4px 18px,
    rgba(0, 0, 0, 0.027) 0px 2.025px 7.84688px,
    rgba(0, 0, 0, 0.02) 0px 0.8px 2.925px,
    rgba(0, 0, 0, 0.01) 0px 0.175px 1.04062px;
  border: 1px solid var(--md-sys-color-outline-variant);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.import-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.import-title {
  margin: 0;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.4;
  color: var(--md-sys-color-on-surface);
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  cursor: pointer;
}

.close-btn:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-high);
}

/* ===== 拖拽区 ===== */
.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  border: 2px dashed var(--md-sys-color-outline-variant);
  border-radius: 12px;
  color: var(--md-sys-color-on-surface-variant);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.drop-zone:hover:not(.disabled),
.drop-zone.dragging {
  border-color: var(--md-sys-color-primary);
  background: color-mix(in srgb, var(--md-sys-color-primary) 6%, transparent);
  color: var(--md-sys-color-primary);
}

.drop-zone.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.drop-hint {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.drop-sub {
  margin: 0;
  font-size: 0.8rem;
}

.file-input {
  display: none;
}

/* ===== 文件信息 ===== */
.file-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
  font-size: 0.88rem;
}

.file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.file-size {
  color: var(--md-sys-color-on-surface-variant);
}

/* ===== 进度面板 ===== */
.operation-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.operation-heading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--md-sys-color-on-surface);
  font-size: 0.88rem;
}

.operation-heading strong {
  flex: 1;
  font-weight: 600;
}

.operation-heading em {
  font-style: normal;
  color: var(--md-sys-color-primary);
  font-weight: 600;
}

.progress-track {
  height: 6px;
  border-radius: 3px;
  background: var(--md-sys-color-surface-container-highest);
  overflow: hidden;
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: var(--md-sys-color-primary);
  transition: width 0.2s ease;
}

.progress-track span.indeterminate {
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ===== 按钮组 ===== */
.import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.text-btn,
.primary-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 20px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.text-btn {
  background: transparent;
  color: var(--md-sys-color-primary);
}

.text-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-primary) 8%, transparent);
}

.primary-btn {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.text-btn:disabled,
.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ===== 手机适配：底部弹出 ===== */
@media (max-width: 640px) {
  .import-backdrop {
    align-items: flex-end;
    padding: 0;
  }

  .import-container {
    max-width: none;
    max-height: 90dvh;
    overflow-y: auto;
    border-radius: 20px 20px 0 0;
    border-bottom: none;
    padding: 1.25rem 1rem calc(1rem + env(safe-area-inset-bottom));
    gap: 1rem;
  }

  .import-title {
    font-size: 1.125rem;
  }

  /* 手机上点选为主，缩小拖拽区 */
  .drop-zone {
    padding: 1.25rem 0.75rem;
  }

  .drop-hint {
    font-size: 0.88rem;
  }

  .import-actions {
    flex-direction: column-reverse;
  }

  .text-btn,
  .primary-btn {
    justify-content: center;
    width: 100%;
    min-height: 44px;
  }
}
</style>
