import type { ModelTestResult, ModelTestType } from '@/api/types/config'

export type ModelKind = 'llm' | 'embedding' | 'rerank'
export type TestStatus = 'idle' | 'running' | 'success' | 'fail'

export interface TestItem {
  key: ModelTestType
  /** Relative to the modelTestDialog translation namespace. */
  message: string
  icon: string
  checked: boolean
  status: TestStatus
  result: ModelTestResult | null
  error: string
}

export const statusIcons: Record<TestStatus, string> = {
  idle: 'schedule-rounded', running: 'progress-activity',
  success: 'check-circle-rounded', fail: 'error-outline-rounded',
}
