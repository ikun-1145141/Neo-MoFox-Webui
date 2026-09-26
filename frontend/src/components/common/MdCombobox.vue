<template>
  <div ref="field" class="md-combobox">
    <input
      :id="id" ref="input" :value="modelValue" :placeholder="placeholder" :required="required"
      type="text" role="combobox" autocomplete="off" aria-autocomplete="list"
      :aria-expanded="isOpen" :aria-controls="isOpen ? listId : undefined"
      :aria-activedescendant="isOpen && highlighted >= 0 ? listId + '-' + highlighted : undefined"
      @input="handleInput" @focus="open" @blur="close" @keydown="handleKeydown"
    />
    <button type="button" :aria-label="toggleLabel" :aria-expanded="isOpen" :aria-controls="isOpen ? listId : undefined"
      :disabled="!suggestionsReady" @mousedown.prevent @click="toggle">
      <Icon icon="material-symbols:expand-more-rounded" :width="22" :height="22" />
    </button>
    <Teleport to="body">
      <div v-if="isOpen" :id="listId" ref="dropdown" class="md-combobox-list" role="listbox"
        :aria-label="toggleLabel" :aria-busy="loading" :style="dropdownStyle" @mousedown.prevent>
        <div v-if="loading" class="md-combobox-loading" role="status">
          <Icon icon="material-symbols:progress-activity" :width="20" :height="20" class="md-combobox-spinner" />
          <span>{{ loadingText }}</span>
        </div>
        <template v-else>
          <div v-for="(option, index) in filteredOptions" :id="listId + '-' + index" :key="option"
            role="option" :aria-selected="option === modelValue" class="md-combobox-option"
            :class="{ highlighted: highlighted === index }" @mouseenter="highlighted = index" @click="select(option)">
            {{ option }}
          </div>
          <div v-if="!filteredOptions.length" class="md-combobox-empty" role="status">{{ emptyText }}</div>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Icon from './Icon.vue'
import { closeOtherDropdowns, registerDropdown, unregisterDropdown } from '@/utils/useDropdownManager'

const props = withDefaults(defineProps<{
  id: string
  modelValue: string
  options: string[]
  suggestionsReady: boolean
  loading?: boolean
  loadingText?: string
  placeholder?: string
  required?: boolean
  emptyText: string
  toggleLabel: string
}>(), { placeholder: '', required: false, loading: false, loadingText: '' })
const emit = defineEmits<{
  'update:modelValue': [value: string]
  select: [value: string]
  open: []
}>()
const field = ref<HTMLDivElement>()
const input = ref<HTMLInputElement>()
const dropdown = ref<HTMLDivElement>()
const isOpen = ref(false)
const highlighted = ref(-1)
const dropdownStyle = ref<Record<string, string>>({})
const listId = computed(() => props.id + '-options')
const filteredOptions = computed(() => {
  const query = props.modelValue.toLowerCase()
  return props.options.filter(option => option.toLowerCase().includes(query))
})
const instance = { close }

function close() {
  isOpen.value = false
  highlighted.value = -1
}
function position() {
  if (!isOpen.value || !field.value) return
  const rect = field.value.getBoundingClientRect()
  const below = window.innerHeight - rect.bottom - 8
  const above = rect.top - 8
  const upward = below < 240 && above > below
  const width = Math.min(rect.width, window.innerWidth - 16)
  dropdownStyle.value = {
    position: 'fixed', width: width + 'px',
    left: Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)) + 'px',
    maxHeight: Math.max(0, Math.min(280, upward ? above : below)) + 'px',
    ...(upward ? { bottom: window.innerHeight - rect.top + 4 + 'px' } : { top: rect.bottom + 4 + 'px' }),
  }
}
function open() {
  if (!props.suggestionsReady && !props.loading) {
    emit('open')
    return
  }
  closeOtherDropdowns(instance)
  isOpen.value = true
  position()
}
function toggle() {
  if (isOpen.value) close()
  else { input.value?.focus(); open() }
}
function handleInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
  highlighted.value = -1
  if (props.suggestionsReady || props.loading) open()
  else emit('open')
}
function select(value: string) {
  emit('update:modelValue', value)
  emit('select', value)
  close()
  input.value?.focus()
}
function handleKeydown(event: KeyboardEvent) {
  if (event.isComposing) return
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    if (!props.suggestionsReady) {
      if (!props.loading) emit('open')
      return
    }
    event.preventDefault()
    open()
    const length = filteredOptions.value.length
    if (!length) return
    highlighted.value = event.key === 'ArrowDown'
      ? Math.min(highlighted.value + 1, length - 1)
      : highlighted.value < 0 ? length - 1 : Math.max(0, highlighted.value - 1)
    void nextTick(() => document.getElementById(listId.value + '-' + highlighted.value)?.scrollIntoView({ block: 'nearest' }))
  } else if (event.key === 'Enter' && isOpen.value) {
    event.preventDefault()
    const option = filteredOptions.value[highlighted.value]
    if (option !== undefined) select(option)
    else close()
  } else if (event.key === 'Escape' && isOpen.value) {
    event.preventDefault()
    event.stopPropagation()
    close()
  } else if (event.key === 'Tab') close()
}
function outside(event: PointerEvent) {
  const target = event.target as Node
  if (!field.value?.contains(target) && !dropdown.value?.contains(target)) close()
}
watch(filteredOptions, () => { highlighted.value = -1; position() })
watch(() => props.loading, (loading, wasLoading) => {
  if ((loading || wasLoading) && document.activeElement === input.value) open()
})
watch(() => props.suggestionsReady, ready => { if (!ready && !props.loading) close() })
onMounted(() => {
  registerDropdown(instance)
  document.addEventListener('pointerdown', outside)
  window.addEventListener('resize', position)
  window.addEventListener('scroll', position, true)
})
onBeforeUnmount(() => {
  unregisterDropdown(instance)
  document.removeEventListener('pointerdown', outside)
  window.removeEventListener('resize', position)
  window.removeEventListener('scroll', position, true)
})
</script>

<style scoped>
.md-combobox { display: flex; width: 100%; min-width: 0; border: 1px solid var(--md-sys-color-outline); border-radius: 8px; background: var(--md-sys-color-surface); }
.md-combobox:focus-within { outline: 2px solid var(--md-sys-color-primary); outline-offset: -1px; }
.md-combobox input { flex: 1; width: 0; min-width: 0; padding: 12px 16px; border: none; border-radius: inherit; outline: none; background: transparent; color: var(--md-sys-color-on-surface); font: inherit; font-size: 14px; }
.md-combobox input::placeholder { color: var(--md-sys-color-on-surface-variant); }
.md-combobox button { display: flex; align-items: center; justify-content: center; width: 44px; border: none; border-radius: 8px; background: transparent; color: var(--md-sys-color-on-surface-variant); cursor: pointer; }
.md-combobox button:hover:not(:disabled) { background: var(--md-sys-color-surface-container-highest); }
.md-combobox button:disabled { opacity: .4; cursor: default; }
.md-combobox button:focus-visible { outline: 2px solid var(--md-sys-color-primary); }
.md-combobox-list { z-index: 10000; box-sizing: border-box; overflow-y: auto; overscroll-behavior: contain; padding: 8px; border-radius: 12px; background: var(--md-sys-color-surface-container); color: var(--md-sys-color-on-surface); box-shadow: 0 4px 16px #0003; font-size: 14px; }
.md-combobox-option { padding: 12px; border-radius: 8px; cursor: pointer; overflow-wrap: anywhere; }
.md-combobox-option.highlighted { background: var(--md-sys-color-secondary-container); color: var(--md-sys-color-on-secondary-container); }
.md-combobox-option[aria-selected="true"] { font-weight: 600; }
.md-combobox-empty { padding: 12px; color: var(--md-sys-color-on-surface-variant); overflow-wrap: anywhere; }
.md-combobox-loading { display: flex; align-items: center; justify-content: center; gap: 10px; min-height: 72px; color: var(--md-sys-color-on-surface-variant); }
.md-combobox-spinner { animation: md-combobox-spin 1s linear infinite; }
@keyframes md-combobox-spin { to { transform: rotate(360deg); } }
</style>
