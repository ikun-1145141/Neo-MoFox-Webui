<script setup lang="ts">
import { nextTick, onUnmounted, ref } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import Icon from '../components/common/Icon.vue'
import InspectorRecordList from '../components/request-monitor/InspectorRecordList.vue'
import InspectorRecordDetail from '../components/request-monitor/InspectorRecordDetail.vue'
import { useRequestMonitor } from '../composables/useRequestMonitor'
import { useDialogStore } from '../utils/dialog'
import { useToastStore } from '../utils/toast'
import { useI18n } from '../utils/i18n'
import '../styles/request-monitor.css'
const { t } = useI18n()
const dialog = useDialogStore()
const toast = useToastStore()
const {
  snapshot,
  detail,
  selectedId,
  search,
  status,
  model,
  models,
  records,
  paused,
  failed,
  authFailed,
  failureMessage,
  refreshing,
  detailLoading,
  clearing,
  lastUpdated,
  notice,
  selectRecord,
  refreshNow,
  pause,
  resume,
  clear,
} = useRequestMonitor()
const exporting = ref(false)
const downloadUrl = ref('')
const downloadName = ref('')
const downloadLink = ref<HTMLAnchorElement | null>(null)
let disposed = false
let revokeTimer: ReturnType<typeof setTimeout> | null = null
function revokeDownload() {
  if (downloadUrl.value) URL.revokeObjectURL(downloadUrl.value)
  downloadUrl.value = ''
}
onUnmounted(() => {
  disposed = true
  if (revokeTimer) clearTimeout(revokeTimer)
  revokeDownload()
})
async function clearRecords() {
  if (
    !(await dialog.confirm(
      t('requestMonitor.clearMessage'),
      t('requestMonitor.clearTitle'),
      t('requestMonitor.clear'),
      t('requestMonitor.cancel'),
    ))
  )
    return
  if (disposed) return
  try {
    await clear()
    if (disposed) return
    toast.show(t('requestMonitor.clearSuccess'), 'success')
  } catch {
    /* API interceptor reports the error. */
  }
}
async function copyJson(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    toast.show(t('requestMonitor.copySuccess'), 'success')
  } catch {
    toast.show(t('requestMonitor.copyFailed'), 'error')
  }
}
async function exportDetail(value: unknown, scope: string) {
  if (!detail.value || exporting.value) return
  exporting.value = true
  try {
    if (revokeTimer) clearTimeout(revokeTimer)
    revokeDownload()
    downloadName.value = `mofox-record-${detail.value.id}-v${detail.value.version}-${scope}.json`
    downloadUrl.value = URL.createObjectURL(
      new Blob([JSON.stringify(value, null, 2)], {
        type: 'application/json',
      }),
    )
    await nextTick()
    if (disposed) { revokeDownload(); return }
    downloadLink.value?.click()
    revokeTimer = setTimeout(revokeDownload, 5000)
    toast.show(t('requestMonitor.exportSuccess'), 'success')
  } catch {
    toast.show(t('requestMonitor.exportFailed'), 'error')
  } finally {
    exporting.value = false
  }
}
</script>
<template>
  <AppShell no-padding>
    <section class="rm-page">
      <header class="rm-header">
        <div class="rm-title">
          <h1>{{ t('requestMonitor.title') }}</h1>
          <p>{{ t('requestMonitor.subtitle') }}</p>
        </div>
        <div class="rm-actions">
          <span class="rm-live" :class="{ 'is-paused': paused }"
            ><i></i
            >{{
              t(paused ? 'requestMonitor.paused' : 'requestMonitor.live')
            }}</span
          ><button
            class="rm-button"
            :disabled="clearing"
            @click="paused ? resume() : pause()"
          >
            {{
              t(paused ? 'requestMonitor.resume' : 'requestMonitor.pause')
            }}</button
          ><button
            class="rm-button"
            :disabled="refreshing || clearing"
            @click="refreshNow()"
          >
            <Icon
              icon="material-symbols:refresh-rounded"
              width="18"
              height="18"
            />{{ t('requestMonitor.refresh') }}</button
          ><button
            class="rm-button rm-danger"
            :disabled="!snapshot?.records.length || clearing"
            @click="clearRecords()"
          >
            {{ t('requestMonitor.clear') }}
          </button>
        </div>
      </header>
      <div class="rm-buffer-bar">
        <span
          >{{ t('requestMonitor.buffer') }}
          <strong
            >{{ snapshot?.stats.total ?? 0 }} /
            {{ snapshot?.capacity ?? 200 }}</strong
          ></span
        ><span class="rm-last-updated"
          >{{ t('requestMonitor.updated') }}
          {{
            lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : '—'
          }}</span
        >
      </div>
      <p v-if="failed" class="rm-banner rm-error" role="alert">
        {{ t(authFailed ? 'requestMonitor.authFailed' : 'requestMonitor.refreshFailed') }}
        <span v-if="failureMessage"> {{ failureMessage }}</span>
      </p>
      <p v-if="notice" class="rm-banner rm-info" role="status">
        {{ t(`requestMonitor.${notice}`) }}
      </p>
      <div class="rm-workspace">
        <InspectorRecordList
          v-model:search="search"
          v-model:status="status"
          v-model:model="model"
          :records="records"
          :models="models"
          :selected-id="selectedId"
          :loading="refreshing && !snapshot"
          @select="selectRecord"
        /><InspectorRecordDetail
          :record="detail"
          :filtered-out="selectedId !== null && !records.some(record => record.id === selectedId)"
          :loading="detailLoading"
          :exporting="exporting"
          @copy="copyJson"
          @export="exportDetail"
        />
      </div>
      <a
        ref="downloadLink"
        class="rm-sr-only"
        :href="downloadUrl || undefined"
        :download="downloadName"
        aria-hidden="true"
        tabindex="-1"
        >{{ t('requestMonitor.export') }}</a
      >
    </section>
  </AppShell>
</template>
