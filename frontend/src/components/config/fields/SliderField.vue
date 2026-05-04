<!--
  @file SliderField.vue
  @description 滑块输入字段组件
  
  功能：
  - 数字滑块输入
  - 实时显示当前值
  - 支持最小值、最大值、步进值
  - Material Design 3 样式
-->
<template>
  <div class="slider-field">
    <div class="slider-container">
      <input
        type="range"
        :value="modelValue"
        @input="handleInput"
        :disabled="readonly"
        :min="field.ge ?? field.gt ?? 0"
        :max="field.le ?? field.lt ?? 100"
        :step="field.step ?? 1"
        class="slider-input"
      />
    </div>
    
    <div class="slider-footer">
      <div class="slider-labels">
        <span class="slider-min">{{ field.ge ?? field.gt ?? 0 }}</span>
        <span class="slider-max">{{ field.le ?? field.lt ?? 100 }}</span>
      </div>
      <div class="slider-value">
        <input
          type="number"
          :value="modelValue"
          @input="handleNumberInput"
          :readonly="readonly"
          :min="field.ge ?? field.gt ?? 0"
          :max="field.le ?? field.lt ?? 100"
          :step="field.step ?? 1"
          class="value-input"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FieldSchema } from '@/api/types/config'

interface Props {
  modelValue: number
  field: FieldSchema
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  const value = parseFloat(target.value)
  emit('update:modelValue', isNaN(value) ? 0 : value)
}

function handleNumberInput(event: Event) {
  const target = event.target as HTMLInputElement
  let value = parseFloat(target.value)
  
  if (isNaN(value)) {
    value = 0
  }
  
  // 应用范围限制
  const min = props.field.ge ?? props.field.gt ?? 0
  const max = props.field.le ?? props.field.lt ?? 100
  
  if (value < min) value = min
  if (value > max) value = max
  
  emit('update:modelValue', value)
}
</script>

<style scoped>
.slider-field {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.slider-container {
  padding: 8px 0;
}

.slider-input {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--md-sys-color-surface-container-highest);
  border-radius: 3px;
  outline: none;
  transition: all 0.2s;
}

.slider-input:hover {
  background: var(--md-sys-color-surface-container-high);
}

.slider-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Webkit (Chrome, Safari, Edge) 滑块样式 */
.slider-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--md-sys-color-primary);
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider-input::-webkit-slider-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.3);
}

.slider-input::-webkit-slider-thumb:active {
  transform: scale(1.05);
}

.slider-input:disabled::-webkit-slider-thumb {
  cursor: not-allowed;
  opacity: 0.5;
}

/* Firefox 滑块样式 */
.slider-input::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 50%;
  background: var(--md-sys-color-primary);
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider-input::-moz-range-thumb:hover {
  transform: scale(1.15);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.3);
}

.slider-input::-moz-range-thumb:active {
  transform: scale(1.05);
}

.slider-input:disabled::-moz-range-thumb {
  cursor: not-allowed;
  opacity: 0.5;
}

/* Firefox 轨道样式 */
.slider-input::-moz-range-track {
  background: var(--md-sys-color-surface-container-highest);
  border-radius: 3px;
  height: 6px;
}

.slider-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.slider-labels {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 500;
}

.slider-value {
  display: flex;
  align-items: center;
  gap: 8px;
}

.value-input {
  width: 80px;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--md-sys-color-primary);
  background: var(--md-sys-color-primary-container);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  outline: none;
  transition: all 0.2s;
  text-align: center;
  font-family: inherit;
}

.value-input:focus {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 3px rgba(0, 88, 189, 0.1);
}

.value-input:read-only {
  background: var(--md-sys-color-surface-container-low);
  cursor: not-allowed;
  opacity: 0.7;
}

/* Chrome, Safari, Edge 数字输入框去除上下箭头 */
.value-input::-webkit-outer-spin-button,
.value-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* Firefox 数字输入框去除上下箭头 */
.value-input[type=number] {
  -moz-appearance: textfield;
  appearance: textfield;
}
</style>
