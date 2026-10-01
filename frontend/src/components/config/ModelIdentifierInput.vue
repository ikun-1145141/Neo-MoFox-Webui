<template>
  <div ref="fieldRef" class="model-identifier">
    <div class="model-identifier__field" :class="{ 'model-identifier__field--open': isOpen }">
      <input
        :id="inputId"
        ref="inputRef"
        :value="modelValue"
        type="text"
        required
        autocomplete="off"
        spellcheck="false"
        role="combobox"
        aria-autocomplete="list"
        aria-haspopup="listbox"
        :aria-expanded="isOpen"
        :aria-controls="listId"
        :aria-activedescendant="activeOptionId"
        :aria-describedby="hintId"
        :placeholder="t('modelEditDialog.modelList.placeholder')"
        @focus="openDropdown"
        @click="openDropdown"
        @input="handleInput"
        @keydown="handleKeyDown"
        @compositionstart="composing = true"
        @compositionend="handleCompositionEnd"
      />
      <button
        type="button"
        class="model-identifier__toggle"
        tabindex="-1"
        :aria-label="t('modelEditDialog.modelList.toggleLabel')"
        :aria-expanded="isOpen"
        @mousedown.prevent
        @click="toggleDropdown"
      >
        <Icon
          :icon="
            isOpen
              ? 'material-symbols:arrow-drop-up-rounded'
              : 'material-symbols:arrow-drop-down-rounded'
          "
          :size="24"
        />
      </button>
    </div>
    <p :id="hintId" class="model-identifier__hint">
      {{ t('modelEditDialog.modelList.manualHint') }}
    </p>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="dropdownRef"
        class="model-identifier__dropdown"
        :style="dropdownStyle"
        @mousedown.prevent
      >
        <div
          :id="listId"
          class="model-identifier__list"
          role="listbox"
          :aria-label="t('modelEditDialog.modelList.listLabel')"
          :aria-busy="loading"
        >
          <div v-if="loading" class="model-identifier__status" role="status" aria-live="polite">
            <span class="model-identifier__spinner" aria-hidden="true"></span>
            <span>{{ t('modelEditDialog.modelList.loading') }}</span>
          </div>
          <div v-else-if="notice" class="model-identifier__status" role="status">{{ notice }}</div>
          <div
            v-else-if="error"
            class="model-identifier__status model-identifier__status--error"
            role="status"
          >
            {{ error }}
          </div>
          <div v-else-if="!filteredOptions.length" class="model-identifier__status" role="status">
            {{
              options.length
                ? t('modelEditDialog.modelList.noMatch')
                : t('modelEditDialog.modelList.empty')
            }}
          </div>
          <template v-else>
            <div
              v-for="(option, index) in filteredOptions"
              :id="optionId(index)"
              :key="option.id"
              class="model-identifier__option"
              :class="{
                'model-identifier__option--highlighted': highlightedIndex === index,
                'model-identifier__option--selected': option.id === modelValue,
              }"
              role="option"
              :aria-selected="option.id === modelValue"
              @mouseenter="highlightedIndex = index"
              @click="selectOption(option)"
            >
              <span class="model-identifier__option-label">
                <span class="model-identifier__id">{{ option.id }}</span>
                <span
                  v-if="option.display_name && option.display_name !== option.id"
                  class="model-identifier__name"
                >
                  {{ option.display_name }}
                </span>
              </span>
              <Icon
                v-if="option.id === modelValue"
                icon="material-symbols:check-rounded"
                :size="20"
              />
            </div>
          </template>
        </div>
        <button
          v-if="error && !loading && !notice"
          type="button"
          class="model-identifier__retry"
          @click="emit('retry')"
        >
          {{ t('modelEditDialog.modelList.retry') }}
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { RemoteModelOption } from '@/api/types/config'
import { useI18n } from '@/utils/i18n'
import {
  closeOtherDropdowns,
  registerDropdown,
  unregisterDropdown,
} from '@/utils/useDropdownManager'
import Icon from '../common/Icon.vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    options: RemoteModelOption[]
    loading: boolean
    error: string
    notice: string
    resetKey: string
    inputId?: string
  }>(),
  { inputId: 'model-identifier' }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  select: [option: RemoteModelOption]
  open: []
  close: []
  retry: []
}>()

const { t } = useI18n()
const fieldRef = ref<HTMLDivElement>()
const inputRef = ref<HTMLInputElement>()
const dropdownRef = ref<HTMLDivElement>()
const isOpen = ref(false)
const composing = ref(false)
const query = ref('')
const highlightedIndex = ref(-1)
const dropdownStyle = ref<Record<string, string>>({})
const listId = computed(() => props.inputId + '-list')
const hintId = computed(() => props.inputId + '-hint')
const currentInstance = { close: closeDropdown }
let resizeObserver: ResizeObserver | undefined

const filteredOptions = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  if (!keyword) return props.options
  return props.options.filter(
    (option) =>
      option.id.toLowerCase().includes(keyword) ||
      (option.display_name ?? '').toLowerCase().includes(keyword)
  )
})
const activeOptionId = computed(() =>
  isOpen.value &&
  !props.loading &&
  !props.error &&
  !props.notice &&
  filteredOptions.value[highlightedIndex.value]
    ? optionId(highlightedIndex.value)
    : undefined
)

function optionId(index: number): string {
  return props.inputId + '-option-' + index
}

function openDropdown() {
  if (isOpen.value) return
  closeOtherDropdowns(currentInstance)
  isOpen.value = true
  // 展开时展示全部模型，不把已有 ID 自动当成搜索条件。
  query.value = ''
  highlightedIndex.value = -1
  updatePosition()
  emit('open')
  void nextTick(updatePosition)
}

function closeDropdown() {
  if (!isOpen.value) return
  isOpen.value = false
  highlightedIndex.value = -1
  emit('close')
}

function toggleDropdown() {
  if (isOpen.value) {
    closeDropdown()
  } else {
    inputRef.value?.focus({ preventScroll: true })
    openDropdown()
  }
}

function handleInput(event: Event) {
  const value = (event.target as HTMLInputElement).value
  openDropdown()
  emit('update:modelValue', value)
  if (!composing.value) query.value = value
}

function handleCompositionEnd(event: CompositionEvent) {
  composing.value = false
  handleInput(event)
}

function selectOption(option: RemoteModelOption) {
  emit('update:modelValue', option.id)
  emit('select', option)
  closeDropdown()
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.isComposing || composing.value || event.keyCode === 229) return
  if (event.key === 'Tab') {
    closeDropdown()
    return
  }
  if (event.key === 'Escape' && isOpen.value) {
    event.preventDefault()
    event.stopPropagation()
    closeDropdown()
    return
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    openDropdown()
    if (props.loading || props.error || props.notice) return
    const count = filteredOptions.value.length
    if (!count) return
    if (event.key === 'ArrowDown') {
      highlightedIndex.value = (highlightedIndex.value + 1) % count
    } else {
      highlightedIndex.value = highlightedIndex.value <= 0 ? count - 1 : highlightedIndex.value - 1
    }
    void nextTick(() => {
      dropdownRef.value
        ?.querySelector('.model-identifier__option--highlighted')
        ?.scrollIntoView({ block: 'nearest' })
    })
  } else if (event.key === 'Enter' && isOpen.value) {
    // 未高亮选项时保留手动输入，不允许回车穿透到弹窗提交。
    event.preventDefault()
    event.stopPropagation()
    const option = filteredOptions.value[highlightedIndex.value]
    if (option && !props.loading && !props.error && !props.notice) {
      selectOption(option)
    } else if (props.error && !props.loading && !props.notice) {
      emit('retry')
    } else {
      closeDropdown()
    }
  }
}

function handleOutside(event: Event) {
  if (!isOpen.value || !(event.target instanceof Node)) return
  if (!fieldRef.value?.contains(event.target) && !dropdownRef.value?.contains(event.target))
    closeDropdown()
}

function updatePosition() {
  if (!isOpen.value || !inputRef.value) return
  const rect = inputRef.value.getBoundingClientRect()
  const viewport = window.visualViewport
  const top = viewport?.offsetTop ?? 0
  const left = viewport?.offsetLeft ?? 0
  const height = viewport?.height ?? window.innerHeight
  const width = viewport?.width ?? window.innerWidth
  if (rect.bottom < top || rect.top > top + height) {
    closeDropdown()
    return
  }
  const below = Math.max(0, top + height - rect.bottom - 8)
  const above = Math.max(0, rect.top - top - 8)
  const desired = Math.min(320, Math.max(96, filteredOptions.value.length * 56))
  const upward = below < desired && above > below
  const available = Math.min(320, upward ? above : below)
  const panelWidth = Math.min(rect.width, Math.max(0, width - 16))
  dropdownStyle.value = {
    position: 'fixed',
    left: Math.max(left + 8, Math.min(rect.left, left + width - panelWidth - 8)) + 'px',
    width: panelWidth + 'px',
    maxHeight: available + 'px',
    ...(upward
      ? { top: rect.top - 4 + 'px', transform: 'translateY(-100%)' }
      : { top: rect.bottom + 4 + 'px' }),
  }
}

watch(filteredOptions, () => {
  highlightedIndex.value = -1
  void nextTick(updatePosition)
})
watch(
  () => [props.loading, props.error, props.notice],
  () => void nextTick(updatePosition)
)
watch(
  () => props.resetKey,
  () => {
    closeDropdown()
    query.value = ''
  }
)

onMounted(() => {
  registerDropdown(currentInstance)
  document.addEventListener('pointerdown', handleOutside)
  document.addEventListener('focusin', handleOutside)
  window.addEventListener('resize', updatePosition)
  window.addEventListener('scroll', updatePosition, true)
  window.visualViewport?.addEventListener('resize', updatePosition)
  window.visualViewport?.addEventListener('scroll', updatePosition)
  resizeObserver = new ResizeObserver(updatePosition)
  if (fieldRef.value) resizeObserver.observe(fieldRef.value)
})

onBeforeUnmount(() => {
  closeDropdown()
  unregisterDropdown(currentInstance)
  resizeObserver?.disconnect()
  document.removeEventListener('pointerdown', handleOutside)
  document.removeEventListener('focusin', handleOutside)
  window.removeEventListener('resize', updatePosition)
  window.removeEventListener('scroll', updatePosition, true)
  window.visualViewport?.removeEventListener('resize', updatePosition)
  window.visualViewport?.removeEventListener('scroll', updatePosition)
})
</script>

<style scoped>
.model-identifier {
  min-width: 0;
}
.model-identifier__field {
  display: flex;
  position: relative;
  align-items: center;
}
.model-identifier__field input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 12px 44px 12px 16px;
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 8px;
  background: var(--md-sys-color-surface-container-low);
  color: var(--md-sys-color-on-surface);
  font: inherit;
  font-size: 14px;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}
.model-identifier__field input::placeholder {
  color: var(--md-sys-color-on-surface-variant);
}
.model-identifier__field input:focus {
  outline: none;
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 1px var(--md-sys-color-primary);
}
.model-identifier__toggle {
  position: absolute;
  right: 2px;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  cursor: pointer;
}
.model-identifier__hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--md-sys-color-on-surface-variant);
}
.model-identifier__dropdown {
  z-index: 9999;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
  box-shadow: 0 5px 16px rgb(0 0 0 / 20%);
}
.model-identifier__list {
  overflow-y: auto;
  overscroll-behavior: contain;
  min-height: 0;
  padding: 4px 0;
}
.model-identifier__status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px 16px;
  font-size: 14px;
  line-height: 1.5;
  overflow-wrap: anywhere;
  color: var(--md-sys-color-on-surface-variant);
}
.model-identifier__status--error {
  color: var(--md-sys-color-error);
}
.model-identifier__spinner {
  flex: 0 0 auto;
  width: 20px;
  height: 20px;
  border: 2px solid var(--md-sys-color-outline-variant);
  border-top-color: var(--md-sys-color-primary);
  border-radius: 50%;
  animation: model-list-spin 0.8s linear infinite;
}
.model-identifier__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  min-height: 44px;
  box-sizing: border-box;
  cursor: pointer;
}
.model-identifier__option--highlighted {
  background: var(--md-sys-color-surface-container-highest);
}
.model-identifier__option--selected {
  color: var(--md-sys-color-primary);
}
.model-identifier__option-label {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 4px;
}
.model-identifier__id {
  font-size: 14px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.model-identifier__name {
  font-size: 12px;
  line-height: 1.5;
  color: var(--md-sys-color-on-surface-variant);
  overflow-wrap: anywhere;
}
.model-identifier__retry {
  flex-shrink: 0;
  padding: 12px 16px;
  border: 0;
  border-top: 1px solid var(--md-sys-color-outline-variant);
  background: transparent;
  color: var(--md-sys-color-primary);
  cursor: pointer;
  font: inherit;
  font-size: 14px;
}
.model-identifier__retry:hover,
.model-identifier__toggle:hover {
  background: var(--md-sys-color-surface-container-highest);
}
.model-identifier__retry:focus-visible {
  outline: 2px solid var(--md-sys-color-primary);
  outline-offset: -3px;
}
@keyframes model-list-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .model-identifier__spinner {
    animation-duration: 2s;
  }
}
</style>
