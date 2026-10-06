/**
 * 插件管理数据模型（与后端 Pydantic 模型严格对应）
 */

/**
 * 组件状态类型
 */
export type ComponentStatus = 'active' | 'inactive' | 'error'

/**
 * 插件组件信息
 */
export interface PluginComponentInfo {
  /** 组件签名（plugin_name:component_type:component_name） */
  signature: string
  /** 组件类型（action/adapter/command/router/agent等） */
  component_type: string
  /** 组件名称 */
  component_name: string
  /** 组件描述 */
  description?: string
  /** 组件状态 */
  status: ComponentStatus
  /** 组件类型特有的扩展属性 */
  extra?: Record<string, any>
}

/**
 * 插件摘要信息（列表展示）
 */
export interface PluginSummary {
  /** 插件名称 */
  plugin_name: string
  /** 插件描述 */
  plugin_description?: string
  /** 版本号 */
  plugin_version: string
  /** 是否已加载 */
  is_loaded: boolean
  /** 是否有配置文件 */
  has_config: boolean
  /** 组件总数 */
  component_count: number
  /** 包含的组件类型列表 */
  component_types: string[]
  /** 插件路径（可选，未加载插件会包含） */
  plugin_path?: string
}

/**
 * 插件详细信息（详情展示）
 */
export interface PluginDetail extends PluginSummary {
  /** 插件路径 */
  plugin_path: string
  /** 插件清单（原始数据） */
  manifest: Record<string, any>
  /** 组件列表 */
  components: PluginComponentInfo[]
  /** 依赖的组件签名列表 */
  dependencies: string[]
}

/**
 * 插件重载结果
 */
export interface PluginReloadResult {
  /** 是否成功 */
  success: boolean
  /** 插件名称 */
  plugin_name: string
  /** 重载时间（ISO 8601 格式） */
  reload_time: string
  /** 错误信息 */
  error_message?: string
}

/**
 * 插件加载结果
 */
export interface PluginLoadResult {
  /** 是否成功 */
  success: boolean
  /** 插件名称 */
  plugin_name: string
  /** 插件路径 */
  plugin_path: string
  /** 加载时间（ISO 8601 格式） */
  load_time: string
  /** 错误信息 */
  error_message?: string
}

/**
 * 插件卸载结果
 */
export interface PluginUnloadResult {
  /** 是否成功 */
  success: boolean
  /** 插件名称 */
  plugin_name: string
  /** 卸载时间（ISO 8601 格式） */
  unload_time: string
  /** 错误信息 */
  error_message?: string
}

/**
 * 插件包导入结果
 */
export interface PluginImportResult {
  /** 是否导入成功（conflict 为 true 时表示等待用户确认覆盖） */
  success: boolean
  /** 是否检测到同名插件，等待用户确认是否覆盖 */
  conflict: boolean
  /** 插件名称（取自包内 manifest） */
  plugin_name: string
  /** 插件版本 */
  plugin_version: string
  /** 落盘后的插件包路径（冲突或失败时为空） */
  plugin_path: string | null
  /** 已存在的同名插件版本 */
  existing_version: string | null
  /** 已存在的同名插件当前是否正在运行 */
  existing_loaded: boolean
  /** 依赖该插件的已加载插件列表 */
  dependents: string[]
  /** 是否覆盖了已存在的插件包 */
  replaced: boolean
  /** 是否已完成热加载 */
  loaded: boolean
  /** 是否需要重启 Neo-MoFox 才能生效 */
  restart_required: boolean
  /** 不阻断导入的提示信息 */
  warnings: string[]
  /** 导入时间（ISO 8601 格式） */
  import_time: string
  /** 错误信息或热加载失败原因 */
  error_message: string | null
}
