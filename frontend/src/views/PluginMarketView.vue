<script setup lang="ts">
import AppShell from '../components/common/AppShell.vue'
</script>

<template>
  <AppShell no-padding>
    <div style="position: relative; flex: 1 1 auto; width: 100%; min-width: 0; min-height: 0; overflow: hidden">
      <iframe
        src="/webui/plugin-market/"
        title="插件市场"
        loading="eager"
        referrerpolicy="same-origin"
        style="position: absolute; inset: 0; display: block; width: 100%; height: 100%; border: 0; background: var(--md-sys-color-surface)"
      />
    </div>
  </AppShell>
</template>
