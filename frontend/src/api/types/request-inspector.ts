export interface InspectorOverviewItem {
  label: string
  value: string
}

export interface InspectorMessageBlock {
  type: 'markdown' | 'unknown' | 'media' | 'tool_call' | 'tool_result' | 'empty' | string
  label?: string
  text?: string
  media_type?: string
  title?: string
  meta?: string
  call_id?: string
  name?: string
  arguments_text?: string
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

export interface InspectorRequestSummary {
  id: number
  ts: number
  ts_str: string
  api_name: string
  model: string
  api_provider: string
  request_name: string
  estimated_input_tokens?: number | null
  msg_count: number
  tool_count: number
}

export interface InspectorRequestDetail extends InspectorRequestSummary {
  params: Record<string, unknown>
  metadata: Record<string, unknown>
  rendered: InspectorRenderedView
}

export interface InspectorAnalytics {
  summary: Record<string, unknown>
  by_model: Record<string, unknown>[]
  by_request_name: Record<string, unknown>[]
  by_stream: Record<string, unknown>[]
}
