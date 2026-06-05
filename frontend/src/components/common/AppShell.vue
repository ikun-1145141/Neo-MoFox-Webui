<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { logout } from '../../api/modules/auth'
import { restartBot, shutdownBot } from '../../api/modules/system'
import { setIsRestarting, startHealthCheck } from '../../api/base'
import { useDialogStore } from '../../utils/dialog'
import { useToastStore } from '../../utils/toast'
import { useI18n } from '../../utils/i18n'

const showSystemMenu = ref(false)

const props = defineProps<{
  noPadding?: boolean
}>()

const router = useRouter()
const route = useRoute()
const dialogStore = useDialogStore()
const toastStore = useToastStore()
const { t } = useI18n()

const navItems = [
  { labelKey: 'app.nav.home', icon: 'material-symbols:home-outline-rounded', name: 'home', path: '/' },
  { labelKey: 'app.nav.config', icon: 'material-symbols:tune-rounded', name: 'config', path: '/config' },
  { labelKey: 'app.nav.plugins', icon: 'material-symbols:extension-outline-rounded', name: 'plugins', path: '/plugins' },
  { labelKey: 'app.nav.config-plugins', icon: 'material-symbols:settings-outline-rounded', name: 'config-plugins', path: '/config/plugins' },
  { labelKey: 'app.nav.llmMetrics', icon: 'material-symbols:bar-chart-rounded', name: 'llm-metrics', path: '/llm-metrics' },
  { labelKey: 'app.nav.settings', icon: 'material-symbols:setting-outline-rounded', name: 'settings-theme', path: '/settings' },
]

const pageTitle = computed(() => {
  const routeName = typeof route.name === 'string' ? route.name : ''
  return routeName ? t(`routes.${routeName}`) : 'Neo-MoFox WebUI'
})

const isActive = (path: string) => {
  // 精确匹配
  if (route.path === path) return true
  
  // 检查是否是子路径
  if (!route.path.startsWith(path + '/')) return false
  
  // 如果是子路径，检查是否有其他更具体的导航项匹配当前路由
  const hasMoreSpecificMatch = navItems.some(item => 
    item.path !== path && 
    item.path.startsWith(path) && 
    (route.path === item.path || route.path.startsWith(item.path + '/'))
  )
  
  // 如果有更具体的匹配项，当前项不激活
  return !hasMoreSpecificMatch
}

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

async function handleRestart() {
  const result = await dialogStore.confirm(
    t('app.dialogs.restartMessage'),
    t('app.dialogs.restartTitle'),
    t('app.dialogs.restartConfirm'),
    t('app.dialogs.cancel')
  )
  
  if (result) {
    await performRestart()
  }
}

async function performRestart() {
  // 显示重启进行中对话框（无按钮，不可关闭）
  const restartDialogId = dialogStore.show({
    title: t('app.dialogs.restartingTitle'),
    message: t('app.dialogs.restartingMessage'),
    buttons: [],
  })

  try {
    // 先调用重启 API（在设置重启状态之前）
    await restartBot()

    // 重启指令发送成功后，设置重启状态，阻断所有非健康检查请求
    setIsRestarting(true)

    // 等待 2 秒让 Bot 真正开始重启，避免过早的健康检查返回成功
    await new Promise(resolve => setTimeout(resolve, 2000))

    // 开始健康检查轮询
    startHealthCheck(() => {
      // 系统恢复健康
      dialogStore.close(restartDialogId)
      setIsRestarting(false)
      toastStore.show(t('app.toast.restartSuccess'), 'success')
      
      // 刷新页面以获取最新状态
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    })
  } catch (error) {
    console.error('重启失败:', error)
    setIsRestarting(false)
    dialogStore.close(restartDialogId)
    toastStore.show(t('app.toast.restartFailed'), 'error')
  }
}

async function handleShutdown() {
  const result = await dialogStore.confirm(
    t('app.dialogs.shutdownMessage'),
    t('app.dialogs.shutdownTitle'),
    t('app.dialogs.shutdownConfirm'),
    t('app.dialogs.cancel')
  )
  
  if (result) {
    await performShutdown()
  }
}

async function performShutdown() {
  try {
    await shutdownBot()
    toastStore.show(t('app.toast.shutdownSent'), 'success')
    
    // 延迟跳转到登录页
    setTimeout(() => {
      sessionStorage.removeItem('neo_token')
      router.push({ name: 'login' })
    }, 2000)
  } catch (error) {
    toastStore.show(t('app.toast.shutdownFailed'), 'error')
  }
}

function toggleSystemMenu() {
  showSystemMenu.value = !showSystemMenu.value
}

function closeSystemMenu() {
  showSystemMenu.value = false
}

async function handleSystemAction(action: 'restart' | 'shutdown' | 'logout') {
  closeSystemMenu()
  
  switch (action) {
    case 'restart':
      await handleRestart()
      break
    case 'shutdown':
      await handleShutdown()
      break
    case 'logout':
      await handleLogout()
      break
  }
}
</script>

<template>
  <div class="layout">
    <!-- M3 Navigation Rail (桌面端侧边导航栏) -->
    <aside class="nav-rail">
      <!-- Logo / 品牌区 -->
      <div class="rail-header">
        <button class="rail-fab" @click="router.push('/')" :aria-label="t('app.aria.goHome')">
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
          :aria-label="t(item.labelKey)"
        >
          <div class="rail-item-indicator"></div>
          <Icon :icon="item.icon" width="24" height="24" class="rail-item-icon" />
          <span class="rail-item-label">{{ t(item.labelKey) }}</span>
        </router-link>
      </nav>

      <!-- 底部操作区 -->
      <div class="rail-footer">
        <button 
          class="rail-item rail-restart" 
          @click="handleRestart"
          :aria-label="t('app.aria.restartSystem')"
          :title="t('app.actions.restart') + ' Bot'"
        >
          <div class="rail-item-indicator"></div>
          <Icon icon="material-symbols:restart-alt-rounded" width="24" height="24" class="rail-item-icon" />
          <span class="rail-item-label">{{ t('app.actions.restart') }}</span>
        </button>
        
        <button 
          class="rail-item rail-shutdown" 
          @click="handleShutdown"
          :aria-label="t('app.aria.shutdownSystem')"
          :title="t('app.actions.shutdown') + ' Bot'"
        >
          <div class="rail-item-indicator"></div>
          <Icon icon="material-symbols:power-settings-new-rounded" width="24" height="24" class="rail-item-icon" />
          <span class="rail-item-label">{{ t('app.actions.shutdown') }}</span>
        </button>
        
        <button 
          class="rail-item rail-logout" 
          @click="handleLogout"
          :aria-label="t('app.aria.logout')"
        >
          <div class="rail-item-indicator"></div>
          <Icon icon="material-symbols:logout-rounded" width="24" height="24" class="rail-item-icon" />
          <span class="rail-item-label">{{ t('app.actions.logout') }}</span>
        </button>
      </div>
    </aside>

    <!-- 主体内容区 -->
    <main class="main-content">
      <!-- 顶栏 -->
      <header class="top-bar">
        <h2 class="page-title">
          <Icon
            v-if="typeof route.meta?.icon === 'string'"
            :icon="route.meta.icon"
            width="20"
            height="20"
            class="page-title-icon"
          />
          {{ pageTitle }}
        </h2>
        <div class="top-bar-actions">
          <button class="icon-btn" @click="handleLogout" :aria-label="t('app.aria.logout')">
            <Icon icon="material-symbols:logout-rounded" width="22" height="22" />
          </button>
        </div>
      </header>

      <!-- 页面内容插槽 -->
      <div class="page-slot" :class="{ 'no-padding': noPadding }">
        <slot />
      </div>
    </main>

    <!-- M3 Bottom Navigation Bar (移动端底部导航栏) -->
    <nav class="bottom-nav" :aria-label="t('app.aria.openMenu')">
      <div class="bottom-nav-scroll">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="item.path"
          class="bottom-nav-item"
          :class="{ active: isActive(item.path) }"
          :aria-label="t(item.labelKey)"
        >
          <span class="bottom-nav-indicator">
            <Icon :icon="item.icon" width="24" height="24" class="bottom-nav-icon" />
          </span>
          <span class="bottom-nav-label">{{ t(item.labelKey) }}</span>
        </router-link>
        
        <!-- 系统操作按钮 -->
        <div class="bottom-nav-item system-menu-wrapper">
          <button
            class="system-menu-button"
            @click="toggleSystemMenu"
            :aria-label="t('app.aria.systemActions')"
          >
            <span class="bottom-nav-indicator">
              <Icon icon="material-symbols:more-vert-rounded" width="24" height="24" class="bottom-nav-icon" />
            </span>
            <span class="bottom-nav-label">{{ t('app.actions.system') }}</span>
          </button>
          
          <!-- 下拉菜单 -->
          <Transition name="menu-fade">
            <div v-if="showSystemMenu" class="system-menu" @click.stop>
              <div class="system-menu-backdrop" @click="closeSystemMenu"></div>
              <div class="system-menu-content">
                <button
                  class="system-menu-item restart"
                  @click="handleSystemAction('restart')"
                >
                  <Icon icon="material-symbols:restart-alt-rounded" width="20" height="20" />
                  <span>{{ t('app.actions.restart') }}</span>
                </button>
                <button
                  class="system-menu-item shutdown"
                  @click="handleSystemAction('shutdown')"
                >
                  <Icon icon="material-symbols:power-settings-new-rounded" width="20" height="20" />
                  <span>{{ t('app.actions.shutdown') }}</span>
                </button>
                <button
                  class="system-menu-item logout"
                  @click="handleSystemAction('logout')"
                >
                  <Icon icon="material-symbols:logout-rounded" width="20" height="20" />
                  <span>{{ t('app.actions.logout') }}</span>
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </nav>
  </div>
</template>

<style scoped>
/* ====== 布局框架 ====== */
.layout {
  display: flex;
  min-height: 100dvh;
  flex-direction: column;
}

/* 桌面端布局 */
@media (min-width: 900px) {
  .layout {
    flex-direction: row;
  }
}

/* ====== M3 Navigation Rail (桌面端侧边导航栏) ====== */
.nav-rail {
  width: 80px;
  flex-shrink: 0;
  background: var(--md-sys-color-surface-container-low);
  flex-direction: column;
  align-items: center;
  padding: 0.75rem 0;
  gap: 0.5rem;
  position: sticky;
  top: 0;
  height: 100dvh;
  z-index: 200;
  /* 移动端不显示侧边栏，使用底栏代替 */
  display: none;
}

/* 桌面端显示侧边栏 */
@media (min-width: 900px) {
  .nav-rail {
    display: flex;
  }
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

.rail-restart {
  color: var(--md-sys-color-primary);
}

.rail-restart:hover {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.rail-shutdown {
  color: var(--md-sys-color-tertiary);
}

.rail-shutdown:hover {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.rail-logout {
  color: var(--md-sys-color-error);
}

.rail-logout:hover {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

/* ====== 主内容区 ====== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: color-mix(in srgb, var(--md-sys-color-surface) calc(var(--wallpaper-mask-opacity, 0.88) * 100%), transparent);
  /* 为移动端底部导航栏留出空间（桌面端为 0） */
  padding-bottom: var(--app-bottom-nav-height, 80px);
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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}

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
  max-width: 100%;
  width: 100%;
  margin: 0 auto;
  /* overflow-x: hidden; removed to let sticky to work */
}

@media (max-width: 640px) {
  .page-slot {
    padding: 1rem;
  }
}

.page-slot.no-padding {
  padding: 0;
  max-width: none;
  margin: 0;
  display: flex;
  flex-direction: column;
}

/* ====== M3 Bottom Navigation Bar (移动端底栏) ====== */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--app-bottom-nav-height, 80px);
  background: var(--md-sys-color-surface-container);
  border-top: 1px solid var(--md-sys-color-outline-variant);
  z-index: 150;
  padding-bottom: env(safe-area-inset-bottom, 0);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.08);
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
}

/* 关键：min-width: max-content 让滚动容器至少能容纳所有内容
   width: 100% 让其在内容较少时填满外部容器
   两者结合：内容少时按钮均匀分布充满，内容多时自动触发横向滚动 */
.bottom-nav-scroll {
  display: flex;
  align-items: center;
  justify-content: space-around;
  width: 100%;
  min-width: max-content;
  height: 100%;
  padding: 0 0.5rem;
  gap: 0.25rem;
  box-sizing: border-box;
}

/* 桌面端隐藏底栏 */
@media (min-width: 900px) {
  .bottom-nav {
    display: none;
  }
}

/* 默认状态：可增长不可收缩，让按钮均匀分布 */
.bottom-nav-item {
  flex: 1 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  text-decoration: none;
  color: var(--md-sys-color-on-surface-variant);
  padding: 0.5rem 0.5rem;
  min-width: 72px;
  max-width: 140px;
  position: relative;
  transition: color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
}

/* 中等屏幕（如平板）：按钮更宽松，更充满底栏 */
@media (min-width: 600px) and (max-width: 899px) {
  .bottom-nav-item {
    min-width: 96px;
    max-width: 180px;
    padding: 0.5rem 0.75rem;
  }
  .bottom-nav-scroll {
    gap: 0.5rem;
    padding: 0 1rem;
  }
}

/* 小屏幕（窄手机）：紧凑显示 */
@media (max-width: 360px) {
  .bottom-nav-item {
    min-width: 64px;
    padding: 0.5rem 0.25rem;
  }
}

.bottom-nav-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 32px;
  border-radius: 16px;
  transition: background 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.bottom-nav-item.active .bottom-nav-indicator {
  background: var(--md-sys-color-secondary-container);
}

.bottom-nav-item.active {
  color: var(--md-sys-color-on-secondary-container);
}

.bottom-nav-icon {
  transition: transform 0.2s;
}

.bottom-nav-item:active .bottom-nav-icon {
  transform: scale(0.92);
}

.bottom-nav-label {
  font-size: 0.6875rem;
  font-weight: 500;
  text-align: center;
  line-height: 1.2;
  letter-spacing: 0.02em;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bottom-nav-item.active .bottom-nav-label {
  font-weight: 600;
}

/* ====== 系统菜单 ====== */
.system-menu-wrapper {
  position: relative;
  /* 由内部 button 处理 padding，避免重复 */
  padding: 0 !important;
}

.system-menu-button {
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  color: inherit;
  font: inherit;
  padding: 0.5rem 0.5rem;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  transition: color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.system-menu-button:hover .bottom-nav-indicator {
  background: var(--md-sys-color-surface-container-high);
}

.system-menu {
  position: fixed;
  inset: 0;
  z-index: 200;
}

.system-menu-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}

.system-menu-content {
  position: absolute;
  bottom: calc(var(--app-bottom-nav-height, 80px) + 0.5rem);
  right: 0.5rem;
  background: var(--md-sys-color-surface-container-high);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  min-width: 160px;
}

.system-menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.875rem 1rem;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--md-sys-color-on-surface);
  font-size: 0.875rem;
  font-weight: 500;
  text-align: left;
  transition: background 0.15s;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.system-menu-item:last-child {
  border-bottom: none;
}

.system-menu-item:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.system-menu-item:active {
  background: var(--md-sys-color-surface-container);
}

.system-menu-item.restart {
  color: var(--md-sys-color-primary);
}

.system-menu-item.shutdown {
  color: var(--md-sys-color-tertiary);
}

.system-menu-item.logout {
  color: var(--md-sys-color-error);
}

/* 菜单动画 */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.2s ease;
}

.menu-fade-enter-active .system-menu-content,
.menu-fade-leave-active .system-menu-content {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
}

.menu-fade-enter-from .system-menu-content,
.menu-fade-leave-to .system-menu-content {
  transform: translateY(8px);
  opacity: 0;
}

/* 隐藏滚动条但保持滚动功能 */
.bottom-nav::-webkit-scrollbar {
  display: none;
}

.bottom-nav {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
