import http from '../base'

export interface LoginRequest { password: string }
export interface LoginResponse { token: string }

export function login(payload: LoginRequest): Promise<LoginResponse> {
  return http.post('/api/auth/login', payload)
}

export function logout(): Promise<null> {
  return http.post('/api/auth/logout')
}
