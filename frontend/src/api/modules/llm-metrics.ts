import instance from '../base'
import type {
  LLMMetricsOverview,
  LLMModelMetrics,
  LLMRequestMetrics,
  LLMStreamMetrics,
  LLMRecentRequest,
} from '../types/llm-metrics'
import { API_WEBUI_PREFIX } from '../config'


const BASE_URL = `${API_WEBUI_PREFIX}/llm-metrics`

export function getOverview(): Promise<LLMMetricsOverview> {
  return instance.get(`${BASE_URL}/overview`)
}

export function listModels(): Promise<LLMModelMetrics[]> {
  return instance.get(`${BASE_URL}/models`)
}

export function listRequestNames(): Promise<LLMRequestMetrics[]> {
  return instance.get(`${BASE_URL}/request-names`)
}

export function listStreams(): Promise<LLMStreamMetrics[]> {
  return instance.get(`${BASE_URL}/streams`)
}

export function getRecentRequests(limit = 100, offset = 0): Promise<LLMRecentRequest[]> {
  return instance.get(`${BASE_URL}/recent`, {
    params: { limit, offset },
  })
}

export function getCacheHitRate(streamId?: string): Promise<{ cache_hit_rate: number }> {
  return instance.get(`${BASE_URL}/cache-hit-rate`, {
    params: { stream_id: streamId },
  })
}

export function getTimeRangeSummary(startTs: number, endTs: number): Promise<LLMMetricsOverview> {
  return instance.get(`${BASE_URL}/time-range`, {
    params: { start_ts: startTs, end_ts: endTs },
  })
}

export function getLastHoursSummary(hours = 5.0): Promise<LLMMetricsOverview> {
  return instance.get(`${BASE_URL}/last-hours`, {
    params: { hours },
  })
}
