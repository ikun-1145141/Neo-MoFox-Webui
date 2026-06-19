<script setup lang="ts">
/** SysIconButton - 图标按钮组件。 */
defineProps<{ icon?: string; disabled?: boolean; loading?: string; variant?: string }>()
const emit = defineEmits<{ (e: 'click'): void }>()
</script>
<template>
  <button class="sys-icon-button" :class="`sys-icon-button--${variant || 'standard'}`"
    :disabled="disabled || loading === 'true'" :aria-label="icon" @click="emit('click')">
    <span v-if="loading === 'true'" class="material-symbols-rounded spinning">progress_activity</span>
    <span v-else class="material-symbols-rounded">{{ icon || 'circle' }}</span>
  </button>
</template>
<style scoped>
.sys-icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  cursor: pointer;
  transition: background 0.15s;
}

.sys-icon-button:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-highest);
}

.sys-icon-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sys-icon-button--filled {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.sys-icon-button .material-symbols-rounded {
  font-size: 22px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}
</style>
