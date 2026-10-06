<script setup lang="ts">
/**
 * 聊天监视视图。
 *
 * 全屏聊天面板，展示聊天流列表、实时消息窗口和发送入口。
 * 移动端顶部直接显示当前流标题，点击可切换流。
 */

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import Icon from '../components/common/Icon.vue'
import {
  createChatNotificationClient,
  createChatStreamClient,
  getChatMedia,
  getChatStreams,
  type ChatWsClient,
  type ChatWsState,
} from '../api/modules/chat'
import type {
  ChatMessage,
  ChatMessageSegment,
  ChatReply,
  ChatStreamGroup,
  ChatStreamInfo,
  SendMessageResult,
} from '../api/types/chat'
import { useI18n } from '../utils/i18n'
import { useToastStore } from '../utils/toast'

const { t } = useI18n()
const toastStore = useToastStore()

const groups = ref<ChatStreamGroup[]>([])
const messages = ref<ChatMessage[]>([])
const selectedStream = ref<ChatStreamInfo | null>(null)
const isLoadingStreams = ref(false)
const isLoadingMessages = ref(false)
const streamsSearchText = ref('')
const composerText = ref('')
const notificationState = ref<ChatWsState>('disconnected')
const streamState = ref<ChatWsState>('disconnected')
const hasMoreBefore = ref(false)
const lastUpdatedAt = ref('')
const isMobileStreamMenuOpen = ref(false)
const messageListRef = ref<HTMLElement | null>(null)
// 媒体按需加载缓存：media_id -> data URL
const mediaUrls = ref<Record<string, string>>({})
const mediaStates = ref<Record<string, 'loading' | 'error'>>({})
const failedAvatars = ref<Record<string, boolean>>({})
const previewImage = ref<{ url: string; alt: string } | null>(null)
const highlightedMessageId = ref('')

let notificationClient: ChatWsClient | null = null
let streamClient: ChatWsClient | null = null
let unwatchNotificationState: (() => void) | null = null
let unwatchStreamState: (() => void) | null = null
let unsubscribeNotification: (() => void) | null = null
let unsubscribeStreamMessages: (() => void) | null = null
let unsubscribeStreamWindow: (() => void) | null = null
let unsubscribeStreamSendResult: (() => void) | null = null
let unsubscribeStreamAround: (() => void) | null = null
let unsubscribeStreamError: (() => void) | null = null
let mediaObserver: IntersectionObserver | null = null
let highlightTimer: number | null = null

const flatStreams = computed(() => groups.value.flatMap((group) => group.streams))

const filteredGroups = computed(() => {
  const keyword = streamsSearchText.value.trim().toLowerCase()
  if (!keyword) return groups.value

  return groups.value
    .map((group) => ({
      ...group,
      streams: group.streams.filter((stream) => streamHaystack(stream, group).includes(keyword)),
    }))
    .filter((group) => group.streams.length > 0)
})

const selectedTitle = computed(() => selectedStream.value?.display_name || t('chat.empty.selectTitle'))
const selectedMeta = computed(() => {
  if (!selectedStream.value) return t('chat.empty.selectHint')
  return formatStreamMeta(selectedStream.value)
})

const connectionTone = computed(() => {
  if (streamState.value === 'connected') return 'connected'
  if (streamState.value === 'connecting') return 'connecting'
  return 'disconnected'
})

const canSend = computed(() => Boolean(selectedStream.value && composerText.value.trim() && streamState.value === 'connected'))

onMounted(async () => {
  await refreshStreams()
  connectNotifications()
})

onUnmounted(() => {
  disconnectNotifications()
  disconnectStream()
  mediaObserver?.disconnect()
  mediaObserver = null
  if (highlightTimer !== null) window.clearTimeout(highlightTimer)
})

watch(messages, () => observePendingMedia())

watch(selectedStream, (stream) => {
  connectSelectedStream(stream)
})

async function refreshStreams(): Promise<void> {
  isLoadingStreams.value = true
  try {
    const data = await getChatStreams()
    groups.value = data.groups
    lastUpdatedAt.value = new Date().toLocaleTimeString()
    reconcileSelectedStream()
  } finally {
    isLoadingStreams.value = false
  }
}

function reconcileSelectedStream(): void {
  if (!selectedStream.value) {
    selectedStream.value = flatStreams.value[0] ?? null
    return
  }

  const freshStream = flatStreams.value.find((stream) => stream.stream_id === selectedStream.value?.stream_id)
  selectedStream.value = freshStream ?? flatStreams.value[0] ?? null
}

function connectNotifications(): void {
  disconnectNotifications()
  notificationClient = createChatNotificationClient()
  unwatchNotificationState = notificationClient.onStateChange((state) => {
    notificationState.value = state
  })
  unsubscribeNotification = notificationClient.on('message_notify', (payload) => {
    upsertStreamFromNotification(payload.stream_id, payload.display_name, payload.message)
  })
  notificationClient.connect()
}

function disconnectNotifications(): void {
  unsubscribeNotification?.()
  unsubscribeNotification = null
  unwatchNotificationState?.()
  unwatchNotificationState = null
  notificationClient?.disconnect()
  notificationClient = null
}

function connectSelectedStream(stream: ChatStreamInfo | null): void {
  disconnectStream()
  messages.value = []
  hasMoreBefore.value = false
  if (!stream) return

  isLoadingMessages.value = true
  streamClient = createChatStreamClient(stream.stream_id)
  unwatchStreamState = streamClient.onStateChange((state) => {
    streamState.value = state
    if (state === 'connected') {
      streamClient?.loadWindow(null, 'up', 50)
    }
  })
  unsubscribeStreamMessages = streamClient.on('message_new', (message) => {
    appendMessage(message)
  })
  unsubscribeStreamWindow = streamClient.on('messages_window', (payload) => {
    hasMoreBefore.value = payload.has_more
    applyMessageWindow(payload.messages, payload.direction)
    isLoadingMessages.value = false
  })
  unsubscribeStreamAround = streamClient.on('messages_around', (payload) => {
    isLoadingMessages.value = false
    messages.value = dedupeMessages([...messages.value, ...payload.messages]).sort((a, b) => a.time - b.time)
    scrollToMessage(payload.message_id)
  })
  unsubscribeStreamSendResult = streamClient.on('send_result', handleSendResult)
  unsubscribeStreamError = streamClient.on('error', (payload) => {
    isLoadingMessages.value = false
    toastStore.show(payload.message, 'error')
  })
  streamClient.connect()
}

function disconnectStream(): void {
  unsubscribeStreamMessages?.()
  unsubscribeStreamMessages = null
  unsubscribeStreamWindow?.()
  unsubscribeStreamWindow = null
  unsubscribeStreamAround?.()
  unsubscribeStreamAround = null
  unsubscribeStreamSendResult?.()
  unsubscribeStreamSendResult = null
  unsubscribeStreamError?.()
  unsubscribeStreamError = null
  unwatchStreamState?.()
  unwatchStreamState = null
  streamClient?.disconnect()
  streamClient = null
  streamState.value = 'disconnected'
}

function reconnectStream(): void {
  if (selectedStream.value) {
    connectSelectedStream(selectedStream.value)
  }
}

function selectStream(stream: ChatStreamInfo): void {
  selectedStream.value = stream
  isMobileStreamMenuOpen.value = false
}

function toggleMobileStreamMenu(): void {
  isMobileStreamMenuOpen.value = !isMobileStreamMenuOpen.value
}

function closeMobileStreamMenu(): void {
  isMobileStreamMenuOpen.value = false
}

function loadOlderMessages(): void {
  if (!streamClient || !messages.value.length || isLoadingMessages.value) return
  isLoadingMessages.value = true
  streamClient.loadWindow(messages.value[0].message_id, 'up', 40)
}

function sendMessage(): void {
  const content = composerText.value.trim()
  if (!content || !streamClient || !canSend.value) return

  streamClient.sendChatMessage({
    message_type: 'text',
    content,
    client_message_id: `webui-${Date.now()}`,
  })
  composerText.value = ''
}

function handleComposerKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' || event.shiftKey) return
  event.preventDefault()
  sendMessage()
}

function handleSendResult(result: SendMessageResult): void {
  if (!result.ok) {
    toastStore.show(result.error || t('chat.toast.sendFailed'), 'error')
    return
  }
  if (result.message) appendMessage(result.message)
}

function applyMessageWindow(nextMessages: ChatMessage[], direction: 'up' | 'down'): void {
  if (direction === 'up') {
    messages.value = dedupeMessages([...nextMessages, ...messages.value]).sort((a, b) => a.time - b.time)
  } else {
    messages.value = dedupeMessages([...messages.value, ...nextMessages]).sort((a, b) => a.time - b.time)
  }
  scrollMessagesToBottom()
}

function appendMessage(message: ChatMessage): void {
  messages.value = dedupeMessages([...messages.value, message]).sort((a, b) => a.time - b.time)
  scrollMessagesToBottom()
}

function dedupeMessages(items: ChatMessage[]): ChatMessage[] {
  const byId = new Map<string, ChatMessage>()
  for (const item of items) {
    byId.set(item.message_id, item)
  }
  return Array.from(byId.values())
}

function scrollMessagesToBottom(): void {
  nextTick(() => {
    const container = messageListRef.value
    if (!container) return
    container.scrollTop = container.scrollHeight
  })
}

function streamHaystack(stream: ChatStreamInfo, group: ChatStreamGroup): string {
  return [
    stream.stream_id,
    stream.display_name,
    stream.group_name,
    stream.group_id,
    stream.person_id,
    stream.last_message_preview,
    group.platform,
    group.chat_type,
  ].filter(Boolean).join(' ').toLowerCase()
}

function upsertStreamFromNotification(streamId: string, displayName: string, message: ChatMessage): void {
  const existing = flatStreams.value.find((stream) => stream.stream_id === streamId)
  if (existing) {
    existing.display_name = displayName
    existing.last_active_time = message.time
    existing.last_message_preview = messagePreview(message)
    existing.last_message_type = message.message_type
  }
  if (selectedStream.value?.stream_id === streamId) {
    appendMessage(message)
  }
}

function formatStreamMeta(stream: ChatStreamInfo): string {
  const parts = [stream.platform, chatTypeLabel(stream.chat_type)]
  if (stream.group_name) parts.push(stream.group_name)
  return parts.filter(Boolean).join(' · ')
}

function chatTypeLabel(value: string): string {
  if (value === 'group') return t('chat.types.group')
  if (value === 'private') return t('chat.types.private')
  return value || t('chat.types.unknown')
}

const MEDIA_LABEL_KEYS: Record<string, string> = {
  image: 'chat.message.image',
  emoji: 'chat.message.emoji',
  voice: 'chat.message.voice',
  video: 'chat.message.video',
  file: 'chat.message.file',
}

/** 片段的单行文本，用于搜索、预览与无障碍说明。 */
function segmentsToText(segments: ChatMessageSegment[]): string {
  const parts = segments.map((segment) => {
    if (segment.type === 'text') return segment.text
    if (segment.type === 'at') return `@${segment.text} `
    const label = t(MEDIA_LABEL_KEYS[segment.type] || 'chat.message.unsupported')
    return segment.text ? `${label} ${segment.text}` : label
  })
  return ' '.join(''.join(parts).split())
}

/** 消息正文文本。 */
function messageContent(message: ChatMessage): string {
  if (message.segments && message.segments.length) {
    const text = segmentsToText(message.segments)
    if (text) return text
  }
  return message.processed_plain_text || message.content || t('chat.message.unsupported')
}

function messagePreview(message: ChatMessage): string {
  return messageContent(message)
}

function streamPreview(stream: ChatStreamInfo): string {
  const key = MEDIA_LABEL_KEYS[stream.last_message_type || '']
  if (key && !stream.last_message_preview) return t(key)
  return stream.last_message_preview || t('chat.streams.noPreview')
}

function streamInitial(stream: ChatStreamInfo): string {
  return (stream.display_name || '?').trim().slice(0, 1).toUpperCase()
}

function initial(name: string): string {
  return (name || '?').trim().slice(0, 1).toUpperCase()
}

/** QQ 平台可用官方头像接口，其他平台退回名称首字母。 */
function avatarUrl(platform: string, userId: string | null | undefined): string {
  if (!platform || !userId) return ''
  if (platform === 'qq' && /^\d{5,12}$/.test(userId)) {
    return `https://q1.qlogo.cn/g?b=qq&nk=${userId}&s=100`
  }
  return ''
}

function avatarKey(platform: string, userId: string | null | undefined): string {
  return `${platform}:${userId || ''}`
}

function messageAvatar(message: ChatMessage): string {
  if (message.is_self) return ''
  return avatarUrl(message.platform, message.sender_id)
}

function streamAvatar(stream: ChatStreamInfo): string {
  return avatarUrl(stream.platform, stream.peer_user_id)
}

function markAvatarFailed(key: string): void {
  failedAvatars.value = { ...failedAvatars.value, [key]: true }
}

function showAvatar(key: string, url: string): boolean {
  return Boolean(url) && !failedAvatars.value[key]
}

/** 同一发送者 5 分钟内的连续消息合并显示。 */
function isGrouped(index: number): boolean {
  if (index <= 0) return false
  const current = messages.value[index]
  const previous = messages.value[index - 1]
  if (!current || !previous) return false
  const sameSender = (current.sender_id || current.sender_name) === (previous.sender_id || previous.sender_name)
  return sameSender && current.time - previous.time < 300
}

function senderLabel(message: ChatMessage): string {
  return message.sender_name || t('chat.message.unknownSender')
}

function replySenderLabel(reply: ChatReply): string {
  if (reply.is_self) return t('chat.message.replySelf')
  return reply.sender_name || t('chat.message.unknownSender')
}

/** 片段的可渲染地址：内联数据优先，否则用按需加载缓存。 */
function segmentSrc(segment: ChatMessageSegment): string {
  if (segment.data_url) return segment.data_url
  if (segment.media_id) return mediaUrls.value[segment.media_id] || ''
  return ''
}

function segmentState(segment: ChatMessageSegment): 'ready' | 'loading' | 'error' | 'idle' {
  if (segmentSrc(segment)) return 'ready'
  if (!segment.media_id) return 'idle'
  return mediaStates.value[segment.media_id] || 'idle'
}

/** 懒加载媒体：进入视口后再请求，避免一次拉满整屏图片。 */
function observePendingMedia(): void {
  const container = messageListRef.value
  if (!container) return
  if (!mediaObserver) {
    mediaObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          const element = entry.target as HTMLElement
          const mediaId = element.dataset.mediaId
          if (mediaId) void loadMedia(mediaId)
          mediaObserver?.unobserve(element)
        }
      },
      { root: container, rootMargin: '300px 0px' },
    )
  }
  nextTick(() => {
    container.querySelectorAll<HTMLElement>('[data-media-id]').forEach((element) => {
      const mediaId = element.dataset.mediaId
      if (!mediaId || mediaUrls.value[mediaId] || element.dataset.observing === '1') return
      element.dataset.observing = '1'
      mediaObserver?.observe(element)
    })
  })
}

async function loadMedia(mediaId: string): Promise<void> {
  if (!mediaId || mediaUrls.value[mediaId] || mediaStates.value[mediaId] === 'loading') return
  mediaStates.value = { ...mediaStates.value, [mediaId]: 'loading' }
  try {
    const media = await getChatMedia(mediaId)
    mediaUrls.value = { ...mediaUrls.value, [mediaId]: media.data_url }
    const next = { ...mediaStates.value }
    delete next[mediaId]
    mediaStates.value = next
  } catch {
    mediaStates.value = { ...mediaStates.value, [mediaId]: 'error' }
  }
}

function openPreview(url: string, alt: string): void {
  if (url) previewImage.value = { url, alt }
}

function closePreview(): void {
  previewImage.value = null
}

function mediaLabel(segment: ChatMessageSegment): string {
  return t(MEDIA_LABEL_KEYS[segment.type] || 'chat.message.unsupported')
}

/** 跳转到被引用的消息：按上下文加载后高亮并滚动。 */
function jumpToReply(message: ChatMessage): void {
  const reply = message.reply
  if (!reply || !streamClient) return
  if (!reply.found || !reply.message_id) {
    toastStore.show(t('chat.message.replyUnavailable'), 'error')
    return
  }
  highlightedMessageId.value = reply.message_id
  if (highlightTimer !== null) window.clearTimeout(highlightTimer)
  highlightTimer = window.setTimeout(() => {
    highlightedMessageId.value = ''
  }, 2400)
  streamClient.loadAround(reply.message_id, 20, 20)
}

function scrollToMessage(messageId: string): void {
  nextTick(() => {
    document.getElementById(`chat-msg-${messageId}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  })
}

function formatTime(timestamp: number): string {
  if (!timestamp) return '—'
  return new Date(timestamp * 1000).toLocaleString()
}
</script>

<template>
  <AppShell no-padding>
    <div class="chat-view">
      <!-- 顶部栏：模糊背景 + 连接状态 + 流标题 -->
      <header class="chat-top-bar">
        <div class="top-bar-left">
          <!-- 移动端：点击流标题切换流（类似 QQ） -->
          <button class="stream-title-btn mobile-only" @click="toggleMobileStreamMenu">
            <h2 class="stream-title-text">{{ selectedTitle }}</h2>
            <Icon icon="material-symbols:expand-more-rounded" width="20" height="20" class="stream-title-chevron" :class="{ open: isMobileStreamMenuOpen }" />
          </button>
          <!-- 桌面端：只显示标题 -->
          <h2 class="stream-title-text desktop-only">{{ selectedTitle }}</h2>
          <p class="stream-meta">{{ selectedMeta }}</p>
        </div>
        <div class="top-bar-right">
          <span class="connection-pill" :class="connectionTone">
            <span class="connection-dot"></span>
            {{ t(`chat.status.${streamState}`) }}
          </span>
          <button
            v-if="streamState === 'disconnected' && selectedStream"
            class="icon-button connect-btn"
            @click="reconnectStream"
            :title="t('chat.actions.connect')"
          >
            <Icon icon="material-symbols:link-rounded" width="20" height="20" />
          </button>
          <button
            v-if="streamState === 'connected'"
            class="icon-button disconnect-btn"
            @click="disconnectStream"
            :title="t('chat.actions.disconnect')"
          >
            <Icon icon="material-symbols:link-off-rounded" width="20" height="20" />
          </button>
          <button class="icon-button" :disabled="isLoadingStreams" @click="refreshStreams" :title="t('chat.actions.refresh')">
            <Icon icon="material-symbols:refresh-rounded" width="20" height="20" />
          </button>
        </div>
      </header>

      <!-- 移动端流选择弹出层 -->
      <div v-if="isMobileStreamMenuOpen" class="mobile-menu-backdrop" @click="closeMobileStreamMenu"></div>
      <aside class="mobile-stream-menu" :class="{ open: isMobileStreamMenuOpen }" aria-label="chat streams">
        <div class="mobile-menu-header">
          <strong>{{ t('chat.streams.title') }}</strong>
          <button class="icon-button" @click="closeMobileStreamMenu">
            <Icon icon="material-symbols:close-rounded" width="20" height="20" />
          </button>
        </div>
        <div class="stream-list-wrap">
          <input
            v-model="streamsSearchText"
            class="search-input"
            :placeholder="t('chat.streams.search')"
          />
          <div v-if="isLoadingStreams" class="stream-empty">{{ t('chat.actions.loading') }}</div>
          <div v-else-if="filteredGroups.length === 0" class="stream-empty">{{ t('chat.empty.noStreams') }}</div>
          <div v-else class="stream-groups">
            <section v-for="group in filteredGroups" :key="group.platform + group.chat_type" class="stream-group">
              <div class="stream-group-title">
                <strong>{{ group.platform }}</strong>
                <span>{{ chatTypeLabel(group.chat_type) }}</span>
              </div>
              <button
                v-for="stream in group.streams"
                :key="stream.stream_id"
                class="stream-item"
                :class="{ active: selectedStream?.stream_id === stream.stream_id }"
                @click="selectStream(stream)"
              >
                <span class="stream-avatar">
                  <img
                    v-if="showAvatar(avatarKey(stream.platform, stream.peer_user_id), streamAvatar(stream))"
                    :src="streamAvatar(stream)"
                    alt=""
                    loading="lazy"
                    @error="markAvatarFailed(avatarKey(stream.platform, stream.peer_user_id))"
                  />
                  <span v-else>{{ streamInitial(stream) }}</span>
                </span>
                <span class="stream-main">
                  <strong>{{ stream.display_name }}</strong>
                  <em>{{ streamPreview(stream) }}</em>
                </span>
                <small>{{ formatTime(stream.last_active_time) }}</small>
              </button>
            </section>
          </div>
        </div>
      </aside>

      <!-- 主工作区 -->
      <div class="workspace">
        <!-- 桌面端左侧流列表 -->
        <aside class="stream-list-panel">
          <div class="stream-list-wrap">
            <div class="stream-list-heading">
              <span class="eyebrow">{{ t('chat.streams.eyebrow') }}</span>
              <h2>{{ t('chat.streams.title') }}</h2>
              <p>{{ t('chat.streams.desc') }}</p>
            </div>
            <input
              v-model="streamsSearchText"
              class="search-input"
              :placeholder="t('chat.streams.search')"
            />
            <div v-if="isLoadingStreams" class="stream-empty">{{ t('chat.actions.loading') }}</div>
            <div v-else-if="filteredGroups.length === 0" class="stream-empty">{{ t('chat.empty.noStreams') }}</div>
            <div v-else class="stream-groups">
              <section v-for="group in filteredGroups" :key="group.platform + group.chat_type" class="stream-group">
                <div class="stream-group-title">
                  <strong>{{ group.platform }}</strong>
                  <span>{{ chatTypeLabel(group.chat_type) }}</span>
                </div>
                <button
                  v-for="stream in group.streams"
                  :key="stream.stream_id"
                  class="stream-item"
                  :class="{ active: selectedStream?.stream_id === stream.stream_id }"
                  @click="selectStream(stream)"
                >
                  <span class="stream-avatar">
                    <img
                      v-if="showAvatar(avatarKey(stream.platform, stream.peer_user_id), streamAvatar(stream))"
                      :src="streamAvatar(stream)"
                      alt=""
                      loading="lazy"
                      @error="markAvatarFailed(avatarKey(stream.platform, stream.peer_user_id))"
                    />
                    <span v-else>{{ streamInitial(stream) }}</span>
                  </span>
                  <span class="stream-main">
                    <strong>{{ stream.display_name }}</strong>
                    <em>{{ streamPreview(stream) }}</em>
                  </span>
                  <small>{{ formatTime(stream.last_active_time) }}</small>
                </button>
              </section>
            </div>
          </div>
        </aside>

        <!-- 聊天消息面板 -->
        <main class="chat-panel">
          <div v-if="!selectedStream" class="empty-state">
            <Icon icon="material-symbols:forum-outline-rounded" width="48" height="48" />
            <h2>{{ t('chat.empty.selectTitle') }}</h2>
            <p>{{ t('chat.empty.selectHint') }}</p>
          </div>

          <template v-else>
            <div ref="messageListRef" class="message-list">
              <button v-if="hasMoreBefore" class="load-more-button" :disabled="isLoadingMessages" @click="loadOlderMessages">
                {{ isLoadingMessages ? t('chat.actions.loading') : t('chat.actions.loadOlder') }}
              </button>
              <div v-if="isLoadingMessages && messages.length === 0" class="empty-state compact">
                <Icon icon="material-symbols:sync-rounded" width="34" height="34" />
                <p>{{ t('chat.empty.loadingMessages') }}</p>
              </div>
              <div v-else-if="messages.length === 0" class="empty-state compact">
                <Icon icon="material-symbols:chat-bubble-outline-rounded" width="34" height="34" />
                <p>{{ t('chat.empty.noMessages') }}</p>
              </div>
              <article
                v-for="(message, index) in messages"
                :id="`chat-msg-${message.message_id}`"
                :key="message.message_id"
                class="message-row"
                :class="{
                  self: message.is_self,
                  grouped: isGrouped(index),
                  highlight: highlightedMessageId === message.message_id,
                }"
              >
                <span class="message-avatar">
                  <img
                    v-if="showAvatar(avatarKey(message.platform, message.sender_id), messageAvatar(message))"
                    :src="messageAvatar(message)"
                    alt=""
                    loading="lazy"
                    @error="markAvatarFailed(avatarKey(message.platform, message.sender_id))"
                  />
                  <span v-else>{{ message.is_self ? 'B' : initial(senderLabel(message)) }}</span>
                </span>

                <div class="message-bubble">
                  <div v-if="!isGrouped(index)" class="message-meta">
                    <strong>{{ senderLabel(message) }}</strong>
                    <span>{{ formatTime(message.time) }}</span>
                  </div>

                  <button
                    v-if="message.reply"
                    class="reply-block"
                    type="button"
                    :title="t('chat.message.replyJump')"
                    @click="jumpToReply(message)"
                  >
                    <span class="reply-name">{{ replySenderLabel(message.reply) }}</span>
                    <span class="reply-body">
                      <template v-for="(segment, segIndex) in message.reply.segments" :key="segIndex">
                        <span v-if="segment.type === 'text'" class="reply-text">{{ segment.text }}</span>
                        <span v-else-if="segment.type === 'at'" class="reply-at">@{{ segment.text }}</span>
                        <img
                          v-else-if="(segment.type === 'image' || segment.type === 'emoji') && segment.data_url"
                          class="reply-thumb"
                          :src="segment.data_url"
                          :alt="mediaLabel(segment)"
                        />
                        <span v-else class="reply-media">{{ mediaLabel(segment) }}</span>
                      </template>
                      <span v-if="!message.reply.segments.length" class="reply-text">
                        {{ message.reply.preview || t('chat.message.replyUnavailable') }}
                      </span>
                    </span>
                  </button>

                  <div class="message-body">
                    <template v-for="(segment, segIndex) in message.segments" :key="segIndex">
                      <span v-if="segment.type === 'text'" class="segment-text">{{ segment.text }}</span>
                      <span v-else-if="segment.type === 'at'" class="segment-at">@{{ segment.text }}</span>

                      <template v-else-if="segment.type === 'image' || segment.type === 'emoji'">
                        <figure
                          v-if="segmentSrc(segment)"
                          class="segment-media"
                          :class="{ emoji: segment.type === 'emoji' }"
                        >
                          <img
                            :src="segmentSrc(segment)"
                            :alt="segment.text || mediaLabel(segment)"
                            loading="lazy"
                            @click="openPreview(segmentSrc(segment), segment.text || mediaLabel(segment))"
                          />
                        </figure>
                        <span v-else class="media-placeholder" :data-media-id="segment.media_id || undefined">
                          <Icon
                            :icon="segmentState(segment) === 'error'
                              ? 'material-symbols:broken-image-outline-rounded'
                              : 'material-symbols:image-outline-rounded'"
                            width="18"
                            height="18"
                          />
                          {{ segmentState(segment) === 'error'
                            ? t('chat.message.mediaFailed')
                            : t('chat.message.mediaLoading') }}
                        </span>
                      </template>

                      <audio
                        v-else-if="segment.type === 'voice' && segmentSrc(segment)"
                        class="message-audio"
                        :src="segmentSrc(segment)"
                        controls
                        preload="metadata"
                      ></audio>
                      <span
                        v-else-if="segment.type === 'voice'"
                        class="media-placeholder"
                        :data-media-id="segment.media_id || undefined"
                      >
                        <Icon icon="material-symbols:graphic-eq-rounded" width="18" height="18" />
                        {{ segmentState(segment) === 'error'
                          ? t('chat.message.mediaFailed')
                          : t('chat.message.mediaLoading') }}
                      </span>

                      <span v-else class="media-chip">
                        <Icon
                          :icon="segment.type === 'video'
                            ? 'material-symbols:movie-outline-rounded'
                            : 'material-symbols:description-outline-rounded'"
                          width="17"
                          height="17"
                        />
                        {{ mediaLabel(segment) }}<template v-if="segment.text"> · {{ segment.text }}</template>
                      </span>
                    </template>

                    <span v-if="!message.segments.length" class="segment-text">{{ messageContent(message) }}</span>
                  </div>
                </div>
              </article>
            </div>

            <form class="composer" @submit.prevent="sendMessage">
              <textarea
                v-model="composerText"
                :placeholder="t('chat.composer.placeholder')"
                rows="2"
                @keydown="handleComposerKeydown"
              ></textarea>
              <button class="send-button" :disabled="!canSend" type="submit">
                <Icon icon="material-symbols:send-rounded" width="20" height="20" />
                {{ t('chat.actions.send') }}
              </button>
            </form>
          </template>
        </main>
      </div>
    </div>

    <!-- 图片预览 -->
    <Teleport to="body">
      <div v-if="previewImage" class="image-preview" @click.self="closePreview">
        <button class="preview-close" type="button" :title="t('chat.message.closePreview')" @click="closePreview">
          <Icon icon="material-symbols:close-rounded" width="24" height="24" />
        </button>
        <img :src="previewImage.url" :alt="previewImage.alt" />
      </div>
    </Teleport>
  </AppShell>
</template>

<style scoped>
.chat-view {
  height: calc(100dvh - var(--app-top-bar-height, 64px) - var(--app-bottom-nav-height, 0px));
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: transparent;
}

/* ====== 顶部栏：模糊背景 ====== */
.chat-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 12px 20px;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  flex-shrink: 0;
  z-index: 10;
}

.top-bar-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stream-title-btn {
  display: none;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: inherit;
  font: inherit;
  text-align: left;
}

.stream-title-text {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--md-sys-color-on-surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stream-title-chevron {
  color: var(--md-sys-color-on-surface-variant);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.stream-title-chevron.open {
  transform: rotate(180deg);
}

.stream-meta {
  margin: 0;
  font-size: 0.78rem;
  color: var(--md-sys-color-on-surface-variant);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.connection-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.72rem;
  font-weight: 700;
  white-space: nowrap;
}

.connection-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.connection-pill.connected {
  color: #1aae39;
  background: color-mix(in srgb, #1aae39 13%, transparent);
}

.connection-pill.connected .connection-dot {
  background: #1aae39;
}

.connection-pill.connecting {
  color: #dd5b00;
  background: color-mix(in srgb, #dd5b00 13%, transparent);
}

.connection-pill.connecting .connection-dot {
  background: #dd5b00;
}

.connection-pill.disconnected {
  color: var(--md-sys-color-error);
  background: var(--md-sys-color-error-container);
}

.connection-pill.disconnected .connection-dot {
  background: var(--md-sys-color-error);
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 999px;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
  cursor: pointer;
  transition: background 0.15s;
}

.icon-button:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.icon-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* ====== 主工作区 ====== */
.workspace {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
  overflow: hidden;
}

/* ====== 左侧流列表面板 ====== */
.stream-list-panel {
  border-right: 1px solid var(--md-sys-color-outline-variant);
  padding: 1rem;
  overflow-y: auto;
  background: color-mix(in srgb, var(--md-sys-color-surface) 75%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.stream-list-wrap,
.stream-list-heading,
.stream-groups,
.stream-group {
  display: flex;
  flex-direction: column;
}

.stream-list-wrap {
  gap: 0.9rem;
}

.stream-list-heading {
  gap: 0.25rem;
}

.eyebrow {
  color: var(--md-sys-color-primary);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.stream-list-heading h2 {
  margin: 0;
  font-size: 1.4rem;
  letter-spacing: -0.03em;
  color: var(--md-sys-color-on-surface);
}

.stream-list-heading p {
  margin: 0;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.82rem;
}

.search-input {
  width: 100%;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 14px;
  background: var(--md-sys-color-surface-container-lowest);
  color: var(--md-sys-color-on-surface);
  padding: 0.7rem 0.9rem;
  outline: none;
  font: inherit;
  font-size: 0.88rem;
}

.stream-groups {
  gap: 0.9rem;
}

.stream-group {
  gap: 0.4rem;
}

.stream-group-title {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.75rem;
  text-transform: uppercase;
  font-weight: 600;
}

.stream-item {
  width: 100%;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 0.7rem;
  text-align: left;
  border: 1px solid transparent;
  border-radius: 16px;
  background: transparent;
  color: var(--md-sys-color-on-surface);
  padding: 0.7rem;
  cursor: pointer;
  font: inherit;
  transition: background 0.15s, border-color 0.15s;
}

.stream-item:hover,
.stream-item.active {
  background: var(--md-sys-color-secondary-container);
  border-color: var(--md-sys-color-outline-variant);
}

.stream-avatar {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  font-weight: 900;
  font-size: 0.9rem;
}

.stream-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.stream-main strong,
.stream-main em,
.stream-item small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stream-main strong {
  font-size: 0.88rem;
}

.stream-main em,
.stream-item small,
.stream-empty {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.78rem;
  font-style: normal;
}

.stream-item small {
  grid-column: 2;
}

/* ====== 聊天面板 ====== */
.chat-panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 72%, transparent);
}

.message-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem 1.25rem;
  overflow-y: auto;
}

.load-more-button {
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  border: 0;
  border-radius: 999px;
  font-weight: 700;
  cursor: pointer;
  padding: 0.6rem 1rem;
  color: var(--md-sys-color-on-primary-container);
  background: var(--md-sys-color-primary-container);
  font-size: 0.82rem;
}

.load-more-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.message-row {
  width: min(100%, 780px);
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: end;
  gap: 0.6rem;
}

.message-row.self {
  margin-left: auto;
  grid-template-columns: minmax(0, 1fr) 34px;
}

.message-row.self .message-avatar {
  order: 2;
}

.message-avatar {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 50%;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  font-size: 0.78rem;
  font-weight: 800;
  user-select: none;
}

.message-row.self .message-avatar {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.message-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 连续消息不重复显示头像与昵称，只留出对齐空间 */
.message-row.grouped .message-avatar {
  visibility: hidden;
}

.message-bubble {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.6rem 0.85rem;
  border-radius: 16px 16px 16px 6px;
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline-variant);
}

.message-row.self .message-bubble {
  border-radius: 16px 16px 6px 16px;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.message-row.highlight .message-bubble {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--md-sys-color-primary) 45%, transparent);
}

.message-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.73rem;
}

.message-row.self .message-meta {
  color: color-mix(in srgb, var(--md-sys-color-on-primary-container) 70%, transparent);
}

/* ====== 引用卡片 ====== */
.reply-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  padding: 0.35rem 0.6rem;
  border: 0;
  border-left: 3px solid var(--md-sys-color-primary);
  border-radius: 8px;
  background: var(--md-sys-color-surface-container-high);
  color: inherit;
  font: inherit;
  font-size: 0.78rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}

.reply-block:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.message-row.self .reply-block {
  background: color-mix(in srgb, var(--md-sys-color-surface) 40%, transparent);
}

.reply-name {
  color: var(--md-sys-color-primary);
  font-size: 0.74rem;
  font-weight: 700;
}

.message-row.self .reply-name {
  color: var(--md-sys-color-on-primary-container);
}

.reply-body {
  display: block;
  overflow: hidden;
  color: var(--md-sys-color-on-surface-variant);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reply-at {
  color: var(--md-sys-color-primary);
  font-weight: 600;
}

.reply-media {
  opacity: 0.85;
}

.reply-thumb {
  display: inline-block;
  width: 30px;
  height: 30px;
  margin: 0 3px;
  border-radius: 5px;
  object-fit: cover;
  vertical-align: middle;
}

/* ====== 正文片段 ====== */
.message-body {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 6px;
}

.segment-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.55;
  font-size: 0.9rem;
}

.segment-at {
  padding: 0 0.3rem;
  border-radius: 6px;
  color: var(--md-sys-color-primary);
  background: color-mix(in srgb, var(--md-sys-color-primary) 14%, transparent);
  font-size: 0.86rem;
  font-weight: 700;
}

.message-row.self .segment-at {
  color: var(--md-sys-color-on-primary-container);
  background: color-mix(in srgb, var(--md-sys-color-on-primary-container) 14%, transparent);
}

.segment-media {
  margin: 0;
}

.segment-media img {
  display: block;
  max-width: min(100%, 360px);
  max-height: 380px;
  width: auto;
  border-radius: 12px;
  border: 1px solid var(--md-sys-color-outline-variant);
  background: var(--md-sys-color-surface-container-lowest);
  object-fit: contain;
  cursor: zoom-in;
}

.segment-media.emoji img {
  max-width: 132px;
  max-height: 132px;
  border: 0;
  background: transparent;
}

.media-placeholder,
.media-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 0.3rem 0.65rem;
  border-radius: 10px;
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.78rem;
}

.media-placeholder {
  min-width: 104px;
}

.message-row.self .media-placeholder,
.message-row.self .media-chip {
  background: color-mix(in srgb, var(--md-sys-color-surface) 55%, transparent);
}

.message-audio {
  width: min(100%, 320px);
  max-width: 100%;
}

/* ====== 图片预览 ====== */
.image-preview {
  position: fixed;
  inset: 0;
  z-index: 9500;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.72);
}

.image-preview img {
  max-width: 100%;
  max-height: 92dvh;
  border-radius: 12px;
  object-fit: contain;
}

.preview-close {
  position: absolute;
  top: calc(1rem + env(safe-area-inset-top));
  right: 1rem;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 50%;
  color: #ffffff;
  background: rgba(255, 255, 255, 0.16);
  cursor: pointer;
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem;
  padding: 0.85rem 1.25rem;
  border-top: 1px solid var(--md-sys-color-outline-variant);
  background: color-mix(in srgb, var(--md-sys-color-surface) 85%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.composer textarea {
  width: 100%;
  resize: vertical;
  max-height: 160px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 16px;
  background: var(--md-sys-color-surface-container-lowest);
  color: var(--md-sys-color-on-surface);
  padding: 0.7rem 1rem;
  outline: none;
  font: inherit;
  font-size: 0.88rem;
}

.send-button {
  align-self: end;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.7rem 1rem;
  border: 0;
  border-radius: 999px;
  font-weight: 700;
  cursor: pointer;
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  font-size: 0.85rem;
}

.send-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.empty-state {
  flex: 1;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  padding: 1.5rem;
  color: var(--md-sys-color-on-surface-variant);
  text-align: center;
}

.empty-state.compact {
  min-height: 180px;
}

.empty-state h2 {
  margin: 0;
  color: var(--md-sys-color-on-surface);
  font-size: 1.2rem;
}

.empty-state p {
  margin: 0;
}

/* ====== 移动端：流选择菜单 ====== */
.mobile-stream-menu,
.mobile-menu-backdrop {
  display: none;
}

.mobile-menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.mobile-menu-header strong {
  font-size: 1rem;
}

/* 桌面端显示/隐藏控制 */
.mobile-only {
  display: none;
}

.desktop-only {
  display: block;
}

/* ====== 响应式：移动端 ====== */
@media (max-width: 899px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .stream-list-panel {
    display: none;
  }

  .desktop-only {
    display: none;
  }

  .mobile-only {
    display: flex;
  }

  .stream-title-btn {
    display: flex;
  }

  .chat-top-bar {
    padding: 10px 16px;
  }

  .stream-title-text {
    font-size: 1rem;
  }

  .message-list {
    gap: 0.5rem;
    padding: 0.7rem 0.65rem;
  }

  /* 手机上留出更多横向空间，气泡随内容收缩 */
  .message-row {
    width: 100%;
    grid-template-columns: 30px minmax(0, 1fr);
    gap: 0.45rem;
  }

  .message-row.self {
    grid-template-columns: minmax(0, 1fr) 30px;
  }

  .message-avatar {
    width: 30px;
    height: 30px;
    font-size: 0.72rem;
  }

  .message-bubble {
    padding: 0.5rem 0.7rem;
  }

  .segment-text {
    font-size: 0.88rem;
  }

  .segment-media img {
    max-height: 300px;
  }

  .image-preview {
    padding: 0.75rem;
  }

  .image-preview img {
    max-height: 82dvh;
  }

  .composer {
    grid-template-columns: 1fr;
    padding: 0.75rem;
  }

  .send-button {
    width: 100%;
  }

  /* 移动端流选择弹出层 */
  .mobile-menu-backdrop {
    position: fixed;
    inset: 0;
    z-index: 70;
    display: block;
    background: rgba(0, 0, 0, 0.32);
    animation: fade-in 0.15s ease;
  }

  .mobile-stream-menu {
    position: fixed;
    left: 0.75rem;
    right: 0.75rem;
    top: 4.5rem;
    z-index: 80;
    display: block;
    max-height: min(76vh, 620px);
    overflow: auto;
    padding: 1rem;
    border-radius: 20px;
    background: var(--md-sys-color-surface);
    border: 1px solid var(--md-sys-color-outline-variant);
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.12),
      0 2px 8px rgba(0, 0, 0, 0.08);
    transform: translateY(-12px) scale(0.98);
    opacity: 0;
    pointer-events: none;
    transition: transform 0.18s ease, opacity 0.18s ease;
  }

  .mobile-stream-menu.open {
    transform: translateY(0) scale(1);
    opacity: 1;
    pointer-events: auto;
  }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
