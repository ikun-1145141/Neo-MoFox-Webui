/**
 * XML 渲染器核心逻辑。
 *
 * 将 XML 字符串解析为 DOM 树，再遍历转换为 Vue VNode 树。
 * 负责：
 * - DOMParser 解析 XML
 * - <definitions> 段预处理（变量声明、API 模板注册、子模板存储）
 * - 元素节点到 Vue 组件的映射
 * - 属性中占位符的响应式绑定
 * - 条件渲染（hidden/disabled）
 * - 管道指令属性（on-click/on-change 等）的绑定
 */

import { h, type VNode, type Component } from 'vue'
import type { PluginUIVarStore } from '../../stores/plugin-ui-vars'
import type { ApiTemplateEngine } from './api-template-engine'
import { parseApiTemplateFromElement } from './api-template-engine'
import { resolvePlaceholderSync, hasPlaceholders } from './placeholder-parser'
import { safeEvaluate } from './expression-evaluator'
import type { PipeContext } from './pipe-executor'
import { executePipe } from './pipe-executor'
import { getXmlComponent } from '../../components/plugin-ui/xml-components'

// === 类型定义 ===

/** XML 解析结果 */
export interface XmlParseResult {
  /** 是否解析成功 */
  success: boolean
  /** 错误信息（解析失败时） */
  error: string | null
  /** 解析后的 DOM Document（成功时） */
  document: Document | null
}

/** 渲染上下文（传递给组件树的共享状态） */
export interface XmlRenderContext {
  /** 变量池 */
  store: PluginUIVarStore
  /** API 模板引擎 */
  apiEngine: ApiTemplateEngine
  /** 管道执行上下文 */
  pipeContext: PipeContext
  /** 子模板注册表 */
  templates: Map<string, Element>
  /** 是否为移动端 */
  isMobile: boolean
}

// === XML 解析 ===

/**
 * 解析 XML 字符串为 DOM Document。
 *
 * @param xmlString - XML 字符串
 * @returns 解析结果
 */
export function parseXml(xmlString: string): XmlParseResult {
  try {
    const parser = new DOMParser()
    const doc = parser.parseFromString(xmlString, 'application/xml')

    // 检查解析错误
    const parseError = doc.querySelector('parsererror')
    if (parseError) {
      return {
        success: false,
        error: parseError.textContent || 'XML 解析失败',
        document: null,
      }
    }

    return { success: true, error: null, document: doc }
  } catch (err: any) {
    return {
      success: false,
      error: err?.message || 'XML 解析异常',
      document: null,
    }
  }
}

// === <definitions> 处理 ===

/**
 * 预处理 XML 中的 <definitions> 段。
 *
 * - <var> → 写入 store
 * - <api> → 注册到 apiEngine
 * - <template> → 存储到 templates Map
 *
 * @param doc - 解析后的 XML Document
 * @param store - 变量池
 * @param apiEngine - API 模板引擎
 * @returns 子模板注册表
 */
export function processDefinitions(
  doc: Document,
  store: PluginUIVarStore,
  apiEngine: ApiTemplateEngine
): Map<string, Element> {
  const templates = new Map<string, Element>()
  const definitions = doc.querySelector('definitions')
  if (!definitions) return templates

  for (const child of Array.from(definitions.children)) {
    switch (child.tagName) {
      case 'var': {
        const name = child.getAttribute('name')
        const defaultValue = child.getAttribute('default')
        if (name) {
          // 仅当变量尚未存在时才写入默认值，避免 computed 重算时覆盖已修改的值
          if (store.get(name) === undefined) {
            let value: any = null
            if (defaultValue) {
              try {
                value = JSON.parse(defaultValue)
              } catch {
                value = defaultValue
              }
            }
            console.debug(`[XmlRenderer] 初始化变量: ${name} =`, value)
            store.set(name, value)
          }
        }
        break
      }

      case 'api': {
        const template = parseApiTemplateFromElement(child)
        if (template.id) {
          apiEngine.register(template)
        }
        break
      }

      case 'template': {
        const id = child.getAttribute('id')
        if (id) {
          templates.set(id, child)
        }
        break
      }
    }
  }

  return templates
}

// === VNode 渲染 ===

/**
 * 将 XML DOM 元素树转换为 Vue VNode 树。
 *
 * @param rootElement - XML 根元素（通常是 <page> 或 <definitions> 之后的内容根）
 * @param context - 渲染上下文
 * @returns VNode 数组
 */
export function renderElementToVNodes(
  rootElement: Element,
  context: XmlRenderContext
): VNode[] {
  const children = Array.from(rootElement.children)
  const vnodes: VNode[] = []

  for (const child of children) {
    // 跳过 <definitions>（已在 processDefinitions 中处理）
    if (child.tagName === 'definitions') continue

    // <layout> 作为透传容器：渲染其子节点而非自身
    if (child.tagName === 'layout') {
      for (const layoutChild of Array.from(child.children)) {
        const vnode = renderSingleElement(layoutChild, context)
        if (vnode) {
          vnodes.push(vnode)
        }
      }
      continue
    }

    const vnode = renderSingleElement(child, context)
    if (vnode) {
      vnodes.push(vnode)
    }
  }

  return vnodes
}

/**
 * 将单个 XML 元素转换为 Vue VNode。
 *
 * @param element - XML 元素
 * @param context - 渲染上下文
 * @returns VNode 或 null（条件不满足时不渲染）
 */
function renderSingleElement(element: Element, context: XmlRenderContext): VNode | null {
  const { store, isMobile } = context

  // mobile-only / desktop-only 检查
  if (element.hasAttribute('mobile-only') && !isMobile) return null
  if (element.hasAttribute('desktop-only') && isMobile) return null

  // hidden 条件检查
  const hiddenAttr = element.getAttribute('hidden')
  if (hiddenAttr) {
    const isHidden = evaluateCondition(hiddenAttr, store)
    console.debug(`[XmlRenderer] hidden 条件: "${hiddenAttr}" → ${isHidden}`)
    if (isHidden) return null
  }

  // 查找对应的 Vue 组件
  const tagName = element.tagName.toLowerCase()
  const component = getXmlComponent(tagName)

  if (!component) {
    // 未知标签 → 渲染为错误提示
    return h('div', {
      class: 'xml-render-error',
      style: 'color: var(--md-sys-color-error); padding: 4px 8px; font-size: 12px; border: 1px dashed currentColor; border-radius: 4px;',
    }, `未知组件: <${tagName}>`)
  }

  // 解析属性
  const props = resolveAttributes(element, context)

  // 解析子节点
  const children = resolveChildren(element, context)

  return h(component as Component, props, children)
}

/**
 * 解析元素属性为 Vue props。
 *
 * 处理：
 * - 普通属性值中的占位符解析
 * - on-* 事件属性绑定管道执行
 * - disabled / hidden 条件属性
 *
 * @param element - XML 元素
 * @param context - 渲染上下文
 * @returns props 对象
 */
function resolveAttributes(
  element: Element,
  context: XmlRenderContext
): Record<string, any> {
  const { store, pipeContext } = context
  const props: Record<string, any> = {}

  for (const attr of Array.from(element.attributes)) {
    const name = attr.name
    const value = attr.value

    // hidden / mobile-only / desktop-only 已在 renderSingleElement 中处理，
    // 不传递给子组件。hidden 若作为 HTML fallthrough 属性会导致元素被意外隐藏。
    if (name === 'hidden' || name === 'mobile-only' || name === 'desktop-only') {
      continue
    }

    // 事件属性（on-click, on-change 等）→ 绑定管道执行
    if (name.startsWith('on-')) {
      const eventName = name.slice(3) // 'click', 'change' 等
      props[`on${capitalize(eventName)}`] = () => {
        console.debug(`[XmlRenderer] 事件触发: ${name}="${value}"`)
        executePipe(value, pipeContext).catch((err: Error) => {
          console.warn(`[XmlRenderer] 管道执行失败 (${name}):`, err.message)
        })
      }
      continue
    }

    // disabled 属性 → 布尔表达式
    if (name === 'disabled') {
      props.disabled = evaluateCondition(value, store)
      continue
    }

    // bind:xxx 属性 → 变量池双向绑定路径
    if (name.startsWith('bind:')) {
      const bindPath = name.slice(5)
      props[`bind_${bindPath}`] = value
      continue
    }

    // 普通属性 → 解析占位符
    if (hasPlaceholders(value)) {
      props[attrToProp(name)] = resolvePlaceholderSync(value, store)
    } else {
      props[attrToProp(name)] = value
    }
  }

  // 注入渲染上下文引用（供组件内部使用）
  props.__xmlContext = context

  return props
}

/**
 * 解析元素的子节点。
 *
 * @param element - XML 元素
 * @param context - 渲染上下文
 * @returns VNode 子节点（可能是数组或默认 slot 函数）
 */
function resolveChildren(
  element: Element,
  context: XmlRenderContext
): any {
  const childNodes = Array.from(element.childNodes)

  // 如果没有子节点
  if (childNodes.length === 0) return undefined

  const result: (VNode | string)[] = []

  for (const node of childNodes) {
    if (node.nodeType === Node.TEXT_NODE) {
      // 文本节点 → 解析占位符
      const text = node.textContent || ''
      const trimmed = text.trim()
      if (trimmed) {
        if (hasPlaceholders(trimmed)) {
          result.push(resolvePlaceholderSync(trimmed, context.store))
        } else {
          result.push(trimmed)
        }
      }
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      // 元素节点 → 递归渲染
      const vnode = renderSingleElement(node as Element, context)
      if (vnode) {
        result.push(vnode)
      }
    }
  }

  if (result.length === 0) return undefined

  // 返回为默认 slot
  return () => result
}

// === 辅助函数 ===

/**
 * 求值条件表达式（用于 hidden / disabled 等属性）。
 *
 * @param condition - 条件字符串（占位符格式或直接表达式）
 * @param store - 变量池
 * @returns 布尔结果
 */
function evaluateCondition(condition: string, store: PluginUIVarStore): boolean {
  // 如果包含占位符花括号，去掉外层 {}
  let expr = condition.trim()
  if (expr.startsWith('{') && expr.endsWith('}')) {
    expr = expr.slice(1, -1).trim()
  }

  // 字面量 true/false
  if (expr === 'true') return true
  if (expr === 'false') return false

  return Boolean(safeEvaluate(expr, store, false))
}

/**
 * 将 kebab-case 属性名转为 camelCase prop 名。
 *
 * @param attr - 属性名如 "page-size"
 * @returns prop 名如 "pageSize"
 */
function attrToProp(attr: string): string {
  return attr.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase())
}

/**
 * 首字母大写。
 *
 * @param str - 输入字符串
 * @returns 首字母大写后的字符串
 */
function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

