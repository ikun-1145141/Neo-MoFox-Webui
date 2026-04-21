<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
import { Icon } from '@iconify/vue'

const route = useRoute()

const tabs = [
  { label: '主题', icon: 'material-symbols:palette-outline-rounded', to: '/settings/theme' },
  { label: '通用', icon: 'material-symbols:tune-rounded', to: '/settings/general' },
  { label: '数据', icon: 'material-symbols:database-outline-rounded', to: '/settings/data' },
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
  align-items: flex-start;
  min-height: 100%;
}

/* 侧边选项卡 */
.settings-sidebar {
  width: 220px;
  position: fixed;
  left: 80px; /* 紧贴左侧 nav-rail (在桌面端) */
  top: 72px;  /* 避开顶栏，top-bar 高度大约 72px */
  bottom: 0;
  padding: 1.5rem 1rem;
  background: var(--md-sys-color-surface-container-lowest);
  border-right: 1px solid var(--md-sys-color-outline-variant);
  overflow-y: auto;
  z-index: 5;
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
  margin-left: 180px; /* 如果用固定的话给点 margin */
}

@media (min-width: 1300px) {
  .settings-content {
    margin-left: auto;
  }
}

@media (max-width: 900px) {
  .settings-sidebar { left: 0; top: 60px; /* 移动端 nav-rail 隐藏或变形，重新适配 */ }
}

@media (max-width: 700px) {
  .settings-layout { flex-direction: column; }
  .settings-sidebar { 
    width: 100%; 
    position: static; 
    border-right: none;
    border-bottom: 1px solid var(--md-sys-color-outline-variant);
    padding: 1rem;
  }
  .settings-tabs { flex-direction: row; flex-wrap: wrap; }
  .settings-content { padding-left: 0; }
}
</style>
