import axios from 'axios'
import type { AxiosInstance } from 'axios'
import { API_BASE_URL, API_TIMEOUT } from './config'
import type { BaseResponse } from './types/base'
import { useToastStore } from '../utils/toast'

const instance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：注入 token
instance.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('neo_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
    config.headers['X-API-Key'] = token
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

    const shouldSkipToast =
      import.meta.env.DEV && requestUrl.includes('/api/auth/login') && error?.code === 'ERR_NETWORK'

    if (!shouldSkipToast) {
      useToastStore().show(msg, 'error')
    }

    return Promise.reject(error)
  },
)

export default instance
