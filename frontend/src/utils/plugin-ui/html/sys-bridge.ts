/**
 * sys 桥接对象（HTML 轨唯一交互通道）。
 *
 * 每个 HTML 沙箱实例对应一个独立的 SysBridge 对象，
 * 注入到沙箱脚本上下文（window.__plugin_sys_<pageId>）。
 *
 * 与设计文档 §5.4 1:1 对齐。
 */

import type { Router } from 'vue-router'
import type { PluginUIVarStore } from '../plugin-ui-vars'
import type { ApiTemplateEngine } from '../api-template-engine'
import { useToastStore } from '../../../utils/toast'
import { useDialogStore } from '../../../utils/dialog'
import type { FetchProxyContext } from './fetch-proxy'
import { t } from '../../../utils/i18n'
import thirdPartyInstance from '../../../api/third-party'

// === Page-level EventEmitter（替代 mitt） ===

type AnyFn = (...args: any[]) => void

class PageBus {
  private map = new Map<string, Set<AnyFn>>()

  on(event: string, fn: AnyFn): void {
    let set = this.map.get(event)
    if (!set) {
      set = new Set()
      this.map.set(event, set)
    }
    set.add(fn)
  }

  off(event: string, fn: AnyFn): void {
    const set = this.map.get(event)
    if (set) set.delete(fn)
  }

  emit(event: string, ...args: any[]): void {
    const set = this.map.get(event)
    if (set) {
      for (const fn of set) {
        try {
          fn(...args)
        } catch (e) {
          console.error(`[sys.bus] 事件处理器 "${event}" 抛出异常:`, e)
        }
      }
    }
  }

  clear(): void {
    this.map.clear()
  }
}

// === SysBridge 接口 ===

export interface SysBridge {
  /** page scope 变量池 */
  vars: Record<string, any>
  /** plugin scope 变量池 */
  plugin: Record<string, any>
  /** global scope 变量池（只读） */
  readonly global: Readonly<Record<string, any>>

  /** 调用预定义 API 模板 */
  api(id: string, params?: Record<string, any>): Promise<any>
  /** 统一请求方法 */
  request(url: string, options?: RequestInit): Promise<any>

  /** 事件总线（仅当前 page） */
  bus: {
    on(event: string, fn: AnyFn): void
    off(event: string, fn: AnyFn): void
    emit(event: string, ...args: any[]): void
  }

  /** UI 交互快捷入口 */
  ui: {
    notify(msg: string, level?: 'info' | 'success' | 'warn' | 'error'): void
    toast(msg: string, level?: 'info' | 'success' | 'warn' | 'error'): void
    notice(msg: string, opts?: any): void
    confirm(msg: string, opts?: any): Promise<boolean>
    alert(msg: string, opts?: any): Promise<void>
    dialog: {
      open(id: string): void
      close(id: string): void
    }
  }

  /** 当前主题（只读） */
  readonly theme: Readonly<{ mode: string; primary: string }>

  /** 路由（路径仍由系统管理，不可手写绝对路径） */
  route: {
    current: string
    back(): void
    go(plugin: string, page: string): void
  }

  /** 格式化辅助 */
  format: {
    date(val: any, pattern?: string): string
    number(val: number, opts?: Intl.NumberFormatOptions): string
    currency(val: number, opts?: Intl.NumberFormatOptions): string
  }

  /** 文案翻译 */
  i18n: { t(key: string, params?: Record<string, string>): string }

  /** 销毁：清理事件总线、解除监听 */
  destroy(): void
}

// === 工厂函数 ===

export interface SysBridgeOptions {
  store: PluginUIVarStore
  apiEngine: ApiTemplateEngine
  pluginName: string
  pageId: string
  router: Router
  /** fetch 代理上下文（用于 sys.request 与重写后的 window.fetch/XHR） */
  fetchProxyCtx?: FetchProxyContext
}

/**
 * 创建一个 sys 桥接对象。
 *
 * 调用方负责把返回的 sys 暴露给沙箱脚本（通常是 window.__plugin_sys_<pageId>）。
 */
export function createSysBridge(opts: SysBridgeOptions): SysBridge {
  const { store, apiEngine, pageId, router } = opts
  const bus = new PageBus()
  const toastStore = useToastStore()
  const dialogStore = useDialogStore()

  // vars / plugin 用 Proxy 包装 store，使读写透明地走 store.get / store.set
  const varsProxy = new Proxy(store.page, {
    get(_t, prop) {
      if (typeof prop === 'string') return store.get(prop)
      return undefined
    },
    set(_t, prop, value) {
      if (typeof prop === 'string') store.set(prop, value)
      return true
    },
    has(_t, prop) {
      return typeof prop === 'string' ? store.get(prop) !== undefined : false
    },
    ownKeys() {
      return Reflect.ownKeys(store.page)
    },
    getOwnPropertyDescriptor(_t, prop) {
      if (typeof prop === 'string') {
        const v = store.get(prop)
        if (v !== undefined) {
          return { configurable: true, enumerable: true, writable: true, value: v }
        }
      }
      return undefined
    },
  })

  const pluginProxy = new Proxy(store.plugin, {
    get(_t, prop) {
      if (typeof prop === 'string') {
        // plugin scope 通过 store.set('plugin.x', ...) 写入，因此读路径也走 'plugin.' 前缀
        return store.get(`plugin.${prop}`)
      }
      return undefined
    },
    set(_t, prop, value) {
      if (typeof prop === 'string') store.set(`plugin.${prop}`, value)
      return true
    },
  })

  const globalProxy = Object.freeze({ ...store.global }) as Readonly<Record<string, any>>

  // 获取当前主题信息
  const getTheme = () => {
    const themeMode = store.global?.theme?.mode ?? 'auto'
    const themePrimary = store.global?.theme?.primary_color ?? '#0058bd'
    return Object.freeze({ mode: themeMode, primary: themePrimary })
  }

  // === sys.request ===
  // 复用 third-party.ts 的 axios 实例 —— 它已内置：
  //   - Token 注入（Authorization / X-API-Key）
  //   - 系统重启拦截
  //   - BaseResponse 协议解包到 .data
  //   - 错误统一 Toast
  //   - __rawResponse 配置跳过 BaseResponse 校验
  //
  // 作者侧 API 保持 fetch-like 风格（url + options），
  // 内部把 options 映射为 axios config。
  //
  // 与裸 window.fetch 的差异：
  //   - window.fetch（已被 fetch-proxy 重写）只注入头，不解包 —— 兼容第三方库
  //   - sys.request 注入头 + 解包 + 错误 Toast —— 推荐入口
  const sysRequest = async (url: string, options?: RequestInit): Promise<any> => {
    const method = (options?.method || 'GET').toUpperCase() as
      | 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

    // fetch body → axios data
    let data: any = undefined
    if (options?.body != null) {
      if (typeof options.body === 'string') {
        data = options.body
      } else if (options.body instanceof FormData) {
        data = options.body
      } else {
        // 其他 BodyInit 类型（Blob/ArrayBuffer 等）原样传
        data = options.body as any
      }
    }

    // fetch headers → axios headers
    const headers: Record<string, string> = {}
    if (options?.headers) {
      const h = options.headers as Headers | Record<string, string>
      if (h instanceof Headers) {
        h.forEach((v, k) => { headers[k] = v })
      } else {
        Object.assign(headers, h)
      }
    }

    const config: any = { headers }

    switch (method) {
      case 'GET':
        return thirdPartyInstance.get(url, config)
      case 'POST':
        return thirdPartyInstance.post(url, data, config)
      case 'PUT':
        return thirdPartyInstance.put(url, data, config)
      case 'PATCH':
        return thirdPartyInstance.patch(url, data, config)
      case 'DELETE':
        return thirdPartyInstance.delete(url, config)
      default:
        return thirdPartyInstance.get(url, config)
    }
  }

  // === sys.ui ===
  const levelToToastType: Record<string, 'info' | 'success' | 'error'> = {
    info: 'info',
    success: 'success',
    warn: 'info',
    warning: 'info',
    error: 'error',
  }

  const sysUi = {
    notify: (msg: string, level: 'info' | 'success' | 'warn' | 'error' = 'info') => {
      toastStore.show(msg, levelToToastType[level] || 'info')
    },
    toast: (msg: string, level: 'info' | 'success' | 'warn' | 'error' = 'info') => {
      toastStore.show(msg, levelToToastType[level] || 'info')
    },
    notice: (msg: string, _opts?: any) => {
      // TODO: 接入 WebUI 通知中心
      toastStore.show(msg, 'info')
    },
    confirm: (msg: string, opts?: any) => {
      return dialogStore.confirm(msg, opts?.title, opts?.confirmText, opts?.cancelText)
    },
    alert: (msg: string, opts?: any) => {
      return dialogStore.alert(msg, opts?.title)
    },
    dialog: {
      open: (id: string) => {
        store.set(`__dialog_${id}_open`, true)
      },
      close: (id: string) => {
        store.set(`__dialog_${id}_open`, false)
      },
    },
  }

  // === sys.route ===
  const sysRoute = {
    get current(): string {
      return router.currentRoute.value.fullPath
    },
    back(): void {
      router.back()
    },
    go(plugin: string, page: string): void {
      router.push({ path: '/plugin-ui', query: { plugin, page } })
    },
  }

  // === sys.format ===
  const sysFormat = {
    date(val: any, pattern = 'yyyy-MM-dd HH:mm:ss'): string {
      if (!val) return ''
      const d = new Date(val)
      if (Number.isNaN(d.getTime())) return String(val)
      // 简单 pattern 替换
      const pad = (n: number) => String(n).padStart(2, '0')
      return pattern
        .replace(/yyyy/g, String(d.getFullYear()))
        .replace(/MM/g, pad(d.getMonth() + 1))
        .replace(/dd/g, pad(d.getDate()))
        .replace(/HH/g, pad(d.getHours()))
        .replace(/mm/g, pad(d.getMinutes()))
        .replace(/ss/g, pad(d.getSeconds()))
    },
    number(val: number, opts?: Intl.NumberFormatOptions): string {
      try {
        return new Intl.NumberFormat(undefined, opts).format(val)
      } catch {
        return String(val)
      }
    },
    currency(val: number, opts?: Intl.NumberFormatOptions): string {
      try {
        return new Intl.NumberFormat(undefined, { style: 'currency', ...opts }).format(val)
      } catch {
        return String(val)
      }
    },
  }

  // === sys.i18n ===
  const sysI18n = {
    t: (key: string, params?: Record<string, string>) => t(key, params),
  }

  // === sys.api ===
  const sysApi = async (id: string, params?: Record<string, any>): Promise<any> => {
    const result = await apiEngine.execute(id, params)
    if (!result.success) {
      throw new Error(result.error || 'API 调用失败')
    }
    return result.data
  }

  // === 组装 sys ===
  const sys: SysBridge = {
    vars: varsProxy,
    plugin: pluginProxy,
    global: globalProxy,
    api: sysApi,
    request: sysRequest,
    bus: { on: bus.on.bind(bus), off: bus.off.bind(bus), emit: bus.emit.bind(bus) },
    ui: sysUi,
    get theme() {
      return getTheme()
    },
    route: sysRoute,
    format: sysFormat,
    i18n: sysI18n,
    destroy() {
      bus.clear()
    },
  }

  // 暴露到 window 以便插件脚本能取到
  const globalKey = `__plugin_sys_${pageId}`
  ;(window as any)[globalKey] = sys

  return sys
}

/**
 * 销毁 sys 桥接对象并清理 window 引用。
 */
export function destroySysBridge(sys: SysBridge, pageId: string): void {
  sys.destroy()
  const globalKey = `__plugin_sys_${pageId}`
  delete (window as any)[globalKey]
}

// 工具：暴露给插件脚本读取 sys 的脚本前缀
export function getSysAccessSnippet(pageId: string): string {
  return `const sys = window.__plugin_sys_${pageId};`
}
