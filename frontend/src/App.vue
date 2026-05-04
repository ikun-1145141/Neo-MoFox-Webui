<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watchEffect } from 'vue'
import ToastManager from './components/common/ToastManager.vue'
import DialogManager from './components/common/DialogManager.vue'
import { applyMd3Theme } from './utils/md3theme'
import { getSettings } from './api/modules/settings'
import { getWallpaperStatus, getWallpaperImageUrl } from './api/modules/wallpaper'
import { setLocale } from './utils/i18n'

type ThemeMode = 'auto' | 'light' | 'dark'

let mediaQuery: MediaQueryList | null = null
let currentThemeMode: ThemeMode = 'auto'
let currentPrimaryColor = '#0058bd'
const hasWallpaper = ref(false)
const wallpaperType = ref<'image' | 'video' | 'none'>('none')
const wallpaperBlur = ref(0)
const wallpaperOpacity = ref(0.5)
const wallpaperVersion = ref(Date.now())

const wallpaperImageStyle = computed(() => {
  if (!hasWallpaper.value) {
    return {}
  }

  return {
    backgroundImage: `url('${getWallpaperImageUrl(wallpaperVersion.value)}')`,
    filter: `blur(${wallpaperBlur.value}px)`,
  }
})

watchEffect(() => {
  document.documentElement.style.setProperty('--wallpaper-mask-opacity', String(wallpaperOpacity.value))
})

function handleSystemThemeChange() {
  applyThemeFromState()
}

function applyThemeFromState() {
  const prefersDark = mediaQuery?.matches ?? window.matchMedia('(prefers-color-scheme: dark)').matches
  const isDark = currentThemeMode === 'dark' || (currentThemeMode === 'auto' && prefersDark)
  applyMd3Theme(currentPrimaryColor, isDark)
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
}

async function syncSettingsAndApplyTheme() {
  try {
    const settings = await getSettings()
    currentThemeMode = settings.theme.mode
    currentPrimaryColor = settings.theme.primary_color
    setLocale(settings.ui.language)
  } catch {
    // 后端不可用时回退到默认主题
  } finally {
    applyThemeFromState()
  }
}

async function syncWallpaperStatus(forceImageUpdate = false) {
  try {
    const status = await getWallpaperStatus()
    hasWallpaper.value = status.has_wallpaper
    wallpaperType.value = status.wallpaper_type
    wallpaperBlur.value = status.wallpaper_blur
    wallpaperOpacity.value = status.wallpaper_opacity
    if (forceImageUpdate) wallpaperVersion.value = Date.now()
  } catch {
    hasWallpaper.value = false
    wallpaperType.value = 'none'
  }
}

function handleWallpaperUpdated(e: Event) {
  if (e instanceof CustomEvent && e.detail) {
    if (e.detail.has_wallpaper !== undefined) hasWallpaper.value = e.detail.has_wallpaper
    if (e.detail.wallpaper_blur !== undefined) wallpaperBlur.value = e.detail.wallpaper_blur
    if (e.detail.wallpaper_opacity !== undefined) wallpaperOpacity.value = e.detail.wallpaper_opacity
    if (e.detail.force) wallpaperVersion.value = Date.now()
  } else {
    void syncWallpaperStatus(true)
  }
}

// 应用启动时同步设置并应用主题
onMounted(() => {
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  void syncSettingsAndApplyTheme()
  void syncWallpaperStatus(true)

  mediaQuery.addEventListener('change', handleSystemThemeChange)
  window.addEventListener('wallpaper-updated', handleWallpaperUpdated as EventListener)
})

onBeforeUnmount(() => {
  if (!mediaQuery) return
  mediaQuery.removeEventListener('change', handleSystemThemeChange)
  window.removeEventListener('wallpaper-updated', handleWallpaperUpdated as EventListener)
})
</script>

<template>
  <div v-if="hasWallpaper" class="wallpaper-layer" aria-hidden="true">
    <!-- 图片壁纸 -->
    <div 
      v-if="wallpaperType === 'image'" 
      class="wallpaper-image" 
      :style="wallpaperImageStyle" 
    />
    
    <!-- 视频壁纸 -->
    <video
      v-else-if="wallpaperType === 'video'"
      class="wallpaper-video"
      :style="{ filter: `blur(${wallpaperBlur}px)` }"
      :src="getWallpaperImageUrl(wallpaperVersion)"
      autoplay
      loop
      muted
      playsinline
    />
  </div>

  <div class="app-content-layer">
    <RouterView />
    <ToastManager />
    <DialogManager />
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

*, *::before, *::after {
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}

html {
  background: transparent;
  color: var(--md-sys-color-on-surface, #1b1b1f);
}

#app {
  min-height: 100dvh;
}

.wallpaper-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}

.wallpaper-image {
  position: absolute;
  inset: -24px;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transform: scale(1.04);
}

.wallpaper-video {
  position: absolute;
  inset: -24px;
  width: calc(100% + 48px);
  height: calc(100% + 48px);
  object-fit: cover;
  transform: scale(1.04);
}

.app-content-layer {
  position: relative;
  z-index: 1;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--md-sys-color-outline-variant, #c4c7cc);
  border-radius: 9999px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--md-sys-color-outline, #74777f);
}
</style>

