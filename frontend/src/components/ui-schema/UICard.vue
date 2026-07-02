<!--
  @file UICard.vue
  @description 卡片容器组件，支持标题和 MD3 阴影层级。
  消费共享工具：xmlParser（UiNode）。
-->
<template>
  <div :class="['ui-card', `elevation-${elevation}`]" :style="cardStyle">
    <div v-if="node.attrs.title" class="ui-card-header">
      <h3 class="card-title">{{ evaluate(node.attrs.title) }}</h3>
    </div>
    <div class="ui-card-content">
      <SchemaRenderer
        v-for="(child, index) in node.children"
        :key="index"
        :node="child"
        :store="store"
        :api-base="apiBase"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import SchemaRenderer from './SchemaRenderer.vue'

interface Props {
  node: UiNode
  store?: Record<string, any>
  apiBase?: string
}

const props = defineProps<Props>()

const evaluate = inject<any>('uiSchemaEvaluate')

const elevation = computed(() => {
  const elev = Number(props.node.attrs.elevation)
  return isNaN(elev) ? 1 : Math.max(0, Math.min(5, elev))
})

const cardStyle = computed(() => {
  const attrs = props.node.attrs
  if (attrs.style) {
    return parseInlineStyle(attrs.style)
  }
  return {}
})

function parseInlineStyle(styleStr: string): Record<string, string> {
  const result: Record<string, string> = {}
  styleStr.split(';').forEach((item) => {
    const parts = item.split(':')
    if (parts.length === 2) {
      result[parts[0].trim()] = parts[1].trim()
    }
  })
  return result
}
</script>

<style scoped>
.ui-card {
  background: var(--md-sys-color-surface-container-low);
  border-radius: 16px;
  padding: 20px;
  box-sizing: border-box;
  width: 100%;
  transition: box-shadow 0.2s;
  border: 1px solid var(--md-sys-color-outline-variant);
}

/* MD3 阴影层级 */
.elevation-0 {
  box-shadow: none;
}

.elevation-1 {
  box-shadow: var(--md-sys-elevation-1);
}

.elevation-2 {
  box-shadow: var(--md-sys-elevation-2);
}

.elevation-3 {
  box-shadow: var(--md-sys-elevation-3);
}

.elevation-4 {
  box-shadow: var(--md-sys-elevation-4);
}

.elevation-5 {
  box-shadow: var(--md-sys-elevation-5);
}

.ui-card-header {
  margin-bottom: 16px;
}

.card-title {
  font-size: 18px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

.ui-card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}
</style>
