/**
 * 配置管理相关类型定义
 * 对应后端 Plugin/utils/config_types.py
 */

/**
 * UI 控件类型（对应后端 FieldUIType）
 */
export type FieldUIType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'boolean'
  | 'select'
  | 'multiselect'
  | 'json'
  | 'color'
  | 'file'
  | 'password'
  | 'url'
  | 'email'
  | 'slider'
  | 'date'
  | 'datetime'
  | 'time'

/**
 * 字段 Schema（对应后端 FieldSchema）
 */
export interface FieldSchema {
  key: string
  label: string
  description: string
  type: string
  default?: unknown
  input_type: string
  tag?: string
  placeholder?: string
  hint?: string
  order: number
  hidden: boolean
  disabled: boolean
  // 验证约束
  ge?: number
  le?: number
  gt?: number
  lt?: number
  min_length?: number
  max_length?: number
  pattern?: string
  // 控件特定
  choices?: unknown[]
  rows?: number
  step?: number
  // 列表配置
  item_type?: string
  item_fields?: Record<string, unknown>
  min_items?: number
  max_items?: number
  // 条件显示
  depends_on?: string
  depends_value?: unknown
}

/**
 * 配置节 Schema（对应后端 SectionSchema）
 */
export interface SectionSchema {
  name: string
  title?: string
  description?: string
  tag?: string
  fields: FieldSchema[]
  // 前端扩展字段（用于区分列表类型的节）
  is_list?: boolean
}

/**
 * 增强配置响应（对应后端 EnhancedConfigResponse）
 */
export interface EnhancedConfigResponse {
  config_type: 'bot' | 'model' | 'plugin'
  config_name: string
  config_path: string
  schema: SectionSchema[]
  data: Record<string, unknown>
  plugin_name?: string
}

/**
 * 全量写入请求（对应后端 FullWriteRequest）
 */
export interface FullWriteRequest {
  config_type: 'bot' | 'model' | 'plugin'
  plugin_name?: string
  data: Record<string, unknown>
}

/**
 * 增量写入请求（对应后端 PatchWriteRequest）
 */
export interface PatchWriteRequest {
  config_type: 'bot' | 'model' | 'plugin'
  plugin_name?: string
  data: Record<string, unknown>
}

/**
 * 模型测试请求（对应后端 ModelTestRequest）
 */
export interface ModelTestRequest {
  provider_name: string
  model_name: string
  test_prompt: string
  timeout: number
}

/**
 * 模型测试结果（对应后端 ModelTestResult）
 */
export interface ModelTestResult {
  success: boolean
  response_text?: string
  latency_ms?: number
  error_message?: string
  model_identifier: string
  provider_base_url: string
}

/**
 * 插件配置条目（对应后端 PluginConfigEntry）
 */
export interface PluginConfigEntry {
  plugin_name: string
  config_name: string
  config_path: string
  config_description: string
  is_loaded: boolean
}