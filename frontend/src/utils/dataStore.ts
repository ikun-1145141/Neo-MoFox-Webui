import { reactive } from 'vue'

/**
 * 获取嵌套对象中指定路径的值。
 * 例如 getValueByPath({ form: { name: 'Alice' } }, 'form.name') → 'Alice'
 */
export function getValueByPath(obj: Record<string, any>, path: string): any {
  if (!path) return undefined
  const keys = path.split('.')
  let current: any = obj
  for (const key of keys) {
    if (current == null || typeof current !== 'object') return undefined
    current = current[key]
  }
  return current
}

/**
 * 设置嵌套对象中指定路径的值（自动创建中间对象）。
 */
export function setValueByPath(obj: Record<string, any>, path: string, value: any): void {
  if (!path) return
  const keys = path.split('.')
  const lastKey = keys.pop()!
  let current: any = obj
  for (const key of keys) {
    if (current[key] == null || typeof current[key] !== 'object') {
      current[key] = {}
    }
    current = current[key]
  }
  current[lastKey] = value
}

/**
 * 创建页面级响应式数据存储。
 * 每个插件页面持有独立的 store 实例。
 */
export function createDataStore() {
  return reactive<Record<string, any>>({
    form: {},
    response: {},
    tables: {},
    dialogs: {},
  })
}
