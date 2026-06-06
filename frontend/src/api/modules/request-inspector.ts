import instance from '../base'
import { API_WEBUI_PREFIX } from '../config'
import type {
  InspectorAnalytics,
  InspectorRequestDetail,
  InspectorRequestSummary,
} from '../types/request-inspector'

const BASE_URL = `${API_WEBUI_PREFIX}/request-inspector`

export function listInspectorRequests(): Promise<InspectorRequestSummary[]> {
  return instance.get(`${BASE_URL}/requests`)
}

export function getInspectorRequest(requestId: number): Promise<InspectorRequestDetail> {
  return instance.get(`${BASE_URL}/requests/${requestId}`)
}

export function clearInspectorRequests(): Promise<Record<string, unknown>> {
  return instance.delete(`${BASE_URL}/requests`)
}

export function getInspectorAnalytics(): Promise<InspectorAnalytics> {
  return instance.get(`${BASE_URL}/analytics`)
}
