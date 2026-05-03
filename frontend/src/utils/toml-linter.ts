/**
 * TOML 语法验证器（浏览器端）
 * 结合基础语法检查和 toml 库完整解析
 */
import type { Text, Diagnostic } from '@codemirror/lint'
import { parse as parseTOML } from 'toml'

/**
 * TOML 语法检查（用于 CodeMirror Lint）
 * @param doc - CodeMirror 文档对象
 * @returns 诊断信息数组
 */
export function lintTOML(doc: Text): Diagnostic[] {
  const diagnostics: Diagnostic[] = []
  const text = doc.toString()

  try {
    // ═══ 阶段 1: 基础语法检查 ═══
    const lines = text.split('\n')

    lines.forEach((line, lineIndex) => {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) return

      // 检查未闭合的引号
      if (
        (trimmed.match(/"/g) || []).length % 2 !== 0 ||
        (trimmed.match(/'/g) || []).length % 2 !== 0
      ) {
        const lineStart = doc.line(lineIndex + 1).from
        const lineEnd = doc.line(lineIndex + 1).to
        diagnostics.push({
          from: lineStart,
          to: lineEnd,
          severity: 'error',
          message: '未闭合的引号',
        })
        return
      }

      // 检查键值对格式
      if (!trimmed.startsWith('[') && !trimmed.startsWith('[[') && trimmed.includes('=')) {
        const parts = trimmed.split('=')
        if (parts.length === 2) {
          const key = parts[0].trim()
          const value = parts[1].trim()

          if (!key) {
            const lineStart = doc.line(lineIndex + 1).from
            const lineEnd = doc.line(lineIndex + 1).to
            diagnostics.push({
              from: lineStart,
              to: lineEnd,
              severity: 'error',
              message: '缺少键名',
            })
          }

          if (!value) {
            const lineStart = doc.line(lineIndex + 1).from
            const lineEnd = doc.line(lineIndex + 1).to
            diagnostics.push({
              from: lineStart,
              to: lineEnd,
              severity: 'warning',
              message: '缺少值',
            })
          }
        }
      }
    })

    // 检查括号匹配
    const bracketStack: Array<{ char: string; pos: number }> = []
    for (let i = 0; i < text.length; i++) {
      const char = text[i]
      if (char === '[' || char === '{') {
        bracketStack.push({ char, pos: i })
      } else if (char === ']' || char === '}') {
        const last = bracketStack.pop()
        if (!last || (char === ']' && last.char !== '[') || (char === '}' && last.char !== '{')) {
          diagnostics.push({
            from: i,
            to: i + 1,
            severity: 'error',
            message: '括号不匹配',
          })
        }
      }
    }

    // 未闭合的括号
    bracketStack.forEach((bracket) => {
      diagnostics.push({
        from: bracket.pos,
        to: bracket.pos + 1,
        severity: 'error',
        message: '未闭合的括号',
      })
    })

    // ═══ 阶段 2: 完整 TOML 解析验证 ═══
    // 只有在基础检查没有发现致命错误时才进行完整解析
    const hasCriticalErrors = diagnostics.some((d) => d.severity === 'error')

    if (!hasCriticalErrors) {
      try {
        parseTOML(text)
      } catch (error: any) {
        // 解析 toml 错误信息
        let errorMessage = error.message || String(error)
        let errorLine = 0
        let errorColumn = 0

        // 提取行列信息（toml 错误格式：Error at line X, column Y: ...）
        const lineMatch = errorMessage.match(/line (\d+)/)
        const columnMatch = errorMessage.match(/column (\d+)/)

        if (lineMatch) {
          errorLine = parseInt(lineMatch[1], 10) - 1
        }
        if (columnMatch) {
          errorColumn = parseInt(columnMatch[1], 10) - 1
        }

        // 翻译错误信息
        errorMessage = translateTOMLError(errorMessage)

        // 定位错误位置
        let errorFrom = 0
        let errorTo = text.length

        if (errorLine > 0 && errorLine <= lines.length) {
          const line = doc.line(errorLine + 1)
          errorFrom = line.from + Math.max(0, errorColumn)
          errorTo = Math.min(line.to, errorFrom + 20)
        } else {
          errorFrom = 0
          errorTo = Math.min(text.length, 20)
        }

        diagnostics.push({
          from: errorFrom,
          to: errorTo,
          severity: 'error',
          message: errorMessage,
        })
      }
    }
  } catch (error: any) {
    // 如果检查过程中出错，显示在文档末尾
    diagnostics.push({
      from: doc.length,
      to: doc.length,
      severity: 'error',
      message: `语法检查异常: ${error.message}`,
    })
  }

  return diagnostics
}

/**
 * 翻译 TOML 错误信息为中文
 * @param errorMessage - 原始英文错误信息
 * @returns 中文化的错误信息
 */
function translateTOMLError(errorMessage: string): string {
  const msg = errorMessage.trim()

  // 键重复错误
  if (msg.includes('Cannot redefine existing key')) {
    const match = msg.match(/Cannot redefine existing key '([^']+)'/)
    if (match) {
      return `不能重新定义已存在的键: ${match[1]}`
    }
    return '不能重新定义已存在的键'
  }

  // 数组类型不匹配
  if (msg.includes('Cannot add value of type')) {
    return '数组类型不匹配'
  }

  // Unicode 错误
  if (msg.includes('Invalid Unicode escape code')) {
    return 'Unicode 转义序列无效'
  }

  // 未闭合的字符串
  if (msg.includes('Expected "\\"\\"\\"",') || msg.includes('Expected "\\"\\"\\"\\"')) {
    return '未闭合的三引号字符串'
  }
  if (msg.includes("Expected \"'''\"")) {
    return '未闭合的单引号字符串'
  }
  if (msg.includes('Expected "\\"",') || msg.includes('Expected "\\"" or any character')) {
    return '未闭合的双引号字符串'
  }
  if (msg.includes("Expected \"'\"") || msg.includes("Expected \"'\" or any character")) {
    return '未闭合的单引号字符串'
  }

  // 日期时间格式错误
  if (msg.includes('Expected "T" but " " found')) {
    return '日期时间格式错误：日期和时间之间应使用 T 分隔'
  }
  if (msg.includes('Expected "T" but end of input found')) {
    return '日期时间格式不完整'
  }

  // 内联表换行错误
  if (msg.includes('Expected "}", [ \\t] or [A-Za-z0-9_\\-] but "\\n" found')) {
    return '内联表不能换行'
  }

  // 值后的意外字符
  if (msg.includes('Expected "#", "\\n", "\\r" or [ \\t] but')) {
    return '值后有意外字符'
  }

  // 输入结束错误
  if (msg.includes('but end of input found')) {
    return 'TOML 格式不完整'
  }

  // 缺少等号
  if (msg.includes('Expected "=" or [ \\t]')) {
    return '缺少等号'
  }

  // 缺少值
  if (msg.includes("Expected \"'\", \"'''\", \"+\", \"-\", \"[\", \"\\\"\",")) {
    return '缺少值'
  }

  // 通用格式错误
  if (msg.includes('Expected') && msg.includes('but') && msg.includes('found')) {
    return 'TOML 格式错误'
  }

  return 'TOML 解析错误'
}
