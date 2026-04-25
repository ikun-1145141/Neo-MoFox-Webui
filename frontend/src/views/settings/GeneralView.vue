<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted, watch } from 'vue'
import { getSettings, updateSettings, resetSettings } from '../../api/modules/settings'
import { useToastStore } from '../../utils/toast'
import type { WebuiSettings } from '../../api/types/settings'

const IS_DEV = import.meta.env.DEV
const toast = useToastStore()
const loading = ref(true)
const saving = ref(false)
const autoSaveEnabled = ref(false)
const lastSavedSnapshot = ref('')

let autoSaveTimer: number | null = null
const AUTO_SAVE_DELAY_MS = 600

const fontSizeOptions: { label: string; value: 'small' | 'medium' | 'large'; icon: string }[] = [
  { label: '小', value: 'small', icon: 'material-symbols:format-size-rounded' },
  { label: '中', value: 'medium', icon: 'material-symbols:format-size-rounded' },
  { label: '大', value: 'large', icon: 'material-symbols:format-size-rounded' },
]

const DEFAULT_SETTINGS: WebuiSettings = {
  theme: { mode: 'auto', primary_color: '#0058bd' },
  ui: { language: 'zh-CN', font_size: 'medium' },
  system: { auto_update: false, check_update_on_startup: true },
}

const settings = ref<WebuiSettings>(structuredClone(DEFAULT_SETTINGS))

function getCurrentSnapshot(): string {
  return JSON.stringify({
    ui: settings.value.ui,
    system: settings.value.system,
  })
}

function clearAutoSaveTimer() {
  if (autoSaveTimer !== null) {
    window.clearTimeout(autoSaveTimer)
    autoSaveTimer = null
  }
}

async function persistChanges() {
  if (loading.value) return

  const currentSnapshot = getCurrentSnapshot()
  if (currentSnapshot === lastSavedSnapshot.value) return

  saving.value = true
  try {
    const updated = await updateSettings({ ui: settings.value.ui, system: settings.value.system })
    settings.value.ui = updated.ui
    settings.value.system = updated.system
    lastSavedSnapshot.value = JSON.stringify({ ui: updated.ui, system: updated.system })
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动，更改不会持久化', 'info')
  } finally {
    saving.value = false
  }
}

function scheduleAutoSave() {
  if (!autoSaveEnabled.value) return
  clearAutoSaveTimer()
  autoSaveTimer = window.setTimeout(() => {
    void persistChanges()
  }, AUTO_SAVE_DELAY_MS)
}

async function fetchSettings() {
  loading.value = true
  autoSaveEnabled.value = false
  clearAutoSaveTimer()
  try {
    settings.value = await getSettings()
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动，使用默认配置', 'info')
  } finally {
    lastSavedSnapshot.value = getCurrentSnapshot()
    autoSaveEnabled.value = true
    loading.value = false
  }
}

async function handleReset() {
  saving.value = true
  autoSaveEnabled.value = false
  clearAutoSaveTimer()
  try {
    const data = await resetSettings()
    settings.value = data
    toast.show('已重置为默认设置', 'success')
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动', 'info')
  } finally {
    lastSavedSnapshot.value = getCurrentSnapshot()
    autoSaveEnabled.value = true
    saving.value = false
  }
}

watch(
  () => [
    settings.value.ui.language,
    settings.value.ui.font_size,
    settings.value.system.auto_update,
    settings.value.system.check_update_on_startup,
  ],
  () => {
    scheduleAutoSave()
  }
)

onBeforeUnmount(() => {
  clearAutoSaveTimer()
})

onMounted(fetchSettings)
</script>

<template>
  <div class="general-view">
    <div class="view-header">
      <h2 class="view-title">通用设置</h2>
      <p class="view-sub">调整界面语言、字体与系统行为偏好</p>
      <p class="autosave-hint">
        <Icon icon="material-symbols:cloud-done-outline-rounded" width="16" height="16" />
        修改后自动保存
      </p>
    </div>

    <div v-if="loading" class="loading-wrap">
      <Icon icon="material-symbols:progress-activity" class="spin" width="32" height="32" />
      <span>加载配置中…</span>
    </div>

    <template v-else>
      <section class="setting-section">
        <div class="section-text">
          <h3 class="section-heading">界面</h3>
          <p class="section-desc">语言和字体大小等显示相关选项</p>
        </div>

        <div class="field-row">
          <div class="field-label-wrap">
            <span class="field-label">界面语言</span>
            <span class="field-hint">选择 WebUI 的显示语言</span>
          </div>
          <div class="radio-group">
            <label class="radio-card" :class="{ active: settings.ui.language === 'zh-CN' }">
              <input type="radio" name="language" value="zh-CN" v-model="settings.ui.language" hidden />
              <Icon icon="material-symbols:translate-rounded" width="20" height="20" />
              <span>简体中文</span>
              <div v-if="settings.ui.language === 'zh-CN'" class="radio-check">
                <Icon icon="material-symbols:check-rounded" width="14" height="14" />
              </div>
            </label>
            <label class="radio-card" :class="{ active: settings.ui.language === 'en-US' }">
              <input type="radio" name="language" value="en-US" v-model="settings.ui.language" hidden />
              <Icon icon="material-symbols:translate-rounded" width="20" height="20" />
              <span>English</span>
              <div v-if="settings.ui.language === 'en-US'" class="radio-check">
                <Icon icon="material-symbols:check-rounded" width="14" height="14" />
              </div>
            </label>
          </div>
        </div>

        <div class="field-row">
          <div class="field-label-wrap">
            <span class="field-label">字体大小</span>
            <span class="field-hint">调整文字显示尺寸</span>
          </div>
          <div class="radio-group">
            <label
              v-for="opt in fontSizeOptions"
              :key="opt.value"
              class="radio-card"
              :class="{ active: settings.ui.font_size === opt.value }"
            >
              <input type="radio" name="font_size" :value="opt.value" v-model="settings.ui.font_size" hidden />
              <Icon :icon="opt.icon" width="20" height="20" />
              <span>{{ opt.label }}</span>
              <div v-if="settings.ui.font_size === opt.value" class="radio-check">
                <Icon icon="material-symbols:check-rounded" width="14" height="14" />
              </div>
            </label>
          </div>
        </div>
      </section>

      <section class="setting-section">
        <div class="section-text">
          <h3 class="section-heading">系统</h3>
          <p class="section-desc">更新检查等后台行为选项</p>
        </div>

        <div class="toggle-list">
          <div class="toggle-row">
            <div class="toggle-label-wrap">
              <span class="toggle-label">自动更新</span>
              <span class="toggle-hint">发现新版本后自动下载并安装</span>
            </div>
            <button
              class="toggle-btn"
              :class="{ on: settings.system.auto_update }"
              @click="settings.system.auto_update = !settings.system.auto_update"
              role="switch"
              :aria-checked="settings.system.auto_update"
            >
              <div class="toggle-thumb" />
            </button>
          </div>

          <div class="toggle-row">
            <div class="toggle-label-wrap">
              <span class="toggle-label">启动时检查更新</span>
              <span class="toggle-hint">每次启动时自动检测是否有新版本</span>
            </div>
            <button
              class="toggle-btn"
              :class="{ on: settings.system.check_update_on_startup }"
              @click="settings.system.check_update_on_startup = !settings.system.check_update_on_startup"
              role="switch"
              :aria-checked="settings.system.check_update_on_startup"
            >
              <div class="toggle-thumb" />
            </button>
          </div>
        </div>
      </section>

      <div class="actions-row">
        <button class="btn-outlined" @click="fetchSettings" :disabled="saving">
          <Icon icon="material-symbols:refresh-rounded" width="18" height="18" />
          重新获取
        </button>
        <button class="btn-outlined btn-danger" @click="handleReset" :disabled="saving">
          <Icon icon="material-symbols:restart-alt-rounded" width="18" height="18" />
          恢复默认
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.general-view { display: flex; flex-direction: column; gap: 2rem; }
.view-title {
  margin: 0 0 0.375rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em;
  color: var(--md-sys-color-on-surface);
}
.view-sub { margin: 0; font-size: 0.875rem; color: var(--md-sys-color-on-surface-variant); }
.autosave-hint {
  margin: 0.5rem 0 0;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant);
}
.loading-wrap {
  display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 3rem;
  color: var(--md-sys-color-on-surface-variant); font-size: 0.9rem;
}
.setting-section {
  background: var(--md-sys-color-surface-container-low);
  border-radius: 1.25rem; padding: 1.75rem;
  display: flex; flex-direction: column; gap: 1.5rem;
}
.section-text { display: flex; flex-direction: column; gap: 0.25rem; }
.section-heading {
  margin: 0;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.0625rem; font-weight: 600; color: var(--md-sys-color-on-surface);
}
.section-desc { margin: 0; font-size: 0.875rem; color: var(--md-sys-color-on-surface-variant); }
.field-row {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 1.5rem; flex-wrap: wrap;
}
.field-label-wrap { display: flex; flex-direction: column; gap: 0.125rem; min-width: 120px; }
.field-label { font-size: 0.9375rem; font-weight: 500; color: var(--md-sys-color-on-surface); }
.field-hint { font-size: 0.8125rem; color: var(--md-sys-color-on-surface-variant); }
.radio-group { display: flex; gap: 0.625rem; flex-wrap: wrap; }
.radio-card {
  position: relative;
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.625rem 1rem;
  background: var(--md-sys-color-surface-container);
  border-radius: 0.75rem; cursor: pointer; font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
  transition: background 0.15s, color 0.15s; user-select: none;
}
.radio-card:hover { background: var(--md-sys-color-surface-container-high); }
.radio-card.active {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container); font-weight: 600;
}
.radio-check {
  width: 18px; height: 18px; border-radius: 9999px;
  background: var(--md-sys-color-primary); color: var(--md-sys-color-on-primary);
  display: flex; align-items: center; justify-content: center;
}
.toggle-list { display: flex; flex-direction: column; gap: 0.25rem; }
.toggle-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.875rem 0.25rem;
  border-bottom: 1px solid var(--md-sys-color-outline-variant); gap: 1rem;
}
.toggle-row:last-child { border-bottom: none; }
.toggle-label-wrap { display: flex; flex-direction: column; gap: 0.125rem; }
.toggle-label { font-size: 0.9375rem; font-weight: 500; color: var(--md-sys-color-on-surface); }
.toggle-hint { font-size: 0.8125rem; color: var(--md-sys-color-on-surface-variant); }
.toggle-btn {
  position: relative; width: 52px; height: 30px; border-radius: 9999px;
  border: none; background: var(--md-sys-color-surface-container-highest);
  cursor: pointer; transition: background 0.2s; flex-shrink: 0; padding: 0;
}
.toggle-btn.on { background: var(--md-sys-color-primary); }
.toggle-thumb {
  position: absolute; top: 50%; left: 4px; transform: translateY(-50%);
  width: 22px; height: 22px; border-radius: 9999px;
  background: var(--md-sys-color-outline);
  transition: left 0.2s, width 0.15s, background 0.2s;
}
.toggle-btn.on .toggle-thumb { left: 26px; background: var(--md-sys-color-on-primary); }
.toggle-btn:hover .toggle-thumb { width: 26px; }
.actions-row { display: flex; justify-content: flex-end; gap: 0.75rem; flex-wrap: wrap; }
.btn-outlined {
  display: flex; align-items: center; gap: 0.5rem;
  height: 2.75rem; padding: 0 1.25rem; border: none; border-radius: 9999px;
  background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface);
  font-size: 0.9375rem; font-weight: 500; cursor: pointer; transition: background 0.15s;
}
.btn-outlined:hover { background: var(--md-sys-color-surface-container-highest); }
.btn-outlined:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { color: var(--md-sys-color-error); }
.btn-danger:hover { background: var(--md-sys-color-error-container); color: var(--md-sys-color-on-error-container); }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
