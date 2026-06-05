export interface LLMMetricsOverview {
  window_hours?: number
  total_requests: number
  success_count?: number
  error_count?: number
  success_rate: number
  total_prompt_tokens?: number
  total_completion_tokens?: number
  total_tokens?: number
  total_input_tokens?: number
  total_output_tokens?: number
  total_tokens_in?: number
  total_tokens_out?: number
  total_cache_hit_tokens?: number
  total_cache_miss_tokens?: number
  cache_hit_rate: number
  total_cost: number
  avg_latency?: number
  avg_latency_ms?: number
  updated_at?: string
}

export interface LLMMemoryOverview {
  model_count: number
  total_requests: number
  success_count: number
  error_count: number
  success_rate: number
  avg_latency_seconds: number
  avg_latency_ms: number
  total_tokens_in: number
  total_tokens_out: number
  total_cost: number
  updated_at: string
}

export interface LLMMetricsCombinedOverview {
  legacy: LLMMemoryOverview
  persistent: LLMMetricsOverview
  updated_at: string
}

export interface LLMModelMetrics {
  model_name: string
  model_identifier?: string
  provider?: string
  api_provider: string
  total_requests: number
  success_count: number
  error_count: number
  success_rate?: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_input_tokens?: number
  total_output_tokens?: number
  total_tokens: number
  total_cache_hit_tokens?: number
  total_cost: number
  avg_latency: number
}

export interface LLMRequestMetrics {
  request_name: string
  total_requests: number
  success_count: number
  error_count: number
  success_rate?: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_input_tokens?: number
  total_output_tokens?: number
  total_tokens: number
  total_cache_hit_tokens?: number
  total_cost: number
  avg_latency: number
}

export interface LLMStreamMetrics {
  stream_id: string
  total_requests: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_input_tokens?: number
  total_output_tokens?: number
  total_cache_hit: number
  total_cache_miss: number
  cache_hit_rate: number
  total_cost: number
  success_rate?: number
}

export interface LLMRecentRequest {
  id: number
  timestamp: number
  request_name: string
  model_name: string
  model_identifier?: string
  provider?: string
  api_provider: string
  stream_id: string | null
  prompt_tokens: number
  completion_tokens: number
  input_tokens?: number
  output_tokens?: number
  total_tokens: number
  cache_hit_tokens: number
  cache_miss_tokens: number
  cache_hit?: boolean
  cache_write_tokens?: number
  cost: number
  latency: number
  success: boolean | number
  error_type: string | null
  stream?: boolean | number
  retry_count?: number
}
