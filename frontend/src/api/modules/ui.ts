/**
 * UI 扩展系统 API 调用模块
 */
import http from '../base'
import type { UiPageMeta, UiPageSchema } from '../types/ui'
import { API_WEBUI_PREFIX } from '../config'

const BASE = API_WEBUI_PREFIX

/**
 * GET /webui/api/ui/discovery - 获取所有已注册页面的元数据列表
 */
export function getUiDiscovery(): Promise<UiPageMeta[]> {
  return http.get(`${BASE}/ui/discovery`)
}

/**
 * GET /webui/api/ui/schema/{plugin_name}/{page_id} - 获取指定页面的完整 XML 描述
 * @param pluginName 插件名称
 * @param pageId 页面ID
 */
export function getUiSchema(pluginName: string, pageId: string): Promise<UiPageSchema> {
  return http.get(`${BASE}/ui/schema/${encodeURIComponent(pluginName)}/${encodeURIComponent(pageId)}`)
}
