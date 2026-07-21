/**
 * 配置管理 API 模块
 * 对应后端 Plugin/components/router/config/ 下的路由
 */

import http from '../base'
import { API_WEBUI_PREFIX } from '../config'
import type {
  EnhancedConfigResponse,
  McpTestRequest,
  McpTestResult,
  ModelTestRequest,
  ModelTestResult,
  PluginConfigEntry,
  SectionSchema,
} from '../types/config'

const BASE = `${API_WEBUI_PREFIX}/config`

// ===== core配置路由 =====

/**
 * 热重载机器人配置（从磁盘重新加载到运行时）
 */
export function reloadBotConfig(): Promise<void> {
  return http.post(`${BASE}-bot/reload`)
}

// ===== 主配置路由 =====

/**
 * 获取增强配置（包含 Schema 和数据）
 * @param configType 配置类型：bot | model | plugin
 * @param pluginName 插件名（config_type=plugin 时必填）
 */
export function getConfig(
  configType: 'bot' | 'model' | 'plugin' | 'mcp',
  pluginName?: string
): Promise<EnhancedConfigResponse> {
  const params = pluginName ? `?plugin_name=${pluginName}` : ''
  return http.get(`${BASE}/read/${configType}${params}`)
}

/**
 * 获取原始 TOML 文件内容
 * @param configType 配置类型：bot | model | plugin
 * @param pluginName 插件名（config_type=plugin 时必填）
 */
export function getRawConfig(
  configType: 'bot' | 'model' | 'plugin' | 'mcp',
  pluginName?: string
): Promise<string> {
  const params = pluginName ? `?plugin_name=${pluginName}` : ''
  return http.get(`${BASE}/raw/${configType}${params}`)
}

/**
 * 全量写入配置
 * @param configType 配置类型：bot | model | plugin
 * @param data 配置数据
 * @param pluginName 插件名（plugin 类型时必填）
 */
export function fullWriteConfig(
  configType: 'bot' | 'model' | 'plugin' | 'mcp',
  data: Record<string, any>,
  pluginName?: string
): Promise<EnhancedConfigResponse> {
  const params = pluginName ? `?plugin_name=${pluginName}` : ''
  return http.put(`${BASE}/write/${configType}${params}`, { data })
}

/**
 * 增量写入配置
 * @param configType 配置类型：bot | model | plugin
 * @param data 配置数据（部分）
 * @param pluginName 插件名（plugin 类型时必填）
 */
export function patchWriteConfig(
  configType: 'bot' | 'model' | 'plugin' | 'mcp',
  data: Record<string, any>,
  pluginName?: string
): Promise<EnhancedConfigResponse> {
  const params = pluginName ? `?plugin_name=${pluginName}` : ''
  return http.patch(`${BASE}/patch/${configType}${params}`, { data })
}

// ===== 模型配置路由 =====

/**
 * 热重载模型配置（从磁盘重新加载到运行时）
 */
export function reloadModelConfig(): Promise<void> {
  return http.post(`${BASE}-model/reload`)
}

/**
 * 测试模型连通性
 * @param request 测试请求
 */
export function testModel(request: ModelTestRequest): Promise<ModelTestResult> {
  return http.post(`${BASE}-model/test`, request)
}

/**
 * 获取所有提供商名称列表
 */
export function listProviders(): Promise<string[]> {
  return http.get(`${BASE}-model/providers`)
}

/**
 * 获取模型名称列表
 * @param provider 提供商名称（可选，不指定则返回所有模型）
 */
export function listModels(provider?: string): Promise<string[]> {
  const params = provider ? `?provider=${provider}` : ''
  return http.get(`${BASE}-model/models${params}`)
}

// ===== MCP 配置路由 =====

/**
 * 热重载 MCP 配置（从磁盘重新加载到运行时）
 */
export function reloadMcpConfig(): Promise<void> {
  return http.post(`${BASE}-mcp/reload`)
}

export function testMcpServer(request: McpTestRequest): Promise<McpTestResult> {
  return http.post(`${BASE}-mcp/test`, request)
}

// ===== 插件配置路由 =====

/**
 * 获取可配置插件列表
 */
export function listPluginConfigs(): Promise<PluginConfigEntry[]> {
  return http.get(`${BASE}-plugin/list`)
}

/**
 * 热重载指定插件的配置（从磁盘重新加载到运行时）
 * @param pluginName 插件名
 */
export function reloadPluginConfig(pluginName: string): Promise<void> {
  return http.post(`${BASE}-plugin/${encodeURIComponent(pluginName)}/reload`)
}

/**
 * 获取插件配置 Schema
 * @param pluginName 插件名
 */
export function getPluginConfigSchema(pluginName: string): Promise<SectionSchema[]> {
  return http.get(`${BASE}-plugin/${pluginName}/schema`)
}
