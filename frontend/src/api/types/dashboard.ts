export interface DashboardOverview {
  runtime: {
    event: {
      handler_count: number;
      temporary_handler_count: number;
      event_type_count: number;
      total_subscriptions: number;
    };
    task: {
      total_tasks: number;
      active_tasks: number;
      daemon_tasks: number;
      grouped_tasks: number;
      groups: number;
      process_workers: number;
      process_pool_running: boolean;
    };
    scheduler: {
      is_running: boolean;
      uptime_seconds: number;
      total_tasks: number;
      running_tasks: number;
      success_rate: number;
    };
    adapter: {
      active_count: number;
      active_signatures: string[];
    };
  };
  business: {
    messages: {
      today_total: number;
      today_inbound: number;
      today_outbound: number;
      today_start_timestamp: number;
    };
    streams: {
      active_count: number;
    };
    plugins: {
      loaded_count: number;
      failed_count: number;
    };
    components: {
      total_count: number;
      by_type: Record<string, number>;
    };
  };
  llm: {
    model_count: number;
    total_requests: number;
    success_count: number;
    error_count: number;
    success_rate: number;
    avg_latency_seconds: number;
    avg_latency_ms: number;
    total_tokens_in: number;
    total_tokens_out: number;
    total_cost: number;
    updated_at: string;
  };
  updated_at: string;
}

export interface DailyMessageStats {
  total: number;
  inbound: number;
  outbound: number;
}

export interface MessageTrend {
  date_range: string[];
  daily_stats: Record<string, DailyMessageStats>;
  summary: {
    total_messages: number;
    avg_per_day: number;
    growth_rate: number;
  };
  platform_distribution: Record<string, number>;
}

export interface PlatformStatistic {
  platform: string;
  count: number;
  percentage: number;
}

export interface PlatformStatistics {
  platforms: PlatformStatistic[];
  total: number;
}
