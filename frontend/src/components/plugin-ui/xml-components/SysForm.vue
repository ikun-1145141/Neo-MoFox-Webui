<script setup lang="ts">
/** SysForm - 表单容器组件。 */
defineProps<{ gap?: string }>()
const emit = defineEmits<{ (e: 'submit'): void }>()
function handleSubmit(event: Event): void { event.preventDefault(); emit('submit') }
</script>
<template>
  <form class="sys-form" :style="{ gap: gap || '1rem' }" @submit="handleSubmit">
    <slot />
  </form>
</template>
<style scoped>
.sys-form { display: flex; flex-direction: column; width: 100%; }
</style>
