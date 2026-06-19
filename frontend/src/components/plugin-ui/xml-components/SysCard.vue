<script setup lang="ts">
/**
 * SysCard - 卡片容器。
 *
 * MD3 风格的 Surface 容器，带圆角、阴影和内边距。
 */
defineProps<{
  /** 卡片标题 */
  title?: string
  /** 卡片变体：elevated / outlined / filled */
  variant?: string
  /** 内边距 */
  padding?: string
}>()
</script>

<template>
  <div class="sys-card" :class="`sys-card--${variant || 'elevated'}`" :style="{ padding: padding || '1rem' }">
    <h3 v-if="title" class="sys-card-title">{{ title }}</h3>
    <slot />
  </div>
</template>

<style scoped>
.sys-card {
  border-radius: 12px;
  width: 100%;
}

.sys-card--elevated {
  background: var(--md-sys-color-surface);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05), 0 2px 8px rgba(0, 0, 0, 0.04);
}

.sys-card--outlined {
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
}

.sys-card--filled {
  background: var(--md-sys-color-surface-container);
}

.sys-card-title {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}
</style>
