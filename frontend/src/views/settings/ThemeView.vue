<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted, watch } from 'vue'
import { getSettings, updateSettings, resetSettings } from '../../api/modules/settings'
import { applyMd3Theme } from '../../utils/md3theme'
import { useToastStore } from '../../utils/toast'
import type { WebuiSettings } from '../../api/types/settings'

const IS_DEV = import.meta.env.DEV
const toast = useToastStore()
const loading = ref(true)
const saving = ref(false)
const autoSaveEnabled = ref(false)
const lastSavedThemeSnapshot = ref('')

let autoSaveTimer: number | null = null
const AUTO_SAVE_DELAY_MS = 600

const DEFAULT_SETTINGS: WebuiSettings = {
  theme: { mode: 'auto', primary_color: '#0058bd' },
  ui: { language: 'zh-CN', font_size: 'medium' },
  system: { auto_update: false, check_update_on_startup: true },
}

const settings = ref<WebuiSettings>(structuredClone(DEFAULT_SETTINGS))

const presetColors = [
  { label: '深空蓝', hex: '#0058bd' },
  { label: '翡翠绿', hex: '#1b8f6e' },
  { label: '珊瑚橙', hex: '#e8591a' },
  { label: '薰衣草', hex: '#7c4dff' },
  { label: '玫瑰红', hex: '#c2185b' },
  { label: '金黄色', hex: '#f9a825' },
]

const themeModes: { label: string; value: WebuiSettings['theme']['mode']; icon: string }[] = [
  { label: '跟随系统', value: 'auto', icon: 'material-symbols:brightness-auto-outline-rounded' },
  { label: '浅色', value: 'light', icon: 'material-symbols:light-mode-outline-rounded' },
  { label: '深色', value: 'dark', icon: 'material-symbols:dark-mode-outline-rounded' },
]

function getCurrentThemeSnapshot(): string {
  return JSON.stringify(settings.value.theme)
}

function clearAutoSaveTimer() {
  if (autoSaveTimer !== null) {
    window.clearTimeout(autoSaveTimer)
    autoSaveTimer = null
  }
}

async function persistThemeChanges() {
  if (loading.value) return

  const currentSnapshot = getCurrentThemeSnapshot()
  if (currentSnapshot === lastSavedThemeSnapshot.value) return

  saving.value = true
  try {
    const updated = await updateSettings({ theme: settings.value.theme })
    settings.value.theme = updated.theme
    lastSavedThemeSnapshot.value = JSON.stringify(updated.theme)
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
    void persistThemeChanges()
  }, AUTO_SAVE_DELAY_MS)
}

async function fetchSettings() {
  loading.value = true
  autoSaveEnabled.value = false
  clearAutoSaveTimer()
  try {
    settings.value = await getSettings()
    applyCurrentTheme()
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动，使用默认配置', 'info')
    applyCurrentTheme()
  } finally {
    lastSavedThemeSnapshot.value = getCurrentThemeSnapshot()
    autoSaveEnabled.value = true
    loading.value = false
  }
}

function applyCurrentTheme() {
  const { mode, primary_color } = settings.value.theme
  const isDark =
    mode === 'dark' ||
    (mode === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  applyMd3Theme(primary_color, isDark)
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
}

function selectColor(hex: string) {
  settings.value.theme.primary_color = hex
  applyCurrentTheme()
}

watch(() => settings.value.theme.mode, applyCurrentTheme)

watch(
  () => [settings.value.theme.mode, settings.value.theme.primary_color],
  () => {
    scheduleAutoSave()
  }
)

async function handleReset() {
  saving.value = true
  autoSaveEnabled.value = false
  clearAutoSaveTimer()
  try {
    const data = await resetSettings()
    settings.value = data
    applyCurrentTheme()
    toast.show('已重置为默认设置', 'success')
  } catch {
    if (IS_DEV) toast.show('[DEV] 后端未启动', 'info')
  } finally {
    lastSavedThemeSnapshot.value = getCurrentThemeSnapshot()
    autoSaveEnabled.value = true
    saving.value = false
  }
}

onBeforeUnmount(() => {
  clearAutoSaveTimer()
})

onMounted(fetchSettings)
</script>

<template>
  <div class="theme-view">
    <div class="view-header">
      <h2 class="view-title">主题设置</h2>
      <p class="view-sub">自定义颜色方案与外观偏好，所有设置同步至后端持久化</p>
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
          <h3 class="section-heading">外观模式</h3>
          <p class="section-desc">选择界面的亮暗主题，或设置随系统自动切换</p>
        </div>
        <div class="mode-grid">
          <button
            v-for="mode in themeModes"
            :key="mode.value"
            class="mode-card"
            :class="{ active: settings.theme.mode === mode.value }"
            @click="settings.theme.mode = mode.value"
          >
            <Icon :icon="mode.icon" width="28" height="28" />
            <span>{{ mode.label }}</span>
            <div v-if="settings.theme.mode === mode.value" class="mode-check">
              <Icon icon="material-symbols:check-rounded" width="16" height="16" />
            </div>
          </button>
        </div>
      </section>

      <section class="setting-section">
        <div class="section-text">
          <h3 class="section-heading">主题主色调</h3>
          <p class="section-desc">选择全局界面的主导配色，UI 引擎将基于该色彩生成完整的 MD3 衍生色板</p>
        </div>

        <div class="color-presets">
          <button
            v-for="c in presetColors"
            :key="c.hex"
            class="color-swatch"
            :style="{ background: c.hex }"
            :title="c.label"
            :class="{ active: settings.theme.primary_color === c.hex }"
            @click="selectColor(c.hex)"
          >
            <Icon
              v-if="settings.theme.primary_color === c.hex"
              icon="material-symbols:check-rounded"
              width="18"
              height="18"
              style="color: #fff"
            />
          </button>
        </div>

        <div class="custom-color-row">
          <label class="custom-color-label">
            <Icon icon="material-symbols:colorize-outline-rounded" width="18" height="18" />
            自定义颜色
          </label>
          <div class="custom-color-wrap">
            <input
              type="color"
              class="color-picker"
              :value="settings.theme.primary_color"
              @input="(e) => selectColor((e.target as HTMLInputElement).value)"
            />
            <span class="color-hex-val">{{ settings.theme.primary_color }}</span>
          </div>
        </div>

        <div class="color-preview-strip">
          <div class="preview-chip primary-chip">Primary</div>
          <div class="preview-chip secondary-chip">Secondary</div>
          <div class="preview-chip tertiary-chip">Tertiary</div>
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
.theme-view { display: flex; flex-direction: column; gap: 2rem; }
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
.mode-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }
.mode-card {
  position: relative; display: flex; flex-direction: column; align-items: center; gap: 0.5rem;
  padding: 1.25rem 1rem; background: var(--md-sys-color-surface-container);
  border-radius: 1rem; border: none; cursor: pointer; font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant); transition: background 0.15s, color 0.15s;
}
.mode-card:hover { background: var(--md-sys-color-surface-container-high); }
.mode-card.active {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container); font-weight: 600;
}
.mode-check {
  position: absolute; top: 0.5rem; right: 0.5rem; width: 20px; height: 20px;
  border-radius: 9999px; background: var(--md-sys-color-primary); color: var(--md-sys-color-on-primary);
  display: flex; align-items: center; justify-content: center;
}
.color-presets { display: flex; flex-wrap: wrap; gap: 0.75rem; }
.color-swatch {
  width: 44px; height: 44px; border-radius: 9999px; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.15s, box-shadow 0.15s; box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}
.color-swatch:hover { transform: scale(1.1); }
.color-swatch.active { outline: 3px solid var(--md-sys-color-outline); outline-offset: 2px; }
.custom-color-row {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem;
}
.custom-color-label {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.9rem; color: var(--md-sys-color-on-surface-variant);
}
.custom-color-wrap { display: flex; align-items: center; gap: 0.75rem; }
.color-picker {
  width: 44px; height: 44px; border-radius: 9999px; border: none; padding: 0; cursor: pointer; background: none;
}
.color-picker::-webkit-color-swatch-wrapper { padding: 0; }
.color-picker::-webkit-color-swatch { border-radius: 9999px; border: none; }
.color-hex-val {
  font-family: 'Inter', monospace; font-size: 0.875rem; color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container); padding: 0.25rem 0.75rem; border-radius: 0.5rem;
}
.color-preview-strip { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.preview-chip { padding: 0.375rem 1rem; border-radius: 9999px; font-size: 0.8125rem; font-weight: 600; }
.primary-chip { background: var(--md-sys-color-primary); color: var(--md-sys-color-on-primary); }
.secondary-chip { background: var(--md-sys-color-secondary); color: var(--md-sys-color-on-secondary); }
.tertiary-chip { background: var(--md-sys-color-tertiary); color: var(--md-sys-color-on-tertiary); }
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
