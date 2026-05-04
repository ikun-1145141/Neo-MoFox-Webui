<script setup lang="ts">
import Icon from '../common/Icon.vue'

interface Props {
  label: string
  value: string | number
  icon: string
  colorVariant?: 'primary' | 'secondary' | 'tertiary' | 'success' | 'error' | 'outline'
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  colorVariant: 'primary',
  loading: false
})
</script>

<template>
  <div class="stat-card">
    <Icon 
      :icon="loading ? 'material-symbols:progress-activity' : icon" 
      width="28" 
      height="28" 
      class="stat-icon"
      :class="[colorVariant, { spin: loading }]" 
    />
    <div>
      <div class="stat-val">{{ loading ? '—' : value }}</div>
      <div class="stat-label">{{ label }}</div>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 95%, transparent);
  border-radius: 1.25rem;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(12px);
  transition: transform 0.2s, box-shadow 0.2s;
}

@media (max-width: 640px) {
  .stat-card {
    padding: 1rem;
  }
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0px 6px 20px rgba(24, 28, 32, 0.08);
}

.stat-icon {
  flex-shrink: 0;
}

.stat-icon.primary {
  color: var(--md-sys-color-primary);
}

.stat-icon.secondary {
  color: var(--md-sys-color-secondary);
}

.stat-icon.tertiary {
  color: var(--md-sys-color-tertiary);
}

.stat-icon.success {
  color: var(--md-sys-color-tertiary, #4caf82);
}

.stat-icon.error {
  color: var(--md-sys-color-error);
}

.stat-icon.outline {
  color: var(--md-sys-color-outline);
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.stat-val {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  color: var(--md-sys-color-on-surface);
  line-height: 1.2;
}

.stat-label {
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant);
  margin-top: 0.125rem;
  line-height: 1.2;
}
</style>
