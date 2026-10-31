/**
 * 模型测试对话框共享类型
 * @file modelTestDialogTypes.ts
 */

import type { ModelTestResult } from '@/api/types/config'

export type TestStatus = 'idle' | 'running' | 'success' | 'fail'

export type ModelKind = 'llm' | 'embedding' | 'rerank'

export type LLMTestKey = 'chat' | 'stream' | 'tool_call' | 'vlm'

export interface TestItem {
  /** 测试项键名，LLM 集群中同时作为 test_type 使用 */
  key: string
  label: string
  desc: string
  icon: string
  checked: boolean
  status: TestStatus
  result: ModelTestResult | null
  error: string
}