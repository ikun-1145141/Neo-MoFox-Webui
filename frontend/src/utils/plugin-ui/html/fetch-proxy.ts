/**
 * fetch / XHR 代理重写。
 *
 * 在 HTML 沙箱的脚本执行上下文中重写 `window.fetch` 与
 * `XMLHttpRequest`，使所有出站请求透明地经过统一拦截链：
 *
 * - 注入 Authorization / X-API-Key / X-Plugin-Name 头
 * - **不**做 BaseResponse 解包（window.fetch 保持透传语义）
 *
 * BaseResponse 解包由 `sys.request` / `sys.api` 负责 —— 插件作者
 * 需要解包时显式使用 `sys.request(url)` 或 `sys.api(id, params)`，
 * 而非裸 `fetch(url)`。这与设计文档 §5.4 的「sys.* 是唯一交互通道」
 * 心智模型一致：`fetch` 是兼容层（让第三方库能工作），`sys.*` 才是
 * 推荐入口（带类型/错误语义）。
 *
 * `installFetchProxy()` 返回 `uninstall` 函数，沙箱销毁时调用
 * 以还原原始方法。
 */

export interface FetchProxyContext {
  /** 当前插件名，用于注入 X-Plugin-Name 头 */
  pluginName: string
  /** 获取 token 的回调，返回 null 表示无 token */
  getToken(): string | null
  /** 错误回调（保留参数供未来扩展，目前 fetch 透传不主动触发） */
  onError?: (msg: string) => void
}

/**
 * 安装 fetch / XHR 代理。
 *
 * 警告：会修改全局 `window.fetch` 和 `XMLHttpRequest.prototype`。
 * 多沙箱并存时需引用计数（暂按单沙箱实现，TODO）。
 *
 * @returns uninstall 函数
 */
export function installFetchProxy(ctx: FetchProxyContext): () => void {
  const originalFetch = window.fetch
  const originalXhrOpen = XMLHttpRequest.prototype.open
  const originalXhrSend = XMLHttpRequest.prototype.send
  const originalXhrSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader

  // 注入公共请求头
  function applyAuthHeaders(headers: Headers): void {
    const token = ctx.getToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
      headers.set('X-API-Key', token)
    }
    if (!headers.has('X-Plugin-Name')) {
      headers.set('X-Plugin-Name', ctx.pluginName)
    }
  }

  // === 重写 fetch ===
  // 仅注入头，透传 Response。解包由 sys.request 负责。
  window.fetch = async function (
    input: RequestInfo | URL,
    init?: RequestInit
  ): Promise<Response> {
    const headers = new Headers(init?.headers || {})
    applyAuthHeaders(headers)
    const mergedInit: RequestInit = { ...init, headers }
    return originalFetch(input, mergedInit)
  }

  // === 重写 XHR ===
  // 仅注入头，不干预响应解析。

  XMLHttpRequest.prototype.open = function (
    method: string,
    url: string,
    async: boolean = true,
    username?: string | null,
    password?: string | null
  ): void {
    return originalXhrOpen.call(this, method, url, async, username, password)
  }

  XMLHttpRequest.prototype.setRequestHeader = function (name: string, value: string): void {
    return originalXhrSetRequestHeader.call(this, name, value)
  }

  XMLHttpRequest.prototype.send = function (body?: Document | XMLHttpRequestBodyInit | null): void {
    // 自动注入 token / X-Plugin-Name（若未显式设置）
    const token = ctx.getToken()
    if (token) {
      try { originalXhrSetRequestHeader.call(this, 'Authorization', `Bearer ${token}`) } catch { /* already set */ }
      try { originalXhrSetRequestHeader.call(this, 'X-API-Key', token) } catch { /* already set */ }
    }
    try { originalXhrSetRequestHeader.call(this, 'X-Plugin-Name', ctx.pluginName) } catch { /* already set */ }
    return originalXhrSend.call(this, body)
  }

  // === 卸载 ===
  return function uninstall(): void {
    window.fetch = originalFetch
    XMLHttpRequest.prototype.open = originalXhrOpen
    XMLHttpRequest.prototype.send = originalXhrSend
    XMLHttpRequest.prototype.setRequestHeader = originalXhrSetRequestHeader
  }
}
