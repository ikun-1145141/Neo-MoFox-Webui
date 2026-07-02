/**
 * UI 扩展系统数据模型（与后端 Pydantic 模型 UiPageMeta / UiPageSchema 严格对应）
 */

/**
 * 已注册页面的元数据（对应 GET /api/ui/discovery 返回值单项）
 */
export interface UiPageMeta {
  /** 所属插件名称 */
  plugin_name: string
  /** 页面唯一标识符 */
  page_id: string
  /** 页面标题 */
  title: string
  /** 页面描述 */
  description?: string
  /** Material Symbols 图标名 */
  icon?: string
  /** API 端点前缀 */
  api_base?: string
  /** 排序权重 */
  order: number
  /** 注册时间戳 */
  registered_at: number
}

/**
 * 页面 Schema 响应（对应 GET /api/ui/schema/{plugin}/{page_id} 返回值）
 */
export interface UiPageSchema {
  /** 所属插件名称 */
  plugin_name: string
  /** 页面唯一标识符 */
  page_id: string
  /** 完整 XML 页面描述 */
  page_xml: string
}
