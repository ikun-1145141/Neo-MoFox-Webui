import instance from '../base'
import type {
  LLMMetricsOverview,
  LLMStreamMetrics,
  LLMRecentRequest,
} from '../types/llm-metrics'
import { API_WEBUI_PREFIX } from '../config'

const BASE_URL = `${API_WEBUI_PREFIX}/llm-metrics`

export function getOverview(): Promise<LLMMetricsOverview> {
  return instance.get(`${BASE_URL}/overview`)
}

export function listStreams(): Promise<LLMStreamMetrics[]> {
  return instance.get(`${BASE_URL}/streams`)
}

export function getRecentRequestsByTime(
  hours = 5.0,
  limit = 1000,
  offset = 0,
): Promise<LLMRecentRequest[]> {
  return instance.get(`${BASE_URL}/recent-by-time`, {
    params: { hours, limit, offset },
  })
}

export function getLastHoursSummary(hours = 5.0): Promise<LLMMetricsOverview> {
  return instance.get(`${BASE_URL}/last-hours`, {
    params: { hours },
  })
}
