<!--
  @file UITabs.vue
  @description 标签页组件，支持多 Tab 切换和嵌套渲染。
  消费共享工具：xmlParser（UiNode）。
-->
<template>
  <div class="ui-tabs">
    <!-- Tab 头部 -->
    <div class="tabs-header">
      <div
        v-for="(tab, index) in tabs"
        :key="index"
        :class="['tab-item', { 'is-active': activeIndex === index }]"
        @click="activeIndex = index"
      >
        <span v-if="tab.attrs.icon" class="material-symbols-outlined tab-icon">
          {{ tab.attrs.icon }}
        </span>
        <span class="tab-title">{{ evaluate(tab.attrs.title || `Tab ${index + 1}`) }}</span>
      </div>
    </div>

    <!-- Tab 内容 -->
    <div class="tabs-content" v-if="tabs[activeIndex]">
      <SchemaRenderer
        v-for="(child, index) in tabs[activeIndex].children"
        :key="index"
        :node="child"
        :store="store"
        :api-base="apiBase"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import SchemaRenderer from './SchemaRenderer.vue'

interface Props {
  node: UiNode
  store?: Record<string, any>
  apiBase?: string
}

const props = defineProps<Props>()

const evaluate = inject<any>('uiSchemaEvaluate')

const activeIndex = ref(0)

// 过滤出 tab 子节点
const tabs = computed(() => {
  return props.node.children.filter((child) => child.tag === 'tab')
})
</script>

<style scoped>
.ui-tabs {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.tabs-header {
  display: flex;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  gap: 8px;
  overflow-x: auto;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 14px;
  font-weight: 500;
  position: relative;
  transition: all 0.2s;
  user-select: none;
  white-space: nowrap;
}

.tab-item:hover {
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container-low);
  border-radius: 8px 8px 0 0;
}

.tab-item.is-active {
  color: var(--md-sys-color-primary);
}

.tab-item.is-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--md-sys-color-primary);
  border-radius: 3px 3px 0 0;
}

.tab-icon {
  font-size: 18px;
}

.tabs-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}
</style>
