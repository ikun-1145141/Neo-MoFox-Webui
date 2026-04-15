<script setup lang="ts">
import { onMounted } from 'vue'
import ToastManager from './components/common/ToastManager.vue'
import { applyMd3Theme } from './utils/md3theme'

// 应用启动时加载默认主题（后端返回后会覆盖）
onMounted(() => {
  const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  applyMd3Theme('#0058bd', isDark)
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    applyMd3Theme('#0058bd', e.matches)
    document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light')
  })
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

