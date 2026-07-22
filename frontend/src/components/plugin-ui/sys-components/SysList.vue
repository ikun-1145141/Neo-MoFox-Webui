<script setup lang="ts">
/**
 * SysList - 列表组件。
 *
 * 渲染数组数据为列表项，支持通过 `item` 具名插槽自定义每一项的展示。
 * 列表项入场有 stagger 动画。
 */
import { computed } from 'vue'

const props = defineProps<{
  /** JSON 数据数组 */
  data?: string | any[]
  /** 是否有分割线 */
  divider?: string
  /** 是否两行布局 */
  twoLine?: boolean
  /** 是否启用入场动画 */
  animated?: boolean
}>()

const parsedData = computed<any[]>(() => {
  if (!props.data) return []
  if (Array.isArray(props.data)) return props.data
  try {
    const parsed = JSON.parse(props.data)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
})
</script>

<template>
  <TransitionGroup
    name="sys-list"
    tag="div"
    class="sys-list"
    :class="{ 'sys-list--divider': divider !== 'false' }"
  >
    <div
      v-for="(item, idx) in parsedData"
      :key="idx"
      class="sys-list-item"
      :class="{ 'sys-list-item--two-line': twoLine }"
      :style="animated === false ? null : { animationDelay: `${Math.min(idx, 12) * 30}ms` }"
    >
      <slot name="item" :item="item" :index="idx">
        {{ typeof item === 'object' ? JSON.stringify(item) : item }}
      </slot>
    </div>
  </TransitionGroup>
  <div v-if="parsedData.length === 0" class="sys-list-empty">
    <slot name="empty">
      暂无数据
    </slot>
  </div>
</template>

<style scoped>
.sys-list {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.sys-list-item {
  padding: 0.625rem 0.75rem;
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface, #1a1b20);
  border-radius: 0;
  transition:
    background var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
  animation: sys-slide-down var(--md-sys-motion-duration-medium) var(--md-sys-motion-decelerated) both;
}

.sys-list-item:hover {
  background: color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 4%, transparent);
}

.sys-list-item:active {
  transform: scale(0.995);
}

.sys-list--divider .sys-list-item + .sys-list-item {
  border-top: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
}

.sys-list-item--two-line {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0.75rem;
}

.sys-list-empty {
  padding: 1.5rem;
  text-align: center;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  font-size: 0.875rem;
}

/* TransitionGroup 类 */
.sys-list-enter-active,
.sys-list-leave-active {
  transition:
    opacity var(--md-sys-motion-duration-short) var(--md-sys-motion-standard),
    transform var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized);
}

.sys-list-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.sys-list-leave-to {
  opacity: 0;
  transform: translateX(8px);
}

.sys-list-move {
  transition: transform var(--md-sys-motion-duration-medium) var(--md-sys-motion-emphasized);
}
</style>
