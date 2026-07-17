<!--
  @file UISwitch.vue
  @description 开关切换组件，支持布尔值双向绑定。
  消费共享工具：dataStore（getValueByPath / setValueByPath）。
-->
<template>
  <div class="ui-switch" :class="{ 'is-disabled': node.attrs.disabled === 'true' }">
    <label class="switch-control">
      <input
        type="checkbox"
        :id="node.attrs.id"
        v-model="boundValue"
        :disabled="node.attrs.disabled === 'true'"
      />
      <span class="slider"></span>
    </label>
    <span v-if="node.attrs.label" class="switch-label">
      {{ node.attrs.label }}
    </span>
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
    if (!bindPath.value) return false
    return !!getValue(dataStore, bindPath.value)
  },
  set: (val) => {
    if (!bindPath.value) return
    setValue(dataStore, bindPath.value, val)
  },
})
</script>

<style scoped>
.ui-switch {
  display: flex;
  align-items: center;
  gap: 12px;
  user-select: none;
  padding: 4px 0;
}

.switch-control {
  position: relative;
  display: inline-block;
  width: 52px;
  height: 32px;
  flex-shrink: 0;
}

.switch-control input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: var(--md-sys-color-surface-container-highest);
  border: 2px solid var(--md-sys-color-outline);
  transition: 0.3s;
  border-radius: 34px;
}

.slider:before {
  position: absolute;
  content: '';
  height: 20px;
  width: 20px;
  left: 4px;
  bottom: 4px;
  background-color: var(--md-sys-color-outline);
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: var(--md-sys-color-primary);
  border-color: var(--md-sys-color-primary);
}

input:checked + .slider:before {
  transform: translateX(20px);
  background-color: var(--md-sys-color-on-primary);
}

input:disabled + .slider {
  opacity: 0.38;
  cursor: not-allowed;
}

.switch-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface);
}

.is-disabled .switch-label {
  color: var(--md-sys-color-on-surface);
  opacity: 0.38;
}
</style>
