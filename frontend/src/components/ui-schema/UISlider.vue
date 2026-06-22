<!--
  @file UISlider.vue
  @description 滑块组件，支持数值范围选择。
  消费共享工具：dataStore（getValueByPath / setValueByPath）。
-->
<template>
  <div class="ui-slider" :class="{ 'is-disabled': node.attrs.disabled === 'true' }">
    <div class="slider-header">
      <label v-if="node.attrs.label" :for="node.attrs.id" class="field-label">
        {{ node.attrs.label }}
      </label>
      <span class="slider-value">{{ boundValue }}</span>
    </div>
    <div class="slider-wrapper">
      <input
        type="range"
        :id="node.attrs.id"
        v-model.number="boundValue"
        :min="Number(node.attrs.min || 0)"
        :max="Number(node.attrs.max || 100)"
        :step="Number(node.attrs.step || 1)"
        :disabled="node.attrs.disabled === 'true'"
        class="range-input"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import { getValueByPath, setValueByPath } from '@/utils/dataStore'

interface Props {
  node: UiNode
  store?: Record<string, any>
  apiBase?: string
}

const props = defineProps<Props>()

const dataStore = props.store || inject<any>('uiSchemaDataStore')
const getValue = inject<any>('uiSchemaGetValue', getValueByPath)
const setValue = inject<any>('uiSchemaSetValue', setValueByPath)

const bindPath = computed(() => props.node.attrs['data-bind'])

const boundValue = computed({
  get: () => {
    if (!bindPath.value) return Number(props.node.attrs.min || 0)
    return Number((getValue(dataStore, bindPath.value) ?? props.node.attrs.min) || 0)
  },
  set: (val) => {
    if (!bindPath.value) return
    setValue(dataStore, bindPath.value, val)
  },
})
</script>

<style scoped>
.ui-slider {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface);
}

.slider-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--md-sys-color-primary);
  background: var(--md-sys-color-primary-container);
  padding: 2px 8px;
  border-radius: 12px;
  min-width: 24px;
  text-align: center;
}

.slider-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
  height: 32px;
}

.range-input {
  width: 100%;
  height: 4px;
  background: var(--md-sys-color-surface-container-highest);
  border-radius: 2px;
  outline: none;
  appearance: none;
  cursor: pointer;
}

.range-input::-webkit-slider-thumb {
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--md-sys-color-primary);
  cursor: pointer;
  transition: transform 0.1s;
}

.range-input::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.range-input:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.range-input:disabled::-webkit-slider-thumb {
  background: var(--md-sys-color-on-surface);
  cursor: not-allowed;
}

.is-disabled .slider-value {
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container-highest);
  opacity: 0.38;
}
</style>
