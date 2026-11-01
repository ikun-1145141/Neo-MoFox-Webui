<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
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

// 仅控制展示：自动选中记录时，不跳转到手机详情页。
const compact = ref(false)
const mobileDetail = ref(false)
let media: MediaQueryList | null = null
function updateLayout() { compact.value = media?.matches ?? false }
onMounted(() => {
  media = window.matchMedia('(max-width: 899px)')
  updateLayout()
  media.addEventListener('change', updateLayout)
})
watch(selectedId, id => { if (id === null) mobileDetail.value = false }, { flush: 'sync' })
function openRecord(id: number) {
  mobileDetail.value = true
  if (id !== selectedId.value || !detail.value) void selectRecord(id)
}
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
  media?.removeEventListener('change', updateLayout)
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
    /* 接口拦截器负责显示错误提示。 */
  }
}

async function copyJson(text: string) {
  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      try {
        await navigator.clipboard.writeText(text)
        toast.show(t('requestMonitor.copySuccess'), 'success')
        return
      } catch {
        // 不支持异步剪贴板或权限被拒时，尝试兼容旧版浏览器的复制方式。
      }
    }

    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.top = '0'
    textarea.style.left = '0'
    textarea.style.opacity = '0'
    let copied = false
    try {
      document.body.appendChild(textarea)
      textarea.select()
      copied = document.execCommand('copy')
    } finally {
      textarea.remove()
    }
    if (!copied) throw new Error('Clipboard copy failed')
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
    <section class="rm-page" :class="{ 'rm-show-detail': mobileDetail }">
      <!-- 页面顶栏：使用与主程序各页面对齐的毛玻璃与胶囊工具栏 -->
      <header class="rm-header">
        <div class="rm-header-left">
          <div class="rm-title-wrapper">
            <h1 class="rm-main-title">{{ t('requestMonitor.title') }}</h1>
            <span class="rm-subtitle">{{ t('requestMonitor.subtitle') }}</span>
          </div>

          <div class="rm-badge-group">
            <span class="rm-status-chip" :class="{ 'is-paused': paused }">
              <span class="rm-status-dot"></span>
              {{ t(paused ? 'requestMonitor.paused' : 'requestMonitor.live') }}
            </span>
            <span class="rm-metric-chip">
              <Icon icon="material-symbols:database-outline" width="14" height="14" />
              <span>{{ snapshot?.stats.total ?? 0 }} / {{ snapshot?.capacity ?? 200 }}</span>
            </span>
            <span class="rm-metric-chip rm-last-updated" v-if="lastUpdated">
              <Icon icon="material-symbols:schedule-outline" width="14" height="14" />
              <span>{{ new Date(lastUpdated).toLocaleTimeString() }}</span>
            </span>
          </div>
        </div>

        <div class="rm-header-actions">
          <button
            class="rm-btn rm-btn-tonal"
            :aria-label="t(paused ? 'requestMonitor.resume' : 'requestMonitor.pause')"
            :title="t(paused ? 'requestMonitor.resume' : 'requestMonitor.pause')"
            :disabled="clearing"
            @click="paused ? resume() : pause()"
          >
            <Icon
              :icon="paused ? 'material-symbols:play-arrow-rounded' : 'material-symbols:pause-rounded'"
              width="18"
              height="18"
            />
            <span class="rm-btn-text">{{ t(paused ? 'requestMonitor.resume' : 'requestMonitor.pause') }}</span>
          </button>

          <button
            class="rm-btn rm-btn-tonal"
            :aria-label="t('requestMonitor.refresh')"
            :title="t('requestMonitor.refresh')"
            :disabled="refreshing || clearing"
            @click="refreshNow()"
          >
            <Icon
              icon="material-symbols:refresh-rounded"
              width="18"
              height="18"
              :class="{ 'rm-spin': refreshing }"
            />
            <span class="rm-btn-text">{{ t('requestMonitor.refresh') }}</span>
          </button>

          <button
            class="rm-btn rm-btn-danger-tonal"
            :aria-label="t('requestMonitor.clear')"
            :title="t('requestMonitor.clear')"
            :disabled="!snapshot?.records.length || clearing"
            @click="clearRecords()"
          >
            <Icon icon="material-symbols:delete-sweep-outline-rounded" width="18" height="18" />
            <span class="rm-btn-text">{{ t('requestMonitor.clear') }}</span>
          </button>
        </div>
      </header>

      <!-- 异常提示条 -->
      <div v-if="failed" class="rm-banner rm-banner-error" role="alert">
        <Icon icon="material-symbols:error-outline-rounded" width="18" height="18" />
        <div>
          <strong>{{ t(authFailed ? 'requestMonitor.authFailed' : 'requestMonitor.refreshFailed') }}</strong>
          <span v-if="failureMessage"> ({{ failureMessage }})</span>
        </div>
      </div>
      <div v-else-if="notice" class="rm-banner rm-banner-info" role="status">
        <Icon icon="material-symbols:info-outline-rounded" width="18" height="18" />
        <span>{{ t(`requestMonitor.${notice}`) }}</span>
      </div>

      <!-- 核心工作区：桌面左右分栏，移动端列表/详情单屏切换 -->
      <div class="rm-workspace">
        <InspectorRecordList
          v-model:search="search"
          v-model:status="status"
          v-model:model="model"
          :records="records"
          :models="models"
          :selected-id="selectedId"
          :active="!compact || !mobileDetail"
          :loading="refreshing && !snapshot"
          @select="openRecord"
        />
        <InspectorRecordDetail
          :record="detail"
          :compact="compact"
          :active="!compact || mobileDetail"
          @back="mobileDetail = false"
          :loading="detailLoading"
          :exporting="exporting"
          :filtered-out="selectedId !== null && !records.some(record => record.id === selectedId)"
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
      >
        {{ t('requestMonitor.export') }}
      </a>
    </section>
  </AppShell>
</template>
