export interface ThemeSettings {
  mode: 'light' | 'dark' | 'auto'
  primary_color: string
  has_wallpaper: boolean
  wallpaper_blur: number
  wallpaper_opacity: number
}

export interface UISettings {
  language: 'zh-CN' | 'en-US'
  font_size: 'small' | 'medium' | 'large'
}

export interface SystemSettings {
  auto_update: boolean
  check_update_on_startup: boolean
}

export interface ConfigSettings {
  auto_reload_after_save: boolean
}

export interface WebuiSettings {
  theme: ThemeSettings
  ui: UISettings
  system: SystemSettings
  config: ConfigSettings
}

export interface UpdateSettingsRequest {
  updates: Partial<{
    theme: Partial<ThemeSettings>
    ui: Partial<UISettings>
    system: Partial<SystemSettings>
    config: Partial<ConfigSettings>
  }>
}

export interface ReplaceSettingsRequest {
  settings: WebuiSettings
}
