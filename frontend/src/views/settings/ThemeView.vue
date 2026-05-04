<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted, watch, computed } from 'vue'
import { getSettings, updateSettings, resetSettings } from '../../api/modules/settings'
import {
  deleteWallpaper,
  getWallpaperImageUrl,
  getWallpaperStatus,
  uploadWallpaper,
} from '../../api/modules/wallpaper'
import { applyMd3Theme } from '../../utils/md3theme'
import { useToastStore } from '../../utils/toast'
import type { WebuiSettings } from '../../api/types/settings'
import {
  extractColorsFromImage,
  saveWallpaperColors,
  loadWallpaperColors,
  clearWallpaperColors,
} from '../../utils/wallpaperColorManager'
import {
  extractFirstFrameAsFile,
  isVideoFile,
  isImageFile,
} from '../../utils/videoFrameExtractor'

const IS_DEV = import.meta.env.DEV
const toast = useToastStore()
const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)
const autoSaveEnabled = ref(false)
const lastSavedThemeSnapshot = ref('')
const wallpaperVersion = ref(Date.now())
const wallpaperType = ref<'image' | 'video' | 'none'>('none')
const wallpaperInputRef = ref<HTMLInputElement | null>(null)
const wallpaperColors = ref<string[]>([])
const extractingColors = ref(false)

let autoSaveTimer: number | null = null
const AUTO_SAVE_DELAY_MS = 600

const DEFAULT_SETTINGS: WebuiSettings = {
  theme: {
    mode: 'auto',
    primary_color: '#0058bd',
    has_wallpaper: false,
    wallpaper_blur: 0,
    wallpaper_opacity: 0.5,
  },
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

// 判断颜色来源
const colorSource = computed(() => {
  const currentColor = settings.value.theme.primary_color
  
  // 检查是否是预设颜色
  if (presetColors.some(c => c.hex === currentColor)) {
    return 'preset'
  }
  
  // 检查是否是壁纸取色
  if (wallpaperColors.value.includes(currentColor)) {
    return 'wallpaper'
  }
  
  // 其他情况为自定义
  return 'custom'
})

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

function getCurrentWallpaperImageUrl(): string {
  return getWallpaperImageUrl(wallpaperVersion.value)
}

function emitWallpaperUpdated(payload?: any) {
  if (payload) {
    window.dispatchEvent(new CustomEvent('wallpaper-updated', { detail: payload }))
  } else {
    window.dispatchEvent(new CustomEvent('wallpaper-updated', { detail: { force: true } }))
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
    await refreshWallpaperStatus()
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

async function refreshWallpaperStatus() {
  try {
    const status = await getWallpaperStatus()
    settings.value.theme.has_wallpaper = status.has_wallpaper
    wallpaperType.value = status.wallpaper_type
    settings.value.theme.wallpaper_blur = status.wallpaper_blur
    settings.value.theme.wallpaper_opacity = status.wallpaper_opacity
    wallpaperVersion.value = Date.now()
  } catch {
    settings.value.theme.has_wallpaper = false
    wallpaperType.value = 'none'
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
  () => [
    settings.value.theme.mode,
    settings.value.theme.primary_color,
    settings.value.theme.wallpaper_blur,
    settings.value.theme.wallpaper_opacity,
  ],
  (newValues, oldValues) => {
    scheduleAutoSave()
    
    // 即时预览壁纸效果
    if (
      newValues[2] !== oldValues?.[2] ||
      newValues[3] !== oldValues?.[3]
    ) {
      emitWallpaperUpdated({
        wallpaper_blur: newValues[2],
        wallpaper_opacity: newValues[3],
      })
    }
  }
)

async function handleWallpaperFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  // 判断文件类型
  const isImage = isImageFile(file)
  const isVideo = isVideoFile(file)
  
  if (!isImage && !isVideo) {
    toast.show('仅支持 JPG、PNG、WEBP、MP4、WEBM 格式', 'error')
    input.value = ''
    return
  }

  // 根据文件类型检查大小限制
  const maxSize = isImage ? 10 * 1024 * 1024 : 50 * 1024 * 1024  // 图片 10MB，视频 50MB
  const maxSizeMB = maxSize / (1024 * 1024)
  
  if (file.size > maxSize) {
    toast.show(`${isImage ? '图片' : '视频'}壁纸文件不能超过 ${maxSizeMB}MB`, 'error')
    input.value = ''
    return
  }

  uploading.value = true
  extractingColors.value = true
  
  try {
    // 准备取色的源文件：图片直接使用，视频提取第一帧
    let colorSourceFile: File
    
    if (isVideo) {
      console.log('正在从视频提取第一帧...', 'info')
      // 从视频提取第一帧作为图片
      colorSourceFile = await extractFirstFrameAsFile(file)
    } else {
      colorSourceFile = file
    }
    
    // 对图片（或视频第一帧）进行取色
    console.log('正在分析壁纸颜色...', 'info')
    const colors = await extractColorsFromImage(colorSourceFile, 6)
    wallpaperColors.value = colors
    saveWallpaperColors(colors)
    
    // 上传原始文件（图片或视频）到后端
    const status = await uploadWallpaper(file)
    settings.value.theme.has_wallpaper = status.has_wallpaper
    wallpaperType.value = status.wallpaper_type
    settings.value.theme.wallpaper_blur = status.wallpaper_blur
    settings.value.theme.wallpaper_opacity = status.wallpaper_opacity
    wallpaperVersion.value = Date.now()
    emitWallpaperUpdated()
    
    // 自动应用第一个取色
    if (colors.length > 0) {
      settings.value.theme.primary_color = colors[0]
      applyCurrentTheme()
    }
    
    toast.show(`${isImage ? '图片' : '视频'}壁纸上传成功`, 'success')
  } catch (error) {
    console.error('上传壁纸失败:', error)
    toast.show(`上传壁纸失败: ${error instanceof Error ? error.message : '未知错误'}`, 'error')
  } finally {
    uploading.value = false
    extractingColors.value = false
    input.value = ''
  }
}

async function handleDeleteWallpaper() {
  uploading.value = true
  try {
    await deleteWallpaper()
    settings.value.theme.has_wallpaper = false
    wallpaperVersion.value = Date.now()
    emitWallpaperUpdated()
    
    // 清除壁纸取色
    wallpaperColors.value = []
    clearWallpaperColors()
    
    toast.show('壁纸已删除', 'success')
  } catch {
    // 错误提示由全局拦截器处理
  } finally {
    uploading.value = false
  }
}

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

onMounted(() => {
  fetchSettings()
  // 加载 localStorage 中的壁纸颜色
  const savedColors = loadWallpaperColors()
  if (savedColors && savedColors.length > 0) {
    wallpaperColors.value = savedColors
  }
})
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

      <section class="setting-section theme-layout-section">
        <div class="section-text">
          <h3 class="section-heading">主题与壁纸</h3>
          <p class="section-desc">配置个性化背景壁纸，选择或自动提取界面主色彩</p>
        </div>

        <div class="theme-layout">
          <!-- 壁纸卡片 -->
          <div class="theme-card">
            <div class="card-header">
              <div class="card-title">
                <Icon icon="material-symbols:image-outline" width="20" height="20" />
                <span>界面壁纸</span>
              </div>
              <div class="card-actions">
                <button
                  class="action-btn-danger"
                  v-if="settings.theme.has_wallpaper"
                  :disabled="uploading"
                  @click="handleDeleteWallpaper"
                  title="删除壁纸"
                >
                  <Icon icon="material-symbols:delete-outline-rounded" width="16" height="16" />
                </button>
                <button
                  class="action-btn"
                  :disabled="uploading"
                  @click="wallpaperInputRef?.click()"
                >
                  <Icon icon="material-symbols:upload-rounded" width="16" height="16" />
                  {{ settings.theme.has_wallpaper ? '更换' : '上传' }}
                </button>
              </div>
            </div>

            <div class="wallpaper-preview" :class="{ empty: !settings.theme.has_wallpaper }">
              <!-- 图片壁纸预览 -->
              <img
                v-if="settings.theme.has_wallpaper && wallpaperType === 'image'"
                :src="getCurrentWallpaperImageUrl()"
                alt="当前壁纸"
                class="wallpaper-preview-img"
              />
              
              <!-- 视频壁纸预览 -->
              <video
                v-else-if="settings.theme.has_wallpaper && wallpaperType === 'video'"
                :src="getCurrentWallpaperImageUrl()"
                class="wallpaper-preview-video"
                autoplay
                loop
                muted
                playsinline
                disablePictureInPicture
              />
              
              <!-- 无壁纸提示 -->
              <div v-else class="wallpaper-empty">
                <Icon icon="material-symbols:wallpaper-rounded" width="32" height="32" style="opacity:0.4; margin-bottom: 8px" />
                <span>当前未设置壁纸</span>
              </div>
            </div>

            <div class="slider-grid" :class="{ 'disabled': !settings.theme.has_wallpaper }">
              <label class="slider-row">
                <span class="slider-label">模糊强度</span>
                <input
                  v-model.number="settings.theme.wallpaper_blur"
                  type="range" min="0" max="20" step="1"
                  :disabled="!settings.theme.has_wallpaper"
                />
                <span class="slider-val">{{ settings.theme.wallpaper_blur }}px</span>
              </label>

              <label class="slider-row">
                <span class="slider-label">遮罩透明度</span>
                <input
                  v-model.number="settings.theme.wallpaper_opacity"
                  type="range" min="0" max="1" step="0.05"
                  :disabled="!settings.theme.has_wallpaper"
                />
                <span class="slider-val">{{ Math.round(settings.theme.wallpaper_opacity * 100) }}%</span>
              </label>
            </div>
            
            <input
              ref="wallpaperInputRef"
              type="file"
              class="wallpaper-file-input"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/webm"
              @change="handleWallpaperFileChange"
            />
          </div>

          <!-- 主题色卡片 -->
          <div class="theme-card">
            <div class="card-header">
              <div class="card-title">
                <Icon icon="material-symbols:palette-outline" width="20" height="20" />
                <span>主题色彩</span>
              </div>
            </div>

            <div class="colors-scroll-area">
              <!-- 壁纸取色 -->
              <div class="color-group" v-if="wallpaperColors.length > 0">
                <div class="color-group-title">
                  <span>壁纸取色</span>
                  <span v-if="colorSource === 'wallpaper'" class="active-badge">使用中</span>
                </div>
                <div class="color-presets">
                  <button
                    v-for="(hex, idx) in wallpaperColors"
                    :key="hex"
                    class="color-swatch ring-swatch"
                    :style="{ background: hex }"
                    :title="`壁纸取色 ${idx + 1}`"
                    :class="{ active: settings.theme.primary_color === hex }"
                    @click="selectColor(hex)"
                  >
                    <Icon v-if="settings.theme.primary_color === hex" icon="material-symbols:check-rounded" width="18" height="18" style="color: #fff" />
                  </button>
                </div>
              </div>

              <!-- 预设颜色 -->
              <div class="color-group">
                <div class="color-group-title">
                  <span>推荐预设</span>
                  <span v-if="colorSource === 'preset'" class="active-badge">使用中</span>
                </div>
                <div class="color-presets">
                  <button
                    v-for="c in presetColors"
                    :key="c.hex"
                    class="color-swatch ring-swatch"
                    :style="{ background: c.hex }"
                    :title="c.label"
                    :class="{ active: settings.theme.primary_color === c.hex }"
                    @click="selectColor(c.hex)"
                  >
                    <Icon v-if="settings.theme.primary_color === c.hex" icon="material-symbols:check-rounded" width="18" height="18" style="color: #fff" />
                  </button>
                </div>
              </div>

              <!-- 自定义颜色 -->
              <div class="color-group">
                <div class="color-group-title">
                  <span>自定义颜色</span>
                  <span v-if="colorSource === 'custom'" class="active-badge">使用中</span>
                </div>
                <div class="custom-color-inline">
                  <input
                    type="color"
                    class="color-picker"
                    :value="settings.theme.primary_color"
                    @input="(e) => selectColor((e.target as HTMLInputElement).value)"
                  />
                  <span class="color-hex-val">{{ settings.theme.primary_color.toUpperCase() }}</span>
                </div>
              </div>
            </div>
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

/* ==== 新壁纸与主题卡片布局 ==== */
.theme-layout-section {
  padding: 1.5rem;
}
.theme-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}
@media (min-width: 800px) {
  .theme-layout {
    grid-template-columns: 1fr 1fr;
  }
}
.theme-card {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  background: var(--md-sys-color-surface);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  padding: 1.25rem;
  box-shadow: rgba(0, 0, 0, 0.02) 0px 4px 18px;
}
html[data-theme='dark'] .theme-card {
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: rgba(0, 0, 0, 0.2) 0px 4px 18px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}
.action-btn {
  display: flex; align-items: center; gap: 0.375rem;
  height: 2rem; padding: 0 0.75rem; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px;
  background: transparent; color: var(--md-sys-color-on-surface);
  font-size: 0.8125rem; font-weight: 500; cursor: pointer; transition: background 0.15s;
}
html[data-theme='dark'] .action-btn { border-color: rgba(255,255,255,0.15); }
.action-btn:hover:not(:disabled) { background: var(--md-sys-color-surface-container-highest); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.action-btn-danger {
  display: flex; align-items: center; justify-content: center;
  width: 2rem; height: 2rem; border: none; border-radius: 8px;
  background: var(--md-sys-color-error-container); color: var(--md-sys-color-on-error-container);
  cursor: pointer; transition: filter 0.15s;
}
.action-btn-danger:hover:not(:disabled) { filter: brightness(0.9); }
.action-btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

.colors-scroll-area {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.color-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.color-group-title {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.8125rem; color: var(--md-sys-color-on-surface-variant); font-weight: 500;
}
.active-badge {
  padding: 0.125rem 0.375rem;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  border-radius: 4px;
  font-size: 0.6875rem;
  font-weight: 600;
}
.ring-swatch.active { outline: 2px solid var(--md-sys-color-primary); outline-offset: 2px; }

.custom-color-inline {
  display: flex; align-items: center; gap: 0.5rem;
}
/* ==== 旧样式保留区 ==== */
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
.color-picker {
  width: 44px; height: 44px; border-radius: 9999px; border: none; padding: 0; cursor: pointer; background: none;
}
.color-picker::-webkit-color-swatch-wrapper { padding: 0; }
.color-picker::-webkit-color-swatch { border-radius: 9999px; border: none; }
.color-hex-val {
  font-family: 'Inter', monospace; font-size: 0.875rem; color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container); padding: 0.25rem 0.75rem; border-radius: 0.5rem;
}
.wallpaper-file-input { display: none; }
.wallpaper-preview {
  border-radius: 1rem;
  overflow: hidden;
  min-height: 140px;
  background: var(--md-sys-color-surface-container);
  border: 1px solid var(--md-sys-color-outline-variant);
}
.wallpaper-preview.empty {
  display: flex;
  align-items: center;
  justify-content: center;
}
.wallpaper-preview-img {
  width: 100%;
  height: 180px;
  display: block;
  object-fit: cover;
}
.wallpaper-preview-video {
  width: 100%;
  height: 180px;
  display: block;
  object-fit: cover;
}
.wallpaper-empty {
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
}
.wallpaper-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.slider-grid {
  display: grid;
  gap: 0.75rem;
}
.slider-row {
  display: grid;
  grid-template-columns: minmax(70px, max-content) 1fr 46px;
  align-items: center;
  gap: 0.75rem;
}
@media (max-width: 500px) {
  .slider-row {
    grid-template-columns: 1fr 46px;
    gap: 0.5rem;
  }
  .slider-label {
    grid-column: 1 / -1;
    margin-bottom: -0.25rem;
  }
}
.slider-label {
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface);
}
.slider-val {
  text-align: right;
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant);
}
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
