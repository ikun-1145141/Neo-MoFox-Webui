<!--
  @file DictField.vue
  @description 字典字段编辑器组件
  
  功能：
  - 支持字典/对象类型字段的编辑
  - 添加、删除、编辑键值对
  - Material Design 3 样式
-->
<template>
  <div class="dict-field">
    <!-- 键值对列表 -->
    <div v-if="entries.length > 0" class="dict-entries">
      <div
        v-for="(entry, index) in entries"
        :key="index"
        class="dict-entry"
      >
        <div class="dict-entry-content">
          <input
            v-model="entry.key"
            type="text"
            class="dict-key-input"
            :readonly="readonly"
            placeholder="键"
            @input="handleEntryChange"
          />
          <span class="dict-separator">:</span>
          <input
            v-model="entry.value"
            type="text"
            class="dict-value-input"
            :readonly="readonly"
            placeholder="值"
            @input="handleEntryChange"
          />
        </div>
        <button
          v-if="!readonly"
          type="button"
          class="icon-btn delete-btn"
          @click="removeEntry(index)"
          title="删除"
        >
          <Icon icon="material-symbols:close-rounded" :size="20" />
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <Icon icon="material-symbols:data-object-rounded" :size="32" />
      <span>暂无键值对</span>
    </div>

    <!-- 添加按钮 -->
    <button
      v-if="!readonly"
      type="button"
      class="add-btn"
      @click="addEntry"
    >
      <Icon icon="material-symbols:add-rounded" :size="20" />
      <span>添加键值对</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Icon from '../../common/Icon.vue'
import type { FieldSchema } from '@/api/types/config'

interface Props {
  modelValue: Record<string, any>
  field: FieldSchema
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({}),
  readonly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
}>()

// 内部状态：键值对数组
interface DictEntry {
  key: string
  value: string
}

const entries = ref<DictEntry[]>([])

// 初始化数据
watch(
  () => props.modelValue,
  (newValue) => {
    if (typeof newValue === 'object' && newValue !== null && !Array.isArray(newValue)) {
      entries.value = Object.entries(newValue).map(([key, value]) => ({
        key,
        value: String(value)
      }))
    } else {
      entries.value = []
    }
  },
  { immediate: true }
)

// 添加键值对
function addEntry() {
  entries.value.push({ key: '', value: '' })
  emitChange()
}

// 删除键值对
function removeEntry(index: number) {
  entries.value.splice(index, 1)
  emitChange()
}

// 处理键值对变更
function handleEntryChange() {
  emitChange()
}

// 发出变更事件
function emitChange() {
  // 过滤掉空键的条目
  const validEntries = entries.value.filter(entry => entry.key.trim() !== '')
  
  // 转换为对象
  const dict: Record<string, any> = {}
  validEntries.forEach(entry => {
    // 尝试解析值为合适的类型
    const value = entry.value.trim()
    
    // 尝试解析为数字
    if (value !== '' && !isNaN(Number(value))) {
      dict[entry.key] = Number(value)
    }
    // 尝试解析为布尔值
    else if (value === 'true') {
      dict[entry.key] = true
    }
    else if (value === 'false') {
      dict[entry.key] = false
    }
    // 尝试解析为 null
    else if (value === 'null') {
      dict[entry.key] = null
    }
    // 否则保持为字符串
    else {
      dict[entry.key] = value
    }
  })
  
  emit('update:modelValue', dict)
}
</script>

<style scoped>
.dict-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dict-entries {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dict-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  padding: 8px 12px;
  transition: all 0.2s;
}

.dict-entry:hover {
  border-color: var(--md-sys-color-outline);
}

.dict-entry:focus-within {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 3px rgba(0, 88, 189, 0.1);
}

.dict-entry-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dict-key-input,
.dict-value-input {
  flex: 1;
  padding: 6px 8px;
  font-size: 14px;
  color: var(--md-sys-color-on-surface);
  background: transparent;
  border: none;
  outline: none;
  font-family: inherit;
  min-width: 0;
}

.dict-key-input {
  font-weight: 500;
  color: var(--md-sys-color-primary);
}

.dict-key-input:read-only,
.dict-value-input:read-only {
  cursor: not-allowed;
  opacity: 0.7;
}

.dict-key-input::placeholder,
.dict-value-input::placeholder {
  color: var(--md-sys-color-on-surface-variant);
  opacity: 0.6;
}

.dict-separator {
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 500;
  flex-shrink: 0;
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
