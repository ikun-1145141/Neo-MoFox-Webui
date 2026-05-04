import http from '../base'
import type { LoginRequest, LoginResponse } from '../types/auth'
import { API_WEBUI_PREFIX } from '../config'

const BASE = API_WEBUI_PREFIX

export function login(payload: LoginRequest): Promise<LoginResponse> {
  return http.post(`${BASE}/auth/login`, payload)
}

export function logout(): Promise<null> {
  return http.post(`${BASE}/auth/logout`)
}
