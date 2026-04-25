<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import ToastManager from './components/common/ToastManager.vue'
import { applyMd3Theme } from './utils/md3theme'
import { getSettings } from './api/modules/settings'

type ThemeMode = 'auto' | 'light' | 'dark'

let mediaQuery: MediaQueryList | null = null
let currentThemeMode: ThemeMode = 'auto'
let currentPrimaryColor = '#0058bd'

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
  } catch {
    // 后端不可用时回退到默认主题
  } finally {
    applyThemeFromState()
  }
}

// 应用启动时同步设置并应用主题
onMounted(() => {
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  void syncSettingsAndApplyTheme()

  mediaQuery.addEventListener('change', handleSystemThemeChange)
})

onBeforeUnmount(() => {
  if (!mediaQuery) return
  mediaQuery.removeEventListener('change', handleSystemThemeChange)
})
</script>

<template>
  <RouterView />
  <ToastManager />
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
  background: var(--md-sys-color-surface, #f7f9ff);
  color: var(--md-sys-color-on-surface, #1b1b1f);
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

