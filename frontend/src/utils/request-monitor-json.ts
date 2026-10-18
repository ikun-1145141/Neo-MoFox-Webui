/** Display-only JSON utilities. Never interpret provider protocols or merge request fields. */
import type { JsonValue } from '../api/types/request-inspector'

export const JSON_PAGE_SIZE = 100
export const JSON_ROW_LIMIT = 1500
export const TEXT_PAGE_SIZE = 4096
export interface JsonNodeState { expanded?: boolean; offset?: number; textLength?: number }
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

/** An unambiguous JSON Pointer, including empty keys, slash and tilde. */
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
/** Iterative, lazy traversal: never descend into collapsed nodes or build all array entries. */
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

/** Resolve only own JSON keys; never walk prototypes or evaluate a path as code. */
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
