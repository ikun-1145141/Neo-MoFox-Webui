<script setup lang="ts">
/** SysIcon - 图标组件。 */
defineProps<{ name?: string; size?: string; color?: string }>()
</script>
<template>
  <span class="material-symbols-rounded sys-icon" :style="{ fontSize: size || '24px', color: color || undefined }">{{
    name || '' }}
    <slot />
  </span>
</template>
<style scoped>
.sys-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
</style>
