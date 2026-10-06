import http from '../base'
import { API_WEBUI_PREFIX } from '../config'
import type { PluginImportCommit, PluginImportOperation, PluginImportPreview } from '../types/plugin-import'

const BASE = API_WEBUI_PREFIX + '/plugin/import'

/** Upload one package for non-executing validation and preview. */
export function preparePluginImport(file: File, onProgress: (progress: number) => void, signal?: AbortSignal): Promise<PluginImportPreview> {
  const data = new FormData()
  data.append('file', file)
  return http.post(BASE + '/prepare', data, {
    timeout: 180000,
    signal,
    onUploadProgress: event => onProgress(event.total ? Math.min(100, Math.round(event.loaded / event.total * 100)) : 0),
  })
}

/** Retry the same upload ID, never create another upload on a lost response. */
export function commitPluginImport(request: PluginImportCommit): Promise<PluginImportOperation> {
  return http.post(BASE + '/commit', request)
}

export function getPluginImportOperation(id: string, signal?: AbortSignal): Promise<PluginImportOperation> {
  return http.get(BASE + '/operations/' + encodeURIComponent(id), { signal })
}

export function discardPluginImport(id: string): Promise<{ deleted: boolean }> {
  return http.delete(BASE + '/uploads/' + encodeURIComponent(id))
}
