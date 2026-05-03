import axios from 'axios'
import type { AxiosInstance } from 'axios'
import { API_BASE_URL, API_TIMEOUT } from './config'
import type { BaseResponse } from './types/base'
import { useToastStore } from '../utils/toast'
import { healthCheck } from './modules/settings'

const instance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
})

// ========== 系统状态管理 ==========
let isRestarting = false
let healthCheckTimer: number | null = null

/**
 * 获取系统重启状态
 */
export function getIsRestarting(): boolean {
  return isRestarting
}

/**
 * 设置系统重启状态
 */
export function setIsRestarting(value: boolean): void {
  isRestarting = value
}

/**
 * 启动健康检查轮询
 * 
 * @param onHealthy - 系统恢复健康时的回调
 * @param interval - 检查间隔（毫秒），默认 2000ms
 * @param maxAttempts - 最大尝试次数，默认 60 次（2 分钟）
 */
export function startHealthCheck(
  onHealthy: () => void,
  interval = 2000,
  maxAttempts = 60
): void {
  let attempts = 0

  const check = async () => {
    attempts++

    try {
      await healthCheck()
      // 健康检查成功
      stopHealthCheck()
      setIsRestarting(false)
      onHealthy()
    } catch {
      // 健康检查失败，继续等待
      if (attempts >= maxAttempts) {
        // 超过最大尝试次数
        stopHealthCheck()
        setIsRestarting(false)
        console.error('健康检查超时，系统可能未能成功重启')
      }
    }
  }

  // 立即执行第一次检查
  check()

  // 设置定时器
  healthCheckTimer = window.setInterval(check, interval)
}

/**
 * 停止健康检查轮询
 */
export function stopHealthCheck(): void {
  if (healthCheckTimer !== null) {
    clearInterval(healthCheckTimer)
    healthCheckTimer = null
  }
}

// 请求拦截器：注入 token 和检查系统状态
instance.interceptors.request.use((config) => {
  // 检查系统是否正在重启（除健康检查接口外）
  if (getIsRestarting() && !config.url?.includes('/api/webui/health')) {
    return Promise.reject(new Error('系统正在重启，请稍候...'))
  }

  const token = sessionStorage.getItem('neo_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
    config.headers['X-API-Key'] = token
  }
  
  // 如果是 FormData，删除默认的 Content-Type，让浏览器自动设置（包括 boundary）
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  
  return config
})

// 响应拦截器：统一处理业务错误
instance.interceptors.response.use(
  (response) => {
    const res = response.data as BaseResponse
    if (res.code !== 200) {
      useToastStore().show(res.message ?? '操作失败', 'error')
      return Promise.reject(res)
    }
    return res.data as any
  },
  (error) => {
    const requestUrl = String(error?.config?.url ?? '')
    const status = error?.response?.status as number | undefined
    const backendMessage = error?.response?.data?.message as string | undefined
    const backendDetail = error?.response?.data?.detail as string | undefined

    let msg: string = backendMessage ?? backendDetail ?? ''
    if (!msg) {
      if (status === 401 && requestUrl.includes('/api/auth/login')) {
        msg = '密码错误，请重试'
      } else if (status === 403) {
        msg = '认证失败，请重新登录'
      } else if (error?.code === 'ERR_NETWORK') {
        msg = '无法连接后端服务，请确认服务已启动'
      } else {
        msg = error?.message ?? '网络请求失败'
      }
    }

    // 跳过以下情况的 Toast 提示：
    // 1. 开发环境下登录接口的网络错误
    // 2. 健康检查接口的错误（重启期间的预期行为）
    const shouldSkipToast =
      (import.meta.env.DEV && requestUrl.includes('/api/auth/login') && error?.code === 'ERR_NETWORK') ||
      (requestUrl.includes('/api/webui/health') && getIsRestarting())

    if (!shouldSkipToast) {
      useToastStore().show(msg, 'error')
    }

    return Promise.reject(error)
  },
)

export default instance
