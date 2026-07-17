<!--
  @file UIContainer.vue
  @description 布局容器组件，支持垂直、水平和网格布局。
  消费 UiNode（attrs 字段）。
-->
<template>
  <div class="ui-container" :style="containerStyle">
    <SchemaRenderer
      v-for="(child, index) in node.children"
      :key="index"
      :node="child"
      :store="store"
      :api-base="apiBase"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import SchemaRenderer from './SchemaRenderer.vue'

interface Props {
  node: UiNode
  /** 页面级数据存储 */
  store?: Record<string, any>
  /** API 基础路径前缀 */
  apiBase?: string
}

const props = defineProps<Props>()

const containerStyle = computed(() => {
  const attrs = props.node.attrs
  const layout = attrs.layout || 'vertical'
  const spacing = attrs.spacing ? `${attrs.spacing}px` : undefined
  const padding = attrs.padding ? `${attrs.padding}px` : undefined
  const align = attrs.align || undefined
  const justify = attrs.justify || undefined

  const style: Record<string, string> = {}

  if (padding) {
    style.padding = padding
  }

  if (layout === 'grid') {
    style.display = 'grid'
    const columns = attrs.columns || '1'
    if (columns === 'auto-fit') {
      style.gridTemplateColumns = 'repeat(auto-fit, minmax(250px, 1fr))'
    } else if (!isNaN(Number(columns))) {
      style.gridTemplateColumns = `repeat(${columns}, minmax(0, 1fr))`
    } else {
      style.gridTemplateColumns = columns
    }

    const rowGap = attrs['row-gap'] || attrs.gap || attrs.spacing || '16'
    const colGap = attrs['col-gap'] || attrs.gap || attrs.spacing || '16'
    style.rowGap = `${rowGap}px`
    style.columnGap = `${colGap}px`
  } else {
    style.display = 'flex'
    style.flexDirection = layout === 'horizontal' ? 'row' : 'column'

    if (spacing) {
      style.gap = spacing
    }

    if (align) {
      const alignMap: Record<string, string> = {
        start: 'flex-start',
        center: 'center',
        end: 'flex-end',
      }
      style.alignItems = alignMap[align] || align
    }

    if (justify) {
      const justifyMap: Record<string, string> = {
        start: 'flex-start',
        center: 'center',
        end: 'flex-end',
        'space-between': 'space-between',
        'space-around': 'space-around',
      }
      style.justifyContent = justifyMap[justify] || justify
    }
  }

  // 支持额外的自定义 style 属性
  if (attrs.style) {
    return { ...style, ...parseInlineStyle(attrs.style) }
  }

  return style
})

// 解析内联样式字符串为对象
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
.ui-container {
  box-sizing: border-box;
  width: 100%;
}
</style>
