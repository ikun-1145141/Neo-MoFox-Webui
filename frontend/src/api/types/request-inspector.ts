export interface InspectorOverviewItem {
  label: string
  value: string
}

export interface InspectorMessageBlock {
  type:
    | 'markdown'
    | 'unknown'
    | 'media'
    | 'tool_call'
    | 'tool_result'
    | 'empty'
    | string
  label: string | null
  text: string | null
  media_type: string | null
  title: string | null
  meta: string | null
  call_id: string | null
  name: string | null
  arguments_text: string | null
}

export interface InspectorMessageView {
  index: number
  role: string
  label: string
  meta: string
  blocks: InspectorMessageBlock[]
}

export interface InspectorToolProperty {
  name: string
  type: string
  description: string
  required: boolean
}

export interface InspectorToolView {
  index: number
  name: string
  kind: string
  description: string
  required: string[]
  properties: InspectorToolProperty[]
  raw_json: string
}

export interface InspectorRenderedView {
  overview: InspectorOverviewItem[]
  tools: InspectorToolView[]
  messages: InspectorMessageView[]
}

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue }
export type InspectorStatus =
  | 'captured'
  | 'pending'
  | 'running'
  | 'streaming'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export interface InspectorRecordSummary {
  id: number
  version: number
  ts: number
  ts_str: string
  api_name: string
  model: string
  api_provider: string
  request_name: string
  estimated_input_tokens: number | null
  msg_count: number
  tool_count: number
  status: InspectorStatus
  logical_request_id: string
  attempt: number
  stream: boolean
  started_at: number | null
  finished_at: number | null
  duration_ms: number | null
  first_token_ms: number | null
  tokens_in: number | null
  tokens_out: number | null
}

export interface InspectorResponse {
  kind: 'chat' | 'embedding' | 'rerank' | null
  message: string | null
  reasoning_content: string | null
  reasoning_parts: JsonValue[]
  tool_calls: JsonValue[]
  usage: Record<string, JsonValue> | null
  stop_reason: string | null
  embeddings: number[][]
  results: JsonValue[]
}

export interface InspectorCaptureInfo {
  redacted: boolean
  raw_bytes: number
  raw_limit_bytes: number
  raw_truncated: boolean
  raw_unavailable: boolean
  request_unavailable: boolean
  metadata_unavailable: boolean
}

export interface InspectorRecordDetail extends InspectorRecordSummary {
  instance_id: string
  params: Record<string, JsonValue>
  metadata: Record<string, JsonValue>
  rendered: InspectorRenderedView
  response: InspectorResponse
  raw_response: JsonValue
  raw_events: JsonValue[]
  error: { type: string; message: string; status_code: number | null } | null
  capture_info: InspectorCaptureInfo
}

export interface InspectorBufferStats {
  total: number
  by_status: Partial<Record<InspectorStatus, number>>
  tokens_in: number
  tokens_out: number
}

export interface InspectorRecordsSnapshot {
  instance_id: string
  revision: number
  capacity: number
  records: InspectorRecordSummary[]
  stats: InspectorBufferStats
}

export interface InspectorClearResult {
  instance_id: string
  revision: number
  cleared_count: number
}
