export interface BaseResponse<T = unknown> {
  code: number
  data: T | null
  message: string
}

export interface LoginRequest {
  password: string
}

export interface LoginResponse {
  token: string
}

export interface SettingsData {
  theme: ThemeMode
  theme_source_color: string | null
  language: string
  bot_name: string
  wallpaper_path: string | null
}

export type ThemeMode = 'light' | 'dark' | 'auto'
