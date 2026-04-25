<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
  icon?: string
}>()
</script>

<template>
  <div class="page-header">
    <div v-if="icon" class="page-header-icon">
      <Icon :icon="icon" width="28" height="28" />
    </div>
    <div>
      <h1 class="page-header-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header-sub">{{ subtitle }}</p>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}
.page-header-icon {
  width: 52px;
  height: 52px;
  border-radius: 1rem;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.page-header-title {
  margin: 0;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--md-sys-color-on-surface);
}
.page-header-sub {
  margin: 0.25rem 0 0;
  font-size: 0.9rem;
  color: var(--md-sys-color-on-surface-variant);
}
</style>
