<script setup lang="ts">
/** SysSlider - 滑块组件。 */
defineProps<{ label?: string; value?: string; min?: string; max?: string; step?: string; disabled?: boolean }>()
const emit = defineEmits<{ (e: 'change', value: number): void }>()
function handleInput(event: Event): void { emit('change', parseFloat((event.target as HTMLInputElement).value)) }
</script>
<template>
  <div class="sys-slider-wrapper">
    <label v-if="label" class="sys-slider-label">{{ label }}</label>
    <input type="range" class="sys-slider" :value="value || '50'" :min="min || '0'" :max="max || '100'"
      :step="step || '1'" :disabled="disabled" @input="handleInput" />
  </div>
</template>
<style scoped>
.sys-slider-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.sys-slider-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
}

.sys-slider {
  width: 100%;
  accent-color: var(--md-sys-color-primary);
}

.sys-slider:disabled {
  opacity: 0.5;
}
</style>
