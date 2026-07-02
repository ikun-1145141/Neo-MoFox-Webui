/**
 * API Executor for UI Schema
 *
 * 处理插件页面中声明式 API 调用（`<button>`、`<data-table>`、动态 `<select>`
 * 等）的执行逻辑，包括：
 * - 端点解析（相对路径自动拼接 `api-base` 前缀）；
 * - 路径参数替换（如 `/api/users/:id` → `/api/users/123`）；
 * - 请求体来源解析（`api-data-from` 指向 dataStore 的某个命名空间）；
 * - 动作字符串解析（`on-success` / `on-error`，如
 *   `show-toast:成功;refresh-table:usersTable`）。
 *
 * 实际 HTTP 发送复用 `frontend/src/api/base.ts` 的 axios 实例：
 * 该实例已统一注入认证头、解包 BaseResponse 为 data、并对错误弹出 Toast。
 */
import http from '../api/base'
import { getValueByPath } from './dataStore'

/** 支持的 HTTP 方法。 */
export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

/** API 调用参数。 */
export interface ApiCallOptions {
  /** API 端点，可为相对路径（拼接 apiBase）或绝对路径。支持 `:param` 路径参数。 */
  endpoint: string
  /** HTTP 方法，默认 `GET`。 */
  method?: ApiMethod
  /** 页面级 API 前缀（来自 `<metadata><api-base>`），相对端点会拼接此前缀。 */
  apiBase?: string | null
  /** 请求数据（请求体或查询参数）。 */
  data?: Record<string, any>
  /**
   * 路径参数替换的数据上下文。
   * 例如 endpoint=`/api/users/:id`，pathContext=`{ id: 123 }` → `/api/users/123`。
   */
  pathContext?: Record<string, any>
  /**
   * 发起请求的插件名称（设计文档 8.2 API 权限控制）。
   * 非空时在请求头注入 `X-Plugin-Name`，供后端校验页面来源插件，
   * 防止某插件注册的页面跨插件调用其他插件的 API。
   */
  pluginName?: string | null
}

/** 解析后的单个动作。 */
export interface ParsedAction {
  /** 动作类型，如 `show-toast`、`refresh-table`、`navigate`、`reload-page`、`close-dialog`。 */
  type: string
  /** 动作参数（冒号后内容），无参数时为空字符串。 */
  arg: string
}

/** 判断端点是否为绝对路径（以 `/` 或协议开头）。 */
function isAbsoluteEndpoint(endpoint: string): boolean {
  return endpoint.startsWith('/') || /^https?:\/\//i.test(endpoint)
}

/**
 * 将端点与 api-base 前缀拼接为完整端点。
 * - 绝对路径（以 `/` 或 `http` 开头）直接返回。
 * - 相对路径在存在 apiBase 时拼接，自动处理斜杠。
 */
export function resolveEndpoint(endpoint: string, apiBase?: string | null): string {
  if (isAbsoluteEndpoint(endpoint) || !apiBase) {
    return endpoint
  }
  const base = apiBase.endsWith('/') ? apiBase.slice(0, -1) : apiBase
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `${base}${path}`
}

/**
 * 替换端点中的路径参数（`:name`）为上下文中的对应值。
 *
 * @param endpoint 含 `:param` 占位符的端点
 * @param context 提供参数值的数据对象
 * @returns 替换后的端点。未在 context 中找到的占位符保持原样。
 */
export function replacePathParams(
  endpoint: string,
  context?: Record<string, any>,
): string {
  if (!context) return endpoint
  return endpoint.replace(/:([a-zA-Z_][a-zA-Z0-9_]*)/g, (match, key: string) => {
    const value = context[key]
    return value === undefined || value === null ? match : encodeURIComponent(String(value))
  })
}

/**
 * 从 dataStore 中按 `api-data-from` 路径解析请求数据。
 *
 * @param store 页面级 dataStore
 * @param dataFrom 数据来源路径（如 `form`、`user.profile`），为空时返回 undefined
 * @returns 解析出的数据对象
 */
export function resolveRequestData(
  store: Record<string, any>,
  dataFrom?: string | null,
): Record<string, any> | undefined {
  if (!dataFrom) return undefined
  const value = getValueByPath(store, dataFrom)
  return value as Record<string, any> | undefined
}

/**
 * 解析动作字符串为结构化动作列表。
 * 多个动作以 `;` 分隔，每个动作形如 `type:arg` 或 `type`。
 *
 * 示例：`show-toast:提交成功;refresh-table:usersTable`
 *
 * @param spec 动作字符串（来自 `on-success` / `on-error`）
 * @returns 解析后的动作列表
 */
export function parseActions(spec?: string | null): ParsedAction[] {
  if (!spec || !spec.trim()) return []
  const actions: ParsedAction[] = []
  for (const segment of spec.split(';')) {
    const trimmed = segment.trim()
    if (!trimmed) continue
    const colonIdx = trimmed.indexOf(':')
    if (colonIdx === -1) {
      actions.push({ type: trimmed, arg: '' })
    } else {
      actions.push({
        type: trimmed.slice(0, colonIdx).trim(),
        arg: trimmed.slice(colonIdx + 1).trim(),
      })
    }
  }
  return actions
}

/**
 * 执行一次声明式 API 调用。
 *
 * 端点先经过 api-base 拼接与路径参数替换，再按方法发送请求：
 * - GET / DELETE：data 作为查询参数（params）。
 * - POST / PUT / PATCH：data 作为请求体。
 *
 * 复用全局 axios 实例，返回值为已解包的响应 `data` 字段。
 *
 * @param options API 调用参数
 * @returns 后端响应的 data 部分
 */
export async function executeApiCall<T = any>(options: ApiCallOptions): Promise<T> {
  const { endpoint, method = 'GET', apiBase, data, pathContext, pluginName } = options

  let url = resolveEndpoint(endpoint, apiBase)
  url = replacePathParams(url, pathContext)

  const upperMethod = method.toUpperCase() as ApiMethod

  // 设计文档 8.2：注入 X-Plugin-Name 头，供后端校验请求来源插件。
  const headers: Record<string, string> = {}
  if (pluginName) {
    headers['X-Plugin-Name'] = pluginName
  }

  switch (upperMethod) {
    case 'GET':
      return http.get(url, { params: data, headers })
    case 'DELETE':
      return http.delete(url, { params: data, headers })
    case 'POST':
      return http.post(url, data, { headers })
    case 'PUT':
      return http.put(url, data, { headers })
    case 'PATCH':
      return http.patch(url, data, { headers })
    default:
      return http.get(url, { params: data, headers })
  }
}
