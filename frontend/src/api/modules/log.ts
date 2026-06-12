/**
 * 日志相关 API 模块。
 *
 * 提供历史日志列表获取和日志内容分块拉取接口。
 */

import instance from '../base'
import { API_WEBUI_PREFIX } from '../config'
import type { LogFileListResponse, LogContentResponse } from '../types/log'

const LOG_PREFIX = `${API_WEBUI_PREFIX}/log`

/**
 * 获取可用的历史日志文件列表。
 *
 * @returns 日志文件列表响应
 */
export async function getLogFiles(): Promise<LogFileListResponse> {
  return instance.get(`${LOG_PREFIX}/files`)
}

/**
 * 获取指定日志文件的内容（支持偏移量分块）。
 *
 * @param filename - 日志文件名
 * @param offset - 偏移量（字节），0 表示从头开始
 * @param limit - 本次返回的最大字节数
 * @param query - 日志内容搜索关键词
 * @param levels - 日志级别过滤列表
 * @returns 日志内容分块响应
 */
export async function getLogContent(
  filename: string,
  offset: number = 0,
  limit: number = 65536,
  query: string = '',
  levels: string[] = [],
): Promise<LogContentResponse> {
  return instance.get(`${LOG_PREFIX}/content`, {
    params: { filename, offset, limit, query, levels },
  })
}
