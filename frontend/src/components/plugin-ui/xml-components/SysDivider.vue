<script setup lang="ts">
/**
 * SysDivider - 分割线组件。
 */
defineProps<{
  /** 方向：horizontal / vertical */
  direction?: string
  /** 外边距 */
  margin?: string
}>()
</script>

<template>
  <hr
    class="sys-divider"
    :class="{ 'sys-divider--vertical': direction === 'vertical' }"
    :style="{ margin: margin || (direction === 'vertical' ? '0 0.5rem' : '0.5rem 0') }"
    aria-hidden="true"
  />
</template>

<style scoped>
.sys-divider {
  border: none;
  border-top: 1px solid var(--md-sys-color-outline-variant);
  width: 100%;
  margin: 0.5rem 0;
}

.sys-divider--vertical {
  border-top: none;
  border-left: 1px solid var(--md-sys-color-outline-variant);
  width: auto;
  height: 100%;
  min-height: 1rem;
}
</style>
