<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
const route = useRoute()

const tabs = [
  { label: '主题', icon: 'material-symbols:format-paint-outline-rounded', to: '/settings/theme' },
  { label: '通用', icon: 'material-symbols:tune-rounded', to: '/settings/general' },
  { label: '数据', icon: 'material-symbols:storage-rounded', to: '/settings/data' },
]
</script>

<template>
  <AppShell noPadding>
    <div class="settings-layout">
      <!-- 设置侧边选项卡 -->
      <aside class="settings-sidebar">
        <h2 class="settings-sidebar-title">设置</h2>
        <nav class="settings-tabs">
          <router-link
            v-for="tab in tabs"
            :key="tab.to"
            :to="tab.to"
            class="settings-tab"
            :class="{ active: route.path === tab.to }"
          >
            <Icon :icon="tab.icon" width="20" height="20" />
            <span>{{ tab.label }}</span>
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
  min-height: calc(100vh - 64px); /* 视口高度减去 top-bar 高度，保持内容区撑满 */
}

/* 侧边选项卡 */
.settings-sidebar {
  width: 250px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 70%, transparent);
  backdrop-filter: blur(12px);
  overflow-y: auto;
  position: sticky;
  top: 64px; /* 设置吸顶，保持在 top-bar 下方 */
  height: calc(100vh - 64px); /* 视口高度减去 top-bar 高度 */
  z-index: 5;
}

@media (max-width: 900px) {
  .settings-layout {
    flex-direction: column;
    min-height: auto;
  }
  .settings-sidebar {
    width: 100%;
    position: sticky;
    top: 64px;
    height: auto;
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
    flex-wrap: wrap;
    padding: 0 1rem 1rem;
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
  padding: 2rem;
}

@media (max-width: 900px) {
  .settings-content {
    padding: 1.5rem 1rem;
  }
}
</style>
