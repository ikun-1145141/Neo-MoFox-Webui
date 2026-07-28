export type CompatibilityStatus = 'compatible' | 'incompatible' | 'unknown'
export type MarketOperationKind = 'install' | 'uninstall'
export type MarketOperationStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface CompatibilityInfo {
  status: CompatibilityStatus
  summary: string
  reasons: string[]
}

export interface MarketLocalState {
  installed: boolean
  loaded: boolean
  installed_version: string | null
  plugin_path: string | null
  has_config: boolean
  update_available: boolean
  can_uninstall: boolean
  uninstall_reason: string | null
  dependent_plugins: string[]
}

export interface MarketPlugin {
  plugin_id: string
  display_name: string
  summary: string
  description: string
  icon_url: string | null
  homepage: string | null
  repository_url: string | null
  license: string | null
  categories: string[]
  tags: string[]
  status: string
  owner_login: string | null
  owner_display_name: string | null
  owner_avatar_url: string | null
  maintainers: string[]
  trust_level: string
  risk_notice: string | null
  created_at: string | null
  updated_at: string | null
  likes_count: number
  rating_avg: number
  rating_count: number
  comments_count: number
  downloads_count: number
  latest_version: string | null
  latest_version_published_at: string | null
  local_state: MarketLocalState
}

export interface MarketVersion {
  plugin_id: string
  version: string
  release_tag: string | null
  release_title: string | null
  release_url: string | null
  asset_name: string
  asset_download_url: string
  checksum_sha256: string
  file_size: number | null
  published_at: string | null
  is_prerelease: boolean
  is_yanked: boolean
  status: string
  plugin_api_version: string | null
  min_host_version: string | null
  max_host_version: string | null
  supported_platforms: string[]
  download_count: number
  compatibility: CompatibilityInfo
}

export interface MarketDependency {
  plugin_id: string
  version_constraint: string | null
  required_version: string | null
  exists_in_market: boolean
  installed: boolean
  installed_version: string | null
  satisfied: boolean
}

export interface MarketPluginList {
  plugins: MarketPlugin[]
  total: number
  refreshed_at: string
}

export interface MarketPluginDetail {
  plugin: MarketPlugin
  versions: MarketVersion[]
  dependencies: MarketDependency[]
  recommended_version: MarketVersion | null
}

export interface MarketCapabilities {
  market_enabled: boolean
  install_enabled: boolean
  uninstall_enabled: boolean
  supports_streaming_progress: boolean
}

export interface InstallPlan {
  plugin: MarketPlugin
  version: MarketVersion
  dependencies: MarketDependency[]
  action: 'install' | 'update'
  can_install: boolean
  blocking_reasons: string[]
  warnings: string[]
}

export interface MarketOperationResult {
  plugin_id: string
  version: string | null
  restart_required: boolean
}

export interface MarketOperation {
  operation_id: string
  plugin_id: string
  kind: MarketOperationKind
  status: MarketOperationStatus
  stage: string
  progress: number
  message: string
  created_at: string
  updated_at: string
  error_message: string | null
  result: MarketOperationResult | null
}
