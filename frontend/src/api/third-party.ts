/**
 * 第三方 API 请求实例。
 *
 * 专门提供给插件 UI 模板引擎等需要请求**外部第三方接口**的场景使用。
 * 与主系统 [`instance`](Neo-MoFox-Webui/frontend/src/api/base.ts:8) 的差异：
 *   - **不设置 baseURL**：第三方接口域名通常与主系统不同，必须使用完整 URL。
 *   - 其他配置（超时、Content-Type、token 注入、系统重启拦截、统一错误提示、
 *     健康检查相关行为等）与主系统实例保持一致。
 *
 * 注意：响应拦截器仍按照主系统的 BaseResponse 协议处理；如果第三方接口
 * 不返回 `{ code, data, message }` 结构，请在调用方对响应直接取
 * `response.data`（通过传入 `transformResponse` 或自行处理 catch 块）。
 * 这是有意保留的行为，以便和主系统调用风格一致；如未来确认需要放宽
 * 业务校验，可在此文件单独调整拦截器，而不影响主实例。
 *
 * Raw 模式：当请求配置中设置 `__rawResponse: true` 时，响应拦截器将跳过
 * BaseResponse 校验，直接返回 axios 原始 response.data（即 HTTP 响应体原文）。
 * 这使得插件 XML API 模板可以对接不遵循 BaseResponse 协议的第三方接口。
 */

import axios from 'axios'
import type { AxiosInstance } from 'axios'
import { API_TIMEOUT } from './config'
import type { BaseResponse } from './types/base'
import { useToastStore } from '../utils/toast'
import { getIsRestarting } from './base'

const thirdPartyInstance: AxiosInstance = axios.create({
  // 不设置 baseURL，调用方必须传入完整的第三方 URL
  timeout: API_TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：与主实例保持一致的 token 注入与系统状态检查
thirdPartyInstance.interceptors.request.use((config) => {
  console.debug('Outgoing third-party request:', config.method?.toUpperCase(), config.url)

  // 检查系统是否正在重启（与主实例一致；第三方请求无健康检查 URL 例外）
  if (getIsRestarting()) {
    return Promise.reject(new Error('系统正在重启，请稍候...'))
  }

  const token = sessionStorage.getItem('neo_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
    config.headers['X-API-Key'] = token
  }

  // FormData 时让浏览器自动设置带 boundary 的 Content-Type
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }

  return config
})

// 响应拦截器：与主实例保持一致的业务错误统一处理
// 当请求配置中 __rawResponse 为 true 时跳过 BaseResponse 解析，直接返回原始响应体
thirdPartyInstance.interceptors.response.use(
  (response) => {
    // Raw 模式：跳过 BaseResponse 校验，直接透传 HTTP 响应体
    if ((response.config as any).__rawResponse) {
      return response.data
    }

    const res = response.data as BaseResponse
    if (res.code !== 200) {
      console.error('Third-party API Error:', res)
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

    const shouldSkipToast =
      import.meta.env.DEV && requestUrl.includes('/api/auth/login') && error?.code === 'ERR_NETWORK'

    if (!shouldSkipToast) {
      useToastStore().show(msg, 'error')
    }

    return Promise.reject(error)
  },
)

export default thirdPartyInstance
