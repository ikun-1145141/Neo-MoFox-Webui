/**
 * 占位符解析器。
 *
 * 将含有 {expression} 占位符的字符串解析为静态文本段和表达式段，
 * 并结合 Vue 响应式系统返回实时计算的 ComputedRef<string>。
 *
 * 语法（与设计 §2.2 完全对齐）：
 * - {var.path} → 简单变量引用
 * - {!flag} → 取反
 * - {len(list) > 5} → 内置函数 + 比较
 * - {user.name || '匿名'} → 逻辑或
 */

import { computed, type ComputedRef } from 'vue'
import { evaluate, safeEvaluate, type VariableResolver } from './expression-evaluator'

// === 解析段类型 ===

/** 静态文本段 */
interface TextSegment {
  type: 'text'
  value: string
}

/** 表达式段 */
interface ExprSegment {
  type: 'expr'
  expr: string
}

/** 解析后的段列表 */
export type ParsedSegment = TextSegment | ExprSegment

// === 解析器核心 ===

/**
 * 将含占位符的模板字符串解析为段列表。
 *
 * 花括号嵌套通过计数处理，确保 {obj.arr[0]} 等不会误断。
 * 转义序列 \{ 和 \} 按字面量 { } 处理。
 *
 * @param template - 包含 {expression} 占位符的字符串
 * @returns 解析后的段数组
 */
export function parsePlaceholders(template: string): ParsedSegment[] {
  const segments: ParsedSegment[] = []
  let current = ''
  let i = 0

  while (i < template.length) {
    const ch = template[i]

    // 转义处理
    if (ch === '\\' && i + 1 < template.length) {
      const next = template[i + 1]
      if (next === '{' || next === '}') {
        current += next
        i += 2
        continue
      }
    }

    // 进入表达式
    if (ch === '{') {
      // 保存之前的文本段
      if (current.length > 0) {
        segments.push({ type: 'text', value: current })
        current = ''
      }

      // 扫描到匹配的 }，支持嵌套括号
      i++ // 跳过 {
      let depth = 1
      let expr = ''

      while (i < template.length && depth > 0) {
        if (template[i] === '{') {
          depth++
          expr += template[i]
        } else if (template[i] === '}') {
          depth--
          if (depth > 0) {
            expr += template[i]
          }
        } else {
          expr += template[i]
        }
        i++
      }

      const trimmedExpr = expr.trim()
      if (trimmedExpr.length > 0) {
        segments.push({ type: 'expr', expr: trimmedExpr })
      }
      continue
    }

    current += ch
    i++
  }

  // 末尾文本
  if (current.length > 0) {
    segments.push({ type: 'text', value: current })
  }

  return segments
}

/**
 * 检查字符串是否包含占位符表达式。
 *
 * @param template - 待检查的字符串
 * @returns 是否含有 {...} 格式的占位符
 */
export function hasPlaceholders(template: string): boolean {
  return /(?<!\\)\{[^}]+\}/.test(template)
}

// === 响应式绑定 ===

/**
 * 将含占位符的模板字符串解析为响应式计算值。
 *
 * 由于 resolver（通常是 PluginUIVarStore）内部基于 reactive 对象，
 * Vue 的 computed 会自动追踪依赖，在变量变化时重新计算。
 *
 * @param template - 含占位符的模板字符串
 * @param resolver - 变量解析器（通常为 PluginUIVarStore）
 * @returns 响应式计算引用，值为解析后的字符串
 */
export function resolvedPlaceholder(
  template: string,
  resolver: VariableResolver
): ComputedRef<string> {
  const segments = parsePlaceholders(template)

  // 如果模板不含表达式，直接返回静态值
  if (segments.every(seg => seg.type === 'text')) {
    const staticValue = segments.map(seg => (seg as TextSegment).value).join('')
    return computed(() => staticValue)
  }

  return computed(() => {
    return segments.map(seg => {
      if (seg.type === 'text') return seg.value
      const result = safeEvaluate(seg.expr, resolver, '')
      if (result == null) return ''
      return String(result)
    }).join('')
  })
}

/**
 * 对单个表达式求值并返回响应式结果（非字符串化，保留原始类型）。
 *
 * 用于属性绑定（如 disabled="{!form_valid}"）场景，需要获得布尔值而非字符串。
 *
 * @param expression - 表达式字符串
 * @param resolver - 变量解析器
 * @param defaultValue - 出错时的默认值
 * @returns 响应式计算引用
 */
export function resolvedExpression(
  expression: string,
  resolver: VariableResolver,
  defaultValue: any = undefined
): ComputedRef<any> {
  return computed(() => safeEvaluate(expression, resolver, defaultValue))
}

/**
 * 直接对带占位符的模板求值为字符串（非响应式版本）。
 *
 * @param template - 含占位符的模板字符串
 * @param resolver - 变量解析器
 * @returns 解析后的字符串
 */
export function resolvePlaceholderSync(template: string, resolver: VariableResolver): string {
  const segments = parsePlaceholders(template)
  return segments.map(seg => {
    if (seg.type === 'text') return seg.value
    const result = safeEvaluate(seg.expr, resolver, '')
    if (result == null) return ''
    return String(result)
  }).join('')
}

/**
 * 直接对单个表达式求值（非响应式版本，保留原始类型）。
 *
 * @param expression - 表达式字符串
 * @param resolver - 变量解析器
 * @returns 表达式结果
 * @throws ExpressionError 如果表达式有语法错误
 */
export function evaluateExpression(expression: string, resolver: VariableResolver): any {
  return evaluate(expression, resolver)
}
