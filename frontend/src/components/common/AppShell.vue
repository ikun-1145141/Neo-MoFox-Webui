<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { logout } from '../../api/modules/auth'

const router = useRouter()
const route = useRoute()

const navItems = [
  { label: '主页', icon: 'material-symbols:home-outline-rounded', name: 'home', path: '/' },
  { label: '设置', icon: 'material-symbols:setting-outline-rounded', name: 'settings-theme', path: '/settings' },
]

const drawerOpen = ref(false)
const railMode = ref(false) // Rail 模式：仅显示图标

const isActive = (path: string) => route.path === path || route.path.startsWith(path + '/')

async function handleLogout() {
  try {
    await logout()
  } catch {
    // 后端不可用时也允许前端本地退出，避免未捕获异常影响页面。
  } finally {
    sessionStorage.removeItem('neo_token')
    router.push({ name: 'login' })
  }
}
</script>

<template>
  <div class="layout">
    <!-- M3 Navigation Rail (侧边导航栏) -->
    <aside class="nav-rail" :class="{ open: drawerOpen, rail: railMode }">
      <!-- Logo / 品牌区 -->
      <div class="rail-header">
        <button class="rail-fab" @click="router.push('/')" aria-label="导航到主页">
          <Icon icon="material-symbols:robot-2-outline-rounded" width="28" height="28" />
        </button>
      </div>

      <!-- 导航项区域 -->
      <nav class="rail-nav">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="item.path"
          class="rail-item"
          :class="{ active: isActive(item.path) }"
          @click="drawerOpen = false"
          :aria-label="item.label"
        >
          <div class="rail-item-indicator"></div>
          <Icon :icon="item.icon" width="24" height="24" class="rail-item-icon" />
          <span class="rail-item-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 底部操作区 -->
      <div class="rail-footer">
        <button 
          class="rail-item rail-logout" 
          @click="handleLogout"
          aria-label="退出登录"
        >
          <div class="rail-item-indicator"></div>
          <Icon icon="material-symbols:logout-rounded" width="24" height="24" class="rail-item-icon" />
          <span class="rail-item-label">退出</span>
        </button>
      </div>

      <!-- 移动端关闭按钮 -->
      <button class="rail-close-mobile" @click="drawerOpen = false" aria-label="关闭导航">
        <Icon icon="material-symbols:close-rounded" width="24" height="24" />
      </button>
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
          <Icon
            v-if="typeof route.meta?.icon === 'string'"
            :icon="route.meta.icon"
            width="20"
            height="20"
            class="page-title-icon"
          />
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

/* ====== M3 Navigation Rail (仿 Material Design 3 官网) ====== */
.nav-rail {
  width: 80px;
  flex-shrink: 0;
  background: var(--md-sys-color-surface-container-low);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem 0;
  gap: 0.5rem;
  position: fixed;
  inset: 0;
  z-index: 200;
  transform: translateX(-100%);
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1), width 0.28s;
  box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.15);
}

/* 桌面端始终显示 */
@media (min-width: 900px) {
  .nav-rail {
    position: sticky;
    top: 0;
    height: 100dvh;
    transform: none;
    box-shadow: none;
  }
  .menu-btn { display: none; }
  .rail-close-mobile { display: none !important; }
}

/* 移动端打开状态 */
.nav-rail.open {
  transform: translateX(0);
}

.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 199;
  background: rgba(0, 0, 0, 0.4);
}

/* ====== Rail 头部 - FAB 样式 Logo ====== */
.rail-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 0.5rem;
  margin-bottom: 0.5rem;
}

.rail-fab {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: var(--md-sys-color-surface-container-high);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--md-sys-color-primary);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}

.rail-fab:hover {
  background: var(--md-sys-color-primary-container);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transform: scale(1.02);
}

.rail-fab:active {
  transform: scale(0.98);
}

/* ====== Rail 导航项区域 ====== */
.rail-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0 0.5rem;
  overflow-y: auto;
}

.rail-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  width: 100%;
  min-height: 56px;
  padding: 0.5rem 0.75rem;
  border-radius: 16px;
  text-decoration: none;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--md-sys-color-on-surface-variant);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.rail-item:hover {
  background: var(--md-sys-color-surface-container-highest);
}

/* Active 状态指示器（左侧竖条） */
.rail-item-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 3px;
  height: 32px;
  background: var(--md-sys-color-primary);
  border-radius: 0 2px 2px 0;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: center;
}

.rail-item.active .rail-item-indicator {
  transform: translateY(-50%) scaleY(1);
}

.rail-item.active {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.rail-item-icon {
  transition: transform 0.2s;
}

.rail-item:hover .rail-item-icon {
  transform: scale(1.1);
}

.rail-item-label {
  font-size: 0.75rem;
  font-weight: 500;
  text-align: center;
  line-height: 1.2;
  letter-spacing: 0.01em;
}

/* ====== Rail 底部 ====== */
.rail-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.5rem 0;
  width: 100%;
  border-top: 1px solid var(--md-sys-color-outline-variant);
}

.rail-logout {
  color: var(--md-sys-color-error);
}

.rail-logout:hover {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

/* ====== 移动端关闭按钮 ====== */
.rail-close-mobile {
  display: none;
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--md-sys-color-surface-container-high);
  border: none;
  cursor: pointer;
  color: var(--md-sys-color-on-surface);
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.rail-close-mobile:hover {
  background: var(--md-sys-color-surface-container-highest);
}

@media (max-width: 899px) {
  .nav-rail.open .rail-close-mobile {
    display: flex;
  }
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
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--md-sys-color-on-surface);
}

.page-title-icon {
  color: var(--md-sys-color-primary);
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
