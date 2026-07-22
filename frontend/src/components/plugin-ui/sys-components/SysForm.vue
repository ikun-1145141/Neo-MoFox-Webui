<script setup lang="ts">
/**
 * SysForm - 表单容器组件。
 *
 * 包装原生 <form>，提供 gap、loading 状态遮罩、submit 事件。
 */
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 子元素间距 */
    gap?: string
    /** 表单布局：inline / block */
    layout?: string
    /** 是否处于 loading 状态（显示遮罩） */
    loading?: boolean
  }>(),
  {
    gap: '1rem',
    layout: 'block',
    loading: false,
  }
)

const emit = defineEmits<{
  (e: 'submit', ev: Event): void
  (e: 'reset', ev: Event): void
}>()

const isSubmitting = ref(false)

function handleSubmit(event: Event): void {
  event.preventDefault()
  isSubmitting.value = true
  const result = emit('submit', event)
  // 如果 emit 没有阻止，自动恢复（同步 emit）
  Promise.resolve(result).finally(() => {
    isSubmitting.value = false
  })
}

function handleReset(event: Event): void {
  emit('reset', event)
}
</script>

<template>
  <form
    class="sys-form"
    :class="[`sys-form--${layout}`, { 'sys-form--loading': loading || isSubmitting }]"
    :style="{ gap }"
    @submit="handleSubmit"
    @reset="handleReset"
  >
    <slot />
    <Transition name="sys-fade">
      <div
        v-if="loading || isSubmitting"
        class="sys-form-overlay"
      >
        <span class="material-symbols-rounded sys-spinner">progress_activity</span>
      </div>
    </Transition>
  </form>
</template>

<style scoped>
.sys-form {
  display: flex;
  flex-direction: column;
  width: 100%;
  position: relative;
}

.sys-form--inline {
  flex-direction: row;
  align-items: flex-start;
  flex-wrap: wrap;
}

.sys-form-overlay {
  position: absolute;
  inset: 0;
  background: color-mix(in srgb, var(--md-sys-color-surface, #fff) 60%, transparent);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: inherit;
  z-index: 10;
}

.sys-form-overlay .material-symbols-rounded {
  font-size: 28px;
  color: var(--md-sys-color-primary, #0058bd);
}
</style>
