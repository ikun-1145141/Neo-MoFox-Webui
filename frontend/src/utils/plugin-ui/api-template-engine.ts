/**
 * API 模板解析与执行引擎。
 *
 * 将 XML <definitions> 中声明的 <api> 模板解析为可执行的请求配置，
 * 并在管道指令或 sys.api() 调用时实际发起请求。
 *
 * 请求前后自动向变量池写入 api.<id>.pending / error / last_response。
 */

import instance from '../../api/base'
import type { PluginUIVarStore } from '../../stores/plugin-ui-vars'
import { resolvePlaceholderSync } from './placeholder-parser'

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
        const bodyStr = resolvePlaceholderSync(template.body, this.store)
        try {
          resolvedBody = JSON.parse(bodyStr)
        } catch {
          resolvedBody = bodyStr
        }
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
        resolvedHeaders
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
   * 发起 HTTP 请求。
   *
   * @param method - HTTP 方法
   * @param url - 请求 URL
   * @param body - 请求体
   * @param headers - 附加请求头
   * @returns 响应数据
   */
  private async makeRequest(
    method: string,
    url: string,
    body: any,
    headers: Record<string, string>
  ): Promise<any> {
    const config: any = { headers }

    switch (method) {
      case 'GET':
        return instance.get(url, config)
      case 'POST':
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

  // 解析 body（子元素或 body 属性）
  let body: string | null = null
  const bodyEl = element.querySelector('body')
  if (bodyEl) {
    body = bodyEl.textContent || null
  } else {
    body = element.getAttribute('body') || null
  }

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

  return { id, method, url, body, headers, responseMapping, autoFetch }
}
