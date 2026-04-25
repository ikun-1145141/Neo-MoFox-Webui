export interface BaseResponse<T = unknown> {
  code: number
  data: T | null
  message: string
}
