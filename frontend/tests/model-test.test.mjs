// Run: node --test tests/model-test.test.mjs (from frontend/).
// Compile the real SFC setup with the existing Vue/TypeScript dependencies;
// use Vue's in-memory renderer so no DOM, browser, or real provider is needed.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { test } from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import ts from 'typescript'
import * as vue from 'vue'

const require = createRequire(import.meta.url)
const editorSource = readFileSync(new URL('../src/components/config/ModelConfigEditor.vue', import.meta.url), 'utf8')
const { descriptor } = parse(editorSource)
const editorScript = compileScript(descriptor, { id: 'model-test-regression' }).content

function compileModule(source, dependencies) {
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  })
  const exports = {}
  new Function('require', 'exports', 'console', outputText)(
    (name) => Object.hasOwn(dependencies, name) ? dependencies[name] : require(name),
    exports,
    { ...console, log() {} },
  )
  return exports
}

const renderer = vue.createRenderer({
  createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
  insert() {}, remove() {}, setText() {}, setElementText() {}, patchProp() {},
  parentNode: () => null, nextSibling: () => null,
})

const success = {
  success: true, response_text: 'local response', latency_ms: 1,
  model_identifier: 'draft-id', provider_base_url: 'https://draft.invalid/v1',
}

function mountEditor(t, apiTestModel = async () => success) {
  const saved = {
    api_providers: [{ name: 'provider', base_url: 'https://saved.invalid/v1', api_key: 'saved-test-key' }],
    models: [{ name: 'saved', model_identifier: 'saved-id', api_provider: 'provider' }],
    model_tasks: {},
  }
  const requests = []
  const events = []
  const component = compileModule(editorScript, {
    vue,
    '@/utils/i18n': { useI18n: () => ({ t: (key) => key }) },
    '@/utils/dialog': { useDialogStore: () => ({ confirm: async () => true }) },
    '../common/Icon.vue': {}, './TomlEditor.vue': {}, './ModelEditDialog.vue': {},
    '@/api/modules/config': {
      testModel: async (request) => { requests.push(request); return apiTestModel(request) },
      getRawConfig: async () => '# saved TOML',
    },
  }).default
  let state
  const app = renderer.createApp({
    ...component,
    setup(props, context) {
      state = component.setup(props, context)
      return () => null
    },
  }, {
    title: 'Models', schema: [], modelValue: saved,
    onSave: (...args) => events.push(['save', ...args]),
    'onUpdate:modelValue': (...args) => events.push(['update', ...args]),
  })
  app.mount({})
  t.after(() => app.unmount())
  return { state, requests, events, saved }
}

test('new unsaved model sends its current model and provider snapshot without saving', async (t) => {
  const { state, requests, events, saved } = mountEditor(t)
  const model = { name: 'draft', model_identifier: 'draft-id', api_provider: 'provider' }
  state.localData.value.models.push(model)
  await state.testModel(model, 1)
  assert.deepEqual(requests[0], {
    provider_name: 'provider', model_name: 'draft',
    provider: { name: 'provider', base_url: 'https://saved.invalid/v1', api_key: 'saved-test-key' },
    model, test_prompt: '你好', timeout: 30,
  })
  assert.equal(saved.models.length, 1)
  assert.deepEqual(events, [])
  assert.equal(state.hasChanges.value, true)
  assert.deepEqual(state.testResults.value.models.get('1'), success)
  assert.equal(state.testingModels.value.size, 0)
})

test('new unsaved provider and model are both included', async (t) => {
  const { state, requests } = mountEditor(t)
  const provider = { name: 'draft-provider', base_url: 'https://draft.invalid/v1', api_key: 'draft-test-key' }
  const model = { name: 'draft', model_identifier: 'draft-id', api_provider: provider.name }
  state.localData.value.api_providers.push(provider)
  state.localData.value.models.push(model)
  await state.testModel(model, 1)
  assert.deepEqual(requests[0].provider, provider)
  assert.deepEqual(requests[0].model, model)
})

test('unsaved URL, key and identifier edits override saved values without mutating props', async (t) => {
  const { state, requests, saved, events } = mountEditor(t)
  const provider = state.localData.value.api_providers[0]
  const model = state.localData.value.models[0]
  provider.base_url = 'https://edited.invalid/v2'
  provider.api_key = ['first-test-key', 'second-test-key']
  model.model_identifier = 'edited-id'
  await state.testModel(model, 0)
  assert.equal(requests[0].provider.base_url, 'https://edited.invalid/v2')
  assert.equal(requests[0].model.model_identifier, 'edited-id')
  assert.deepEqual(requests[0].provider.api_key, ['first-test-key', 'second-test-key'])
  provider.api_key[0] = 'changed-after-test'
  assert.equal(requests[0].provider.api_key[0], 'first-test-key')
  assert.equal(saved.api_providers[0].api_key, 'saved-test-key')
  assert.equal(saved.models[0].model_identifier, 'saved-id')
  assert.deepEqual(events, [])
})

test('missing local provider shows a specific error and sends no request', async (t) => {
  const { state, requests } = mountEditor(t)
  await state.testModel({ name: 'draft', model_identifier: 'draft-id', api_provider: 'missing' }, 1)
  assert.equal(requests.length, 0)
  assert.match(state.testResults.value.models.get('1').error_message, /providerNotFound.*missing/)
  assert.equal(state.testingModels.value.size, 0)
})

for (const field of ['message', 'detail']) {
  test(`HTTP 400 shows the backend ${field}, not the generic Axios message`, async (t) => {
    const { state } = mountEditor(t, async () => {
      throw { isAxiosError: true, message: 'Request failed with status code 400', response: { data: { [field]: '具体配置错误' } } }
    })
    await state.testModel(state.localData.value.models[0], 0)
    assert.equal(state.testResults.value.models.get('0').error_message, '具体配置错误')
    assert.equal(state.testingModels.value.size, 0)
  })
}

test('business errors also show their backend message', async (t) => {
  const { state } = mountEditor(t, async () => { throw { code: 400, message: '配置不完整' } })
  await state.testModel(state.localData.value.models[0], 0)
  assert.equal(state.testResults.value.models.get('0').error_message, '配置不完整')
})

test('network error without response keeps its readable message', async (t) => {
  const { state } = mountEditor(t, async () => { throw { isAxiosError: true, message: 'Network Error' } })
  await state.testModel(state.localData.value.models[0], 0)
  assert.equal(state.testResults.value.models.get('0').error_message, 'Network Error')
})

test('duplicate clicks are ignored while testing and the row can be tested again', async (t) => {
  let resolve
  const { state, requests } = mountEditor(t, () => new Promise((done) => { resolve = done }))
  const model = state.localData.value.models[0]
  const pending = state.testModel(model, 0)
  assert.equal(state.testingModels.value.has('0'), true)
  await state.testModel(model, 0)
  assert.equal(requests.length, 1)
  resolve(success)
  await pending
  assert.equal(state.testingModels.value.has('0'), false)
  const again = state.testModel(model, 0)
  assert.equal(requests.length, 2)
  assert.equal(state.testResults.value.models.has('0'), false)
  resolve(success)
  await again
})

test('API wrapper gives the backend deadline five seconds of transport margin', async () => {
  const source = readFileSync(new URL('../src/api/modules/config.ts', import.meta.url), 'utf8')
  const calls = []
  const api = compileModule(source, {
    '../base': { post: (...args) => { calls.push(args); return Promise.resolve(success) } },
    '../config': { API_WEBUI_PREFIX: '/webui/api' },
  })
  const request = { provider_name: 'provider', model_name: 'saved', test_prompt: '你好', timeout: 30 }
  assert.deepEqual(await api.testModel(request), success)
  assert.deepEqual(calls, [['/webui/api/config-model/test', request, { timeout: 35000 }]])
})
