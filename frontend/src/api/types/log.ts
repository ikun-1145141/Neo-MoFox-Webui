/**
 * 日志相关 TypeScript 类型定义。
 *
 * 与后端 Pydantic 模型严格对应。
 */

/** 单条实时日志消息 */
export interface RealtimeLogEntry {
  timestamp: string
  level: string
  logger_name: string
  display: string
  color: string
  message: string
  metadata?: Record<string, unknown>
}

/** 日志文件列表项 */
export interface LogFileInfo {
  filename: string
  size: number
  modified_time: string
  path: string
}

/** 日志文件列表响应 */
export interface LogFileListResponse {
  files: LogFileInfo[]
  log_dir: string
}

/** 日志内容分块响应 */
export interface LogContentResponse {
  content: string[]
  offset: number
  size: number
  total_size: number
  has_prev: boolean
  has_next: boolean
  next_offset: number
  prev_offset: number
}
