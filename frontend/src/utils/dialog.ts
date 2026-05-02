import { reactive } from 'vue'

export type DialogType = 'alert' | 'confirm'

interface DialogButton {
  text: string
  variant?: 'primary' | 'secondary' | 'ghost'
  onClick: () => void
}

interface DialogItem {
  id: number
  type: DialogType
  title?: string
  message: string
  buttons: DialogButton[]
  onClose?: () => void
}

const state = reactive<{ items: DialogItem[] }>({ items: [] })
let _id = 0

export function useDialogStore() {
  /**
   * 显示简单的 alert 对话框（单个"确定"按钮）
   * @param message - 对话框消息内容
   * @param title - 可选的对话框标题
   * @returns Promise，在用户点击确定后 resolve
   */
  function alert(message: string, title?: string): Promise<void> {
    return new Promise((resolve) => {
      const id = ++_id
      const dialog: DialogItem = {
        id,
        type: 'alert',
        title,
        message,
        buttons: [
          {
            text: '确定',
            variant: 'primary',
            onClick: () => {
              close(id)
              resolve()
            },
          },
        ],
      }
      state.items.push(dialog)
    })
  }

  /**
   * 显示 confirm 确认对话框（确认/取消按钮）
   * @param message - 对话框消息内容
   * @param title - 可选的对话框标题
   * @param confirmText - 确认按钮文本（默认"确认"）
   * @param cancelText - 取消按钮文本（默认"取消"）
   * @returns Promise<boolean>，确认返回 true，取消返回 false
   */
  function confirm(
    message: string,
    title?: string,
    confirmText = '确认',
    cancelText = '取消'
  ): Promise<boolean> {
    return new Promise((resolve) => {
      const id = ++_id
      const dialog: DialogItem = {
        id,
        type: 'confirm',
        title,
        message,
        buttons: [
          {
            text: cancelText,
            variant: 'secondary',
            onClick: () => {
              close(id)
              resolve(false)
            },
          },
          {
            text: confirmText,
            variant: 'primary',
            onClick: () => {
              close(id)
              resolve(true)
            },
          },
        ],
      }
      state.items.push(dialog)
    })
  }

  /**
   * 显示自定义对话框
   * @param options - 对话框配置选项
   */
  function custom(options: {
    title?: string
    message: string
    buttons: Array<{ text: string; variant?: 'primary' | 'secondary' | 'ghost'; primary?: boolean }>
    onClose?: () => void
  }): Promise<number> {
    return new Promise((resolve) => {
      const id = ++_id
      const dialog: DialogItem = {
        id,
        type: 'alert',
        title: options.title,
        message: options.message,
        buttons: options.buttons.map((btn, index) => ({
          text: btn.text,
          variant: btn.variant || (btn.primary ? 'primary' : 'secondary'),
          onClick: () => {
            close(id)
            resolve(index)
          },
        })),
        onClose: options.onClose,
      }
      state.items.push(dialog)
    })
  }

  /**
   * 关闭指定 ID 的对话框
   */
  function close(id: number) {
    const idx = state.items.findIndex((d) => d.id === id)
    if (idx !== -1) {
      const dialog = state.items[idx]
      state.items.splice(idx, 1)
      dialog.onClose?.()
    }
  }

  /**
   * 关闭所有对话框
   */
  function closeAll() {
    state.items.forEach((dialog) => dialog.onClose?.())
    state.items.length = 0
  }

  return {
    items: state.items,
    alert,
    confirm,
    custom,
    close,
    closeAll,
  }
}

// 导出全局实例，方便在非 Vue 组件中使用
export const dialog = useDialogStore()
