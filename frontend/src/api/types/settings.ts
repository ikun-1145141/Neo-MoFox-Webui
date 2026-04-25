export interface ThemeSettings {
  mode: 'light' | 'dark' | 'auto'
  primary_color: string
}

export interface UISettings {
  language: 'zh-CN' | 'en-US'
  font_size: 'small' | 'medium' | 'large'
}

export interface SystemSettings {
  auto_update: boolean
  check_update_on_startup: boolean
}

export interface WebuiSettings {
  theme: ThemeSettings
  ui: UISettings
  system: SystemSettings
}

export interface UpdateSettingsRequest {
  updates: Partial<{
    theme: Partial<ThemeSettings>
    ui: Partial<UISettings>
    system: Partial<SystemSettings>
  }>
}

export interface ReplaceSettingsRequest {
  settings: WebuiSettings
}
