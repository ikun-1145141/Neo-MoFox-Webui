<script setup lang="ts">
/** SysTag - 标签组件。 */
defineProps<{ color?: string; variant?: string }>()
</script>
<template>
  <span class="sys-tag" :class="`sys-tag--${variant || 'default'}`" :style="{ backgroundColor: color || undefined }">
    <slot />
  </span>
</template>
<style scoped>
.sys-tag { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; }
.sys-tag--default { background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface); }
.sys-tag--primary { background: var(--md-sys-color-primary-container); color: var(--md-sys-color-on-primary-container); }
.sys-tag--error { background: var(--md-sys-color-error-container); color: var(--md-sys-color-on-error-container); }
.sys-tag--success { background: #dcfce7; color: #166534; }
</style>
