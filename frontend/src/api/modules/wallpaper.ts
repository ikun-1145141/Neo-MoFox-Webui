import http from '../base'
import type { WallpaperStatus } from '../types/wallpaper'

const BASE = "/api/wallpaper"

/** POST /api/webui/wallpaper - 上传壁纸 */
export function uploadWallpaper(file: File): Promise<WallpaperStatus> {
  const form = new FormData()
  form.append('file', file)
  return http.post(`${BASE}/upload`, form)
}

/** DELETE /api/webui/wallpaper - 删除壁纸 */
export function deleteWallpaper(): Promise<WallpaperStatus> {
  return http.delete(`${BASE}/delete`)
}

/** GET /api/webui/wallpaper/status - 获取壁纸状态 */
export function getWallpaperStatus(): Promise<WallpaperStatus> {
  return http.get(`${BASE}/status`)
}

/** GET /api/webui/wallpaper/image - 获取壁纸图片地址 */
export function getWallpaperImageUrl(version: number = Date.now()): string {
  return `${BASE}/image?v=${version}`
}
