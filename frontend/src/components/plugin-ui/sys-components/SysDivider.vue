<script setup lang="ts">
/**
 * SysDivider - 分割线组件。
 */
defineProps<{
  direction?: string
  margin?: string
  variant?: string
}>()
</script>

<template>
  <hr
    class="sys-divider"
    :class="[`sys-divider--${variant || 'solid'}`, { 'sys-divider--vertical': direction === 'vertical' }]"
    :style="{ margin: margin || (direction === 'vertical' ? '0 0.5rem' : '0.5rem 0') }"
    aria-hidden="true"
  >
</template>

<style scoped>
.sys-divider {
  border: none;
  border-top: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
  width: 100%;
  margin: 0.5rem 0;
  transform-origin: left;
  animation: sys-scale-in var(--md-sys-motion-duration-medium) var(--md-sys-motion-decelerated);
}

.sys-divider--vertical {
  border-top: none;
  border-left: 1px solid var(--md-sys-color-outline-variant, #cac4d0);
  width: auto;
  height: 100%;
  min-height: 1rem;
  margin: 0 0.5rem;
  transform-origin: top;
}

.sys-divider--dashed {
  border-top-style: dashed;
}

.sys-divider--dotted {
  border-top-style: dotted;
}

.sys-divider--thick {
  border-top-width: 2px;
}
</style>
