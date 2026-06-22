/**
 * 管道指令执行引擎（仅 XML 轨可用）。
 *
 * 解析并执行如 on-click="api: saveUser(name={form.name}) | notify: '保存成功' | refresh: usersTable"
 * 格式的管道指令字符串。
 *
 * 管道节点按顺序执行，任一节点 throw 则中断后续。
 */

import type { Router } from 'vue-router'
import type { PluginUIVarStore } from '../../stores/plugin-ui-vars'
import type { ApiTemplateEngine } from './api-template-engine'
import { resolvePlaceholderSync } from './placeholder-parser'
import { safeEvaluate } from './expression-evaluator'

// === 类型定义 ===

/** 解析后的管道指令节点 */
export interface PipeNode {
  /** 指令名称 */
  name: string
  /** 指令参数（原始字符串） */
  args: string
}

/** 管道执行上下文 */
export interface PipeContext {
  /** 变量池 Store */
  store: PluginUIVarStore
  /** API 模板引擎 */
  apiEngine: ApiTemplateEngine
  /** Vue Router 实例 */
  router: Router
  /** Toast 通知回调 */
  notify: (message: string, level?: 'info' | 'success' | 'warning' | 'error') => void
  /** 确认对话框回调（取消时 reject） */
  confirm: (message: string) => Promise<boolean>
  /** 事件总线 emit */
  busEmit: (event: string, payload?: any) => void
  /** 组件 refresh 回调 */
  refreshComponent: (componentId: string) => void
  /** 插件名称（用于路由解析） */
  pluginName: string
}

// === 管道解析 ===

/**
 * 将管道指令字符串解析为节点列表。
 *
 * 分割规则：以 ' | ' 为分隔符（前后有空格），避免误切字符串内的 |。
 * 每个节点格式为 "name: args" 或 "name"。
 *
 * @param pipeString - 管道指令字符串
 * @returns 解析后的管道节点列表
 */
export function parsePipe(pipeString: string): PipeNode[] {
  // 使用正则拆分，注意保持字符串字面量中的 | 不被拆开
  const nodes: PipeNode[] = []
  const parts = splitPipeString(pipeString)

  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed) continue

    const colonIndex = trimmed.indexOf(':')
    if (colonIndex === -1) {
      nodes.push({ name: trimmed, args: '' })
    } else {
      nodes.push({
        name: trimmed.slice(0, colonIndex).trim(),
        args: trimmed.slice(colonIndex + 1).trim(),
      })
    }
  }

  return nodes
}

/**
 * 按管道分隔符 ' | ' 拆分字符串。
 * 跳过在单引号或双引号内的 |。
 *
 * @param input - 管道指令字符串
 * @returns 拆分后的段落数组
 */
function splitPipeString(input: string): string[] {
  const parts: string[] = []
  let current = ''
  let inSingle = false
  let inDouble = false
  let i = 0

  while (i < input.length) {
    const ch = input[i]

    // 引号状态切换
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle
      current += ch
      i++
      continue
    }
    if (ch === '"' && !inSingle) {
      inDouble = !inDouble
      current += ch
      i++
      continue
    }

    // 管道分隔符检测（不在引号内）
    if (!inSingle && !inDouble && ch === '|') {
      // 检查是否为 ' | ' 格式（前后有空格），或直接作为分隔符
      parts.push(current)
      current = ''
      i++
      continue
    }

    current += ch
    i++
  }

  if (current) {
    parts.push(current)
  }

  return parts
}

// === 管道执行 ===

/**
 * 执行管道指令字符串。
 *
 * 按顺序逐个执行管道节点，任意节点抛出异常则中断后续。
 *
 * @param pipeString - 管道指令字符串
 * @param context - 管道执行上下文
 */
export async function executePipe(pipeString: string, context: PipeContext): Promise<void> {
  const nodes = parsePipe(pipeString)

  for (const node of nodes) {
    await executeNode(node, context)
  }
}

/**
 * 执行单个管道节点。
 *
 * @param node - 管道节点
 * @param context - 执行上下文
 */
async function executeNode(node: PipeNode, context: PipeContext): Promise<void> {
  const { store, apiEngine, router, notify, confirm, busEmit, refreshComponent, pluginName } = context

  switch (node.name) {
    case 'set': {
      // set: path=value 或 set: path={expression}
      const eqIndex = node.args.indexOf('=')
      if (eqIndex === -1) break
      const path = node.args.slice(0, eqIndex).trim()
      const valueStr = node.args.slice(eqIndex + 1).trim()
      const value = resolveValue(valueStr, store)
      console.debug(`[PipeExecutor] set: ${path} = ${JSON.stringify(value)} (from "${valueStr}")`)
      store.set(path, value)
      break
    }

    case 'api': {
      // api: templateId 或 api: templateId(param1=val1, param2=val2)
      const { id, params } = parseApiArgs(node.args, store)
      const result = await apiEngine.execute(id, params)
      if (!result.success) {
        throw new Error(result.error || `API "${id}" 执行失败`)
      }
      break
    }

    case 'notify': {
      // notify: 'message' 或 notify: 'message', level
      const { message, level } = parseNotifyArgs(node.args, store)
      notify(message, level)
      break
    }

    case 'confirm': {
      // confirm: 'message'
      const message = resolveStringArg(node.args, store)
      const confirmed = await confirm(message)
      if (!confirmed) {
        throw new Error('用户取消操作')
      }
      break
    }

    case 'navigate': {
      // navigate: /path 或 navigate: plugin:page
      const target = resolvePlaceholderSync(node.args, store)
      if (target.includes(':')) {
        // 插件页面跳转
        const [plugin, page] = target.split(':')
        router.push({ query: { plugin: plugin || pluginName, page } })
      } else {
        router.push(target)
      }
      break
    }

    case 'open-dialog': {
      // open-dialog: dialogId
      const dialogId = node.args.trim()
      store.set(`__dialog_${dialogId}_open`, true)
      break
    }

    case 'close-dialog': {
      // close-dialog: dialogId
      const dialogId = node.args.trim()
      store.set(`__dialog_${dialogId}_open`, false)
      break
    }

    case 'refresh': {
      // refresh: componentId
      const componentId = node.args.trim()
      refreshComponent(componentId)
      break
    }

    case 'reset': {
      // reset: path 或 reset: path=defaultValue
      const eqIndex = node.args.indexOf('=')
      if (eqIndex === -1) {
        store.set(node.args.trim(), null)
      } else {
        const path = node.args.slice(0, eqIndex).trim()
        const defaultStr = node.args.slice(eqIndex + 1).trim()
        store.set(path, resolveValue(defaultStr, store))
      }
      break
    }

    case 'emit': {
      // emit: eventName 或 emit: eventName, payload
      const commaIndex = node.args.indexOf(',')
      if (commaIndex === -1) {
        busEmit(node.args.trim())
      } else {
        const event = node.args.slice(0, commaIndex).trim()
        const payloadStr = node.args.slice(commaIndex + 1).trim()
        busEmit(event, resolveValue(payloadStr, store))
      }
      break
    }

    default:
      console.warn(`[PipeExecutor] 未知指令: ${node.name}`)
  }
}

// === 辅助解析函数 ===

/**
 * 解析值字符串（支持占位符、JSON 字面量、字符串引号）。
 *
 * @param valueStr - 值字符串
 * @param store - 变量池
 * @returns 解析后的值
 */
function resolveValue(valueStr: string, store: PluginUIVarStore): any {
  // 去除外围引号
  if ((valueStr.startsWith("'") && valueStr.endsWith("'")) ||
      (valueStr.startsWith('"') && valueStr.endsWith('"'))) {
    return valueStr.slice(1, -1)
  }

  // JSON 值尝试
  if (valueStr === 'true') return true
  if (valueStr === 'false') return false
  if (valueStr === 'null') return null
  if (/^-?\d+(\.\d+)?$/.test(valueStr)) return parseFloat(valueStr)

  // 纯占位符表达式 {expr}：直接求值并保留原始类型
  if (valueStr.startsWith('{') && valueStr.endsWith('}')) {
    // 检查是否为 JSON 对象字面量
    try {
      return JSON.parse(valueStr)
    } catch {
      // 不是合法 JSON → 当作表达式求值（保留原始类型，不字符串化）
      const expr = valueStr.slice(1, -1).trim()
      return safeEvaluate(expr, store, valueStr)
    }
  }

  // JSON 数组
  if (valueStr.startsWith('[')) {
    try {
      return JSON.parse(valueStr)
    } catch {
      // 可能是占位符表达式
    }
  }

  // 含占位符的混合字符串（如 "hello {name}"）
  if (valueStr.includes('{')) {
    return resolvePlaceholderSync(valueStr, store)
  }

  // 当作表达式求值
  return safeEvaluate(valueStr, store, valueStr)
}

/**
 * 解析 API 指令参数。
 *
 * 格式：templateId 或 templateId(key1=val1, key2=val2)
 *
 * @param args - 参数字符串
 * @param store - 变量池
 * @returns { id, params }
 */
function parseApiArgs(args: string, store: PluginUIVarStore): { id: string; params?: Record<string, any> } {
  const parenIndex = args.indexOf('(')
  if (parenIndex === -1) {
    return { id: args.trim() }
  }

  const id = args.slice(0, parenIndex).trim()
  const paramsStr = args.slice(parenIndex + 1, args.lastIndexOf(')'))
  const params: Record<string, any> = {}

  // 简单的 key=value 逗号分割解析
  const pairs = paramsStr.split(',')
  for (const pair of pairs) {
    const eqIdx = pair.indexOf('=')
    if (eqIdx === -1) continue
    const key = pair.slice(0, eqIdx).trim()
    const val = pair.slice(eqIdx + 1).trim()
    params[key] = resolveValue(val, store)
  }

  return { id, params }
}

/**
 * 解析 notify 指令参数。
 *
 * 格式：'message' 或 'message', level
 *
 * @param args - 参数字符串
 * @param store - 变量池
 * @returns { message, level }
 */
function parseNotifyArgs(
  args: string,
  store: PluginUIVarStore
): { message: string; level: 'info' | 'success' | 'warning' | 'error' } {
  const commaIndex = findTopLevelComma(args)
  if (commaIndex === -1) {
    return { message: resolveStringArg(args, store), level: 'info' }
  }

  const message = resolveStringArg(args.slice(0, commaIndex), store)
  const levelStr = args.slice(commaIndex + 1).trim().replace(/['"]/g, '')
  const validLevels = ['info', 'success', 'warning', 'error'] as const
  const level = validLevels.includes(levelStr as any) ? levelStr as typeof validLevels[number] : 'info'

  return { message, level }
}

/**
 * 解析字符串参数（去引号 + 占位符解析）。
 *
 * @param arg - 参数字符串
 * @param store - 变量池
 * @returns 解析后的字符串
 */
function resolveStringArg(arg: string, store: PluginUIVarStore): string {
  const trimmed = arg.trim()
  // 去引号
  if ((trimmed.startsWith("'") && trimmed.endsWith("'")) ||
      (trimmed.startsWith('"') && trimmed.endsWith('"'))) {
    return trimmed.slice(1, -1)
  }
  // 含占位符
  if (trimmed.includes('{')) {
    return resolvePlaceholderSync(trimmed, store)
  }
  return trimmed
}

/**
 * 查找顶层逗号位置（不在引号内）。
 *
 * @param input - 输入字符串
 * @returns 逗号位置，未找到返回 -1
 */
function findTopLevelComma(input: string): number {
  let inSingle = false
  let inDouble = false
  for (let i = 0; i < input.length; i++) {
    const ch = input[i]
    if (ch === "'" && !inDouble) inSingle = !inSingle
    else if (ch === '"' && !inSingle) inDouble = !inDouble
    else if (ch === ',' && !inSingle && !inDouble) return i
  }
  return -1
}
