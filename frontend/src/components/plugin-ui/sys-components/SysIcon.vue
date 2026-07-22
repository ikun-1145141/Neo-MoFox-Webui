<script setup lang="ts">
/** SysIcon - 图标组件。 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    name?: string
    size?: string
    color?: string
    spin?: boolean
  }>(),
  {
    size: '24px',
    spin: false,
  }
)

const style = computed(() => ({
  fontSize: props.size,
  color: props.color || undefined,
  animation: props.spin ? `sys-spin 1s var(--md-sys-motion-linear) infinite` : undefined,
}))
</script>

<template>
  <span
    class="material-symbols-rounded sys-icon"
    :style="style"
  >
    {{ name || '' }}
    <slot />
  </span>
</template>

<style scoped>
.sys-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}
</style>
