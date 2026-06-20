/**
 * API 模板解析与执行引擎。
 *
 * 将 XML <definitions> 中声明的 <api> 模板解析为可执行的请求配置，
 * 并在管道指令或 sys.api() 调用时实际发起请求。
 *
 * 请求前后自动向变量池写入 api.<id>.pending / error / last_response。
 */

import instance from '../../api/third-party'
import type { PluginUIVarStore } from '../../stores/plugin-ui-vars'
import { resolvePlaceholderSync } from './placeholder-parser'
import { safeEvaluate } from './expression-evaluator'

// === 类型定义 ===

/** API 模板定义（从 XML <api> 元素解析） */
export interface ApiTemplate {
  /** 唯一标识（对应 <api id="...">) */
  id: string
  /** HTTP 方法 */
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  /** 请求 URL（可含占位符） */
  url: string
  /** 请求体模板（JSON 字符串，可含占位符），仅 POST/PUT/PATCH */
  body: string | null
  /** 请求头模板 */
  headers: Record<string, string>
  /** 响应映射路径（将响应数据写入变量池的指定路径） */
  responseMapping: string | null
  /** 是否自动触发（页面加载时即执行） */
  autoFetch: boolean
  /**
   * 是否使用原始响应模式（跳过 BaseResponse 拦截器）。
   *
   * 当设置为 true 时，响应拦截器不会按 `{ code, data, message }` 结构解析，
   * 而是直接将 HTTP 响应体原文写入变量池。用户可通过 response-to 指定的
   * 变量路径访问完整响应对象，然后在模板中使用点路径取值。
   *
   * XML 用法示例：
   * ```xml
   * <api id="weather" method="GET" url="https://api.example.com/weather"
   *      raw-response="true" response-to="weather_data" />
   * ```
   * 之后可通过 `{weather_data.temperature}` 等点路径访问响应字段。
   */
  rawResponse: boolean
}

/** API 执行结果 */
export interface ApiExecutionResult {
  success: boolean
  data: any
  error: string | null
}

// === API 模板注册表 ===

/**
 * API 模板引擎。
 *
 * 管理一组 API 模板定义，并提供执行能力。
 * 每个 page 实例拥有独立的 ApiTemplateEngine。
 */
export class ApiTemplateEngine {
  private templates = new Map<string, ApiTemplate>()
  private store: PluginUIVarStore

  constructor(store: PluginUIVarStore) {
    this.store = store
  }

  /**
   * 注册一个 API 模板。
   *
   * @param template - API 模板定义
   */
  register(template: ApiTemplate): void {
    this.templates.set(template.id, template)
    // 初始化状态变量
    this.store.set(`api.${template.id}.pending`, false)
    this.store.set(`api.${template.id}.error`, null)
    this.store.set(`api.${template.id}.last_response`, null)
  }

  /**
   * 获取已注册的模板。
   *
   * @param id - 模板 ID
   * @returns 模板定义或 undefined
   */
  getTemplate(id: string): ApiTemplate | undefined {
    return this.templates.get(id)
  }

  /**
   * 获取所有已注册的模板。
   *
   * @returns 模板 Map
   */
  getAllTemplates(): Map<string, ApiTemplate> {
    return this.templates
  }

  /**
   * 执行指定 API 模板。
   *
   * 执行前后会自动更新变量池中的 api.<id>.pending/error/last_response。
   *
   * @param id - 模板 ID
   * @param params - 覆盖参数（用于 sys.api(id, params) 场景）
   * @returns 执行结果
   */
  async execute(id: string, params?: Record<string, any>): Promise<ApiExecutionResult> {
    const template = this.templates.get(id)
    if (!template) {
      return { success: false, data: null, error: `API 模板 "${id}" 未注册` }
    }

    // 如果传入了 params，临时写入 page scope 以便占位符解析
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        this.store.set(`__api_param_${key}`, value)
      }
    }

    // 设置 pending 状态
    this.store.set(`api.${id}.pending`, true)
    this.store.set(`api.${id}.error`, null)

    try {
      // 解析 URL 中的占位符
      const resolvedUrl = resolvePlaceholderSync(template.url, this.store)

      // 解析 body 中的占位符
      let resolvedBody: any = null
      if (template.body) {
        resolvedBody = this.resolveBodyTemplate(template.body)
      }

      // 解析 headers 中的占位符
      const resolvedHeaders: Record<string, string> = {}
      for (const [key, value] of Object.entries(template.headers)) {
        resolvedHeaders[key] = resolvePlaceholderSync(value, this.store)
      }

      // 发起请求
      const response = await this.makeRequest(
        template.method,
        resolvedUrl,
        resolvedBody,
        resolvedHeaders,
        template.rawResponse
      )

      // 写入成功状态
      this.store.set(`api.${id}.last_response`, response)
      this.store.set(`api.${id}.pending`, false)

      // 响应映射
      if (template.responseMapping) {
        this.store.set(template.responseMapping, response)
      }

      return { success: true, data: response, error: null }
    } catch (err: any) {
      const errorMsg = err?.message || '请求失败'
      this.store.set(`api.${id}.error`, errorMsg)
      this.store.set(`api.${id}.pending`, false)
      return { success: false, data: null, error: errorMsg }
    } finally {
      // 清理临时参数
      if (params) {
        for (const key of Object.keys(params)) {
          this.store.set(`__api_param_${key}`, undefined)
        }
      }
    }
  }

  /**
   * 执行所有标记为 autoFetch 的模板。
   * 通常在页面加载完成后调用。
   */
  async executeAutoFetch(): Promise<void> {
    const autoFetchTemplates = [...this.templates.values()].filter(t => t.autoFetch)
    await Promise.allSettled(autoFetchTemplates.map(t => this.execute(t.id)))
  }

  /**
   * 解析 body 模板中的占位符。
   *
   * 由于占位符语法 {expr} 与 JSON 花括号冲突，直接对整个 body 模板
   * 执行字符串级占位符解析会导致 JSON 结构被误判为表达式。
   *
   * 策略：先尝试 JSON.parse 模板字符串，如果成功则递归遍历每个字符串值
   * 单独做占位符解析；如果 JSON.parse 失败（非 JSON 格式），则回退到
   * 普通字符串占位符解析。
   *
   * @param bodyTemplate - 含占位符的 body 模板字符串
   * @returns 解析后的对象或字符串
   */
  private resolveBodyTemplate(bodyTemplate: string): any {
    try {
      // 尝试将模板作为 JSON 解析（此时占位符还未替换，但 JSON 结构可辨识）
      const parsed = JSON.parse(bodyTemplate)
      // 递归解析 JSON 中的字符串值占位符
      return this.resolveJsonValues(parsed)
    } catch {
      // 非合法 JSON（可能是纯占位符表达式如 "{someObj}"），回退到字符串级解析
      const resolved = resolvePlaceholderSync(bodyTemplate, this.store)
      try {
        return JSON.parse(resolved)
      } catch {
        return resolved
      }
    }
  }

  /**
   * 递归解析 JSON 值中的占位符表达式。
   *
   * - 字符串值：执行占位符替换。如果整个字符串是单个占位符 "{expr}"，
   *   则返回表达式的原始类型（数字、布尔、对象等），而非字符串化结果。
   * - 数组：逐元素递归。
   * - 对象：逐值递归。
   * - 其他类型：原样返回。
   *
   * @param value - JSON 值
   * @returns 解析后的值
   */
  private resolveJsonValues(value: any): any {
    if (typeof value === 'string') {
      // 检查是否为纯占位符（整个字符串就是一个 {expr}）
      const pureExprMatch = value.match(/^\{(.+)\}$/)
      if (pureExprMatch && !value.includes('}{')) {
        // 纯表达式：返回原始类型
        return safeEvaluate(pureExprMatch[1], this.store, '')
      }
      // 含混合文本+占位符，或不含占位符：做字符串模板替换
      return resolvePlaceholderSync(value, this.store)
    }

    if (Array.isArray(value)) {
      return value.map(item => this.resolveJsonValues(item))
    }

    if (value !== null && typeof value === 'object') {
      const resolved: Record<string, any> = {}
      for (const [key, val] of Object.entries(value)) {
        resolved[key] = this.resolveJsonValues(val)
      }
      return resolved
    }

    return value
  }

  /**
   * 发起 HTTP 请求。
   *
   * @param method - HTTP 方法
   * @param url - 请求 URL
   * @param body - 请求体
   * @param headers - 附加请求头
   * @param rawResponse - 是否跳过 BaseResponse 拦截器，直接返回原始响应体
   * @returns 响应数据
   */
  private async makeRequest(
    method: string,
    url: string,
    body: any,
    headers: Record<string, string>,
    rawResponse: boolean = false
  ): Promise<any> {
    const config: any = { headers, __rawResponse: rawResponse }

    switch (method) {
      case 'GET':
        return instance.get(url, config)
      case 'POST':
        console.debug(`[ApiTemplateEngine] 发起 POST 请求: ${url} with body`, body, 'and headers', headers)
        return instance.post(url, body, config)
      case 'PUT':
        return instance.put(url, body, config)
      case 'PATCH':
        return instance.patch(url, body, config)
      case 'DELETE':
        return instance.delete(url, config)
      default:
        return instance.get(url, config)
    }
  }

  /**
   * 清理所有注册的模板和状态。
   * 在页面销毁时调用。
   */
  destroy(): void {
    this.templates.clear()
  }
}

// === 模板解析工具 ===

/**
 * 从 XML <api> 元素解析出 ApiTemplate。
 *
 * @param element - XML DOM 元素
 * @returns 解析后的 ApiTemplate
 */
export function parseApiTemplateFromElement(element: Element): ApiTemplate {
  const id = element.getAttribute('id') || ''
  const method = (element.getAttribute('method') || 'GET').toUpperCase() as ApiTemplate['method']
  const url = element.getAttribute('url') || ''
  const responseMapping = element.getAttribute('response-to') || null
  const autoFetch = element.getAttribute('auto-fetch') === 'true'
  const rawResponse = element.getAttribute('raw-response') === 'true'

  // 解析 body（子元素或 body 属性）
  let body: string | null = null
  const bodyEl = element.querySelector('body')
  if (bodyEl) {
    console.debug(`[parseApiTemplate] id="${id}" 从 <body> 子元素获取 body:`, bodyEl.textContent)
    body = bodyEl.textContent || null
  } else {
    body = element.getAttribute('body') || null
    console.debug(`[parseApiTemplate] id="${id}" 从 body 属性获取 body:`, JSON.stringify(body), '| element.getAttribute("body") raw:', element.getAttribute('body'))
  }
  console.debug(`[parseApiTemplate] id="${id}" 最终 body:`, JSON.stringify(body))

  // 解析 headers
  const headers: Record<string, string> = {}
  const headerEls = element.querySelectorAll('header')
  for (const headerEl of headerEls) {
    const name = headerEl.getAttribute('name')
    const value = headerEl.getAttribute('value') || headerEl.textContent || ''
    if (name) {
      headers[name] = value
    }
  }

  return { id, method, url, body, headers, responseMapping, autoFetch, rawResponse }
}
