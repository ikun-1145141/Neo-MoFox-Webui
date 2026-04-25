<script setup lang="ts">
import { ref } from 'vue'
import { getSettings, replaceSettings } from '../../api/modules/settings'
import { useToastStore } from '../../utils/toast'
import type { WebuiSettings } from '../../api/types/settings'

const IS_DEV = import.meta.env.DEV
const toast = useToastStore()

const exporting = ref(false)
const importing = ref(false)
const importJson = ref('')
const importError = ref('')

// ── 导出 ────────────────────────────────────────────
async function handleExport() {
  exporting.value = true
  try {
    const settings = await getSettings()
    const json = JSON.stringify(settings, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `neo-mofox-settings-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    toast.show('配置已导出', 'success')
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动，导出失败', 'info')
  } finally {
    exporting.value = false
  }
}

// ── 从文件选择 ────────────────────────────────────────
function handleFileSelect(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    importJson.value = ev.target?.result as string
    importError.value = ''
  }
  reader.readAsText(file)
}

// ── 导入（PUT /settings）───────────────────────────────
async function handleImport() {
  importError.value = ''
  let parsed: WebuiSettings
  try {
    parsed = JSON.parse(importJson.value)
  } catch {
    importError.value = 'JSON 格式错误，请检查输入内容'
    return
  }

  // 基本字段校验
  if (!parsed.theme || !parsed.ui || !parsed.system) {
    importError.value = '缺少必要字段（theme / ui / system）'
    return
  }

  importing.value = true
  try {
    await replaceSettings(parsed)
    toast.show('配置已导入并保存', 'success')
    importJson.value = ''
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动，导入失败', 'info')
  } finally {
    importing.value = false
  }
}

function clearImport() {
  importJson.value = ''
  importError.value = ''
}
</script>

<template>
  <div class="data-view">
    <div class="view-header">
      <h2 class="view-title">数据管理</h2>
      <p class="view-sub">备份或还原 WebUI 全量配置，使用 JSON 文件进行导出与导入</p>
    </div>

    <!-- 导出 -->
    <section class="setting-section">
      <div class="section-text">
        <h3 class="section-heading">导出配置</h3>
        <p class="section-desc">
          将当前所有设置（主题、界面、系统）导出为 JSON 文件，可用于备份或迁移
        </p>
      </div>
      <div class="export-row">
        <div class="export-hint">
          <Icon icon="material-symbols:info-outline-rounded" width="16" height="16" />
          <span>导出内容包含：主题颜色、外观模式、语言、字体、系统更新选项</span>
        </div>
        <button class="btn-primary" @click="handleExport" :disabled="exporting">
          <Icon
            v-if="exporting"
            icon="material-symbols:progress-activity"
            class="spin"
            width="18"
            height="18"
          />
          <Icon v-else icon="material-symbols:download-rounded" width="18" height="18" />
          <span>{{ exporting ? '导出中…' : '导出配置文件' }}</span>
        </button>
      </div>
    </section>

    <!-- 导入 -->
    <section class="setting-section">
      <div class="section-text">
        <h3 class="section-heading">导入配置</h3>
        <p class="section-desc">
          上传或粘贴 JSON 配置文件内容，将<strong>完全替换</strong>当前所有设置
        </p>
      </div>

      <div class="import-file-row">
        <label class="file-btn">
          <Icon icon="material-symbols:upload-file-outline-rounded" width="18" height="18" />
          从文件选择
          <input type="file" accept=".json,application/json" hidden @change="handleFileSelect" />
        </label>
        <span class="file-hint">或直接在下方粘贴 JSON 内容</span>
      </div>

      <div class="textarea-wrap" :class="{ error: importError }">
        <textarea
          v-model="importJson"
          class="json-textarea"
          placeholder='粘贴配置 JSON，例如：{"theme": {...}, "ui": {...}, "system": {...}}'
          spellcheck="false"
          rows="10"
        />
      </div>

      <div v-if="importError" class="error-msg">
        <Icon icon="material-symbols:error-outline-rounded" width="16" height="16" />
        {{ importError }}
      </div>

      <div class="import-actions">
        <button class="btn-outlined" @click="clearImport" :disabled="importing || !importJson">
          <Icon icon="material-symbols:close-rounded" width="18" height="18" />
          清空
        </button>
        <button
          class="btn-primary btn-warning"
          @click="handleImport"
          :disabled="importing || !importJson.trim()"
        >
          <Icon
            v-if="importing"
            icon="material-symbols:progress-activity"
            class="spin"
            width="18"
            height="18"
          />
          <Icon v-else icon="material-symbols:upload-rounded" width="18" height="18" />
          <span>{{ importing ? '导入中…' : '应用并覆盖当前配置' }}</span>
        </button>
      </div>

      <div class="warning-banner">
        <Icon icon="material-symbols:warning-outline-rounded" width="18" height="18" />
        <span>导入操作将<strong>完全覆盖</strong>当前配置，请确认 JSON 内容正确后再执行</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.data-view { display: flex; flex-direction: column; gap: 2rem; }
.view-title {
  margin: 0 0 0.375rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em;
  color: var(--md-sys-color-on-surface);
}
.view-sub { margin: 0; font-size: 0.875rem; color: var(--md-sys-color-on-surface-variant); }

.setting-section {
  background: var(--md-sys-color-surface-container-low);
  border-radius: 1.25rem; padding: 1.75rem;
  display: flex; flex-direction: column; gap: 1.25rem;
}
.section-text { display: flex; flex-direction: column; gap: 0.25rem; }
.section-heading {
  margin: 0;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.0625rem; font-weight: 600; color: var(--md-sys-color-on-surface);
}
.section-desc { margin: 0; font-size: 0.875rem; color: var(--md-sys-color-on-surface-variant); }
.section-desc strong { color: var(--md-sys-color-error); font-weight: 600; }

/* 导出行 */
.export-row {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;
}
.export-hint {
  display: flex; align-items: center; gap: 0.375rem;
  font-size: 0.8125rem; color: var(--md-sys-color-on-surface-variant);
}

/* 导入文件选择 */
.import-file-row { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.file-btn {
  display: inline-flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 1rem; border-radius: 0.75rem; cursor: pointer;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface); font-size: 0.875rem; font-weight: 500;
  transition: background 0.15s; user-select: none;
}
.file-btn:hover { background: var(--md-sys-color-surface-container-highest); }
.file-hint { font-size: 0.8125rem; color: var(--md-sys-color-on-surface-variant); }

/* textarea */
.textarea-wrap {
  border: 1.5px solid var(--md-sys-color-outline-variant);
  border-radius: 0.875rem; overflow: hidden; transition: border-color 0.15s;
}
.textarea-wrap:focus-within { border-color: var(--md-sys-color-primary); }
.textarea-wrap.error { border-color: var(--md-sys-color-error); }
.json-textarea {
  width: 100%; box-sizing: border-box; padding: 0.875rem 1rem;
  background: var(--md-sys-color-surface-container-lowest); border: none; outline: none;
  font-family: 'Inter', 'Consolas', monospace; font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface); resize: vertical; line-height: 1.6;
}

.error-msg {
  display: flex; align-items: center; gap: 0.375rem;
  font-size: 0.8125rem; color: var(--md-sys-color-error);
}

.import-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }

/* 警告横幅 */
.warning-banner {
  display: flex; align-items: flex-start; gap: 0.5rem;
  padding: 0.875rem 1rem; border-radius: 0.75rem;
  background: color-mix(in srgb, var(--md-sys-color-error-container) 40%, transparent);
  color: var(--md-sys-color-on-error-container); font-size: 0.8125rem;
}
.warning-banner strong { font-weight: 700; }

/* 按钮 */
.btn-primary {
  display: inline-flex; align-items: center; gap: 0.5rem;
  height: 2.75rem; padding: 0 1.5rem; border: none; border-radius: 9999px;
  background: linear-gradient(135deg, var(--md-sys-color-primary) 0%, #2771df 100%);
  color: var(--md-sys-color-on-primary);
  font-size: 0.9375rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary.btn-warning {
  background: linear-gradient(135deg, var(--md-sys-color-error) 0%, #c0392b 100%);
  color: var(--md-sys-color-on-error);
}
.btn-outlined {
  display: inline-flex; align-items: center; gap: 0.5rem;
  height: 2.75rem; padding: 0 1.25rem; border: none; border-radius: 9999px;
  background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface);
  font-size: 0.9375rem; font-weight: 500; cursor: pointer; transition: background 0.15s;
}
.btn-outlined:hover { background: var(--md-sys-color-surface-container-highest); }
.btn-outlined:disabled { opacity: 0.5; cursor: not-allowed; }

.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
