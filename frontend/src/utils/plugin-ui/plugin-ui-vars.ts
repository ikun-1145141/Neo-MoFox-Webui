/**
 * 插件 UI 响应式变量池 Store。
 *
 * 不使用 Pinia —— 变量池是动态的、按页面实例化/销毁的。
 * 采用 Vue 3 reactive + computed 构建三级 scope：page → plugin → global。
 */

import { reactive, readonly } from 'vue'

/**
 * 变量池 Store 接口。
 */
export interface PluginUIVarStore {
  /** page scope：进入页面创建 / 离开销毁 */
  page: Record<string, any>

  /** plugin scope：同插件的所有 page 共享 */
  plugin: Record<string, any>

  /** global scope：只读，WebUI 主程序写入 */
  readonly global: Readonly<Record<string, any>>

  /** 取值（自动按 page → plugin → global 优先级解析路径） */
  get(path: string): any

  /** 写值（仅 page / plugin 可写；global 写操作静默忽略） */
  set(path: string, value: any): void

  /** 销毁 page scope（清空所有 page 级变量） */
  destroyPageScope(): void
}

/**
 * 根据点分隔路径从对象中深层读取值。
 *
 * @param obj - 目标对象
 * @param path - 点分隔路径，如 "user.name"
 * @returns 读取到的值，路径不存在时返回 undefined
 */
function getByPath(obj: Record<string, any>, path: string): any {
  const keys = path.split('.')
  let current: any = obj
  for (const key of keys) {
    if (current == null || typeof current !== 'object') {
      return undefined
    }
    current = current[key]
  }
  return current
}

/**
 * 根据点分隔路径向对象中深层写入值。
 * 中间层不存在时自动创建为空对象。
 *
 * @param obj - 目标对象
 * @param path - 点分隔路径，如 "user.name"
 * @param value - 要写入的值
 */
function setByPath(obj: Record<string, any>, path: string, value: any): void {
  const keys = path.split('.')
  let current: any = obj
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i]
    if (current[key] == null || typeof current[key] !== 'object') {
      current[key] = {}
    }
    current = current[key]
  }
  current[keys[keys.length - 1]] = value
}

// === 全局变量池（WebUI 主程序写入，插件只读）===

const globalVars = reactive<Record<string, any>>({
  theme: { mode: 'auto', primary_color: '#0058bd' },
  language: 'zh-CN',
  webui_version: '1.0.0',
})

/**
 * 获取全局变量池引用（用于主程序更新全局状态）。
 *
 * @returns 全局变量的 reactive 对象
 */
export function getGlobalVars(): Record<string, any> {
  return globalVars
}

// === 插件级变量池缓存（按 plugin_name 索引）===

const pluginScopes = new Map<string, Record<string, any>>()

/**
 * 获取或创建指定插件的 plugin scope。
 *
 * @param pluginName - 插件名称
 * @returns 该插件的 reactive 变量对象
 */
function getOrCreatePluginScope(pluginName: string): Record<string, any> {
  if (!pluginScopes.has(pluginName)) {
    pluginScopes.set(pluginName, reactive<Record<string, any>>({}))
  }
  return pluginScopes.get(pluginName)!
}

/**
 * 创建一个新的插件 UI 变量池 Store 实例。
 *
 * 每个插件页面在渲染时创建自己的 store，离开页面时调 destroyPageScope() 清理。
 *
 * @param pluginName - 插件名称（用于关联 plugin scope）
 * @returns 三级 scope 变量池 Store
 */
export function createPluginUIVarStore(pluginName: string): PluginUIVarStore {
  const page = reactive<Record<string, any>>({})
  const plugin = getOrCreatePluginScope(pluginName)
  const global = readonly(globalVars)

  return {
    page,
    plugin,
    global,

    get(path: string): any {
      // 按优先级：page → plugin → global
      const fromPage = getByPath(page, path)
      if (fromPage !== undefined) return fromPage

      const fromPlugin = getByPath(plugin, path)
      if (fromPlugin !== undefined) return fromPlugin

      return getByPath(global, path)
    },

    set(path: string, value: any): void {
      // 判断目标 scope
      // 如果路径以 global. 开头，静默忽略（设计文档要求）
      if (path.startsWith('global.')) {
        return
      }

      // 如果路径以 plugin. 开头，写入 plugin scope
      if (path.startsWith('plugin.')) {
        setByPath(plugin, path.slice(7), value)
        return
      }

      // 默认写入 page scope
      setByPath(page, path, value)
    },

    destroyPageScope(): void {
      // 清空 page scope 中的所有键
      for (const key of Object.keys(page)) {
        delete page[key]
      }
    },
  }
}
