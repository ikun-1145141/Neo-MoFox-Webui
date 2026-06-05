export interface LLMMetricsOverview {
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_cost: number
  success_rate: number
  cache_hit_rate: number
}

export interface LLMModelMetrics {
  model_name: string
  provider: string
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_cost: number
  success_rate: number
  avg_latency: number
}

export interface LLMRequestMetrics {
  request_name: string
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_cost: number
  success_rate: number
  avg_latency: number
}

export interface LLMStreamMetrics {
  stream_id: string
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  total_cost: number
  success_rate: number
}

export interface LLMRecentRequest {
  id: number
  timestamp: number
  request_name: string
  model_name: string
  provider: string
  stream_id: string | null
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cost: number
  latency: number
  success: boolean
  error_type: string | null
  cache_hit: boolean
}
