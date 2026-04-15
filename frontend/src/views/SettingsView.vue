<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
import { Icon } from '@iconify/vue'

const route = useRoute()

const tabs = [
  { label: '主题', icon: 'material-symbols:palette-outline-rounded', to: '/settings/theme' },
  { label: '通用', icon: 'material-symbols:tune-rounded', to: '/settings/general' },
]
</script>

<template>
  <AppShell>
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
  gap: 2rem;
  align-items: flex-start;
}

/* 侧边选项卡 */
.settings-sidebar {
  width: 180px;
  flex-shrink: 0;
  position: sticky;
  top: 1rem;
}
.settings-sidebar-title {
  margin: 0 0 1rem 0.5rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--md-sys-color-on-surface);
}
.settings-tabs {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
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
  background: var(--md-sys-color-surface-container);
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
}

@media (max-width: 700px) {
  .settings-layout { flex-direction: column; }
  .settings-sidebar { width: 100%; position: static; }
  .settings-tabs { flex-direction: row; }
}
</style>
