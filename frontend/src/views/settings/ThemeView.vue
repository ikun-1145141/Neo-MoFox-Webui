<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { getSettings, saveSettings } from '../../api/modules/settings'
import { applyMd3Theme } from '../../utils/md3theme'
import { useToastStore } from '../../utils/toast'
import type { SettingsData, ThemeMode } from '../../api/types/base'

const toast = useToastStore()

const loading = ref(true)
const saving = ref(false)

const settings = ref<SettingsData>({
  theme: 'auto',
  theme_source_color: '#0058bd',
  language: 'zh_CN',
  bot_name: 'Neo-MoFox',
  wallpaper_path: null,
})

const presetColors = [
  { label: '深空蓝', hex: '#0058bd' },
  { label: '翡翠绿', hex: '#1b8f6e' },
  { label: '珊瑚橙', hex: '#e8591a' },
  { label: '薰衣草', hex: '#7c4dff' },
  { label: '玫瑰红', hex: '#c2185b' },
  { label: '金黄色', hex: '#f9a825' },
]

const themeModes: { label: string; value: ThemeMode; icon: string }[] = [
  { label: '跟随系统', value: 'auto', icon: 'material-symbols:brightness-auto-outline-rounded' },
  { label: '浅色', value: 'light', icon: 'material-symbols:light-mode-outline-rounded' },
  { label: '深色', value: 'dark', icon: 'material-symbols:dark-mode-outline-rounded' },
]

async function fetchSettings() {
  loading.value = true
  try {
    const data = await getSettings()
    settings.value = data
    applyCurrentTheme()
  } finally {
    loading.value = false
  }
}

function applyCurrentTheme() {
  const s = settings.value
  const isDark =
    s.theme === 'dark' ||
    (s.theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  applyMd3Theme(s.theme_source_color ?? '#0058bd', isDark)
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
}

function selectColor(hex: string) {
  settings.value.theme_source_color = hex
  applyCurrentTheme()
}

// 实时预览主题模式切换
watch(() => settings.value.theme, applyCurrentTheme)

async function handleSave() {
  saving.value = true
  try {
    await saveSettings(settings.value)
    toast.show('主题设置已保存', 'success')
  } finally {
    saving.value = false
  }
}

onMounted(fetchSettings)
</script>

<template>
  <div class="theme-view">
    <!-- 页头 -->
    <div class="view-header">
      <h2 class="view-title">主题设置</h2>
      <p class="view-sub">自定义颜色方案与外观偏好，所有设置同步至后端持久化</p>
    </div>

    <div v-if="loading" class="loading-wrap">
      <Icon icon="material-symbols:progress-activity" class="spin" width="32" height="32" />
      <span>加载配置中…</span>
    </div>

    <template v-else>
      <!-- 外观模式 -->
      <section class="setting-section">
        <h3 class="section-heading">外观模式</h3>
        <div class="mode-grid">
          <button
            v-for="mode in themeModes"
            :key="mode.value"
            class="mode-card"
            :class="{ active: settings.theme === mode.value }"
            @click="settings.theme = mode.value"
          >
            <Icon :icon="mode.icon" width="28" height="28" />
            <span>{{ mode.label }}</span>
            <div v-if="settings.theme === mode.value" class="mode-check">
              <Icon icon="material-symbols:check-rounded" width="16" height="16" />
            </div>
          </button>
        </div>
      </section>

      <!-- 主题颜色 -->
      <section class="setting-section">
        <h3 class="section-heading">主题颜色</h3>
        <p class="section-desc">选择主色调，MD3 色彩引擎将自动生成完整配色方案</p>

        <!-- 预设色板 -->
        <div class="color-presets">
          <button
            v-for="c in presetColors"
            :key="c.hex"
            class="color-swatch"
            :style="{ background: c.hex }"
            :title="c.label"
            :class="{ active: settings.theme_source_color === c.hex }"
            @click="selectColor(c.hex)"
          >
            <Icon
              v-if="settings.theme_source_color === c.hex"
              icon="material-symbols:check-rounded"
              width="18"
              height="18"
              style="color: #fff"
            />
          </button>
        </div>

        <!-- 自定义颜色选择器 -->
        <div class="custom-color-row">
          <label class="custom-color-label">
            <Icon icon="material-symbols:colorize-outline-rounded" width="18" height="18" />
            自定义颜色
          </label>
          <div class="custom-color-wrap">
            <input
              type="color"
              class="color-picker"
              :value="settings.theme_source_color ?? '#0058bd'"
              @input="(e) => selectColor((e.target as HTMLInputElement).value)"
            />
            <span class="color-hex-val">{{ settings.theme_source_color }}</span>
          </div>
        </div>

        <!-- 颜色预览块 -->
        <div class="color-preview-strip">
          <div class="preview-chip primary-chip">Primary</div>
          <div class="preview-chip secondary-chip">Secondary</div>
          <div class="preview-chip tertiary-chip">Tertiary</div>
        </div>
      </section>

      <!-- 保存按钮 -->
      <div class="actions-row">
        <button class="btn-outlined" @click="fetchSettings" :disabled="saving">
          <Icon icon="material-symbols:refresh-rounded" width="18" height="18" />
          重新获取
        </button>
        <button class="btn-primary" @click="handleSave" :disabled="saving">
          <Icon v-if="saving" icon="material-symbols:progress-activity" class="spin" width="18" height="18" />
          <Icon v-else icon="material-symbols:save-outline-rounded" width="18" height="18" />
          <span>{{ saving ? '保存中…' : '保存设置' }}</span>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.theme-view {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.view-header { }
.view-title {
  margin: 0 0 0.375rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--md-sys-color-on-surface);
}
.view-sub {
  margin: 0;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
}

/* 加载态 */
.loading-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.9rem;
}

/* 章节 */
.setting-section {
  background: var(--md-sys-color-surface-container-low);
  border-radius: 1.25rem;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.section-heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}
.section-desc {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant);
}

/* 外观模式卡片 */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}
.mode-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.25rem 1rem;
  background: var(--md-sys-color-surface-container);
  border-radius: 1rem;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
  transition: background 0.15s, color 0.15s;
}
.mode-card:hover {
  background: var(--md-sys-color-surface-container-high);
}
.mode-card.active {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  font-weight: 600;
}
.mode-check {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 20px;
  height: 20px;
  border-radius: 9999px;
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 色板 */
.color-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.color-swatch {
  width: 44px;
  height: 44px;
  border-radius: 9999px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s, box-shadow 0.15s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}
.color-swatch:hover { transform: scale(1.1); }
.color-swatch.active {
  outline: 3px solid var(--md-sys-color-outline);
  outline-offset: 2px;
}

/* 自定义颜色 */
.custom-color-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.custom-color-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--md-sys-color-on-surface-variant);
}
.custom-color-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.color-picker {
  width: 44px;
  height: 44px;
  border-radius: 9999px;
  border: none;
  padding: 0;
  cursor: pointer;
  background: none;
}
.color-picker::-webkit-color-swatch-wrapper { padding: 0; }
.color-picker::-webkit-color-swatch { border-radius: 9999px; border: none; }
.color-hex-val {
  font-family: 'Inter', monospace;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container);
  padding: 0.25rem 0.75rem;
  border-radius: 0.5rem;
}

/* MD3 颜色预览条 */
.color-preview-strip {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.preview-chip {
  padding: 0.375rem 1rem;
  border-radius: 9999px;
  font-size: 0.8125rem;
  font-weight: 600;
}
.primary-chip {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}
.secondary-chip {
  background: var(--md-sys-color-secondary);
  color: var(--md-sys-color-on-secondary);
}
.tertiary-chip {
  background: var(--md-sys-color-tertiary);
  color: var(--md-sys-color-on-tertiary);
}

/* 操作按钮行 */
.actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  height: 2.75rem;
  padding: 0 1.5rem;
  border: none;
  border-radius: 9999px;
  background: linear-gradient(135deg, var(--md-sys-color-primary) 0%, #2771df 100%);
  color: var(--md-sys-color-on-primary);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outlined {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  height: 2.75rem;
  padding: 0 1.25rem;
  border: none;
  border-radius: 9999px;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-outlined:hover { background: var(--md-sys-color-surface-container-highest); }
.btn-outlined:disabled { opacity: 0.5; cursor: not-allowed; }

.spin {
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
