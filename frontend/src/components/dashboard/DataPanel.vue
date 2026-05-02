<script setup lang="ts">
import Icon from '../common/Icon.vue'

interface DataItem {
  label: string
  value: string | number
}

interface Props {
  title: string
  icon: string
  items: DataItem[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})
</script>

<template>
  <div class="data-panel">
    <div class="panel-header">
      <Icon :icon="icon" width="24" height="24" />
      <h3>{{ title }}</h3>
    </div>
    <div class="panel-content">
      <div v-if="loading" class="loading-item">
        <div class="spinner"></div>
      </div>
      <div 
        v-else
        v-for="(item, index) in items" 
        :key="index"
        class="data-item"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>
  </div>
</template>

<style scoped>
.data-panel {
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 86%, transparent);
  border-radius: 1.25rem;
  padding: 1.5rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(8px);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 240px;
}

@media (max-width: 640px) {
  .data-panel {
    padding: 1rem;
    min-height: 200px;
  }
}

.data-panel:hover {
  transform: translateY(-2px);
  box-shadow: 0px 6px 20px rgba(24, 28, 32, 0.08);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  color: var(--md-sys-color-primary);
}

.panel-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
}

.loading-item {
  display: flex;
  justify-content: center;
  padding: 2rem 0;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--md-sys-color-outline-variant);
  border-top-color: var(--md-sys-color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.data-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.data-item:last-child {
  border-bottom: none;
}

.data-item span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.9375rem;
}

.data-item strong {
  color: var(--md-sys-color-on-surface);
  font-size: 0.9375rem;
  font-weight: 600;
}
</style>
