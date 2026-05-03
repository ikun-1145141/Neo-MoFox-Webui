<!--
  @file ListField.vue
  @description 列表字段编辑器组件
  
  功能：
  - 支持数组类型字段的编辑
  - 添加、删除、编辑列表项
  - Material Design 3 样式
-->
<template>
  <div class="list-field">
    <!-- 列表项 -->
    <div v-if="items.length > 0" class="list-items">
      <div
        v-for="(_item, index) in items"
        :key="index"
        class="list-item"
      >
        <div class="list-item-index">{{ index + 1 }}</div>
        <input
          :ref="el => setInputRef(el as HTMLInputElement, index)"
          v-model="items[index]"
          type="text"
          class="list-item-input"
          :readonly="readonly"
          :placeholder="`项目 ${index + 1}`"
          @input="handleItemChange"
        />
        <button
          v-if="!readonly"
          type="button"
          class="icon-btn delete-btn"
          @click="removeItem(index)"
          title="删除"
        >
          <Icon icon="material-symbols:close-rounded" :size="20" />
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <Icon icon="material-symbols:list-alt-outline-rounded" :size="32" />
      <span>暂无项目</span>
    </div>

    <!-- 添加按钮 -->
    <button
      v-if="!readonly"
      type="button"
      class="add-btn"
      @click="addItem"
    >
      <Icon icon="material-symbols:add-rounded" :size="20" />
      <span>添加项目</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import Icon from '../../common/Icon.vue'
import type { FieldSchema } from '@/api/types/config'

interface Props {
  modelValue: string[] | any[]
  field: FieldSchema
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

// 内部状态
const items = ref<string[]>([])
const inputRefs = ref<Map<number, HTMLInputElement>>(new Map())

// 设置输入框引用
function setInputRef(el: HTMLInputElement | null, index: number) {
  if (el) {
    inputRefs.value.set(index, el)
  } else {
    inputRefs.value.delete(index)
  }
}

// 初始化数据
watch(
  () => props.modelValue,
  (newValue) => {
    if (Array.isArray(newValue)) {
      items.value = [...newValue]
    } else {
      items.value = []
    }
  },
  { immediate: true }
)

// 添加项目
async function addItem() {
  const newIndex = items.value.length
  items.value.push('')
  emitChange()
  
  // 等待 DOM 更新后聚焦到新输入框
  await nextTick()
  const newInput = inputRefs.value.get(newIndex)
  if (newInput) {
    newInput.focus()
  }
}

// 删除项目
function removeItem(index: number) {
  items.value.splice(index, 1)
  emitChange()
}

// 处理项目变更
function handleItemChange() {
  emitChange()
}

// 发出变更事件
function emitChange() {
  // 直接发出所有项目，包括空项目
  // 让父组件或提交时决定如何处理空值
  emit('update:modelValue', [...items.value])
}
</script>

<style scoped>
.list-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  padding: 8px 12px;
  transition: all 0.2s;
}

.list-item:hover {
  border-color: var(--md-sys-color-outline);
}

.list-item:focus-within {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 3px rgba(0, 88, 189, 0.1);
}

.list-item-index {
  min-width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.list-item-input {
  flex: 1;
  padding: 6px 8px;
  font-size: 14px;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  border: none;
  outline: none;
  font-family: inherit;
}

.list-item-input:read-only {
  cursor: not-allowed;
  opacity: 0.7;
}

.list-item-input::placeholder {
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.6;
}

.icon-btn {
  background: none;
  border: none;
  color: var(--md-sys-color-on-surface-variant);
  cursor: pointer;
  padding: 6px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.icon-btn:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.delete-btn {
  color: var(--md-sys-color-error);
}

.delete-btn:hover {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  gap: 8px;
  color: var(--md-sys-color-on-surface-variant);
  background: var(--md-sys-color-surface-container-low);
  border: 1px dashed var(--md-sys-color-outline-variant);
  border-radius: 8px;
}

.empty-state span {
  font-size: 14px;
}

.add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px;
  background: var(--md-sys-color-surface);
  border: 2px dashed var(--md-sys-color-outline-variant);
  border-radius: 8px;
  color: var(--md-sys-color-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.add-btn:hover {
  background: var(--md-sys-color-primary-container);
  border-color: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary-container);
}

.add-btn:active {
  transform: scale(0.98);
}
</style>
