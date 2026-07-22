<script setup lang="ts">
/** SysBadge - 徽章组件。 */
import { computed, watch, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    value?: string | number
    color?: string
    max?: number
    variant?: string
  }>(),
  {
    variant: 'error',
  }
)

const displayValue = computed(() => {
  const v = props.value
  if (v === undefined || v === null || v === '') return ''
  const num = Number(v)
  if (!Number.isNaN(num) && typeof v !== 'string' && props.max) {
    return num > props.max ? `${props.max}+` : String(num)
  }
  return String(v)
})

const hasValue = computed(() => displayValue.value !== '')

// 数字变化时触发缩放动画
const bumpKey = ref(0)
watch(
  () => props.value,
  (v, prev) => {
    if (v !== prev) bumpKey.value++
  }
)
</script>

<template>
  <span class="sys-badge-wrapper">
    <slot />
    <Transition name="sys-scale">
      <span
        v-if="hasValue"
        :key="bumpKey"
        class="sys-badge"
        :class="[`sys-badge--${variant}`, { 'sys-badge--dot': !hasValue }]"
        :style="{ backgroundColor: color || undefined }"
      >{{ displayValue }}</span>
    </Transition>
  </span>
</template>

<style scoped>
.sys-badge-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.sys-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  background: var(--md-sys-color-error, #ba1a1a);
  color: var(--md-sys-color-on-error, #fff);
  box-shadow: 0 0 0 2px var(--md-sys-color-surface, #fff);
  transform-origin: center;
}

.sys-badge--dot {
  width: 8px;
  height: 8px;
  min-width: 8px;
  padding: 0;
  right: -4px;
  top: -4px;
}

.sys-badge--primary {
  background: var(--md-sys-color-primary, #0058bd);
  color: var(--md-sys-color-on-primary, #fff);
}

.sys-badge--success {
  background: #16a34a;
  color: #fff;
}

.sys-badge--warning {
  background: #f59e0b;
  color: #fff;
}

.sys-badge--info {
  background: var(--md-sys-color-secondary, #565e71);
  color: var(--md-sys-color-on-secondary, #fff);
}
</style>
