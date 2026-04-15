import http from '../base'
import type { SettingsData } from '../types/base'

export function getSettings(): Promise<SettingsData> {
  return http.get('/api/settings')
}

export function saveSettings(payload: SettingsData): Promise<SettingsData> {
  return http.post('/api/settings', payload)
}
