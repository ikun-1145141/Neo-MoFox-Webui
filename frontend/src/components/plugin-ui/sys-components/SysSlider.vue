<script setup lang="ts">
/** SysSlider - 滑块组件。 */
import { ref, computed } from 'vue'

const props = defineProps<{
  label?: string
  value?: string | number
  min?: string | number
  max?: string | number
  step?: string | number
  disabled?: boolean
  showValue?: boolean
}>()

const emit = defineEmits<{
  (e: 'change', value: number): void
}>()

const isHovering = ref(false)
const isDragging = ref(false)

function handleInput(event: Event): void {
  emit('change', parseFloat((event.target as HTMLInputElement).value))
}

const displayValue = computed(() => {
  const v = typeof props.value === 'number' ? props.value : parseFloat(props.value || '50')
  return Number.isFinite(v) ? v : 0
})

const minNum = computed(() => parseFloat(String(props.min ?? 0)) || 0)
const maxNum = computed(() => parseFloat(String(props.max ?? 100)) || 100)
const percent = computed(() => {
  const range = maxNum.value - minNum.value
  if (range <= 0) return 0
  return ((displayValue.value - minNum.value) / range) * 100
})
</script>

<template>
  <div class="sys-slider-wrapper">
    <div
      v-if="label || showValue"
      class="sys-slider-header"
    >
      <label
        v-if="label"
        class="sys-slider-label"
      >{{ label }}</label>
      <span
        v-if="showValue"
        class="sys-slider-value"
      >{{ displayValue }}</span>
    </div>
    <div class="sys-slider-track-wrapper">
      <div
        class="sys-slider-rail"
        :class="{ 'sys-slider-rail--active': isDragging || isHovering }"
      >
        <div
          class="sys-slider-fill"
          :style="{ width: percent + '%' }"
        />
      </div>
      <input
        type="range"
        class="sys-slider"
        :value="value ?? 50"
        :min="min ?? 0"
        :max="max ?? 100"
        :step="step ?? 1"
        :disabled="disabled"
        @input="handleInput"
        @mouseenter="isHovering = true"
        @mouseleave="isHovering = false"
        @mousedown="isDragging = true"
        @mouseup="isDragging = false"
      >
    </div>
  </div>
</template>

<style scoped>
.sys-slider-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.sys-slider-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.sys-slider-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant, #44474e);
}

.sys-slider-value {
  font-size: 0.75rem;
  color: var(--md-sys-color-on-surface-variant, #44474e);
  font-variant-numeric: tabular-nums;
}

.sys-slider-track-wrapper {
  position: relative;
  height: 40px;
  display: flex;
  align-items: center;
}

.sys-slider-rail {
  position: absolute;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--md-sys-color-surface-container-highest, #e6e0e9);
  border-radius: 2px;
  pointer-events: none;
  transition: height var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized);
}

.sys-slider-rail--active {
  height: 6px;
}

.sys-slider-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: var(--md-sys-color-primary, #0058bd);
  border-radius: 2px;
  transition: width var(--md-sys-motion-duration-x-short) var(--md-sys-motion-standard);
}

.sys-slider {
  position: relative;
  width: 100%;
  margin: 0;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  cursor: pointer;
  z-index: 1;
}

.sys-slider::-webkit-slider-runnable-track {
  background: transparent;
  height: 4px;
}

.sys-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--md-sys-color-primary, #0058bd);
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  margin-top: -8px;
  transition:
    transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

.sys-slider:active::-webkit-slider-thumb {
  transform: scale(1.3);
  box-shadow: 0 0 0 8px color-mix(in srgb, var(--md-sys-color-primary, #0058bd) 12%, transparent);
}

.sys-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--md-sys-color-primary, #0058bd);
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition:
    transform var(--md-sys-motion-duration-short) var(--md-sys-motion-emphasized),
    box-shadow var(--md-sys-motion-duration-short) var(--md-sys-motion-standard);
}

.sys-slider::-moz-range-thumb:hover {
  transform: scale(1.15);
}

.sys-slider:active::-moz-range-thumb {
  transform: scale(1.3);
}

.sys-slider:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sys-slider:disabled::-webkit-slider-thumb {
  background: var(--md-sys-color-on-surface-variant, #44474e);
}
</style>
