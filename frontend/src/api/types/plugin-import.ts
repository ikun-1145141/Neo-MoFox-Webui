/** Local package import contracts, matching plugin_import_types.py. */
export interface PluginImportPreview {
  upload_id: string
  expires_at: string
  filename: string
  size_bytes: number
  plugin_name: string
  version: string
  description: string
  installed_version: string | null
  overwrite_required: boolean
  self_update: boolean
  can_import: boolean
  warnings: string[]
  blocking_reasons: string[]
}
export interface PluginImportCommit {
  upload_id: string
  confirm_overwrite: boolean
}
export interface PluginImportResult {
  plugin_name: string
  version: string
  written: boolean
  loaded: boolean
  restart_required: boolean
  load_error: string | null
}
export interface PluginImportOperation {
  operation_id: string
  plugin_name: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  stage: 'queued' | 'validating' | 'storing' | 'loading' | 'completed' | 'failed'
  progress: number
  message: string
  created_at: string
  updated_at: string
  error_message: string | null
  result: PluginImportResult | null
}
