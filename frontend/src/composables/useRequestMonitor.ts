/** Serial polling and stale-response protection for the native request monitor. */
import { computed, onMounted, onUnmounted, ref, shallowRef } from 'vue'
import {
  listInspectorRecords,
  getInspectorRecord,
  clearInspectorRecords,
} from '../api/modules/request-inspector'
import type {
  InspectorRecordsSnapshot,
  InspectorRecordDetail,
  InspectorStatus,
} from '../api/types/request-inspector'

export interface MonitorPorts {
  list: typeof listInspectorRecords
  detail: typeof getInspectorRecord
  clear: typeof clearInspectorRecords
  setTimer: (callback: () => void, ms: number) => ReturnType<typeof setTimeout>
  clearTimer: (timer: ReturnType<typeof setTimeout>) => void
  now: () => number
}
const defaults: MonitorPorts = {
  list: listInspectorRecords,
  detail: getInspectorRecord,
  clear: clearInspectorRecords,
  setTimer: (fn, ms) => setTimeout(fn, ms),
  clearTimer: (timer) => clearTimeout(timer),
  now: Date.now,
}
const cancelled = (error: unknown) => {
  const e = error as { name?: string; code?: string }
  return (
    e?.name === 'AbortError' ||
    e?.name === 'CanceledError' ||
    e?.code === 'ERR_CANCELED'
  )
}

/** Factory separated from Vue lifecycle so races and timers can be tested deterministically. */
export function createRequestMonitor(ports: MonitorPorts = defaults) {
  const snapshot = shallowRef<InspectorRecordsSnapshot | null>(null)
  const detail = shallowRef<InspectorRecordDetail | null>(null)
  const selectedId = ref<number | null>(null)
  const search = ref('')
  const status = ref<InspectorStatus | ''>('')
  const model = ref('')
  const userPaused = ref(false)
  const failed = ref(false)
  const refreshing = ref(false)
  const detailLoading = ref(false)
  const clearing = ref(false)
  const lastUpdated = ref<number | null>(null)
  const notice = ref<'restarted' | 'removed' | 'clearUncertain' | ''>('')
  const authFailed = ref(false)
  const failureMessage = ref('')
  let timer: ReturnType<typeof setTimeout> | null = null
  let listController: AbortController | null = null
  let detailController: AbortController | null = null
  let clearController: AbortController | null = null
  let job: Promise<void> | null = null
  let generation = 0
  let selectionGeneration = 0
  let clearGeneration = 0
  let disposed = false
  let visible = true
  let started = false
  let autoSelected = false
  const paused = computed(() => userPaused.value || failed.value)
  const models = computed(() =>
    [...new Set(snapshot.value?.records.map((r) => r.model) ?? [])].sort(),
  )
  const records = computed(() => {
    const keyword = search.value.trim().toLowerCase()
    return (snapshot.value?.records ?? [])
      .filter(
        (r) =>
          (!status.value || r.status === status.value) &&
          (!model.value || r.model === model.value) &&
          (!keyword ||
            [
              r.id,
              r.model,
              r.api_name,
              r.api_provider,
              r.request_name,
              r.logical_request_id,
            ]
              .join(' ')
              .toLowerCase()
              .includes(keyword)),
      )
      .slice()
      .sort((a, b) => b.id - a.id)
  })
  function stopTimer() {
    if (timer !== null) ports.clearTimer(timer)
    timer = null
  }
  function schedule() {
    stopTimer()
    if (started && !disposed && visible && !paused.value && !clearing.value) {
      timer = ports.setTimer(() => {
        timer = null
        void refresh()
      }, 2000)
    }
  }
  function invalidateSelection(reason: 'restarted' | 'removed' | '' = '') {
    selectionGeneration++
    detailController?.abort()
    detailController = null
    detailLoading.value = false
    selectedId.value = null
    detail.value = null
    notice.value = reason
  }
  function cancelReads() {
    generation++
    selectionGeneration++
    listController?.abort()
    detailController?.abort()
    listController = detailController = null
    job = null
    refreshing.value = detailLoading.value = false
    stopTimer()
  }
  function reportFailure(error: unknown) {
    if (cancelled(error)) return
    // The shared Axios interceptor owns the single global Toast.
    const response = (error as { response?: { status?: number; data?: { message?: unknown } } })?.response
    authFailed.value = response?.status === 401 || response?.status === 403
    failureMessage.value = typeof response?.data?.message === 'string' ? response.data.message : ''
    failed.value = true
    stopTimer()
  }
  async function selectRecord(id: number): Promise<void> {
    if (disposed || clearing.value) return
    const seq = ++selectionGeneration
    const epoch = generation
    const instanceId = snapshot.value?.instance_id
    detailController?.abort()
    const controller = new AbortController()
    detailController = controller
    selectedId.value = id
    if (detail.value?.id !== id) detail.value = null
    detailLoading.value = true
    notice.value = ''
    try {
      const next = await ports.detail(id, controller.signal)
      if (
        disposed ||
        controller.signal.aborted ||
        seq !== selectionGeneration ||
        epoch !== generation
      )
        return
      if (
        next.instance_id !== instanceId ||
        snapshot.value?.instance_id !== instanceId
      ) {
        invalidateSelection('restarted')
        return
      }
      const minimumVersion = Math.max(
        snapshot.value?.records.find(r => r.id === id)?.version ?? 0,
        detail.value?.id === id ? detail.value.version : 0,
      )
      if (next.id !== id || next.version < minimumVersion) return
      detail.value = next
    } catch (error) {
      if (
        disposed ||
        controller.signal.aborted ||
        seq !== selectionGeneration ||
        epoch !== generation
      )
        return
      if (
        (error as { response?: { status?: number } })?.response?.status === 404
      )
        invalidateSelection('removed')
      else reportFailure(error)
    } finally {
      if (seq === selectionGeneration && !disposed) {
        detailLoading.value = false
        detailController = null
      }
    }
  }
  async function performRefresh(): Promise<void> {
    const epoch = generation
    const controller = new AbortController()
    listController = controller
    refreshing.value = true
    try {
      const next = await ports.list(controller.signal)
      if (disposed || controller.signal.aborted || epoch !== generation) return
      if (snapshot.value && snapshot.value.instance_id !== next.instance_id) {
        invalidateSelection('restarted')
        autoSelected = true
      }
      if (snapshot.value?.instance_id === next.instance_id && next.revision < snapshot.value.revision) return
      snapshot.value = next
      if (notice.value === 'clearUncertain') notice.value = ''
      lastUpdated.value = ports.now()
      const selected = next.records.find((r) => r.id === selectedId.value)
      if (selectedId.value !== null && !selected) invalidateSelection('removed')
      if (
        selected &&
        !detailLoading.value &&
        ((detail.value?.version ?? -1) < selected.version ||
          detail.value?.instance_id !== next.instance_id)
      ) {
        await selectRecord(selected.id)
      } else if (
        selectedId.value === null &&
        !autoSelected &&
        next.records.length
      ) {
        autoSelected = true
        await selectRecord(Math.max(...next.records.map((r) => r.id)))
      }
    } catch (error) {
      if (!disposed && !controller.signal.aborted && epoch === generation)
        reportFailure(error)
    } finally {
      if (!disposed && epoch === generation) refreshing.value = false
      if (listController === controller) listController = null
    }
  }
  function refresh(): Promise<void> {
    if (disposed || clearing.value) return Promise.resolve()
    if (job) return job
    stopTimer()
    const epoch = generation
    const running = performRefresh().finally(() => {
      // An aborted request may resolve after a new refresh has already started.
      if (job !== running || epoch !== generation) return
      job = null
      schedule()
    })
    job = running
    return running
  }
  function refreshNow(): Promise<void> {
    failed.value = false
    return refresh()
  }
  function pause() {
    userPaused.value = true
    cancelReads()
  }
  function resume() {
    userPaused.value = false
    failed.value = false
    return refresh()
  }
  function setVisible(value: boolean) {
    visible = value
    stopTimer()
    if (!value) cancelReads()
    else if (!paused.value) void refresh()
  }
  async function clear(): Promise<void> {
    if (disposed || clearing.value) return
    clearing.value = true
    stopTimer()
    cancelReads()
    const epoch = ++clearGeneration
    const controller = new AbortController()
    clearController = controller
    try {
      const result = await ports.clear(controller.signal)
      if (disposed || epoch !== clearGeneration) return
      invalidateSelection()
      failed.value = false
      snapshot.value = {
        ...result,
        capacity: snapshot.value?.capacity ?? 200,
        records: [],
        stats: { total: 0, by_status: {}, tokens_in: 0, tokens_out: 0 },
      }
      lastUpdated.value = ports.now()
      autoSelected = true
    } catch (error) {
      if (!disposed && !controller.signal.aborted) {
        reportFailure(error)
        notice.value = 'clearUncertain'
      }
      throw error
    } finally {
      clearController = null
      if (!disposed) {
        clearing.value = false
        schedule()
      }
    }
  }
  function start(isVisible = true) {
    started = true
    visible = isVisible
    if (visible) void refresh()
  }
  function dispose() {
    disposed = true
    clearGeneration++
    generation++
    selectionGeneration++
    stopTimer()
    listController?.abort()
    detailController?.abort()
    clearController?.abort()
  }
  return {
    snapshot,
    detail,
    selectedId,
    search,
    status,
    model,
    records,
    models,
    paused,
    failed,
    authFailed,
    failureMessage,
    refreshing,
    detailLoading,
    clearing,
    lastUpdated,
    notice,
    selectRecord,
    refreshNow,
    pause,
    resume,
    setVisible,
    clear,
    start,
    dispose,
  }
}

/** Bind the testable monitor to page visibility and component lifetime. */
export function useRequestMonitor() {
  const monitor = createRequestMonitor()
  const onVisibility = () => monitor.setVisible(!document.hidden)
  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibility)
    monitor.start(!document.hidden)
  })
  onUnmounted(() => {
    document.removeEventListener('visibilitychange', onVisibility)
    monitor.dispose()
  })
  return monitor
}
