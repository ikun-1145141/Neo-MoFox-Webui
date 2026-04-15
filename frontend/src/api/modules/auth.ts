import http from '../base'
import type { LoginRequest, LoginResponse } from '../types/base'

export function login(payload: LoginRequest): Promise<LoginResponse> {
  return http.post('/api/auth/login', payload)
}

export function logout(): Promise<null> {
  return http.post('/api/auth/logout')
}
