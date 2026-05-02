# Dashboard API 对接文档（前端）

本文档用于前端接入 WebUI 首页仪表盘接口。

## 1. 接口信息

- Method: `GET`
- Path: `/api/dashboard/overview`
- Auth: 需要登录态，携带 `Authorization: Bearer <token>` 和 `X-API-Key`
- Response: 统一 `BaseResponse`

## 2. 响应结构

```json
{
  "code": 200,
  "message": "获取仪表盘数据成功",
  "data": {
    "runtime": {
      "event": {
        "handler_count": 0,
        "temporary_handler_count": 0,
        "event_type_count": 0,
        "total_subscriptions": 0
      },
      "task": {
        "total_tasks": 0,
        "active_tasks": 0,
        "daemon_tasks": 0,
        "grouped_tasks": 0,
        "groups": 0,
        "process_workers": 0,
        "process_pool_running": false
      },
      "scheduler": {
        "is_running": false,
        "uptime_seconds": 0,
        "total_tasks": 0,
        "running_tasks": 0,
        "success_rate": 0
      },
      "adapter": {
        "active_count": 0,
        "active_signatures": []
      }
    },
    "business": {
      "messages": {
        "today_total": 0,
        "today_inbound": 0,
        "today_outbound": 0,
        "today_start_timestamp": 0
      },
      "streams": {
        "active_count": 0
      },
      "plugins": {
        "loaded_count": 0,
        "failed_count": 0
      },
      "components": {
        "total_count": 0,
        "by_type": {
          "action": 0,
          "agent": 0,
          "tool": 0,
          "adapter": 0,
          "chatter": 0,
          "command": 0,
          "config": 0,
          "event_handler": 0,
          "service": 0,
          "router": 0,
          "plugin": 0
        }
      }
    },
    "llm": {
      "model_count": 0,
      "total_requests": 0,
      "success_count": 0,
      "error_count": 0,
      "success_rate": 0,
      "avg_latency_seconds": 0,
      "avg_latency_ms": 0,
      "total_tokens_in": 0,
      "total_tokens_out": 0,
      "total_cost": 0,
      "updated_at": "2026-05-02T12:00:00"
    },
    "updated_at": "2026-05-02T12:00:00"
  }
}
```

## 3. TypeScript 类型建议

```ts
export interface BaseResponse<T = unknown> {
  code: number;
  data: T | null;
  message: string;
}

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
```

## 4. API 调用示例

```ts
import http from './base';

export function getDashboardOverview(): Promise<DashboardOverview> {
  return http.get('/api/dashboard/overview');
}
```

## 5. 刷新策略建议

- 关键指标（状态卡片）轮询：5 秒
- 大面板（细项）轮询：30 秒
- 保留手动刷新按钮：用户可强制更新

## 6. UI 展示建议

- 顶部 KPI：后端状态、今日消息、LLM 花费、活跃任务、已加载插件、已注册组件
- 中部面板：运行总览 / 业务核心 / LLM 运营
- 底部显示：`data.updated_at`（后端数据时间）

## 7. 兼容与容错

- `success_rate` 范围为 0~1，前端展示百分比时建议 `* 100`
- `total_cost` 为累计成本，单位与后端 LLM 配置一致
- 当后端未产生 LLM 请求时，`llm` 所有数值可为 0，属于正常状态
