/**
 * 聊天相关 API 模块。
 *
 * HTTP 仅用于获取聊天流列表，实时通知、历史加载和发送消息统一走 WebSocket。
 */

import instance from '../base'
import { API_BASE_URL, API_WEBUI_PREFIX } from '../config'
import type {
  ChatStreamsResponse,
  ChatWsEventMap,
  ChatWindowDirection,
  SendMessageRequest,
} from '../types/chat'

const CHAT_PREFIX = `${API_WEBUI_PREFIX}/chat`

export type ChatWsEventName = keyof ChatWsEventMap
export type ChatWsHandler<T extends ChatWsEventName> = (payload: ChatWsEventMap[T]) => void
export type ChatWsState = 'disconnected' | 'connecting' | 'connected'

interface WsEnvelope<T extends ChatWsEventName = ChatWsEventName> {
  event: T
  data: ChatWsEventMap[T]
}

/** 获取聊天流列表。 */
export async function getChatStreams(): Promise<ChatStreamsResponse> {
  return instance.get(`${CHAT_PREFIX}/streams`)
}

/** 聊天 WebSocket 客户端。 */
export class ChatWsClient {
  private ws: WebSocket | null = null
  private listeners: Map<ChatWsEventName, Set<(payload: unknown) => void>> = new Map()
  private stateListeners: Set<(state: ChatWsState) => void> = new Set()
  private state: ChatWsState = 'disconnected'
  private heartbeatTimer: number | null = null
  private readonly path: string

  constructor(path: string) {
    this.path = path
  }

  /** 获取连接状态。 */
  getState(): ChatWsState {
    return this.state
  }

  /** 建立连接。 */
  connect(): void {
    if (this.ws && this.state !== 'disconnected') return

    const origin = API_BASE_URL.replace(/^http/, 'ws')
    const token = sessionStorage.getItem('neo_token')
    const url = `${origin}${this.path}${token ? `?token=${encodeURIComponent(token)}` : ''}`

    this.setState('connecting')
    this.ws = new WebSocket(url)
    this.ws.onopen = () => {
      this.setState('connected')
      this.startHeartbeat()
    }
    this.ws.onmessage = (event) => this.handleMessage(event)
    this.ws.onclose = () => {
      this.stopHeartbeat()
      this.ws = null
      this.setState('disconnected')
    }
    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  /** 断开连接。 */
  disconnect(): void {
    this.stopHeartbeat()
    this.ws?.close()
    this.ws = null
    this.setState('disconnected')
  }

  /** 订阅指定事件。 */
  on<T extends ChatWsEventName>(event: T, handler: ChatWsHandler<T>): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(handler as (payload: unknown) => void)
    return () => this.off(event, handler)
  }

  /** 取消订阅指定事件。 */
  off<T extends ChatWsEventName>(event: T, handler: ChatWsHandler<T>): void {
    const handlers = this.listeners.get(event)
    if (!handlers) return
    handlers.delete(handler as (payload: unknown) => void)
    if (handlers.size === 0) {
      this.listeners.delete(event)
    }
  }

  /** 监听连接状态。 */
  onStateChange(handler: (state: ChatWsState) => void): () => void {
    this.stateListeners.add(handler)
    return () => this.stateListeners.delete(handler)
  }

  /** 请求消息窗口。 */
  loadWindow(anchorMessageId: string | null, direction: ChatWindowDirection, limit = 30): void {
    this.send('load_window', {
      anchor_message_id: anchorMessageId,
      direction,
      limit,
    })
  }

  /** 请求指定消息周围上下文。 */
  loadAround(messageId: string, before = 10, after = 10): void {
    this.send('load_around', {
      message_id: messageId,
      before,
      after,
    })
  }

  /** 发送聊天消息。 */
  sendChatMessage(request: SendMessageRequest): void {
    this.send('send_message', request)
  }

  /** 发送原始 WS 事件。 */
  send(event: string, data: unknown = null): void {
    if (!this.ws || this.state !== 'connected') return
    this.ws.send(JSON.stringify({ event, data }))
  }

  private setState(nextState: ChatWsState): void {
    if (this.state === nextState) return
    this.state = nextState
    for (const handler of this.stateListeners) {
      handler(nextState)
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const envelope = JSON.parse(event.data as string) as WsEnvelope
      const handlers = this.listeners.get(envelope.event)
      if (!handlers) return
      for (const handler of handlers) {
        handler(envelope.data)
      }
    } catch (error) {
      console.error('[ChatWsClient] 消息解析失败:', error)
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      this.send('ping')
    }, 30000)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}

/** 创建全局通知 WS 客户端。 */
export function createChatNotificationClient(): ChatWsClient {
  return new ChatWsClient(`${CHAT_PREFIX}/ws/notifications`)
}

/** 创建指定聊天流 WS 客户端。 */
export function createChatStreamClient(streamId: string): ChatWsClient {
  return new ChatWsClient(`${CHAT_PREFIX}/ws/streams/${encodeURIComponent(streamId)}`)
}
