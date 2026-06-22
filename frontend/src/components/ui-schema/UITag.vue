<!--
  @file UITag.vue
  @description 标签/徽章组件，支持多种 MD3 配色。
  消费共享工具：xmlParser（UiNode）。
-->
<template>
  <span :class="['ui-tag', `tag-${color}`]">
    <slot>{{ evaluate(node.text || '') }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import type { UiNode } from '@/utils/xmlParser'

interface Props {
  node: UiNode
  store?: Record<string, any>
  apiBase?: string
}

const props = defineProps<Props>()

const evaluate = inject<any>('uiSchemaEvaluate')

const color = computed(() => props.node.attrs.color || 'default')
</script>

<style scoped>
.ui-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
  width: fit-content;
  line-height: 1;
}

.tag-primary {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.tag-secondary {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.tag-tertiary {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.tag-success {
  background: rgba(40, 167, 69, 0.15);
  color: #28a745;
  border: 1px solid rgba(40, 167, 69, 0.3);
}

.tag-danger {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.tag-warning {
  background: rgba(255, 193, 7, 0.15);
  color: #ffc107;
  border: 1px solid rgba(255, 193, 7, 0.3);
}

.tag-default {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface-variant);
  border: 1px solid var(--md-sys-color-outline-variant);
}
</style>
