/** 仅用于展示的 JSON 工具，不解析供应商协议，也不合并请求字段。 */
import type { JsonValue } from '../api/types/request-inspector'

export const JSON_PAGE_SIZE = 100
export const JSON_ROW_LIMIT = 1500
export const TEXT_PAGE_SIZE = 4096
export interface JsonNodeState { expanded?: boolean; offset?: number }
export interface JsonRow {
  path: string
  key: string
  value: JsonValue
  depth: number
  type: string
  size: number
  expanded: boolean
  shown: number
  offset: number
  more: boolean
}
export type JsonTreeState = Map<string, JsonNodeState>

/** 生成无歧义的 JSON Pointer 路径，正确处理空键、斜杠和波浪号。 */
export function childPointer(parent: string, key: string): string {
  return `${parent}/${key.replace(/~/g, '~0').replace(/\//g, '~1')}`
}
export function jsonType(value: JsonValue): string {
  return value === null ? 'null' : Array.isArray(value) ? 'array' : typeof value
}
export function parseJsonText(text: string): { value: JsonValue; parsed: boolean } {
  try { return { value: JSON.parse(text) as JsonValue, parsed: true } }
  catch { return { value: text, parsed: false } }
}
export function previewJson(value: JsonValue, limit = 160): string {
  if (typeof value === 'string')
    return JSON.stringify(value.slice(0, limit)) + (value.length > limit ? ' …' : '')
  if (value !== null && typeof value === 'object') return Array.isArray(value) ? '[…]' : '{…}'
  return JSON.stringify(value)
}
/** 使用迭代式惰性遍历，不进入折叠节点，也不一次构建整个数组。 */
export function visibleJsonRows(value: JsonValue, state: JsonTreeState, maxRows = JSON_ROW_LIMIT) {
  const rows: JsonRow[] = []
  const stack: { value: JsonValue; path: string; key: string; depth: number; more?: boolean; size?: number; shown?: number; offset?: number }[] = [
    { value, path: '', key: '$', depth: 0 },
  ]
  while (stack.length && rows.length < maxRows) {
    const node = stack.pop()!
    if (node.more) {
      rows.push({ ...node, type: 'more', size: node.size!, shown: node.shown!, offset: node.offset!, expanded: false, more: true })
      continue
    }
    const type = jsonType(node.value)
    const container = type === 'object' || type === 'array'
    const keys = type === 'object' ? Object.keys(node.value as object) : []
    const size = type === 'array' ? (node.value as JsonValue[]).length : type === 'object' ? keys.length : typeof node.value === 'string' ? node.value.length : 0
    const saved = state.get(node.path)
    const expanded = container && (saved?.expanded ?? node.path === '')
    const offset = Math.min(saved?.offset ?? 0, Math.max(0, Math.floor((size - 1) / JSON_PAGE_SIZE) * JSON_PAGE_SIZE))
    const shown = expanded ? Math.min(size, offset + JSON_PAGE_SIZE) : 0
    rows.push({ ...node, type, size, shown, offset, expanded, more: false })
    if (!expanded) continue
    if (size > JSON_PAGE_SIZE) stack.push({ ...node, more: true, size, shown, offset, depth: node.depth + 1 })
    for (let i = shown - 1; i >= offset; i--) {
      const key = type === 'array' ? String(i) : keys[i]!
      const child = type === 'array' ? (node.value as JsonValue[])[i]! : (node.value as Record<string, JsonValue>)[key]!
      stack.push({ value: child, path: childPointer(node.path, key), key, depth: node.depth + 1 })
    }
  }
  return { rows, limited: stack.length > 0 }
}

/** 只读取 JSON 对象自身的键，不访问原型链，也不将路径作为代码执行。 */
export function hasJsonPath(value: JsonValue, pointer: string): boolean {
  if (pointer === '') return true
  let current = value
  for (const part of pointer.slice(1).split('/')) {
    const key = part.replace(/~1/g, '/').replace(/~0/g, '~')
    if (current === null || typeof current !== 'object' || !Object.hasOwn(current, key)) return false
    current = (current as Record<string, JsonValue>)[key]!
  }
  return true
}
