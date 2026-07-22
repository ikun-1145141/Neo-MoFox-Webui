<script setup lang="ts">
/** SysTag - 标签组件。 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    color?: string
    variant?: string
    closable?: boolean
    icon?: string
  }>(),
  {
    variant: 'default',
    closable: false,
  }
)

const emit = defineEmits<{
  (e: 'close'): void
}>()

const tagStyle = computed(() => ({
  backgroundColor: props.color || undefined,
}))
</script>

<template>
  <span
    class="sys-tag"
    :class="[`sys-tag--${variant}`, { 'sys-tag--custom-color': !!color }]"
    :style="tagStyle"
  >
    <span
      v-if="icon"
      class="material-symbols-rounded sys-tag-icon"
    >{{ icon }}</span>
    <span class="sys-tag-label">
      <slot />
    </span>
    <button
      v-if="closable"
      class="sys-tag-close"
      aria-label="移除"
      @click="emit('close')"
    >
      <span class="material-symbols-rounded">close</span>
    </button>
  </span>
</template>

<style scoped>
.sys-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  animation: sys-scale-in var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
  transition: transform var(--md-sys-motion-duration-x-short) var(--md-sys-motion-emphasized);
}

.sys-tag:hover {
  transform: scale(1.02);
}

.sys-tag--default {
  background: var(--md-sys-color-surface-container-high, #e6e0e9);
  color: var(--md-sys-color-on-surface, #1a1b20);
}

.sys-tag--primary {
  background: var(--md-sys-color-primary-container, #d9e2ff);
  color: var(--md-sys-color-on-primary-container, #001a41);
}

.sys-tag--error {
  background: var(--md-sys-color-error-container, #ffdad6);
  color: var(--md-sys-color-on-error-container, #410002);
}

.sys-tag--success {
  background: #dcfce7;
  color: #166534;
}

.sys-tag--warning {
  background: #fef3c7;
  color: #92400e;
}

.sys-tag--info {
  background: #dbeafe;
  color: #1e40af;
}

.sys-tag--custom-color {
  color: var(--md-sys-color-on-surface, #1a1b20);
}

.sys-tag-icon {
  font-size: 14px;
}

.sys-tag-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 0;
  transition: background var(--md-sys-motion-duration-x-short) var(--md-sys-motion-standard);
}

.sys-tag-close:hover {
  background: rgba(0, 0, 0, 0.1);
}

.sys-tag-close .material-symbols-rounded {
  font-size: 12px;
}
</style>
