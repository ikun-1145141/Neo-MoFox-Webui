/**
 * 插件 UI 扩展系统 TypeScript 类型定义。
 *
 * 与后端 Plugin/utils/plugin_ui/plugin_ui_types.py 严格 1:1 对应。
 */

// === 枚举 ===

/** 页面渲染模式 */
export type PageMode = 'xml' | 'html'

// === HTML 资源声明 ===

/** HTML 轨资源声明，与后端 HTMLAssets 模型对应 */
export interface HTMLAssets {
  /** HTML 入口文件相对路径 */
  entry_html: string
  /** CSS 文件相对路径列表，按数组顺序加载 */
  styles: string[]
  /** JS 文件相对路径列表，按数组顺序加载 */
  scripts: string[]
  /** 静态资源根目录；为空时不暴露任何静态资源 */
  assets_dir: string | null
}

// === Discovery 列表项 ===

/** 页面摘要信息（列表展示用，不含 schema） */
export interface PageSummary {
  /** 插件名称 */
  plugin_name: string
  /** 页面唯一标识 */
  page_id: string
  /** 页面显示名 */
  title: string
  /** Material Symbols 图标名 */
  icon: string | null
  /** 页面简介 */
  description: string | null
  /** 排序权重（升序） */
  order: number
  /** 渲染模式（桌面端和移动端共用） */
  mode: PageMode
  /** 系统生成的路由路径 */
  route_path: string
  /** 是否有移动端 variant */
  has_mobile: boolean
}

// === 详情 ===

/** 页面详情信息（含 assets URL，不含 XML 内容） */
export interface PageDetail extends PageSummary {
  /** 桌面端资源 URL */
  desktop_assets_urls: Record<string, string[]> | null
  /** 移动端资源 URL */
  mobile_assets_urls: Record<string, string[]> | null
}

// === Schema 响应 ===

/** 页面渲染 schema 响应（按 variant 返回 XML 或 assets URL） */
export interface PageSchemaResponse {
  /** 插件名称 */
  plugin_name: string
  /** 页面唯一标识 */
  page_id: string
  /** 渲染模式 */
  mode: PageMode
  /** XML 字符串（XML 模式） */
  xml: string | null
  /** 资源 URL 集合（HTML 模式） */
  assets_urls: Record<string, string[]> | null
}
