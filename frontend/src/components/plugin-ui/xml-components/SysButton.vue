<script setup lang="ts">
/** SysButton - 按钮组件。 */
defineProps<{ variant?: string; icon?: string; disabled?: boolean; loading?: string }>()
const emit = defineEmits<{ (e: 'click'): void }>()
</script>
<template>
  <button class="sys-button" :class="`sys-button--${variant || 'filled'}`" :disabled="disabled || loading === 'true'"
    @click="emit('click')">
    <span v-if="loading === 'true'" class="material-symbols-rounded sys-button-spinner">progress_activity</span>
    <span v-else-if="icon" class="material-symbols-rounded sys-button-icon">{{ icon }}</span>
    <slot />
  </button>
</template>
<style scoped>
.sys-button {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s, background 0.15s;
}

.sys-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sys-button--filled {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.sys-button--filled:hover:not(:disabled) {
  opacity: 0.9;
}

.sys-button--outlined {
  background: transparent;
  color: var(--md-sys-color-primary);
  border: 1px solid var(--md-sys-color-outline);
}

.sys-button--text {
  background: transparent;
  color: var(--md-sys-color-primary);
}

.sys-button--tonal {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.sys-button-icon {
  font-size: 18px;
}

.sys-button-spinner {
  font-size: 18px;
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
