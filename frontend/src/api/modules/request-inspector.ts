/** 需要身份认证的原生记录接口，不兼容旧路径，也不在客户端重复采集。 */
import instance from '../base'
import { API_WEBUI_PREFIX } from '../config'
import type {
  InspectorRecordsSnapshot,
  InspectorRecordDetail,
  InspectorClearResult,
} from '../types/request-inspector'

const RECORDS_URL = `${API_WEBUI_PREFIX}/request-inspector/records`
export function listInspectorRecords(
  signal?: AbortSignal,
): Promise<InspectorRecordsSnapshot> {
  return instance.get(RECORDS_URL, { signal })
}
export function getInspectorRecord(
  id: number,
  signal?: AbortSignal,
): Promise<InspectorRecordDetail> {
  return instance.get(`${RECORDS_URL}/${id}`, { signal, handledErrorStatuses: [404] })
}
export function clearInspectorRecords(
  signal?: AbortSignal,
): Promise<InspectorClearResult> {
  return instance.delete(RECORDS_URL, { signal })
}
