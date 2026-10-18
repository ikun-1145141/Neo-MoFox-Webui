/** Real Vue state and real API source, fake transport/timers; no test framework dependency. */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
function compile(path, globals, names) {
  let source = readFileSync(new URL(path, import.meta.url), 'utf8')
  const parsed = ts.createSourceFile(
    path,
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS,
  )
  for (const node of [...parsed.statements].reverse())
    if (ts.isImportDeclaration(node))
      source = source.slice(0, node.getFullStart()) + source.slice(node.end)
  source = source.replace(/export /g, '')
  const js = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  globals = Object.fromEntries(
    Object.entries(globals).filter(([key]) => /^[a-zA-Z_$][\w$]*$/.test(key)),
  )
  return new Function(...Object.keys(globals), js + `;return {${names}}`)(
    ...Object.values(globals),
  )
}
const { createRequestMonitor } = compile(
  '../src/composables/useRequestMonitor.ts',
  {
    ...vue,
    listInspectorRecords() {},
    getInspectorRecord() {},
    clearInspectorRecords() {},
  },
  'createRequestMonitor',
)
const defer = () => {
  let resolve, reject
  const promise = new Promise((a, b) => {
    resolve = a
    reject = b
  })
  return { promise, resolve, reject }
}
const row = (id, version = 1, extra = {}) => ({
  id,
  version,
  model: 'demo',
  api_name: 'responses.create',
  api_provider: 'local',
  request_name: 'chat',
  logical_request_id: 'trace',
  status: 'succeeded',
  ts: 1,
  ...extra,
})
const snap = (records = [row(1)], instance_id = 'host-a') => ({
  instance_id,
  revision: 1,
  capacity: 200,
  records,
  stats: { total: records.length, by_status: {}, tokens_in: 0, tokens_out: 0 },
})
const detail = (id, version = 1, instance_id = 'host-a') => ({
  ...row(id, version),
  instance_id,
  params: {},
  raw_events: [],
  capture_info: { redacted: true, raw_truncated: true },
})
function setup(overrides = {}) {
  const timers = new Map(),
    calls = { list: 0, detail: [] }
  let timerId = 0
  const ports = {
    list: async () => {
      calls.list++
      return snap()
    },
    detail: async (id) => {
      calls.detail.push(id)
      return detail(id)
    },
    clear: async () => ({
      instance_id: 'host-a',
      revision: 2,
      cleared_count: 1,
    }),
    now: () => 1000,
    setTimer: (fn, ms) => {
      assert.equal(ms, 2000)
      timers.set(++timerId, fn)
      return timerId
    },
    clearTimer: (id) => timers.delete(id),
    ...overrides,
  }
  return { m: createRequestMonitor(ports), timers, calls }
}
test('select newest, filter locally, reload detail only when version changes', async () => {
  let current = snap([row(1), row(2, 1, { model: 'other', status: 'failed' })])
  const { m, calls } = setup({ list: async () => current })
  await m.refreshNow()
  assert.equal(m.selectedId.value, 2)
  assert.deepEqual(calls.detail, [2])
  await m.refreshNow()
  assert.deepEqual(calls.detail, [2])
  current = snap([row(1), row(2, 2, { model: 'other', status: 'failed' })])
  await m.refreshNow()
  assert.deepEqual(calls.detail, [2, 2])
  m.status.value = 'failed'
  assert.equal(m.records.value.length, 1)
  m.model.value = 'demo'
  assert.equal(m.records.value.length, 0)
  m.model.value = ''
  m.status.value = ''
  m.search.value = 'trace'
  assert.equal(m.records.value.length, 2)
  m.search.value = 'missing'
  assert.equal(m.records.value.length, 0)
  m.dispose()
})
test('rapid selection ignores late responses even when transport ignores cancellation', async () => {
  const older = defer(),
    newer = defer()
  const { m } = setup({
    list: async () => snap([]),
    detail: (id) => (id === 2 ? older.promise : newer.promise),
  })
  await m.refreshNow()
  const a = m.selectRecord(2),
    b = m.selectRecord(3)
  newer.resolve(detail(3))
  await b
  older.resolve(detail(2))
  await a
  assert.equal(m.detail.value.id, 3)
  assert.equal(m.detailLoading.value, false)
  m.dispose()
})
test('serial polling coalesces refresh and only schedules after request completion', async () => {
  const pending = defer()
  let count = 0
  const { m, timers } = setup({
    list: () => {
      count++
      return pending.promise
    },
  })
  m.start()
  const a = m.refreshNow(),
    b = m.refreshNow()
  assert.equal(a, b)
  assert.equal(count, 1)
  assert.equal(timers.size, 0)
  pending.resolve(snap([]))
  await a
  assert.equal(timers.size, 1)
  m.pause()
  assert.equal(timers.size, 0)
  m.dispose()
})
test('page visibility pauses polling and becoming visible immediately syncs', async () => {
  const { m, timers, calls } = setup()
  m.start()
  await m.refreshNow()
  assert.equal(timers.size, 1)
  m.setVisible(false)
  assert.equal(timers.size, 0)
  const before = calls.list
  m.setVisible(true)
  await m.refreshNow()
  assert.equal(calls.list, before + 1)
  m.pause()
  m.setVisible(false)
  m.setVisible(true)
  assert.equal(timers.size, 0)
  m.dispose()
})
test('refresh failure retains data, stops polling, and requires explicit recovery', async () => {
  let fail = false
  const { m, timers } = setup({
    list: async () => {
      if (fail) throw new Error('offline')
      return snap()
    },
  })
  m.start()
  await m.refreshNow()
  const previous = m.snapshot.value
  fail = true
  await m.refreshNow()
  assert.equal(m.snapshot.value, previous)
  assert.equal(m.failed.value, true)
  assert.equal(m.paused.value, true)
  assert.equal(timers.size, 0)
  fail = false
  await m.resume()
  assert.equal(m.failed.value, false)
  assert.equal(timers.size, 1)
  m.dispose()
})
test('clearing invalidates pending list responses and cannot resurrect records', async () => {
  const pending = defer()
  let delayed = false
  const { m } = setup({
    list: () => (delayed ? pending.promise : Promise.resolve(snap())),
  })
  await m.refreshNow()
  delayed = true
  const poll = m.refreshNow()
  await m.clear()
  pending.resolve(snap([row(1), row(2)]))
  await poll
  assert.equal(m.snapshot.value.records.length, 0)
  assert.equal(m.selectedId.value, null)
  assert.equal(m.detail.value, null)
  m.dispose()
})
test('restart invalidates reused IDs; eviction removes stale selection', async () => {
  let current = snap()
  const { m } = setup({ list: async () => current })
  await m.refreshNow()
  current = snap([row(1)], 'host-b')
  await m.refreshNow()
  assert.equal(m.detail.value, null)
  assert.equal(m.notice.value, 'restarted')
  current = snap([row(2)])
  await m.refreshNow()
  await m.selectRecord(2)
  current = snap([])
  await m.refreshNow()
  assert.equal(m.detail.value, null)
  assert.equal(m.notice.value, 'removed')
  m.dispose()
})
test('restart between list and detail is rejected; expected 404 clears without polling failure', async () => {
  const { m } = setup({ detail: async (id) => detail(id, 1, 'host-b') })
  await m.refreshNow()
  assert.equal(m.detail.value, null)
  assert.equal(m.notice.value, 'restarted')
  m.dispose()
  const { m: n } = setup({
    detail: async () => {
      throw { response: { status: 404 } }
    },
  })
  await n.refreshNow()
  assert.equal(n.notice.value, 'removed')
  assert.equal(n.failed.value, false)
  n.dispose()
})
test('dispose aborts pending work and discards late completions', async () => {
  const pending = defer()
  let signal
  const { m, timers } = setup({
    list: (s) => {
      signal = s
      return pending.promise
    },
  })
  m.start()
  const job = m.refreshNow()
  m.dispose()
  assert.equal(signal.aborted, true)
  pending.resolve(snap())
  await job
  assert.equal(m.snapshot.value, null)
  assert.equal(timers.size, 0)
})
test('only new records endpoints are used, with AbortSignal forwarded', async () => {
  const calls = [],
    instance = Object.fromEntries(
      ['get', 'delete'].map((method) => [
        method,
        (...args) => {
          calls.push([method, ...args])
          return Promise.resolve({})
        },
      ]),
    )
  const api = compile(
    '../src/api/modules/request-inspector.ts',
    { instance, API_WEBUI_PREFIX: '/webui/api' },
    'listInspectorRecords,getInspectorRecord,clearInspectorRecords',
  )
  const { signal } = new AbortController()
  await api.listInspectorRecords(signal)
  await api.getInspectorRecord(42, signal)
  await api.clearInspectorRecords(signal)
  assert.deepEqual(
    calls.map((c) => c.slice(0, 2)),
    [
      ['get', '/webui/api/request-inspector/records'],
      ['get', '/webui/api/request-inspector/records/42'],
      ['delete', '/webui/api/request-inspector/records'],
    ],
  )
  assert.ok(calls.every((c) => c[2].signal === signal))
})
test('content never uses v-html and JSON export preserves capture integrity markers', () => {
  for (const name of [
    'InspectorMessages',
    'InspectorTools',
    'InspectorResponse',
    'InspectorRecordDetail',
  ])
    assert.ok(
      !readFileSync(
        new URL(
          `../src/components/request-monitor/${name}.vue`,
          import.meta.url,
        ),
        'utf8',
      ).includes('v-html'),
    )
  const exported = JSON.parse(JSON.stringify(detail(1)))
  assert.equal(exported.capture_info.redacted, true)
  assert.equal(exported.capture_info.raw_truncated, true)
})


test('pause aborts active reads, rejects late data, and manual refresh stays paused', async () => {
  const pending = defer()
  let delayed = false, signal
  const { m, timers } = setup({ list: (s) => { signal = s; return delayed ? pending.promise : Promise.resolve(snap()) } })
  m.start(); await m.refreshNow()
  delayed = true
  const old = m.refreshNow()
  m.pause()
  assert.equal(signal.aborted, true)
  delayed = false
  await m.refreshNow()
  pending.resolve(snap([row(99)])); await old
  assert.equal(m.snapshot.value.records[0].id, 1)
  assert.equal(m.paused.value, true)
  assert.equal(timers.size, 0)
  m.dispose()
})

test('hidden page aborts reads and stale finally cannot detach the resumed refresh', async () => {
  const first = defer(), second = defer()
  let calls = 0
  const { m, timers } = setup({ list: () => ++calls === 1 ? first.promise : second.promise })
  m.start(); const old = m.refreshNow()
  m.setVisible(false); m.setVisible(true)
  const current = m.refreshNow()
  first.resolve(snap([row(99)])); await old
  assert.equal(m.refreshNow(), current)
  assert.equal(timers.size, 0)
  second.resolve(snap([])); await current
  assert.equal(m.snapshot.value.records.length, 0)
  assert.equal(timers.size, 1)
  m.dispose()
})

test('clear failure retains selection and detail, marks uncertain state and pauses', async () => {
  const { m, timers } = setup({ clear: async () => { throw new Error('timeout') } })
  m.start(); await m.refreshNow()
  const old = m.detail.value
  await assert.rejects(m.clear())
  assert.equal(m.detail.value, old)
  assert.equal(m.selectedId.value, 1)
  assert.equal(m.snapshot.value.records.length, 1)
  assert.equal(m.notice.value, 'clearUncertain')
  assert.equal(m.paused.value, true)
  assert.equal(timers.size, 0)
  await m.refreshNow()
  assert.equal(m.notice.value, '')
  m.dispose()
})

test('hiding or pausing while DELETE is pending does not discard successful clearing', async () => {
  const pending = defer()
  const { m } = setup({ clear: () => pending.promise })
  await m.refreshNow()
  const clearing = m.clear()
  m.setVisible(false); m.pause()
  pending.resolve({ instance_id: 'host-a', revision: 8, cleared_count: 1 })
  await clearing
  assert.equal(m.snapshot.value.revision, 8)
  assert.equal(m.detail.value, null)
  assert.equal(m.selectedId.value, null)
  assert.equal(m.paused.value, true)
  m.dispose()
})

test('old detail versions and mismatched IDs cannot replace a newer detail', async () => {
  let next = detail(1, 5)
  const { m } = setup({ detail: async () => next })
  await m.refreshNow()
  next = detail(1, 2); await m.selectRecord(1)
  assert.equal(m.detail.value.version, 5)
  next = detail(9, 9); await m.selectRecord(1)
  assert.equal(m.detail.value.id, 1)
  await m.refreshNow()
  assert.equal(m.detail.value.version, 5)
  m.dispose()
})

test('older revisions are ignored and new arrivals never steal the selection', async () => {
  let current = { ...snap(), revision: 5 }
  const { m } = setup({ list: async () => current })
  await m.refreshNow()
  current = { ...snap([row(2)]), revision: 4 }; await m.refreshNow()
  assert.equal(m.snapshot.value.revision, 5)
  assert.equal(m.selectedId.value, 1)
  current = { ...snap([row(1), row(2)]), revision: 6 }; await m.refreshNow()
  assert.equal(m.selectedId.value, 1)
  m.dispose()
})

test('cancelled requests are not failures; authentication pauses with a visible reason', async () => {
  let error = { name: 'CanceledError', code: 'ERR_CANCELED' }
  const { m } = setup({ list: async () => { throw error } })
  await m.refreshNow()
  assert.equal(m.failed.value, false)
  error = { response: { status: 403, data: { message: 'authentication required' } } }
  await m.refreshNow()
  assert.equal(m.authFailed.value, true)
  assert.equal(m.failed.value, true)
  assert.equal(m.failureMessage.value, 'authentication required')
  m.dispose()
})
