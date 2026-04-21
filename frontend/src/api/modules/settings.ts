import http from '../base'
import type {
  WebuiSettings,
  UpdateSettingsRequest,
  ReplaceSettingsRequest,
} from '../types/base'
import { API_WEBUI_PREFIX } from '../config'

const BASE = API_WEBUI_PREFIX

/** GET /api/webui/settings — 获取当前设置 */
export function getSettings(): Promise<WebuiSettings> {
  return http.get(`${BASE}/settings`)
}

/** POST /api/webui/settings — 部分更新设置 */
export function updateSettings(updates: UpdateSettingsRequest['updates']): Promise<WebuiSettings> {
  return http.post(`${BASE}/settings`, { updates } satisfies UpdateSettingsRequest)
}

/** PUT /api/webui/settings — 完全替换设置 */
export function replaceSettings(settings: WebuiSettings): Promise<WebuiSettings> {
  return http.put(`${BASE}/settings`, { settings } satisfies ReplaceSettingsRequest)
}

/** POST /api/webui/settings/reset — 重置为默认值 */
export function resetSettings(): Promise<WebuiSettings> {
  return http.post(`${BASE}/settings/reset`)
}

/** GET /api/webui/health — 健康检查 */
export function healthCheck(): Promise<{ status: string }> {
  return http.get(`${BASE}/health`)
}
