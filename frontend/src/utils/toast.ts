import { reactive } from 'vue'

export type ToastType = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  message: string
  type: ToastType
}

const state = reactive<{ items: ToastItem[] }>({ items: [] })
let _id = 0

export function useToastStore() {
  function show(message: string, type: ToastType = 'info', duration = 3000) {
    const id = ++_id
    state.items.push({ id, message, type })
    setTimeout(() => {
      const idx = state.items.findIndex((t) => t.id === id)
      if (idx !== -1) state.items.splice(idx, 1)
    }, duration)
  }

  return { items: state.items, show }
}
