<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
import { useI18n } from '../utils/i18n'
const route = useRoute()
const { t } = useI18n()

const tabs = [
  { labelKey: 'settings.tabs.theme', icon: 'material-symbols:format-paint-outline-rounded', to: '/settings/theme' },
  { labelKey: 'settings.tabs.general', icon: 'material-symbols:tune-rounded', to: '/settings/general' },
  { labelKey: 'settings.tabs.data', icon: 'material-symbols:storage-rounded', to: '/settings/data' },
]
</script>

<template>
  <AppShell noPadding>
    <div class="settings-layout">
      <!-- 设置侧边选项卡 -->
      <aside class="settings-sidebar">
        <h2 class="settings-sidebar-title">{{ t('settings.title') }}</h2>
        <nav class="settings-tabs">
          <router-link
            v-for="tab in tabs"
            :key="tab.to"
            :to="tab.to"
            class="settings-tab"
            :class="{ active: route.path === tab.to }"
          >
            <Icon :icon="tab.icon" width="20" height="20" />
            <span>{{ t(tab.labelKey) }}</span>
          </router-link>
        </nav>
      </aside>

      <!-- 子页面内容 -->
      <div class="settings-content">
        <router-view />
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.settings-layout {
  display: flex;
  align-items: stretch;
  /* 视口高度减去 top-bar 与移动端底栏，页面自身不滚动 */
  height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
  min-height: 0;
  overflow: hidden;
}

/* 侧边选项卡 */
.settings-sidebar {
  width: 250px;
  height: 100%;
  min-height: 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  overflow-y: auto;
  z-index: 5;
}

@media (max-width: 900px) {
  .settings-layout {
    flex-direction: column;
  }
  .settings-sidebar {
    width: 100%;
    height: auto;
    max-height: 160px;
    border-right: none;
    border-bottom: 1px solid var(--md-sys-color-outline-variant);
  }
}

.settings-sidebar-title {
  margin: 1.5rem 1.5rem 0.5rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--md-sys-color-on-surface);
}

.settings-tabs {
  display: flex;
  flex-direction: column;
  padding: 0.5rem 0.75rem;
  gap: 0.25rem;
}

@media (max-width: 900px) {
  .settings-tabs {
    flex-direction: row;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 0 1rem 1rem;
    -webkit-overflow-scrolling: touch;
  }
  
  .settings-tabs::-webkit-scrollbar {
    display: none;
  }
}

.settings-tab {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 9999px;
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}

.settings-tab:hover {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
}

.settings-tab.active {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  font-weight: 600;
}

/* 内容区 */
.settings-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  padding: 2rem;
}

@media (max-width: 900px) {
  .settings-content {
    padding: 1.5rem 1rem;
  }
}
</style>
