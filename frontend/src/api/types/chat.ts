/**
 * 聊天相关 TypeScript 类型定义。
 *
 * 与后端聊天 Pydantic 模型严格对应。
 */

export type ChatMessageType = 'text' | 'image' | 'voice'
export type ChatWindowDirection = 'up' | 'down'

/** 前端聊天流列表项 */
export interface ChatStreamInfo {
  stream_id: string
  platform: string
  chat_type: string
  display_name: string
  group_id: string | null
  group_name: string | null
  person_id: string
  last_active_time: number
  last_message_preview: string
  last_message_type: ChatMessageType | string
}

/** 按平台与聊天类型分组的聊天流 */
export interface ChatStreamGroup {
  platform: string
  chat_type: string
  streams: ChatStreamInfo[]
}

/** 聊天流列表响应 */
export interface ChatStreamsResponse {
  groups: ChatStreamGroup[]
}

/** 前端可渲染的媒体消息内容 */
export interface ChatMessageMedia {
  mime_type: string
  base64: string
  data_url: string
}

/** 前端可渲染的聊天消息 */
export interface ChatMessage {
  message_id: string
  stream_id: string
  platform: string
  message_type: ChatMessageType
  content: string
  media: ChatMessageMedia | null
  processed_plain_text: string | null
  reply_to: string | null
  sender_id: string | null
  sender_name: string
  sender_role: string | null
  time: number
  is_self: boolean
}

/** 指定锚点消息窗口响应 */
export interface MessageWindowResponse {
  stream_id: string
  anchor_message_id: string | null
  direction: ChatWindowDirection
  messages: ChatMessage[]
  has_more: boolean
}

/** 指定消息周围上下文响应 */
export interface MessageAroundResponse {
  stream_id: string
  message_id: string
  messages: ChatMessage[]
  found: boolean
}

/** 发送消息请求 */
export interface SendMessageRequest {
  message_type: ChatMessageType
  content: string
  reply_to?: string | null
  client_message_id?: string | null
}

/** 发送消息结果 */
export interface SendMessageResult {
  ok: boolean
  client_message_id: string | null
  message: ChatMessage | null
  error: string | null
}

/** 全局新消息通知 */
export interface ChatNotification {
  stream_id: string
  platform: string
  chat_type: string
  display_name: string
  message: ChatMessage
}

export type ChatWsEventMap = {
  message_notify: ChatNotification
  message_new: ChatMessage
  messages_window: MessageWindowResponse
  messages_around: MessageAroundResponse
  send_result: SendMessageResult
  error: { message: string }
  pong: null
}
