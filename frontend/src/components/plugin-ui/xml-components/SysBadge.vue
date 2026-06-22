<script setup lang="ts">
/** SysBadge - 徽章组件。 */
defineProps<{ value?: string; color?: string }>()
</script>
<template>
  <span class="sys-badge" :style="{ backgroundColor: color || undefined }">{{ value }}
    <slot />
  </span>
</template>
<style scoped>
.sys-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  background: var(--md-sys-color-error);
  color: var(--md-sys-color-on-error);
}
</style>
