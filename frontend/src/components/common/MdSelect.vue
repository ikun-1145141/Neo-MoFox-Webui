<!--
  @file MdSelect.vue
  @description Material Design 3 下拉选择组件
  
  功能：
  - MD3 Outlined 风格
  - 支持键盘导航（上下键、回车、ESC）
  - 点击外部自动关闭
  - 禁用状态支持
  - 可选的占位符文本
  - 无障碍访问支持
-->
<template>
  <div
    class="md-select"
    :class="{
      'md-select--disabled': disabled,
      'md-select--focused': isFocused,
      'md-select--open': isOpen,
      'md-select--error': error,
    }"
    ref="selectRef"
  >
    <!-- 选择框主体 -->
    <div
      class="md-select__field"
      @click="toggleDropdown"
      @keydown.enter.prevent="toggleDropdown"
      @keydown.space.prevent="toggleDropdown"
      @keydown.down.prevent="openDropdown"
      @keydown.up.prevent="openDropdown"
      @keydown.esc="closeDropdown"
      :tabindex="disabled ? -1 : 0"
      role="combobox"
      :aria-expanded="isOpen"
      :aria-haspopup="true"
      :aria-disabled="disabled"
      @focus="handleFocus"
      @blur="handleBlur"
    >
      <!-- 显示的值 -->
      <div class="md-select__value">
        <span v-if="hasValue" class="md-select__text">
          {{ displayText }}
        </span>
        <span v-else class="md-select__placeholder">
          {{ placeholder }}
        </span>
      </div>

      <!-- 下拉图标 -->
      <div class="md-select__icon">
        <Icon
          :icon="isOpen ? 'material-symbols:arrow-drop-up-rounded' : 'material-symbols:arrow-drop-down-rounded'"
          :width="24"
          :height="24"
        />
      </div>

      <!-- 简化外框 -->
      <div class="md-select__outline"></div>
    </div>

    <!-- 下拉选项面板 -->
    <Transition name="dropdown">
      <div
        v-show="isOpen"
        class="md-select__dropdown"
        :style="dropdownStyle"
        role="listbox"
        @mousedown.prevent
      >
        <div
          v-for="(option, index) in options"
          :key="getOptionValue(option, index)"
          class="md-select__option"
          :class="{
            'md-select__option--selected': isSelected(option),
            'md-select__option--highlighted': highlightedIndex === index,
          }"
          role="option"
          :aria-selected="isSelected(option)"
          @click="selectOption(option)"
          @mouseenter="highlightedIndex = index"
        >
          <!-- 选中图标 -->
          <Icon
            v-if="isSelected(option)"
            icon="material-symbols:check-rounded"
            :width="20"
            :height="20"
            class="md-select__option-check"
          />
          <span class="md-select__option-text">
            {{ getOptionLabel(option) }}
          </span>
        </div>

        <!-- 空状态 -->
        <div v-if="options.length === 0" class="md-select__empty">
          <Icon icon="material-symbols:info-outline-rounded" :width="20" :height="20" />
          <span>{{ emptyText }}</span>
        </div>
      </div>
    </Transition>

    <!-- 辅助文本 / 错误提示 -->
    <div v-if="helperText || error" class="md-select__helper-text" :class="{ 'md-select__helper-text--error': error }">
      {{ error || helperText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'

// Props
interface Props {
  modelValue?: string | number | null
  options?: Array<string | number | { label: string; value: string | number }>
  label?: string
  placeholder?: string
  disabled?: boolean
  error?: string
  helperText?: string
  emptyText?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  options: () => [],
  placeholder: '-- 请选择 --',
  disabled: false,
  emptyText: '暂无选项',
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
  change: [value: string | number | null]
}>()

// State
const selectRef = ref<HTMLDivElement>()
const isOpen = ref(false)
const isFocused = ref(false)
const highlightedIndex = ref(-1)
const dropdownStyle = ref<Record<string, string>>({})

// Computed
const hasValue = computed(() => {
  return props.modelValue !== null && props.modelValue !== undefined && props.modelValue !== ''
})

const displayText = computed(() => {
  if (!hasValue.value) return ''
  const option = props.options.find((opt) => getOptionValue(opt) === props.modelValue)
  return option ? getOptionLabel(option) : String(props.modelValue)
})

// Methods
function getOptionValue(option: any, index?: number): string | number {
  if (typeof option === 'object' && option !== null) {
    return option.value
  }
  return option
}

function getOptionLabel(option: any): string {
  if (typeof option === 'object' && option !== null) {
    return option.label
  }
  return String(option)
}

function isSelected(option: any): boolean {
  return getOptionValue(option) === props.modelValue
}

function toggleDropdown() {
  if (props.disabled) return
  isOpen.value ? closeDropdown() : openDropdown()
}

function openDropdown() {
  if (props.disabled) return
  isOpen.value = true
  updateDropdownPosition()

  // 高亮当前选中项
  const selectedIndex = props.options.findIndex((opt) => isSelected(opt))
  highlightedIndex.value = selectedIndex >= 0 ? selectedIndex : 0

  // 滚动到高亮项
  setTimeout(() => {
    scrollToHighlighted()
  }, 50)
}

function closeDropdown() {
  isOpen.value = false
  highlightedIndex.value = -1
}

function selectOption(option: any) {
  const value = getOptionValue(option)
  emit('update:modelValue', value)
  emit('change', value)
  closeDropdown()
}

function handleFocus() {
  isFocused.value = true
}

function handleBlur() {
  isFocused.value = false
}

function updateDropdownPosition() {
  if (!selectRef.value) return

  const rect = selectRef.value.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const spaceAbove = rect.top
  const dropdownHeight = Math.min(props.options.length * 48 + 16, 320)

  // 判断是向上还是向下展开
  const openUpward = spaceBelow < dropdownHeight && spaceAbove > spaceBelow

  if (openUpward) {
    dropdownStyle.value = {
      bottom: '100%',
      marginBottom: '4px',
      maxHeight: `${Math.min(dropdownHeight, spaceAbove - 8)}px`,
    }
  } else {
    dropdownStyle.value = {
      top: '100%',
      marginTop: '4px',
      maxHeight: `${Math.min(dropdownHeight, spaceBelow - 8)}px`,
    }
  }
}

function scrollToHighlighted() {
  const dropdown = selectRef.value?.querySelector('.md-select__dropdown')
  const highlighted = dropdown?.querySelector('.md-select__option--highlighted')
  if (dropdown && highlighted) {
    highlighted.scrollIntoView({ block: 'nearest' })
  }
}

// 点击外部关闭
function handleClickOutside(event: MouseEvent) {
  if (selectRef.value && !selectRef.value.contains(event.target as Node)) {
    closeDropdown()
  }
}

// 键盘导航
function handleKeyDown(event: KeyboardEvent) {
  if (!isOpen.value || props.disabled) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      highlightedIndex.value = Math.min(highlightedIndex.value + 1, props.options.length - 1)
      scrollToHighlighted()
      break
    case 'ArrowUp':
      event.preventDefault()
      highlightedIndex.value = Math.max(highlightedIndex.value - 1, 0)
      scrollToHighlighted()
      break
    case 'Enter':
      event.preventDefault()
      if (highlightedIndex.value >= 0 && highlightedIndex.value < props.options.length) {
        selectOption(props.options[highlightedIndex.value])
      }
      break
    case 'Escape':
      event.preventDefault()
      closeDropdown()
      selectRef.value?.querySelector<HTMLDivElement>('.md-select__field')?.focus()
      break
  }
}

// 监听选项变化，重新计算下拉位置
watch(() => props.options, () => {
  if (isOpen.value) {
    updateDropdownPosition()
  }
})

// 生命周期
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeyDown)
  window.addEventListener('resize', updateDropdownPosition)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('resize', updateDropdownPosition)
})
</script>

<style scoped>
/* ===== 主容器 ===== */
.md-select {
  position: relative;
  width: 100%;
  font-family: inherit;
}

/* ===== 选择框主体 ===== */
.md-select__field {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 48px;
  padding: 12px 16px;
  cursor: pointer;
  outline: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.md-select--disabled .md-select__field {
  cursor: not-allowed;
  opacity: 0.38;
}

/* ===== 显示的值 ===== */
.md-select__value {
  flex: 1;
  min-height: 24px;
  display: flex;
  align-items: center;
}

.md-select__text {
  font-size: 16px;
  color: var(--md-sys-color-on-surface);
  line-height: 24px;
}

.md-select__placeholder {
  font-size: 16px;
  color: var(--md-sys-color-on-surface-variant);
  line-height: 24px;
  opacity: 0.6;
}

/* ===== 图标 ===== */
.md-select__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 8px;
  color: var(--md-sys-color-on-surface-variant);
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.md-select--open .md-select__icon {
  transform: rotate(180deg);
}

/* ===== 简化外框 ===== */
.md-select__outline {
  position: absolute;
  inset: 0;
  pointer-events: none;
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 4px;
  transition: border-color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Focused 状态 */
.md-select--focused .md-select__outline {
  border-color: var(--md-sys-color-primary);
  border-width: 2px;
}

/* Error 状态 */
.md-select--error .md-select__outline {
  border-color: var(--md-sys-color-error);
}

/* Hover 状态 */
.md-select:not(.md-select--disabled):hover .md-select__outline {
  border-color: var(--md-sys-color-on-surface);
}

/* ===== 下拉面板 ===== */
.md-select__dropdown {
  position: absolute;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--md-sys-color-surface-container);
  border-radius: 4px;
  box-shadow:
    0px 5px 5px -3px rgba(0, 0, 0, 0.2),
    0px 8px 10px 1px rgba(0, 0, 0, 0.14),
    0px 3px 14px 2px rgba(0, 0, 0, 0.12);
  overflow-y: auto;
  padding: 4px 0;
}

/* ===== 选项 ===== */
.md-select__option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  min-height: 48px;
  cursor: pointer;
  transition: background-color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}

.md-select__option:hover,
.md-select__option--highlighted {
  background: var(--md-sys-color-surface-container-highest);
}

.md-select__option--selected {
  background: var(--md-sys-color-secondary-container);
}

.md-select__option-check {
  color: var(--md-sys-color-primary);
}

.md-select__option-text {
  flex: 1;
  font-size: 16px;
  line-height: 24px;
  color: var(--md-sys-color-on-surface);
}

/* ===== 空状态 ===== */
.md-select__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 16px;
  font-size: 14px;
  color: var(--md-sys-color-on-surface-variant);
}

/* ===== 辅助文本 ===== */
.md-select__helper-text {
  margin-top: 4px;
  padding: 0 16px;
  font-size: 12px;
  line-height: 16px;
  color: var(--md-sys-color-on-surface-variant);
  transition: color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.md-select__helper-text--error {
  color: var(--md-sys-color-error);
}

/* ===== 动画 ===== */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: top;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: scaleY(0.8);
}
</style>
