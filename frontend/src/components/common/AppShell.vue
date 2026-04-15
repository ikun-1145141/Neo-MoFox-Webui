<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Icon } from '@iconify/vue'
import { logout } from '../../api/modules/auth'

const router = useRouter()
const route = useRoute()

const navItems = [
  { label: '主页', icon: 'material-symbols:home-outline-rounded', name: 'home', path: '/' },
  { label: '设置', icon: 'material-symbols:settings-outline-rounded', name: 'settings-theme', path: '/settings' },
]

const drawerOpen = ref(false)

const isActive = (path: string) => route.path === path || route.path.startsWith(path + '/')

async function handleLogout() {
  try {
    await logout()
  } finally {
    sessionStorage.removeItem('neo_token')
    router.push({ name: 'login' })
  }
}
</script>

<template>
  <div class="layout">
    <!-- 侧边导航栏 (Navigation Drawer) -->
    <aside class="nav-drawer" :class="{ open: drawerOpen }">
      <div class="drawer-header">
        <div class="drawer-brand">
          <Icon icon="material-symbols:robot-2-outline-rounded" width="24" height="24" />
          <span>Neo-MoFox</span>
        </div>
        <button class="drawer-close" @click="drawerOpen = false" aria-label="关闭导航">
          <Icon icon="material-symbols:menu-open-rounded" width="24" height="24" />
        </button>
      </div>

      <nav class="drawer-nav">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click="drawerOpen = false"
        >
          <Icon :icon="item.icon" width="22" height="22" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="drawer-footer">
        <button class="nav-item nav-logout" @click="handleLogout">
          <Icon icon="material-symbols:logout-rounded" width="22" height="22" />
          <span>退出登录</span>
        </button>
      </div>
    </aside>

    <!-- 遮罩层（移动端） -->
    <div v-if="drawerOpen" class="drawer-overlay" @click="drawerOpen = false" />

    <!-- 主体内容区 -->
    <main class="main-content">
      <!-- 顶栏 -->
      <header class="top-bar">
        <button class="menu-btn" @click="drawerOpen = !drawerOpen" aria-label="打开菜单">
          <Icon icon="material-symbols:menu-rounded" width="24" height="24" />
        </button>
        <h2 class="page-title">
          {{ route.meta?.title ?? 'Neo-MoFox WebUI' }}
        </h2>
        <div class="top-bar-actions">
          <button class="icon-btn" @click="handleLogout" aria-label="退出登录">
            <Icon icon="material-symbols:logout-rounded" width="22" height="22" />
          </button>
        </div>
      </header>

      <!-- 页面内容插槽 -->
      <div class="page-slot">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
/* ====== 布局框架 ====== */
.layout {
  display: flex;
  min-height: 100dvh;
  background: var(--md-sys-color-surface);
}

/* ====== 侧边栏 ====== */
.nav-drawer {
  width: 260px;
  flex-shrink: 0;
  background: var(--md-sys-color-surface-container-low);
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  gap: 0.5rem;
  position: fixed;
  inset: 0;
  width: 260px;
  z-index: 200;
  transform: translateX(-100%);
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0px 20px 40px rgba(24, 28, 32, 0.06);
}
/* 桌面端始终显示 */
@media (min-width: 900px) {
  .nav-drawer {
    position: sticky;
    top: 0;
    height: 100dvh;
    transform: none;
    box-shadow: none;
  }
  .drawer-close { display: none; }
  .menu-btn { display: none; }
}
.nav-drawer.open {
  transform: translateX(0);
}
.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 199;
  background: rgba(0,0,0,0.3);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.5rem;
  margin-bottom: 1rem;
}
.drawer-brand {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface);
}
.drawer-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--md-sys-color-on-surface-variant);
  display: flex;
  align-items: center;
  padding: 0.25rem;
  border-radius: 0.5rem;
  transition: background 0.15s;
}
.drawer-close:hover { background: var(--md-sys-color-surface-container); }

.drawer-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.75rem 1rem;
  border-radius: 9999px;
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
  transition: background 0.15s, color 0.15s;
  border: none;
  background: none;
  cursor: pointer;
  width: 100%;
  text-align: left;
}
.nav-item:hover {
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
}
.nav-item.active {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  font-weight: 600;
}
.drawer-footer {
  padding-top: 0.5rem;
  border-top: 1px solid transparent;
}
.nav-logout {
  color: var(--md-sys-color-error);
}
.nav-logout:hover {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

/* ====== 主内容区 ====== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.top-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: var(--md-sys-color-surface);
  position: sticky;
  top: 0;
  z-index: 10;
}

.menu-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--md-sys-color-on-surface);
  display: flex;
  align-items: center;
  padding: 0.375rem;
  border-radius: 9999px;
  transition: background 0.15s;
}
.menu-btn:hover { background: var(--md-sys-color-surface-container); }

.page-title {
  flex: 1;
  margin: 0;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--md-sys-color-on-surface);
}

.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--md-sys-color-on-surface-variant);
  display: flex;
  align-items: center;
  padding: 0.375rem;
  border-radius: 9999px;
  transition: background 0.15s, color 0.15s;
}
.icon-btn:hover {
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
}

.page-slot {
  flex: 1;
  padding: 1.5rem;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}
</style>
