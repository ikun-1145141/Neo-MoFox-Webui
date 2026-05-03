/**
 * 系统控制 API 模块
 */

import instance from '../base'
import type { SystemStatus } from '../types/system'

/**
 * 重启 Bot 系统
 */
export async function restartBot(): Promise<SystemStatus> {
  return await instance.post('/api/system/restart')
}

/**
 * 关闭 Bot 系统
 */
export async function shutdownBot(): Promise<SystemStatus> {
  return await instance.post('/api/system/shutdown')
}
