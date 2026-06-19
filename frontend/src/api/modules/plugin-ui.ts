/**
 * 插件 UI 扩展系统 API 模块。
 *
 * 封装 Discovery / Schema 路由的前端调用。
 * 所有请求通过 base.ts 的 axios 实例发出（统一 Token + 错误 Toast）。
 */

import instance from '../base'
import type { PageSummary, PageDetail, PageSchemaResponse } from '../types/plugin-ui'

/**
 * 获取所有插件 UI 页面列表。
 *
 * @returns 按 order 升序排列的页面摘要列表
 */
export function listPluginPages(): Promise<PageSummary[]> {
  return instance.get('/webui/api/plugin-ui/list')
}

/**
 * 获取指定插件的 UI 页面列表。
 *
 * @param pluginName - 插件名称
 * @returns 该插件下的页面摘要列表
 */
export function listPluginPagesByPlugin(pluginName: string): Promise<PageSummary[]> {
  return instance.get(`/webui/api/plugin-ui/list/${pluginName}`)
}

/**
 * 获取页面详情（含 assets URL，不含 XML 内容）。
 *
 * @param pluginName - 插件名称
 * @param pageId - 页面标识
 * @returns 页面详情
 */
export function getPageDetail(pluginName: string, pageId: string): Promise<PageDetail> {
  return instance.get(`/webui/api/plugin-ui/detail/${pluginName}/${pageId}`)
}

/**
 * 获取页面渲染 schema（XML 内容或 HTML assets URL）。
 *
 * @param pluginName - 插件名称
 * @param pageId - 页面标识
 * @param variant - 变体类型，desktop 或 mobile
 * @returns 页面渲染 schema
 */
export function getPageSchema(
  pluginName: string,
  pageId: string,
  variant: 'desktop' | 'mobile' = 'desktop'
): Promise<PageSchemaResponse> {
  return instance.get(`/webui/api/plugin-ui/schema/${pluginName}/${pageId}`, {
    params: { variant }
  })
}
