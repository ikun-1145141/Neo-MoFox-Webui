<script setup lang="ts">
/**
 * 插件 UI 页面视图。
 *
 * 路由 /plugin-ui 对应的顶层 View。
 * 采用左右布局：左侧侧边栏始终显示导航列表，右侧为内容区。
 * 通过 route.query.plugin 和 route.query.page 选择要渲染的插件页面。
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/common/AppShell.vue'
import PluginNavList from '../components/plugin-ui/PluginNavList.vue'
import PluginPageContainer from '../components/plugin-ui/PluginPageContainer.vue'
import { listPluginPages, getPageDetail, getPageSchema } from '../api/modules/plugin-ui'
import type { PageSummary, PageDetail, PageSchemaResponse } from '../api/types/plugin-ui'
import { createPluginUIVarStore, type PluginUIVarStore } from '../stores/plugin-ui-vars'
import { useI18n } from '../utils/i18n'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

/**
 * 移动端视口判定阈值（像素）。与 CSS 媒体查询保持一致。
 *
 * 必须与全局 AppShell 的桌面/移动断点（900px）以及 PluginNavList
 * 内部的 width:100% 断点（max-width:900px）对齐，否则会出现：
 * - 768-899px 区间 PluginUIView 认为是"桌面端"显示 PluginNavList，
 * - 但 PluginNavList 自身宽度变成 100% 把内容区挤压成 0px。
 */
const MOBILE_BREAKPOINT_PX = 899

// === 侧边栏状态 ===

/** 所有已注册的插件页面列表 */
const pages = ref<PageSummary[]>([])
/** 页面列表是否正在加载 */
const listLoading = ref(false)

// === 内容区状态 ===

/** 当前选中的页面详情 */
const currentDetail = ref<PageDetail | null>(null)
/** 当前页面的 schema */
const currentSchema = ref<PageSchemaResponse | null>(null)
/** 当前 schema 实际加载的 variant，用于断点切换时判断是否需要重拉 */
const currentVariant = ref<'desktop' | 'mobile' | null>(null)
/** 内容区是否正在加载 */
const contentLoading = ref(false)
/** 内容区错误信息 */
const contentError = ref<string | null>(null)
/** 是否为移动端 fallback 模式（请求 mobile 但走了 desktop schema） */
const isFallback = ref(false)
/** 是否为移动端视口（响应式，跟随 matchMedia 实时更新） */
const isMobile = ref(
  window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
)

/** 当前页面的变量池 Store */
const currentStore = ref<PluginUIVarStore | null>(null)

/** 移动端导航下拉框是否打开 */
const isMobileNavOpen = ref(false)

/** matchMedia 实例，用于添加/移除断点监听 */
const mediaQuery: MediaQueryList = window.matchMedia(
  `(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`,
)

/**
 * 媒体查询变化处理器。
 *
 * 视口跨越断点时更新 isMobile，并在当前已加载的 variant 与新 variant
 * 不匹配时重新拉取 schema（前提是该插件提供了对应 variant）。
 */
function handleMediaChange(event: MediaQueryListEvent): void {
  const nextIsMobile = event.matches
  if (nextIsMobile === isMobile.value) {
    return
  }
  isMobile.value = nextIsMobile

  // 切到桌面端时关闭可能残留的移动端下拉导航
  if (!nextIsMobile) {
    isMobileNavOpen.value = false
  }

  // 当前没有已加载页面则不需要重拉
  const detail = currentDetail.value
  if (!detail) {
    return
  }

  const desiredVariant: 'desktop' | 'mobile' = nextIsMobile ? 'mobile' : 'desktop'

  // 切回桌面端时，强制重新加载内容，确保从可能的 fallback 状态完全恢复
  // 并让 PluginPageContainer 基于最新 isMobile=false 重新渲染
  if (!nextIsMobile) {
    void loadPage(detail.plugin_name, detail.page_id)
    return
  }

  // 切到 mobile 但插件没有 mobile variant，沿用当前 desktop schema 即可
  if (desiredVariant === 'mobile' && !detail.has_mobile) {
    isFallback.value = true
    return
  }

  // 已经是目标 variant，不需要重拉
  if (currentVariant.value === desiredVariant) {
    return
  }

  void loadPage(detail.plugin_name, detail.page_id)
}

// === 生命周期 ===

onMounted(async () => {
  // 监听视口断点切换；优先使用 addEventListener，老 Safari 回退到 addListener
  if (typeof mediaQuery.addEventListener === 'function') {
    mediaQuery.addEventListener('change', handleMediaChange)
  } else {
    // @ts-expect-error 兼容旧版 Safari
    mediaQuery.addListener(handleMediaChange)
  }

  // 加载页面列表
  await loadPageList()
})

onBeforeUnmount(() => {
  if (typeof mediaQuery.removeEventListener === 'function') {
    mediaQuery.removeEventListener('change', handleMediaChange)
  } else {
    // @ts-expect-error 兼容旧版 Safari
    mediaQuery.removeListener(handleMediaChange)
  }
  // 销毁残留 page scope
  if (currentStore.value) {
    currentStore.value.destroyPageScope()
    currentStore.value = null
  }
})

/** 加载所有已注册的插件页面 */
async function loadPageList(): Promise<void> {
  listLoading.value = true
  try {
    pages.value = await listPluginPages()
  } catch {
    pages.value = []
  } finally {
    listLoading.value = false
  }
}

// === 路由 query 驱动内容区渲染 ===

watch(
  () => ({ plugin: route.query.plugin, page: route.query.page }),
  async (newQuery) => {
    const pluginName = newQuery.plugin as string | undefined
    const pageId = newQuery.page as string | undefined

    // 无参数 → 显示空状态
    if (!pluginName || !pageId) {
      currentDetail.value = null
      currentSchema.value = null
      currentVariant.value = null
      contentError.value = null
      isFallback.value = false
      return
    }

    await loadPage(pluginName, pageId)
  },
  { immediate: true },
)

/**
 * 加载指定插件页面的内容。
 *
 * 流程：
 * 1. 拉取 detail 获取 has_mobile 等元信息；
 * 2. 根据当前视口与 has_mobile 决定直接请求 desktop 还是 mobile schema，
 *    避免无意义的"先 mobile 再 fallback"二次请求；
 * 3. 后端在 variant 缺失时返回 data=null（非错误），作为额外保险再回退到 desktop。
 */
async function loadPage(pluginName: string, pageId: string): Promise<void> {
  contentLoading.value = true
  contentError.value = null
  currentDetail.value = null
  currentSchema.value = null
  currentVariant.value = null
  isFallback.value = false

  // 销毁旧 page scope
  if (currentStore.value) {
    currentStore.value.destroyPageScope()
  }

  try {
    // 1. 获取页面详情
    const detail = await getPageDetail(pluginName, pageId)
    currentDetail.value = detail

    // 2. 创建变量池 Store
    currentStore.value = createPluginUIVarStore(pluginName)

    // 3. 由 detail.has_mobile 与视口共同决定首选 variant
    const wantsMobile = isMobile.value && detail.has_mobile
    const preferredVariant: 'desktop' | 'mobile' = wantsMobile ? 'mobile' : 'desktop'
    // 视口需要 mobile 但插件未提供，则视为 fallback
    if (isMobile.value && !detail.has_mobile) {
      isFallback.value = true
    }

    // 4. 拉取首选 variant 的 schema
    let schema: PageSchemaResponse | null = await getPageSchema(
      pluginName,
      pageId,
      preferredVariant,
    )
    let actualVariant: 'desktop' | 'mobile' = preferredVariant

    // 5. 防御性回退：理论上若 detail.has_mobile=true 则不应触发，
    //    仅在后端注册表与 variant 文件状态不一致时兜底
    if (schema === null && preferredVariant === 'mobile') {
      isFallback.value = true
      schema = await getPageSchema(pluginName, pageId, 'desktop')
      actualVariant = 'desktop'
    }

    if (schema === null) {
      throw new Error(t('pluginUI.loadFailed'))
    }

    currentSchema.value = schema
    currentVariant.value = actualVariant
  } catch (err: any) {
    contentError.value = err?.message || t('pluginUI.loadFailed')
    currentDetail.value = null
    currentSchema.value = null
    currentVariant.value = null
  } finally {
    contentLoading.value = false
  }
}

// === 侧边栏交互 ===

/** 处理侧边栏页面选择 */
function handlePageSelect(pluginName: string, pageId: string): void {
  router.push({ query: { plugin: pluginName, page: pageId } })
  // 移动端：选择后关闭下拉框
  isMobileNavOpen.value = false
}

/** 切换移动端导航下拉框 */
function toggleMobileNav(): void {
  isMobileNavOpen.value = !isMobileNavOpen.value
}

/** 关闭移动端导航下拉框 */
function closeMobileNav(): void {
  isMobileNavOpen.value = false
}

/** 当前选中的插件名称（从 query 读取） */
const activePlugin = ref<string | null>(null)
/** 当前选中的页面 ID（从 query 读取） */
const activePage = ref<string | null>(null)

watch(
  () => route.query,
  (q) => {
    activePlugin.value = (q.plugin as string) || null
    activePage.value = (q.page as string) || null
  },
  { immediate: true },
)

/** 移动端顶部按钮显示的标题：当前页面标题或默认占位 */
const mobileNavTitle = computed<string>(() => {
  if (currentDetail.value?.title) {
    return currentDetail.value.title
  }
  // 从 pages 列表中匹配（避免在 detail 加载完成前显示占位）
  if (activePlugin.value && activePage.value) {
    const matched = pages.value.find(
      (p) => p.plugin_name === activePlugin.value && p.page_id === activePage.value,
    )
    if (matched) {
      return matched.title
    }
  }
  return t('app.nav.pluginCenter') || '插件中心'
})
</script>

<template>
  <AppShell noPadding>
    <div class="plugin-ui-layout">
      <!-- 左侧侧边栏：桌面端始终显示 -->
      <PluginNavList
        class="plugin-nav-desktop"
        :pages="pages"
        :active-plugin="activePlugin"
        :active-page="activePage"
        :loading="listLoading"
        @select="handlePageSelect"
      />

      <!-- 右侧内容区 -->
      <div class="plugin-ui-content">
        <!-- 移动端顶部：当前页面标题按钮（点击展开下拉框） -->
        <button class="plugin-mobile-bar mobile-only" @click="toggleMobileNav">
          <span class="material-symbols-rounded plugin-mobile-bar-icon">widgets</span>
          <span class="plugin-mobile-bar-title">{{ mobileNavTitle }}</span>
          <span
            class="material-symbols-rounded plugin-mobile-bar-chevron"
            :class="{ open: isMobileNavOpen }"
          >expand_more</span>
        </button>

        <!-- 加载中 -->
        <div v-if="contentLoading" class="plugin-ui-state">
          <span class="material-symbols-rounded state-icon spinning">progress_activity</span>
          <p class="state-text">{{ t('pluginUI.loading') }}</p>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="contentError" class="plugin-ui-state plugin-ui-state--error">
          <span class="material-symbols-rounded state-icon">error</span>
          <p class="state-text">{{ contentError }}</p>
          <button class="state-retry-btn" @click="loadPage(activePlugin!, activePage!)">
            {{ t('pluginUI.retry') }}
          </button>
        </div>

        <!-- 空状态（无选择） -->
        <div v-else-if="!currentDetail || !currentSchema" class="plugin-ui-state">
          <span class="material-symbols-rounded state-icon">widgets</span>
          <h3 class="state-title">{{ t('pluginUI.emptyTitle') }}</h3>
          <p class="state-text">{{ t('pluginUI.emptyHint') }}</p>
        </div>

        <!-- 正常渲染 -->
        <PluginPageContainer
          v-else
          :detail="currentDetail"
          :schema="currentSchema"
          :is-fallback="isFallback"
          :store="currentStore ?? undefined"
          :is-mobile="isMobile"
        />
      </div>

      <!-- 移动端下拉导航：背景遮罩 -->
      <div
        v-if="isMobileNavOpen"
        class="plugin-mobile-backdrop"
        @click="closeMobileNav"
      ></div>

      <!-- 移动端下拉导航：浮层容器 -->
      <div class="plugin-mobile-nav" :class="{ open: isMobileNavOpen }">
        <PluginNavList
          :pages="pages"
          :active-plugin="activePlugin"
          :active-page="activePage"
          :loading="listLoading"
          @select="handlePageSelect"
        />
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.plugin-ui-layout {
  position: relative;
  display: flex;
  align-items: stretch;
  height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
  min-height: 0;
  overflow: hidden;
}

/* 内容区 */
.plugin-ui-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

/* 移动端顶部条（默认隐藏，移动端显示） */
.plugin-mobile-bar {
  display: none;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  border: none;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  cursor: pointer;
  text-align: left;
  flex-shrink: 0;
  z-index: 4;
}

.plugin-mobile-bar:active {
  background: var(--md-sys-color-surface-container);
}

.plugin-mobile-bar-icon {
  font-size: 20px;
  color: var(--md-sys-color-primary);
  flex-shrink: 0;
}

.plugin-mobile-bar-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.plugin-mobile-bar-chevron {
  font-size: 20px;
  color: var(--md-sys-color-on-surface-variant);
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.plugin-mobile-bar-chevron.open {
  transform: rotate(180deg);
}

/* 移动端下拉导航容器（默认隐藏） */
.plugin-mobile-backdrop,
.plugin-mobile-nav {
  display: none;
}

/* 移动端 mobile-only 标记（默认隐藏，移动端覆盖显示） */
.mobile-only {
  display: none;
}

/* 状态占位 */
.plugin-ui-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  height: 100%;
  padding: 1.5rem 2rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 72%, transparent);
}

.state-icon {
  font-size: 48px;
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.4;
}

.plugin-ui-state--error .state-icon {
  color: var(--md-sys-color-error);
  opacity: 0.7;
}

.state-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--md-sys-color-on-surface);
}

.state-text {
  margin: 0;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
  text-align: center;
}

.state-retry-btn {
  margin-top: 0.5rem;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 9999px;
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.state-retry-btn:hover {
  opacity: 0.85;
}

/* 加载动画 */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spinning {
  animation: spin 1s linear infinite;
}

/* 移动端响应：与 AppShell / PluginNavList 的 900px 断点保持一致 */
@media (max-width: 899px) {
  /* 桌面端侧边栏隐藏 */
  .plugin-nav-desktop {
    display: none !important;
  }

  /* 顶部按钮显示 */
  .plugin-mobile-bar.mobile-only {
    display: flex;
  }

  /* 下拉框背景遮罩 */
  .plugin-mobile-backdrop {
    position: fixed;
    inset: 0;
    z-index: 70;
    display: block;
    background: rgba(0, 0, 0, 0.32);
    animation: plugin-fade-in 0.15s ease;
  }

  /* 下拉框浮层（从顶部按钮下方滑下） */
  .plugin-mobile-nav {
    position: absolute;
    left: 0.5rem;
    right: 0.5rem;
    top: calc(0.75rem + 0.9375rem * 1.4 + 0.75rem);
    z-index: 80;
    display: block;
    max-height: min(70vh, 560px);
    overflow: hidden;
    border-radius: 20px;
    background: var(--md-sys-color-surface);
    border: 1px solid var(--md-sys-color-outline-variant);
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.12),
      0 2px 8px rgba(0, 0, 0, 0.08);
    transform: translateY(-12px) scale(0.98);
    opacity: 0;
    pointer-events: none;
    transition: transform 0.18s ease, opacity 0.18s ease;
  }

  .plugin-mobile-nav.open {
    transform: translateY(0) scale(1);
    opacity: 1;
    pointer-events: auto;
  }

  /* 下拉框内的 PluginNavList 适配（去掉宽度/边框，撑满浮层） */
  .plugin-mobile-nav :deep(.plugin-nav) {
    width: 100%;
    max-height: min(70vh, 560px);
    border-right: none;
    border-radius: 20px;
    background: transparent;
    backdrop-filter: none;
  }
}

@keyframes plugin-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
