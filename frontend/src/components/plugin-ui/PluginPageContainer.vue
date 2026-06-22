<script setup lang="ts">
/**
 * 插件页面渲染容器组件（双轨分发）。
 *
 * 根据 schema.mode 选择渲染 XmlRenderer 或 HtmlSandbox。
 * XML 模式直接渲染；HTML 模式仍为占位（Phase F-4）。
 */
import { computed } from 'vue'
import type { PageSchemaResponse, PageDetail } from '../../api/types/plugin-ui'
import type { PluginUIVarStore } from '../../stores/plugin-ui-vars'
import XmlRenderer from './XmlRenderer.vue'

const props = defineProps<{
  /** 页面详情 */
  detail: PageDetail
  /** 页面 schema */
  schema: PageSchemaResponse
  /** 是否为 fallback 模式（桌面版在移动端显示） */
  isFallback?: boolean
  /** 变量池 Store（XML 模式需要） */
  store?: PluginUIVarStore
  /** 是否为移动端 */
  isMobile?: boolean
}>()

/** 渲染模式标签 */
const modeLabel = computed(() => {
  return props.schema.mode === 'xml' ? 'XML 声明式' : 'HTML 自由式'
})
</script>

<template>
  <div class="plugin-page-container">
    <!-- Fallback 提示 -->
    <div v-if="isFallback" class="plugin-page-fallback-notice">
      <span class="material-symbols-rounded">phone_iphone</span>
      <span>该插件页面未适配移动端，已启用兼容显示</span>
    </div>

    <!-- 页面头部信息 -->
    <header class="plugin-page-header">
      <div class="plugin-page-header-title">
        <span
          v-if="detail.icon"
          class="material-symbols-rounded plugin-page-header-icon"
        >{{ detail.icon }}</span>
        <h2 class="plugin-page-header-name">{{ detail.title }}</h2>
        <span class="plugin-page-header-badge">{{ modeLabel }}</span>
      </div>
      <p v-if="detail.description" class="plugin-page-header-desc">
        {{ detail.description }}
      </p>
    </header>

    <!-- 渲染区域（Phase F-2/F-4 接入 XmlRenderer / HtmlSandbox） -->
    <div class="plugin-page-content" :class="{ 'fallback-scroll': isFallback }">
      <div v-if="isFallback" class="plugin-page-content-inner" style="min-width: 1024px;">
        <!-- XML 模式：使用 XmlRenderer 渲染 -->
        <XmlRenderer
          v-if="schema.mode === 'xml' && schema.xml && store"
          :xml="schema.xml"
          :store="store"
          :plugin-name="detail.plugin_name"
          :is-mobile="isMobile"
        />
        <!-- HTML 模式占位 -->
        <div v-else class="plugin-page-placeholder">
          <span class="material-symbols-rounded placeholder-icon">web</span>
          <p class="placeholder-text">HTML 沙箱将在 Phase F-4 接入</p>
          <pre class="placeholder-preview">Assets: {{ JSON.stringify(schema.assets_urls, null, 2) }}</pre>
        </div>
      </div>

      <template v-else>
        <!-- XML 模式：使用 XmlRenderer 渲染 -->
        <XmlRenderer
          v-if="schema.mode === 'xml' && schema.xml && store"
          :xml="schema.xml"
          :store="store"
          :plugin-name="detail.plugin_name"
          :is-mobile="isMobile"
        />
        <!-- XML 模式但缺少 store（不应发生） -->
        <div v-else-if="schema.mode === 'xml'" class="plugin-page-placeholder">
          <span class="material-symbols-rounded placeholder-icon">code</span>
          <p class="placeholder-text">XML 渲染器需要变量池 Store</p>
        </div>
        <!-- HTML 模式占位 -->
        <div v-else class="plugin-page-placeholder">
          <span class="material-symbols-rounded placeholder-icon">web</span>
          <p class="placeholder-text">HTML 沙箱将在 Phase F-4 接入</p>
          <pre class="placeholder-preview">Assets: {{ JSON.stringify(schema.assets_urls, null, 2) }}</pre>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.plugin-page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-height: 0;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  overflow: hidden;
}

/* Fallback 提示条 */
.plugin-page-fallback-notice {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
  font-size: 0.8125rem;
  font-weight: 500;
}

.plugin-page-fallback-notice .material-symbols-rounded {
  font-size: 18px;
}

/* 页面头部 */
.plugin-page-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
    backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  flex-shrink: 0;
}

.plugin-page-header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.plugin-page-header-icon {
  font-size: 24px;
  color: var(--md-sys-color-primary);
}

.plugin-page-header-name {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

.plugin-page-header-badge {
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.plugin-page-header-desc {
  margin: 0;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
}

/* 内容区域 */
.plugin-page-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 1.25rem 1.5rem;
}

.plugin-page-content.fallback-scroll {
  overflow-x: auto;
}

.plugin-page-content-inner {
  min-width: 1024px;
}

/* 占位区 */
.plugin-page-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 3rem 2rem;
  border: 1px dashed var(--md-sys-color-outline-variant);
  border-radius: 12px;
  background: var(--md-sys-color-surface-container-lowest);
}

.placeholder-icon {
  font-size: 40px;
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.5;
}

.placeholder-text {
  margin: 0;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
}

.placeholder-preview {
  max-width: 100%;
  max-height: 200px;
  overflow: auto;
  padding: 0.75rem;
  border-radius: 8px;
  background: var(--md-sys-color-surface-container);
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  color: var(--md-sys-color-on-surface-variant);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

/* 移动端响应：header 缩小 */
@media (max-width: 900px) {
  .plugin-page-header {
    padding: 0.75rem 1rem;
  }

  .plugin-page-header-icon {
    font-size: 20px;
  }

  .plugin-page-header-name {
    font-size: 1rem;
  }

  .plugin-page-header-desc {
    font-size: 0.8125rem;
  }

  .plugin-page-content {
    padding: 1rem;
  }
}
</style>
