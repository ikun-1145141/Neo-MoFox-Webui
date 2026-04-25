<script setup lang="ts">
import { computed, useAttrs } from 'vue'

const props = withDefaults(
  defineProps<{
    icon: string
    width?: string | number
    height?: string | number
  }>(),
  {
    width: 24,
    height: 24,
  }
)

const attrs = useAttrs()

const overrideMap: Record<string, string> = {
  'setting-outline-rounded': 'settings',
  'settings-outline-rounded': 'settings',
  'home-outline-rounded': 'home',
  'format-paint-outline-rounded': 'format_paint',
  'check-circle-outline-rounded': 'check_circle',
  'cancel-outline-rounded': 'cancel',
  'robot-2-outline-rounded': 'robot_2',
  'arrow-forward-ios-rounded': 'arrow_forward_ios',
  'lock-outline-rounded': 'lock',
  'visibility-off-outline-rounded': 'visibility_off',
  'visibility-outline-rounded': 'visibility',
  'cloud-done-outline-rounded': 'cloud_done',
  'brightness-auto-outline-rounded': 'brightness_auto',
  'light-mode-outline-rounded': 'light_mode',
  'dark-mode-outline-rounded': 'dark_mode',
  'colorize-outline-rounded': 'colorize',
  'info-outline-rounded': 'info',
  'error-outline-rounded': 'error',
  'warning-outline-rounded': 'warning',
  'upload-file-outline-rounded': 'upload_file',
}

const iconName = computed(() => {
  const raw = props.icon.replace(/^material-symbols:/, '')
  if (overrideMap[raw]) return overrideMap[raw]
  return raw
    .replace(/-(outline-rounded|rounded|sharp|outline)$/g, '')
    .replace(/-/g, '_')
})

const iconClass = computed(() => {
  const raw = props.icon.replace(/^material-symbols:/, '')
  if (raw.endsWith('-sharp')) return 'material-symbols-sharp'
  if (raw.endsWith('-rounded')) return 'material-symbols-rounded'
  return 'material-symbols-outlined'
})

const iconStyle = computed(() => ({
  fontSize: typeof props.width === 'number' ? `${props.width}px` : props.width,
  width: typeof props.width === 'number' ? `${props.width}px` : props.width,
  height: typeof props.height === 'number' ? `${props.height}px` : props.height,
}))
</script>

<template>
  <span v-bind="attrs" :class="iconClass" :style="iconStyle" aria-hidden="true">{{ iconName }}</span>
</template>