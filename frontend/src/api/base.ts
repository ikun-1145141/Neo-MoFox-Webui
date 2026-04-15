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
    const msg = error?.response?.data?.message ?? error?.message ?? '网络请求失败'
    useToastStore().show(msg, 'error')
    return Promise.reject(error)
  },
)

export default instance
