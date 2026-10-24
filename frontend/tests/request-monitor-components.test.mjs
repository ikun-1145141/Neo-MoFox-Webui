/** Real SFC templates + Vue memory renderer; no provider, DOM package or extra test framework. */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import { parse, compileScript } from 'vue/compiler-sfc'
import ts from 'typescript'
import * as vue from 'vue'

const require = createRequire(import.meta.url)
const src = fileURLToPath(new URL('../src/', import.meta.url))
const cache = new Map()
let monitorForView = null
let monitorMounts = 0
function compileModule(source, dependencies) {
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true } }).outputText
  const exports = {}
  new Function('require', 'exports', js)(dependencies, exports)
  return exports
}
function load(file) {
  file = resolve(src, file)
  if (cache.has(file)) return cache.get(file)
  let source = readFileSync(file, 'utf8')
  if (file.endsWith('.vue')) source = compileScript(parse(source, { filename: file }).descriptor, { id: file, inlineTemplate: true }).content
  const result = compileModule(source, name => {
    if (name === 'vue') return vue
    if (name.endsWith('.css')) return {}
    if (name.endsWith('/common/AppShell.vue')) return { __esModule: true, default: { setup: (_, { slots }) => () => vue.h('main', slots.default?.()) } }
    if (name.endsWith('/composables/useRequestMonitor')) return { useRequestMonitor: () => { monitorMounts++; return monitorForView } }
    if (name.endsWith('/utils/dialog')) return { useDialogStore: () => ({ confirm: async () => true }) }
    if (name.endsWith('/utils/toast')) return { useToastStore: () => ({ show() {} }) }
    if (name.endsWith('/common/Icon.vue')) return { __esModule: true, default: { render: () => null } }
    if (name.endsWith('/utils/i18n')) return { useI18n: () => ({ t: key => key }) }
    if (name.startsWith('.')) return load(resolve(dirname(file), name.endsWith('.vue') ? name : name + '.ts'))
    return require(name)
  })
  cache.set(file, result)
  return result
}
const utils = load('utils/request-monitor-json.ts')
function descendants(node) { return [node, ...node.children.flatMap(descendants)] }
function text(node) { return (node.text || '') + node.children.map(text).join('') }
function element(tag = '') {
  const n = { tag, tagName: tag.toUpperCase(), children: [], props: {}, style: {}, text: '', parent: null, scrollTop: 0,
    addEventListener() {}, removeEventListener() {}, focus() { this.focused = true },
    querySelectorAll(selector) { return descendants(this).filter(n => selector === '[role="tab"]' && n.props.role === 'tab') },
  }
  Object.defineProperty(n, 'options', { get: () => descendants(n).filter(n => n.tag === 'option') })
  return n
}
const renderer = vue.createRenderer({
  createElement: tag => element(tag),
  createText: value => ({ ...element('#text'), text: value }),
  createComment: value => ({ ...element('#comment'), text: '' }),
  insert(node, parent, anchor) {
    if (node.parent) { const old = node.parent.children.indexOf(node); if (old >= 0) node.parent.children.splice(old, 1) }
    node.parent = parent
    const i = anchor ? parent.children.indexOf(anchor) : -1
    if (i < 0) parent.children.push(node); else parent.children.splice(i, 0, node)
  },
  remove(node) { const i = node.parent?.children.indexOf(node); if (i >= 0) node.parent.children.splice(i, 1) },
  setText(node, value) { node.text = value },
  setElementText(node, value) { node.text = value; node.children = [] },
  patchProp(node, key, old, value) { node.props[key] = value; if (key === 'style') Object.assign(node.style, value); else node[key] = value },
  parentNode: node => node.parent,
  nextSibling: node => node.parent?.children[node.parent.children.indexOf(node) + 1] || null,
})
function mount(t, name, data) {
  const props = vue.shallowReactive(data)
  const component = load(name === 'RequestInspectorView' ? 'views/RequestInspectorView.vue' : `components/request-monitor/${name}.vue`).default
  const host = element('root')
  const app = renderer.createApp({ setup: () => () => vue.h(component, props) })
  app.mount(host)
  t.after(() => app.unmount())
  return { host, props }
}
const buttons = host => descendants(host).filter(n => n.tag === 'button')
async function click(button) { assert.ok(button, 'button exists'); button.props.onClick?.({ target: button, currentTarget: button }); await vue.nextTick() }
function record(extra = {}) {
  return { id: 1, version: 1, instance_id: 'fixture-a', ts: 1, model: 'fixture', api_name: 'messages.stream', api_provider: 'local', request_name: 'fixture',
    logical_request_id: 'trace', attempt: 1, stream: true, status: 'streaming', duration_ms: null, first_token_ms: null, tokens_in: null, tokens_out: 0, estimated_input_tokens: 5,
    params: { model: 'fixture', extra_body: { 'a/b~': [false, null, 0, ''] } }, metadata: {}, rendered: { overview: [], messages: [], tools: [] },
    response: { kind: 'chat', message: 'hello', reasoning_content: 'reason', reasoning_parts: [], tool_calls: [], usage: null, stop_reason: null, embeddings: [], results: [] },
    raw_response: null, raw_events: [{ type: 'vendor.unknown', x: 0 }], error: null,
    capture_info: { redacted: false, raw_truncated: false, raw_unavailable: false, request_unavailable: false, metadata_unavailable: false, raw_bytes: 35, raw_limit_bytes: 2097152 }, ...extra }
}

test('JSON preserves primitive types, unknown keys and unambiguous pointer escaping', () => {
  assert.equal(utils.childPointer('', 'a/b~.中'), '/a~1b~0.中')
  const value = { null: null, empty: '', array: [], object: {}, zero: 0, no: false, marker: '[unavailable]', '': true }
  const { rows } = utils.visibleJsonRows(value, new Map())
  assert.deepEqual(rows.slice(1).map(r => r.type), ['null', 'string', 'array', 'object', 'number', 'boolean', 'string', 'boolean'])
  assert.equal(rows.at(-1).path, '/')
  assert.equal(utils.previewJson('x'.repeat(10000)).length, 164)
})

test('large arrays and objects are paged without building all child nodes', () => {
  const values = Array.from({ length: 10000 }, (_, i) => i)
  assert.equal(utils.visibleJsonRows(values, new Map()).rows.length, 102)
  const state = new Map([['', { offset: 9900 }]])
  const rows = utils.visibleJsonRows(values, state).rows
  assert.equal(rows[1].value, 9900); assert.equal(rows.at(-2).value, 9999)
  const object = Object.fromEntries(values.map(i => [`key${i}`, i]))
  assert.equal(utils.visibleJsonRows(object, state).rows[1].key, 'key9900')
})

test('deep inputs are iterative and bounded; collapsed branches are not traversed', () => {
  let value = 'leaf'; const state = new Map()
  for (let i = 0; i < 2500; i++) { value = { nested: value }; state.set('/nested'.repeat(i), { expanded: true }) }
  assert.equal(utils.visibleJsonRows(value, new Map()).rows.length, 2)
  const view = utils.visibleJsonRows(value, state)
  assert.equal(view.rows.length, utils.JSON_ROW_LIMIT)
  assert.equal(view.limited, true)
})

test('argument text parsing preserves incomplete strings and non-object JSON', () => {
  assert.deepEqual(utils.parseJsonText('{"x":'), { parsed: false, value: '{"x":' })
  assert.deepEqual(utils.parseJsonText('false'), { parsed: true, value: false })
  assert.deepEqual(utils.parseJsonText('[1,null]'), { parsed: true, value: [1, null] })
})

test('real JSON tree expands, copies paths and copies complete subtrees, not previews', async t => {
  const copied = []
  const data = { 'a/b~': { payload: 'long'.repeat(2000) } }
  const { host, props } = mount(t, 'InspectorJsonTree', { value: data, scope: 'a:1', pathPrefix: '/params', onCopy: x => copied.push(x) })
  await click(buttons(host).find(n => n.props['aria-label']?.includes('requestMonitor.expand a/b~')))
  await click(buttons(host).find(n => n.props['aria-label']?.includes('requestMonitor.copyPath payload')))
  assert.equal(copied.at(-1), '/params/a~1b~0/payload')
  await click(buttons(host).find(n => n.props['aria-label']?.includes('requestMonitor.copyNode a/b~')))
  assert.equal(JSON.parse(copied.at(-1)).payload.length, 8000)
  props.value = { 'a/b~': { payload: 'updated' } }; await vue.nextTick()
  assert.ok(text(host).includes('updated'), 'same record update retains expansion')
  props.scope = 'a:2'; await vue.nextTick()
  assert.ok(!text(host).includes('updated'), 'new selection clears expansion')
})

test('real tree pagination reaches the last array page and can go back', async t => {
  const { host } = mount(t, 'InspectorJsonTree', { value: Array.from({ length: 250 }, (_, i) => i), scope: 'array' })
  await click(buttons(host).find(n => text(n).includes('requestMonitor.moreChildren')))
  assert.ok(descendants(host).some(n => n.props['data-json-path'] === '/100'))
  await click(buttons(host).find(n => text(n).includes('requestMonitor.moreChildren')))
  assert.ok(descendants(host).some(n => n.props['data-json-path'] === '/249'))
  await click(buttons(host).find(n => text(n).includes('requestMonitor.previousPage')))
  assert.ok(descendants(host).some(n => n.props['data-json-path'] === '/100'))
})

test('long response text is previewed safely while copy keeps the full content', async t => {
  const copied = [], payload = '<img src=x onerror=alert(1)>'.repeat(600)
  const { host, props } = mount(t, 'InspectorText', { text: payload, onCopy: x => copied.push(x) })
  assert.equal(descendants(host).find(n => n.tag === 'pre').text.length, utils.TEXT_PAGE_SIZE)
  assert.equal(descendants(host).filter(n => n.tag === 'img').length, 0)
  await click(buttons(host).find(n => text(n) === 'requestMonitor.copyText'))
  assert.equal(copied[0], payload)
  await click(buttons(host).find(n => text(n).includes('requestMonitor.moreText')))
  props.text = payload + 'append'; await vue.nextTick()
  assert.equal(descendants(host).find(n => n.tag === 'pre').text.length, utils.TEXT_PAGE_SIZE * 2)
})

test('four equal tabs retain state and only the active panel receives streaming updates', async t => {
  const first = record()
  const { host, props } = mount(t, 'InspectorRecordDetail', { record: first, loading: false, exporting: false })
  const tabs = () => descendants(host).filter(n => n.props.role === 'tab')
  assert.deepEqual(tabs().map(text), ['requestMonitor.request', 'requestMonitor.response', 'requestMonitor.tools', 'requestMonitor.raw'])
  assert.equal(tabs()[0].props['aria-selected'], true)
  assert.ok(!text(host).includes('requestMonitor.redacted'))
  await click(buttons(host).find(n => text(n).includes('requestMonitor.tree'))); await vue.nextTick(); await click(buttons(host).find(n => n.props['aria-label']?.includes('requestMonitor.expand extra_body')))
  await click(tabs()[1])
  props.record = record({ version: 2, params: { ...first.params, model: 'changed' }, response: { ...first.response, message: 'stream delta' } })
  await vue.nextTick()
  assert.equal(tabs()[1].props['aria-selected'], true)
  assert.ok(text(host).includes('stream delta'))
  const requestPanel = descendants(host).find(n => n.props.id === 'rm-panel-request')
  assert.ok(!text(requestPanel).includes('changed'), 'inactive request panel is frozen')
  await click(tabs()[0])
  assert.ok(text(requestPanel).includes('changed'))
  assert.ok(buttons(host).some(n => n.props['aria-label']?.includes('requestMonitor.collapse extra_body')))
  props.record = record({ id: 2, instance_id: 'other' }); await vue.nextTick()
  assert.ok(!buttons(host).some(n => n.props['aria-label']?.includes('requestMonitor.collapse extra_body')))
})

test('embedding and rerank response templates keep dimensions and unknown result fields', t => {
  for (const kind of ['embedding', 'rerank']) {
    const r = record(); r.response = { ...r.response, kind, embeddings: [[0.1, 0.2], [0.3]], results: [{ vendor_field: true }] }
    const { host } = mount(t, 'InspectorResponse', { record: r })
    assert.ok(text(host).includes(kind === 'embedding' ? 'array (2)' : 'object (1)'))
  }
})

test('raw JSON download emits the complete safe snapshot with integrity flags', async t => {
  const exported = []
  const r = record({ capture_info: { ...record().capture_info, redacted: true, raw_truncated: true } })
  const { host } = mount(t, 'InspectorRawJson', { record: r, onExport: (...args) => exported.push(args) })
  const select = descendants(host).find(n => n.tag === 'select')
  select.props['onUpdate:modelValue']('record'); await vue.nextTick()
  await click(buttons(host).find(n => text(n) === 'requestMonitor.downloadJson'))
  assert.equal(exported[0][1], 'record')
  const saved = JSON.parse(JSON.stringify(exported[0][0]))
  assert.equal(saved.capture_info.raw_truncated, true)
  assert.equal(saved.capture_info.redacted, true)
  assert.deepEqual(saved.raw_events, r.raw_events)
})

test('shared Axios interceptor only suppresses explicitly inline-handled errors, not auth', async () => {
  let handlers; const messages = []
  const instance = { interceptors: { request: { use() {} }, response: { use(...args) { handlers = args } } } }
  const dependencies = { axios: { create: () => instance, isCancel: e => e?.code === 'ERR_CANCELED' },
    './config': { API_BASE_URL: '/', API_TIMEOUT: 1000 }, '../utils/toast': { useToastStore: () => ({ show: msg => messages.push(msg) }) },
    './modules/settings': { healthCheck: async () => {} },
  }
  compileModule(readFileSync(resolve(src, 'api/base.ts'), 'utf8').replaceAll('import.meta.env.DEV', 'false'), name => dependencies[name] || require(name))
  await assert.rejects(handlers[1]({ response: { status: 404 }, config: { handledErrorStatuses: [404] } }))
  assert.equal(messages.length, 0)
  await assert.rejects(handlers[1]({ response: { status: 404 }, config: {} }))
  assert.equal(messages.length, 1)
  await assert.rejects(handlers[1]({ code: 'ERR_CANCELED' }))
  assert.equal(messages.length, 1)
  await assert.rejects(handlers[1]({ response: { status: 403 }, config: { handledErrorStatuses: [403] } }))
  assert.equal(messages.length, 2)
})

// Presentation tests exercise the real page template, without network or storage.
function mobilePage(t) {
  const listeners = new Set()
  const media = { matches: true, addEventListener: (_, fn) => listeners.add(fn), removeEventListener: (_, fn) => listeners.delete(fn) }
  const previousWindow = global.window
  global.window = { matchMedia: query => { assert.equal(query, '(max-width: 899px)'); return media } }
  t.after(() => { global.window = previousWindow })
  const calls = []
  const monitor = {
    snapshot: vue.shallowRef({ records: [record()], stats: { total: 1 }, capacity: 200 }),
    detail: vue.shallowRef(record()), selectedId: vue.ref(1),
    search: vue.ref(''), status: vue.ref(''), model: vue.ref(''), models: vue.ref(['fixture']),
    paused: vue.ref(false), failed: vue.ref(false), authFailed: vue.ref(false),
    failureMessage: vue.ref(''), refreshing: vue.ref(false), detailLoading: vue.ref(false),
    clearing: vue.ref(false), lastUpdated: vue.ref(null), notice: vue.ref(''),
    selectRecord: async id => { calls.push(id); monitor.selectedId.value = id; monitor.detail.value = record({ id }) },
    pause() {}, resume() {}, refreshNow() {}, clear: async () => { monitor.selectedId.value = null; monitor.detail.value = null },
  }
  monitor.records = vue.computed(() => monitor.snapshot.value.records.filter(r => !monitor.search.value || r.model.includes(monitor.search.value)))
  monitorForView = monitor
  monitorMounts = 0
  const mounted = mount(t, 'RequestInspectorView', {})
  return { ...mounted, monitor, calls, listeners, resize(matches) { media.matches = matches; for (const listener of listeners) listener() } }
}
const tick = async () => { await vue.nextTick(); await vue.nextTick() }
const byClass = (host, name) => descendants(host).find(n => String(n.props.class || '').split(' ').includes(name))
const isDetailPage = host => String(byClass(host, 'rm-page').props.class).includes('rm-show-detail')

test('mobile starts on the list even when automatic selection already has a detail', async t => {
  const { host, monitor } = mobilePage(t); await tick()
  assert.equal(isDetailPage(host), false)
  monitor.detail.value = record({ version: 2 }); await tick()
  assert.equal(isDetailPage(host), false, 'polling never opens a detail')
  await click(buttons(host).find(n => String(n.props.class).includes('rm-record ')))
  assert.equal(isDetailPage(host), true)
  assert.ok(buttons(host).some(n => text(n) === 'requestMonitor.backToRecords'))
})

test('returning to the same request retains tabs, expanded tree and filters without refetching', async t => {
  const { host, monitor, calls } = mobilePage(t); await tick()
  await click(buttons(host).find(n => String(n.props.class).includes('rm-record ')))
  await click(buttons(host).find(n => text(n) === 'requestMonitor.tree'))
  await click(buttons(host).find(n => n.props['aria-label'] === 'requestMonitor.expand extra_body'))
  const response = descendants(host).find(n => n.props.id === 'rm-tab-response')
  await click(response)
  monitor.search.value = 'fixture'; await tick()
  await click(buttons(host).find(n => text(n) === 'requestMonitor.backToRecords'))
  assert.equal(isDetailPage(host), false)
  await click(buttons(host).find(n => String(n.props.class).includes('rm-record ')))
  assert.equal(response.props['aria-selected'], true)
  assert.equal(monitor.search.value, 'fixture')
  assert.equal(calls.length, 0, 'same selected detail is reused')
  await click(descendants(host).find(n => n.props.id === 'rm-tab-request'))
  assert.ok(buttons(host).some(n => n.props['aria-label'] === 'requestMonitor.collapse extra_body'))
})

test('mobile filtering does not leave a detail; clear, eviction and restart invalidate navigation', async t => {
  const { host, monitor } = mobilePage(t); await tick()
  for (const reason of ['', 'removed', 'restarted']) {
    monitor.snapshot.value = { ...monitor.snapshot.value, records: [record()] }
    monitor.search.value = ''; monitor.selectedId.value = 1; monitor.detail.value = record(); await tick()
    await click(buttons(host).find(n => String(n.props.class).includes('rm-record ')))
    monitor.search.value = 'hidden'; await tick()
    assert.equal(isDetailPage(host), true)
    monitor.notice.value = reason; monitor.selectedId.value = null; monitor.detail.value = null; await tick()
    assert.equal(isDetailPage(host), false)
  }
})

test('breakpoint changes retain the same page, selected tab and a single monitor instance', async t => {
  const { host, resize, listeners } = mobilePage(t); await tick()
  await click(buttons(host).find(n => String(n.props.class).includes('rm-record ')))
  await click(descendants(host).find(n => n.props.id === 'rm-tab-raw'))
  resize(false); await tick()
  assert.ok(!buttons(host).some(n => text(n) === 'requestMonitor.backToRecords'))
  resize(true); await tick()
  assert.equal(isDetailPage(host), true)
  assert.equal(descendants(host).find(n => n.props.id === 'rm-tab-raw').props['aria-selected'], true)
  assert.equal(monitorMounts, 1)
  assert.equal(listeners.size, 1)
  t.after(() => assert.equal(listeners.size, 0, 'media listener is removed on unmount'))
})

test('the list saves its scroll before hiding and restores it after returning', async t => {
  const { host, props } = mount(t, 'InspectorRecordList', { records: [record()], models: [], search: '', status: '', model: '', selectedId: 1, loading: false, active: true })
  const list = byClass(host, 'rm-records'); list.scrollTop = 312
  props.active = false; await tick(); list.scrollTop = 0
  props.active = true; await tick()
  assert.equal(list.scrollTop, 312)
})

test('mobile detail scroll belongs to each tab and survives hidden views and desktop resizing', async t => {
  const { host, props } = mount(t, 'InspectorRecordDetail', { record: record(), loading: false, exporting: false, compact: true, active: true })
  const scroll = byClass(host, 'rm-detail-scroll')
  const tab = name => descendants(host).find(n => n.props.id === 'rm-tab-' + name)
  scroll.scrollTop = 123; scroll.props.onScroll({ currentTarget: scroll })
  await click(tab('response')); await tick(); assert.equal(scroll.scrollTop, 0)
  scroll.scrollTop = 456
  await click(tab('request')); await tick(); assert.equal(scroll.scrollTop, 123)
  props.active = false; await tick(); scroll.scrollTop = 0
  props.active = true; await tick(); assert.equal(scroll.scrollTop, 123)
  props.record = record({ version: 2 }); await tick(); assert.equal(scroll.scrollTop, 123)
  props.compact = false; await tick()
  const request = descendants(host).find(n => n.props.id === 'rm-panel-request')
  assert.equal(request.scrollTop, 0)
  request.scrollTop = 234; request.props.onScroll({ currentTarget: request })
  props.compact = true; await tick(); assert.equal(scroll.scrollTop, 123)
  await click(tab('response')); await tick(); assert.equal(scroll.scrollTop, 456)
  props.compact = false; await tick(); await click(tab('request')); await tick()
  assert.equal(request.scrollTop, 234, 'desktop scroll has its own retained position')
  props.compact = true; await tick()
  props.record = record({ id: 2 }); await tick(); assert.equal(scroll.scrollTop, 0)
})

test('header shortcuts have accessible labels, metadata is grouped, and default modes stay unchanged', async t => {
  const { host } = mobilePage(t); await tick()
  for (const action of ['pause', 'refresh', 'clear']) assert.ok(buttons(host).some(n => n.props['aria-label'] === 'requestMonitor.' + action))
  assert.equal(descendants(host).filter(n => n.tag === 'dt').length, 9)
  assert.equal(descendants(host).filter(n => n.tag === 'dd').length, 9)
  assert.equal(descendants(host).filter(n => n.props.class === 'rm-overview-item').length, 9)
  assert.equal(buttons(host).find(n => text(n) === 'requestMonitor.messages').props['aria-pressed'], true)
  await click(descendants(host).find(n => n.props.id === 'rm-tab-raw'))
  assert.equal(buttons(host).find(n => text(n) === 'JSON').props['aria-pressed'], true)
})

test('CSS breakpoint events cannot overwrite mobile scroll with a forced zero', async t => {
  const previousWindow = global.window
  let matches = true
  global.window = { matchMedia: () => ({ matches }) }
  t.after(() => { global.window = previousWindow })
  const { host, props } = mount(t, 'InspectorRecordDetail', { record: record(), loading: false, exporting: false, compact: true, active: true })
  const scroll = byClass(host, 'rm-detail-scroll')
  scroll.scrollTop = 650; scroll.props.onScroll({ currentTarget: scroll })
  matches = false
  scroll.scrollTop = 0; scroll.props.onScroll({ currentTarget: scroll })
  props.compact = false; await tick()
  matches = true; props.compact = true; await tick()
  assert.equal(scroll.scrollTop, 650)
})

test('clicking a different mobile request fetches only that detail and does not duplicate the monitor', async t => {
  const { host, monitor, calls } = mobilePage(t); await tick()
  monitor.snapshot.value = { ...monitor.snapshot.value, records: [record({ id: 2 }), record()] }; await tick()
  await click(buttons(host).find(n => n.props['aria-pressed'] === false && String(n.props.class).includes('rm-record')))
  assert.deepEqual(calls, [2])
  assert.equal(isDetailPage(host), true)
  monitor.detail.value = record({ id: 2, version: 2 }); await tick()
  assert.deepEqual(calls, [2])
  assert.equal(monitorMounts, 1)
})


test('expanded JSON strings use a multiline text block and reveal the complete value in pages', async t => {
  const copied = []
  const payload = 'first-page\n' + '中'.repeat(9000) + '<last-page>'
  const { host, props } = mount(t, 'InspectorJsonTree', { value: { description: payload }, scope: 'long-string', onCopy: x => copied.push(x) })
  assert.equal(descendants(host).filter(n => n.tag === 'pre').length, 0)
  const more = () => buttons(host).find(n => text(n).includes('requestMonitor.moreText'))
  await click(more())
  const preview = () => descendants(host).find(n => n.tag === 'pre')
  assert.equal(preview().props.class, 'rm-content')
  assert.equal(preview().parent.props.class, 'rm-tree-text')
  assert.equal(preview().text, utils.previewJson(payload, 160 + utils.TEXT_PAGE_SIZE))
  props.value = { description: payload + 'stream-tail' }; await vue.nextTick()
  assert.equal(preview().text, utils.previewJson(payload + 'stream-tail', 160 + utils.TEXT_PAGE_SIZE))
  while (more()) await click(more())
  assert.equal(preview().text, JSON.stringify(payload + 'stream-tail'))
  assert.ok(preview().text.includes('<last-page>stream-tail'))
  await click(buttons(host).find(n => n.props['aria-label'] === 'requestMonitor.copyNode description'))
  assert.equal(JSON.parse(copied.at(-1)), payload + 'stream-tail')
  props.scope = 'another-record'; await vue.nextTick()
  assert.equal(preview(), undefined, 'new scope resets expanded text')
})

test('medium JSON strings expand fully without a remaining artificial ellipsis', async t => {
  const payload = '工具说明'.repeat(70)
  const { host } = mount(t, 'InspectorJsonTree', { value: payload, scope: 'medium-string' })
  await click(buttons(host).find(n => text(n).includes('requestMonitor.moreText')))
  assert.equal(descendants(host).find(n => n.tag === 'pre').text, JSON.stringify(payload))
  assert.ok(!buttons(host).some(n => text(n).includes('requestMonitor.moreText')))
})

test('null, empty and whitespace chat bodies show the tool-only state instead of a blank text card', async t => {
  for (const message of [null, '', '  \n  ']) {
    const r = record({ status: 'succeeded' })
    r.response = { ...r.response, message, reasoning_content: '', tool_calls: [{ name: 'reply', args: '{"content":"hello"}' }], stop_reason: 'tool_calls' }
    let opened = false
    const { host } = mount(t, 'InspectorResponse', { record: r, onTools: () => { opened = true } })
    assert.ok(text(host).includes('requestMonitor.toolOnlyResponse'))
    assert.ok(!text(host).includes('requestMonitor.responseText'))
    assert.ok(!text(host).includes('requestMonitor.reasoning'))
    assert.equal(descendants(host).filter(n => n.tag === 'pre').length, 1, 'tool arguments are visible, not an empty body')
    assert.ok(text(host).includes('reply'))
    assert.ok(text(host).includes('{"content":"hello"}'))
    await click(buttons(host).find(n => text(n) === 'requestMonitor.viewToolCalls'))
    assert.equal(opened, true)
  }
})

test('empty streaming responses become visible on append without losing reasoning or partial failure output', async t => {
  const first = record(); first.response = { ...first.response, message: '', reasoning_content: null }
  const { host, props } = mount(t, 'InspectorResponse', { record: first })
  assert.ok(text(host).includes('requestMonitor.waitingContent'))
  assert.ok(!text(host).includes('requestMonitor.copyText'))
  props.record = { ...first, version: 2, response: { ...first.response, message: 'normal text', reasoning_content: 'thinking' } }; await vue.nextTick()
  assert.ok(text(host).includes('normal text'))
  assert.ok(text(host).includes('thinking'))
  props.record = { ...props.record, status: 'failed' }; await vue.nextTick()
  assert.ok(text(host).includes('normal text'))
  props.record = { ...first, status: 'succeeded' }; await vue.nextTick()
  assert.ok(text(host).includes('requestMonitor.noResponseText'))
  assert.ok(!text(host).includes('requestMonitor.waitingContent'))
})

test('tool-only response action switches to the existing Tools panel', async t => {
  const r = record({ status: 'succeeded' })
  r.response = { ...r.response, message: '', tool_calls: [{ name: 'reply', args: '{"content":"hello"}' }] }
  const { host } = mount(t, 'InspectorRecordDetail', { record: r, loading: false, exporting: false })
  await click(descendants(host).find(n => n.props.id === 'rm-tab-response'))
  await click(buttons(host).find(n => text(n) === 'requestMonitor.viewToolCalls'))
  assert.equal(descendants(host).find(n => n.props.id === 'rm-tab-tools').props['aria-selected'], true)
  assert.ok(text(host).includes('reply'))
})


test('tool definitions and returned argument strings share the working multiline expansion', async t => {
  const description = 'tool-description-'.repeat(400) + 'definition-end'
  const args = JSON.stringify({ content: 'tool-message-'.repeat(800) + 'arguments-end' })
  const r = record()
  r.rendered.tools = [{ index: 0, name: 'reply', kind: 'function', description, required: [], properties: [], raw_json: JSON.stringify({ type: 'function', function: { name: 'reply', description } }) }]
  r.response.tool_calls = [{ id: 'call-1', name: 'reply', args }]
  const { host } = mount(t, 'InspectorTools', { record: r })
  const details = descendants(host).filter(n => n.tag === 'details')
  for (const detail of details) { detail.props.onToggle({ target: { open: true } }); await vue.nextTick() }
  await click(buttons(host).find(n => n.props['aria-label'] === 'requestMonitor.expand function'))
  const moreIn = node => descendants(node).find(n => n.tag === 'button' && text(n).includes('requestMonitor.moreText'))
  for (const detail of details) {
    while (moreIn(detail)) await click(moreIn(detail))
  }
  const previews = descendants(host).filter(n => n.tag === 'pre').map(n => n.text)
  assert.ok(previews.includes(JSON.stringify(description)), 'full definition is displayed')
  assert.ok(previews.includes(JSON.stringify(args)), 'full original argument string is displayed')
})
