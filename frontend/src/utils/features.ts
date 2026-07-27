import { readonly, ref } from 'vue'

export interface WebuiFeatures {
  plugin_market_enabled: boolean
  plugin_market_install_enabled: boolean
}

const defaultFeatures: WebuiFeatures = {
  plugin_market_enabled: false,
  plugin_market_install_enabled: false,
}

const features = ref<WebuiFeatures>({ ...defaultFeatures })
let loadedForToken: string | null = null
let pendingRequest: Promise<WebuiFeatures> | null = null

export const webuiFeatures = readonly(features)

export async function loadWebuiFeatures(force = false): Promise<WebuiFeatures> {
  const token = sessionStorage.getItem('neo_token')
  if (!token) {
    loadedForToken = null
    features.value = { ...defaultFeatures }
    return features.value
  }
  if (!force && loadedForToken === token) return features.value
  if (pendingRequest) return pendingRequest

  pendingRequest = fetch('/webui/api/webui/features', {
    headers: { 'X-API-Key': token },
    credentials: 'same-origin',
    cache: 'no-store',
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const payload = await response.json()
      if (payload?.code !== 200 || typeof payload?.data !== 'object') {
        throw new Error('Invalid feature response')
      }
      features.value = {
        plugin_market_enabled: payload.data.plugin_market_enabled === true,
        plugin_market_install_enabled: payload.data.plugin_market_install_enabled === true,
      }
      loadedForToken = token
      return features.value
    })
    .catch(() => {
      features.value = { ...defaultFeatures }
      loadedForToken = null
      return features.value
    })
    .finally(() => {
      pendingRequest = null
    })

  return pendingRequest
}

export function resetWebuiFeatures() {
  loadedForToken = null
  features.value = { ...defaultFeatures }
}
