<script setup lang="ts">
/**
 * 插件导航列表侧边栏组件。
 *
 * 按 plugin_name 分组展示所有已注册的插件 page，支持搜索过滤和选中高亮。
 * 纯 WebUI 官方组件，不在插件可用标签清单内。
 */
import { computed, ref } from 'vue'
import type { PageSummary } from '../../api/types/plugin-ui'
import { useI18n } from '../../utils/i18n'

const { t } = useI18n()

const props = defineProps<{
  /** 页面列表数据 */
  pages: PageSummary[]
  /** 当前选中的插件名称 */
  activePlugin: string | null
  /** 当前选中的页面 ID */
  activePage: string | null
  /** 是否正在加载 */
  loading?: boolean
}>()

const emit = defineEmits<{
  /** 用户选择某个 page 时触发 */
  select: [pluginName: string, pageId: string]
}>()

/** 搜索关键词 */
const searchQuery = ref('')

/** 按 plugin_name 分组并过滤 */
const groupedPages = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  const filtered = props.pages.filter((page) => {
    if (!query) return true
    return (
      page.title.toLowerCase().includes(query) ||
      page.plugin_name.toLowerCase().includes(query) ||
      (page.description?.toLowerCase().includes(query) ?? false)
    )
  })

  // 按 plugin_name 分组
  const groups = new Map<string, PageSummary[]>()
  for (const page of filtered) {
    const existing = groups.get(page.plugin_name)
    if (existing) {
      existing.push(page)
    } else {
      groups.set(page.plugin_name, [page])
    }
  }

  // 每组内按 order 排序
  for (const pages of groups.values()) {
    pages.sort((a, b) => a.order - b.order)
  }

  return groups
})

/** 判断是否为当前选中项 */
function isActive(pluginName: string, pageId: string): boolean {
  return props.activePlugin === pluginName && props.activePage === pageId
}

/** 处理页面选择 */
function handleSelect(pluginName: string, pageId: string): void {
  emit('select', pluginName, pageId)
}
</script>

<template>
  <aside class="plugin-nav">
    <h2 class="plugin-nav-title">{{ t('app.nav.pluginCenter') || '插件中心' }}</h2>

    <!-- 搜索框 -->
    <div class="plugin-nav-search">
      <span class="plugin-nav-search-icon material-symbols-rounded">search</span>
      <input
        v-model="searchQuery"
        type="text"
        class="plugin-nav-search-input"
        :placeholder="t('pluginUI.searchPlaceholder') || '搜索插件页面...'"
      />
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="plugin-nav-loading">
      <span class="plugin-nav-loading-text">加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="groupedPages.size === 0" class="plugin-nav-empty">
      <span class="material-symbols-rounded plugin-nav-empty-icon">extension_off</span>
      <span class="plugin-nav-empty-text">
        {{ searchQuery ? '未找到匹配的插件页面' : '暂无已注册的插件页面' }}
      </span>
    </div>

    <!-- 分组列表 -->
    <nav v-else class="plugin-nav-list">
      <div
        v-for="[pluginName, pages] of groupedPages"
        :key="pluginName"
        class="plugin-nav-group"
      >
        <div class="plugin-nav-group-title">{{ pluginName }}</div>
        <button
          v-for="page in pages"
          :key="page.page_id"
          class="plugin-nav-item"
          :class="{ active: isActive(page.plugin_name, page.page_id) }"
          :title="page.description || page.title"
          @click="handleSelect(page.plugin_name, page.page_id)"
        >
          <span
            v-if="page.icon"
            class="material-symbols-rounded plugin-nav-item-icon"
          >{{ page.icon }}</span>
          <span v-else class="material-symbols-rounded plugin-nav-item-icon">extension</span>
          <span class="plugin-nav-item-label">{{ page.title }}</span>
        </button>
      </div>
    </nav>
  </aside>
</template>

<style scoped>
.plugin-nav {
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

.plugin-nav-title {
  margin: 1.5rem 1.5rem 0.5rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--md-sys-color-on-surface);
}

/* 搜索框 */
.plugin-nav-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.5rem 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 9999px;
  background: var(--md-sys-color-surface-container-highest);
  transition: background 0.15s;
}

.plugin-nav-search:focus-within {
  background: var(--md-sys-color-surface-container-high);
  outline: 2px solid var(--md-sys-color-primary);
  outline-offset: -2px;
}

.plugin-nav-search-icon {
  font-size: 20px;
  color: var(--md-sys-color-on-surface-variant);
  flex-shrink: 0;
}

.plugin-nav-search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface);
  min-width: 0;
}

.plugin-nav-search-input::placeholder {
  color: var(--md-sys-color-on-surface-variant);
}

/* 加载/空状态 */
.plugin-nav-loading,
.plugin-nav-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: var(--md-sys-color-on-surface-variant);
}

.plugin-nav-empty-icon {
  font-size: 32px;
  opacity: 0.5;
}

.plugin-nav-empty-text,
.plugin-nav-loading-text {
  font-size: 0.8125rem;
  text-align: center;
}

/* 分组列表 */
.plugin-nav-list {
  display: flex;
  flex-direction: column;
  padding: 0.25rem 0.75rem 1rem;
  gap: 0.5rem;
}

.plugin-nav-group-title {
  padding: 0.5rem 0.75rem 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.7;
}

.plugin-nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  border: none;
  border-radius: 9999px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
  transition: background 0.15s, color 0.15s;
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
}

.plugin-nav-item:hover {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
}

.plugin-nav-item.active {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  font-weight: 600;
}

.plugin-nav-item-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.plugin-nav-item-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 移动端响应 */
@media (max-width: 900px) {
  .plugin-nav {
    width: 100%;
    height: auto;
    max-height: 200px;
    border-bottom: 1px solid var(--md-sys-color-outline-variant);
  }
}
</style>
