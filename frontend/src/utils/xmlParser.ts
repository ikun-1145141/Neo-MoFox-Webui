/**
 * XML Parser for UI Schema
 *
 * 将插件注册的 `<ui-page>` XML 描述解析为结构化的节点树（UiNode），
 * 供前端渲染引擎递归渲染。解析逻辑与后端校验器
 * （Plugin/utils/xml_schema_validator.py）的标签/属性约定保持一致。
 *
 * 设计要点：
 * - 根节点必须为 `<ui-page>` 且声明 `schema-version`。
 * - `<metadata>` 中的 title/description/icon/api-base 被提取为页面元数据。
 * - `<template>` 子树包含 Vue 模板语法（如 `:color`、`{{ row.x }}`），
 *   不再继续解析为节点，而是以原始字符串形式保留（rawTemplate），
 *   由渲染层在隔离上下文中编译。
 */

/** 解析后的单个 UI 节点。 */
export interface UiNode {
  /** 本地标签名（已去除命名空间前缀），如 `container`、`input-field`。 */
  tag: string
  /** 标签属性键值对（属性值统一为字符串）。 */
  attrs: Record<string, string>
  /** 子节点列表。 */
  children: UiNode[]
  /** 文本内容（仅叶子节点，如 `<title>`、`<button>` 的文本）。 */
  text?: string
  /**
   * `<template>` 节点的原始内部 HTML 字符串（含 Vue 模板语法）。
   * 仅当 `tag === 'template'` 时存在。
   */
  rawTemplate?: string
}

/** 页面元数据（来自 `<metadata>`）。 */
export interface UiPageMetadata {
  title: string
  description: string | null
  icon: string | null
  apiBase: string | null
}

/** `parseUiPage` 的解析结果。 */
export interface ParsedUiPage {
  /** schema 版本（来自根节点 `schema-version`）。 */
  schemaVersion: string
  /** 页面元数据。 */
  metadata: UiPageMetadata
  /** `<layout>` 下的顶层节点列表（页面主体内容）。 */
  layout: UiNode[]
  /** 完整的根节点树（包含 metadata/layout 等所有子节点）。 */
  root: UiNode
}

/** 解析失败时抛出的错误。 */
export class XmlParseError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'XmlParseError'
  }
}

/**
 * 去除标签/属性名上可能存在的命名空间前缀。
 * 浏览器 DOMParser 通常已通过 localName 处理命名空间，
 * 但此处兜底处理形如 `ns:tag` 的前缀。
 */
function localName(name: string): string {
  const idx = name.indexOf(':')
  return idx >= 0 ? name.slice(idx + 1) : name
}

/** 读取元素的属性键值对（使用 localName 作为键）。 */
function readAttrs(el: Element): Record<string, string> {
  const attrs: Record<string, string> = {}
  for (const attr of Array.from(el.attributes)) {
    const key = localName(attr.name)
    // 跳过命名空间声明属性
    if (key === 'xmlns') continue
    attrs[key] = attr.value
  }
  return attrs
}

/** 判断元素是否为纯叶子节点（无元素子节点，仅文本）。 */
function isLeaf(el: Element): boolean {
  for (const child of Array.from(el.childNodes)) {
    if (child.nodeType === Node.ELEMENT_NODE) return false
  }
  return true
}

/** 将单个 DOM 元素递归转换为 UiNode。 */
function elementToNode(el: Element): UiNode {
  const tag = localName(el.tagName)
  const node: UiNode = {
    tag,
    attrs: readAttrs(el),
    children: [],
  }

  // <template> 子树保留原始字符串，不继续解析
  if (tag === 'template') {
    node.rawTemplate = el.innerHTML.trim()
    return node
  }

  if (isLeaf(el)) {
    const text = (el.textContent ?? '').trim()
    if (text) node.text = text
    return node
  }

  for (const child of Array.from(el.children)) {
    node.children.push(elementToNode(child))
  }
  return node
}

/** 在节点的直接子节点中查找首个指定标签的节点。 */
function findChild(node: UiNode, tag: string): UiNode | undefined {
  return node.children.find((c) => c.tag === tag)
}

/** 从根节点提取页面元数据。 */
function extractMetadata(root: UiNode): UiPageMetadata {
  const metadata: UiPageMetadata = {
    title: '',
    description: null,
    icon: null,
    apiBase: null,
  }

  const metaNode = findChild(root, 'metadata')
  if (!metaNode) return metadata

  for (const child of metaNode.children) {
    const value = (child.text ?? '').trim() || null
    switch (child.tag) {
      case 'title':
        metadata.title = value ?? ''
        break
      case 'description':
        metadata.description = value
        break
      case 'icon':
        metadata.icon = value
        break
      case 'api-base':
        metadata.apiBase = value
        break
    }
  }

  return metadata
}

/**
 * 解析 `<ui-page>` XML 字符串为结构化页面定义。
 *
 * @param xml 完整的 XML 页面描述字符串
 * @returns 解析后的页面定义（元数据 + 布局节点树）
 * @throws {XmlParseError} XML 为空、解析失败、根节点非 `<ui-page>`、
 *   缺少 `schema-version` 或缺少 `<title>` 时抛出。
 */
export function parseUiPage(xml: string): ParsedUiPage {
  if (!xml || !xml.trim()) {
    throw new XmlParseError('XML 内容为空')
  }

  const parser = new DOMParser()
  const doc = parser.parseFromString(xml, 'application/xml')

  // DOMParser 解析失败时会生成 <parsererror> 元素
  const parseError = doc.querySelector('parsererror')
  if (parseError) {
    throw new XmlParseError(`XML 解析失败: ${parseError.textContent?.trim() ?? '未知错误'}`)
  }

  const rootEl = doc.documentElement
  if (!rootEl || localName(rootEl.tagName) !== 'ui-page') {
    throw new XmlParseError(
      `根节点必须为 <ui-page>，实际为 <${rootEl ? localName(rootEl.tagName) : '空'}>`,
    )
  }

  const schemaVersion = rootEl.getAttribute('schema-version')
  if (!schemaVersion) {
    throw new XmlParseError('根节点 <ui-page> 缺少必需属性 schema-version')
  }

  const root = elementToNode(rootEl)
  const metadata = extractMetadata(root)
  if (!metadata.title) {
    throw new XmlParseError('<metadata> 缺少必需的 <title>')
  }

  const layoutNode = findChild(root, 'layout')
  const layout = layoutNode ? layoutNode.children : []

  return {
    schemaVersion,
    metadata,
    layout,
    root,
  }
}

// ---------------------------------------------------------------------------
// 通用 XML → ComponentNode 解析（不限定 ui-page 根节点）
// ---------------------------------------------------------------------------

/** 通用组件节点（与 UiNode 类似，但使用 `attributes` 字段名且无 rawTemplate）。 */
export interface ComponentNode {
  /** 标签名。 */
  tag: string
  /** 标签属性键值对（属性值统一为字符串，"true"/"false" 保持原样）。 */
  attributes: Record<string, string>
  /** 子节点列表。 */
  children: ComponentNode[]
  /** 文本内容（trim 后若非空则保留）。 */
  text?: string
}

/** 将单个 DOM 元素递归转换为 ComponentNode。 */
function elementToComponentNode(el: Element): ComponentNode {
  const tag = localName(el.tagName)
  const attributes: Record<string, string> = {}
  for (const attr of Array.from(el.attributes)) {
    const key = localName(attr.name)
    if (key === 'xmlns') continue
    // "true"/"false" 保持字符串原样，Vue 组件自行处理布尔转换
    attributes[key] = attr.value
  }

  const node: ComponentNode = { tag, attributes, children: [] }

  if (isLeaf(el)) {
    const text = (el.textContent ?? '').trim()
    if (text) node.text = text
    return node
  }

  for (const child of Array.from(el.children)) {
    node.children.push(elementToComponentNode(child))
  }
  return node
}

/**
 * 将 XML 字符串解析为 ComponentNode 树。
 *
 * 与 `parseUiPage` 不同，此函数不限定根节点类型，也不提取元数据，
 * 仅做通用的 XML → 节点树转换。
 *
 * @param xmlString 完整的 XML 字符串
 * @returns 根 ComponentNode
 * @throws {Error} XML 为空或解析失败时抛出
 */
export function parseUiXml(xmlString: string): ComponentNode {
  if (!xmlString || !xmlString.trim()) {
    throw new Error('XML 内容为空')
  }

  const parser = new DOMParser()
  const doc = parser.parseFromString(xmlString, 'application/xml')

  const parseError = doc.querySelector('parsererror')
  if (parseError) {
    throw new Error(`XML 解析失败: ${parseError.textContent?.trim() ?? '未知错误'}`)
  }

  const rootEl = doc.documentElement
  if (!rootEl) {
    throw new Error('XML 解析失败: 无根元素')
  }

  return elementToComponentNode(rootEl)
}
