<script setup lang="ts">
/**
 * SysDialog - 对话框组件。
 *
 * 使用系统级 dialog 工具（utils/dialog.ts）触发对话框。
 * 本组件本身不渲染 UI，通过 store 中的 __dialog_<id>_open 变量控制打开/关闭。
 * 打开时调用系统 dialog.show() 显示内容。
 */
import { watch, computed } from 'vue'
import { useDialogStore } from '../../../utils/dialog'

const props = defineProps<{
  /** 对话框标题 */
  title?: string
  /** 对话框 ID（用于 open-dialog/close-dialog 指令） */
  id?: string
  /** 对话框消息内容（从 XML 文本内容传入） */
  message?: string
  /** 渲染上下文（由 xml-renderer 注入） */
  __xmlContext?: any
}>()

const dialogStore = useDialogStore()

// 通过变量池控制的 open 状态
const isOpen = computed(() => {
  if (!props.id || !props.__xmlContext?.store) return false
  return props.__xmlContext.store.get(`__dialog_${props.id}_open`) === true
})

// 监听 open 状态变化
let activeDialogId: number | null = null

watch(isOpen, (open) => {
  if (open) {
    activeDialogId = dialogStore.show({
      title: props.title,
      message: props.message || '',
      buttons: [
        {
          text: '关闭',
          variant: 'primary',
          onClick: () => {
            if (props.__xmlContext?.store && props.id) {
              props.__xmlContext.store.set(`__dialog_${props.id}_open`, false)
            }
          },
        },
      ],
      onClose: () => {
        if (props.__xmlContext?.store && props.id) {
          props.__xmlContext.store.set(`__dialog_${props.id}_open`, false)
        }
      },
    })
  } else if (activeDialogId !== null) {
    dialogStore.close(activeDialogId)
    activeDialogId = null
  }
})
</script>

<template>
  <!-- SysDialog 不渲染自己的 UI，委托给系统 Dialog -->
  <slot />
</template>
