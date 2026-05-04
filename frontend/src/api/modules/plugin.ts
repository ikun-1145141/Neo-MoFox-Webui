/**
 * 插件管理 API 调用模块
 */
import http from '../base'
import type {
  PluginSummary,
  PluginDetail,
  PluginReloadResult,
  PluginLoadResult,
  PluginUnloadResult,
  PluginComponentInfo,
} from '../types/plugin'
import { API_WEBUI_PREFIX } from '../config'

const BASE = API_WEBUI_PREFIX

/**
 * GET /api/plugin/list - 获取所有已加载插件的摘要信息列表
 */
export function getPluginList(): Promise<PluginSummary[]> {
  return http.get(`${BASE}/plugin/list`)
}

/**
 * GET /api/plugin/{plugin_name} - 获取指定插件的详细信息
 * @param pluginName 插件名称
 */
export function getPluginDetail(pluginName: string): Promise<PluginDetail> {
  return http.get(`${BASE}/plugin/${encodeURIComponent(pluginName)}`)
}

/**
 * POST /api/plugin/{plugin_name}/reload - 重载指定插件
 * @param pluginName 插件名称
 */
export function reloadPlugin(pluginName: string): Promise<PluginReloadResult> {
  return http.post(`${BASE}/plugin/${encodeURIComponent(pluginName)}/reload`, {})
}

/**
 * GET /api/plugin/{plugin_name}/components - 获取插件的组件列表（支持类型筛选）
 * @param pluginName 插件名称
 * @param componentType 可选的组件类型筛选（如 'router', 'action', 'adapter'）
 */
export function getPluginComponents(
  pluginName: string,
  componentType?: string
): Promise<PluginComponentInfo[]> {
  const params = componentType ? { component_type: componentType } : {}
  return http.get(`${BASE}/plugin/${encodeURIComponent(pluginName)}/components`, { params })
}

/**
 * POST /api/plugin/load - 从指定路径加载插件
 * @param pluginPath 插件路径
 */
export function loadPlugin(pluginPath: string): Promise<PluginLoadResult> {
  return http.post(`${BASE}/plugin/load`, {}, {
    params: { plugin_path: pluginPath }
  })
}

/**
 * POST /api/plugin/{plugin_name}/unload - 卸载指定插件
 * @param pluginName 插件名称
 */
export function unloadPlugin(pluginName: string): Promise<PluginUnloadResult> {
  return http.post(`${BASE}/plugin/${encodeURIComponent(pluginName)}/unload`, {})
}
