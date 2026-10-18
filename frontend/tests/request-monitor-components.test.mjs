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
  const n = { tag, tagName: tag.toUpperCase(), children: [], props: {}, style: {}, text: '', parent: null,
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
  const component = load(`components/request-monitor/${name}.vue`).default
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
  await click(buttons(host).find(n => n.props['aria-label'] === 'requestMonitor.expand a/b~'))
  await click(buttons(host).find(n => n.props['aria-label'] === 'requestMonitor.copyPath payload'))
  assert.equal(copied.at(-1), '/params/a~1b~0/payload')
  await click(buttons(host).find(n => n.props['aria-label'] === 'requestMonitor.copyNode a/b~'))
  assert.equal(JSON.parse(copied.at(-1)).payload.length, 8000)
  props.value = { 'a/b~': { payload: 'updated' } }; await vue.nextTick()
  assert.ok(text(host).includes('updated'), 'same record update retains expansion')
  props.scope = 'a:2'; await vue.nextTick()
  assert.ok(!text(host).includes('updated'), 'new selection clears expansion')
})

test('real tree pagination reaches the last array page and can go back', async t => {
  const { host } = mount(t, 'InspectorJsonTree', { value: Array.from({ length: 250 }, (_, i) => i), scope: 'array' })
  await click(buttons(host).find(n => text(n) === 'requestMonitor.moreChildren'))
  assert.ok(descendants(host).some(n => n.props['data-json-path'] === '/100'))
  await click(buttons(host).find(n => text(n) === 'requestMonitor.moreChildren'))
  assert.ok(descendants(host).some(n => n.props['data-json-path'] === '/249'))
  await click(buttons(host).find(n => text(n) === 'requestMonitor.previousPage'))
  assert.ok(descendants(host).some(n => n.props['data-json-path'] === '/100'))
})

test('long response text is previewed safely while copy keeps the full content', async t => {
  const copied = [], payload = '<img src=x onerror=alert(1)>'.repeat(600)
  const { host, props } = mount(t, 'InspectorText', { text: payload, onCopy: x => copied.push(x) })
  assert.equal(descendants(host).find(n => n.tag === 'pre').text.length, utils.TEXT_PAGE_SIZE)
  assert.equal(descendants(host).filter(n => n.tag === 'img').length, 0)
  await click(buttons(host).find(n => text(n) === 'requestMonitor.copyText'))
  assert.equal(copied[0], payload)
  await click(buttons(host).find(n => text(n).startsWith('requestMonitor.moreText')))
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
  await click(buttons(host).find(n => n.props['aria-label'] === 'requestMonitor.expand extra_body'))
  await click(tabs()[1])
  props.record = record({ version: 2, params: { ...first.params, model: 'changed' }, response: { ...first.response, message: 'stream delta' } })
  await vue.nextTick()
  assert.equal(tabs()[1].props['aria-selected'], true)
  assert.ok(text(host).includes('stream delta'))
  const requestPanel = descendants(host).find(n => n.props.id === 'rm-panel-request')
  assert.ok(!text(requestPanel).includes('changed'), 'inactive request panel is frozen')
  await click(tabs()[0])
  assert.ok(text(requestPanel).includes('changed'))
  assert.ok(buttons(host).some(n => n.props['aria-label'] === 'requestMonitor.collapse extra_body'))
  props.record = record({ id: 2, instance_id: 'other' }); await vue.nextTick()
  assert.ok(!buttons(host).some(n => n.props['aria-label'] === 'requestMonitor.collapse extra_body'))
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
