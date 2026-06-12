/**
 * 统一 WebSocket 连接器。
 *
 * 作为前端与后端长连接的唯一入口，管理连接建立、心跳保活、自动重连，
 * 并提供基于事件名称的订阅/分发机制。
 */

import { API_BASE_URL } from './config'

/** WebSocket 连接状态 */
export type WsState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'

/** 事件回调签名 */
export type WsEventCallback = (payload: unknown) => void

/** WebSocket 消息协议结构 */
export interface WsMessage {
  event: string
  data: unknown
}

/** 连接器配置 */
export interface WsConnectorOptions {
  /** 心跳间隔（毫秒），默认 30000 */
  heartbeatInterval?: number
  /** 重连基础间隔（毫秒），默认 2000 */
  reconnectBaseDelay?: number
  /** 最大重连间隔（毫秒），默认 30000 */
  reconnectMaxDelay?: number
  /** 最大重连次数，0 表示无限，默认 0 */
  maxReconnectAttempts?: number
}

const DEFAULT_OPTIONS: Required<WsConnectorOptions> = {
  heartbeatInterval: 30000,
  reconnectBaseDelay: 2000,
  reconnectMaxDelay: 30000,
  maxReconnectAttempts: 0,
}

/**
 * 统一 WebSocket 连接管理器。
 *
 * 职责：
 * - 统一管理连接建立、心跳保活、自动重连
 * - 提供事件订阅/分发机制（如 on('realtime_log', callback)）
 * - 接收后端推送的实时数据，按事件类型转发给前端对应业务模块
 */
class WsConnector {
  private ws: WebSocket | null = null
  private state: WsState = 'disconnected'
  private options: Required<WsConnectorOptions>
  private listeners: Map<string, Set<WsEventCallback>> = new Map()
  private stateListeners: Set<(state: WsState) => void> = new Set()
  private heartbeatTimer: number | null = null
  private reconnectTimer: number | null = null
  private reconnectAttempts = 0
  private url = ''
  private manualClose = false

  constructor(options?: WsConnectorOptions) {
    this.options = { ...DEFAULT_OPTIONS, ...options }
  }

  /** 获取当前连接状态 */
  getState(): WsState {
    return this.state
  }

  /**
   * 建立 WebSocket 连接。
   *
   * @param path - WebSocket 路径（相对于后端 origin），如 '/webui/api/log/ws'
   */
  connect(path: string): void {
    if (this.ws && (this.state === 'connected' || this.state === 'connecting')) {
      return
    }

    this.manualClose = false

    // 构造 WebSocket URL
    const origin = API_BASE_URL.replace(/^http/, 'ws')
    this.url = `${origin}${path}`

    // 注入 token
    const token = sessionStorage.getItem('neo_token')
    const urlWithAuth = token ? `${this.url}?token=${encodeURIComponent(token)}` : this.url

    this.setState('connecting')
    this.ws = new WebSocket(urlWithAuth)

    this.ws.onopen = () => {
      this.setState('connected')
      this.reconnectAttempts = 0
      this.startHeartbeat()
    }

    this.ws.onmessage = (event: MessageEvent) => {
      this.handleMessage(event)
    }

    this.ws.onclose = () => {
      this.stopHeartbeat()
      if (!this.manualClose) {
        this.scheduleReconnect()
      } else {
        this.setState('disconnected')
      }
    }

    this.ws.onerror = () => {
      // onclose 会紧接着触发，交给 onclose 处理重连
    }
  }

  /** 主动断开连接 */
  disconnect(): void {
    this.manualClose = true
    this.stopHeartbeat()
    this.clearReconnectTimer()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.setState('disconnected')
  }

  /**
   * 订阅指定事件。
   *
   * @param event - 事件名称（与后端推送的 event 字段对应）
   * @param callback - 回调函数
   * @returns 取消订阅的函数
   */
  on(event: string, callback: WsEventCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)

    return () => {
      this.off(event, callback)
    }
  }

  /**
   * 取消订阅指定事件。
   *
   * @param event - 事件名称
   * @param callback - 需要取消的回调
   */
  off(event: string, callback: WsEventCallback): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.delete(callback)
      if (callbacks.size === 0) {
        this.listeners.delete(event)
      }
    }
  }

  /**
   * 订阅连接状态变化。
   *
   * @param callback - 状态变化回调
   * @returns 取消订阅的函数
   */
  onStateChange(callback: (state: WsState) => void): () => void {
    this.stateListeners.add(callback)
    return () => {
      this.stateListeners.delete(callback)
    }
  }

  /**
   * 向后端发送消息。
   *
   * @param event - 事件名称
   * @param data - 数据负载
   */
  send(event: string, data: unknown = null): void {
    if (this.ws && this.state === 'connected') {
      const message: WsMessage = { event, data }
      this.ws.send(JSON.stringify(message))
    }
  }

  // ========== 私有方法 ==========

  private setState(newState: WsState): void {
    if (this.state !== newState) {
      this.state = newState
      for (const cb of this.stateListeners) {
        try {
          cb(newState)
        } catch {
          // 不让外部回调异常影响内部状态
        }
      }
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const msg: WsMessage = JSON.parse(event.data as string)
      if (!msg.event) return

      // pong 消息不需要分发
      if (msg.event === 'pong') return

      const callbacks = this.listeners.get(msg.event)
      if (callbacks) {
        for (const cb of callbacks) {
          try {
            cb(msg.data)
          } catch (err) {
            console.error(`[WsConnector] 事件回调错误 (${msg.event}):`, err)
          }
        }
      }
    } catch {
      // 非 JSON 消息，忽略
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      this.send('ping')
    }, this.options.heartbeatInterval)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private scheduleReconnect(): void {
    const { maxReconnectAttempts, reconnectBaseDelay, reconnectMaxDelay } = this.options

    if (maxReconnectAttempts > 0 && this.reconnectAttempts >= maxReconnectAttempts) {
      this.setState('disconnected')
      return
    }

    this.setState('reconnecting')

    // 指数退避 + 抖动
    const delay = Math.min(
      reconnectBaseDelay * Math.pow(1.5, this.reconnectAttempts) + Math.random() * 1000,
      reconnectMaxDelay,
    )

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectAttempts++
      this.connect(this.url.replace(/^wss?:\/\/[^/]+/, '').replace(/\?.*$/, ''))
    }, delay)
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }
}

/** 全局单例 WebSocket 连接器 */
export const wsConnector = new WsConnector()

export default wsConnector
