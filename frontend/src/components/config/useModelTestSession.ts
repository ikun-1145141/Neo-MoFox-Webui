import { computed, ref } from 'vue'
import { isAxiosError } from 'axios'
import { testModel } from '@/api/modules/config'
import type { ModelTestModel, ModelTestProvider, ModelTestRequest, ModelTestType } from '@/api/types/config'
import { clampNumber } from '@/utils/number'
import type { ModelKind, TestItem } from './modelTestDialogTypes'

export const modelKinds = [
  { key: 'llm', icon: 'forum-rounded' },
  { key: 'embedding', icon: 'data-object-rounded' },
  { key: 'rerank', icon: 'swap-vert-rounded' },
] as const

function initialTests(): Record<ModelKind, TestItem[]> {
  const item = (key: ModelTestType, message: string, icon: string, checked = true): TestItem =>
    ({ key, message, icon, checked, status: 'idle', result: null, error: '' })
  return {
    llm: [
      item('chat', 'llm.chat', 'chat-outline-rounded'),
      item('stream', 'llm.stream', 'stream-rounded'),
      item('tool_call', 'llm.toolCall', 'handyman-outline-rounded'),
      item('vlm', 'llm.vlm', 'image-outline-rounded', false),
    ],
    embedding: [item('embedding', 'embedding.standard', 'data-object-rounded')],
    rerank: [item('rerank', 'rerank.standard', 'format-list-numbered-rounded')],
  }
}

function inferKind(model: ModelTestModel | null): ModelKind {
  const id = String(model?.model_identifier || model?.name || '').toLowerCase()
  if (/embed|bge/.test(id)) return 'embedding'
  return /rerank|re-rank|rank/.test(id) ? 'rerank' : 'llm'
}

function optionalInteger(value: number | '', max: number): number | '' {
  return value === '' ? '' : Math.trunc(clampNumber(value, 1, max))
}

function errorText(error: unknown): string {
  const message = isAxiosError(error)
    ? error.response?.data?.message ?? error.response?.data?.detail ?? error.message
    : error && typeof error === 'object' && 'message' in error ? error.message : error
  return typeof message === 'string' ? message : ''
}

/** One transient dialog session; input and results never leave the editor except for the test request. */
export function useModelTestSession(props: {
  model: ModelTestModel | null
  providers: readonly ModelTestProvider[]
  timeout: number
}) {
  const activeKind = ref<ModelKind>('llm')
  const byKind = ref(initialTests())
  const isRunning = ref(false)
  const dimensions = ref<number | ''>('')
  const query = ref('中国最热门的旅游城市')
  const topN = ref<number | ''>(2)
  let generation = 0

  const tests = computed(() => byKind.value[activeKind.value])
  const provider = computed(() => props.providers.find(p => p?.name === props.model?.api_provider))
  const checkedCount = computed(() => tests.value.filter(test => test.checked).length)
  const blocked = computed(() => !props.model ? 'unknownModel' : !provider.value ? 'errors.providerNotFound'
    : !checkedCount.value ? 'errors.noTestSelected' : null)
  // States (not the live checkboxes) define the last batch, including while it is at 0/N.
  const batch = computed(() => {
    const ran = tests.value.filter(test => test.status !== 'idle')
    const passed = ran.filter(test => test.status === 'success').length
    const failed = ran.filter(test => test.status === 'fail').length
    return { total: ran.length, done: passed + failed, passed, failed }
  })

  function reset() {
    ++generation
    activeKind.value = inferKind(props.model)
    byKind.value = initialTests()
    dimensions.value = ''
    query.value = '中国最热门的旅游城市'
    topN.value = 2
    isRunning.value = false
  }

  function switchKind(kind: ModelKind) { if (!isRunning.value) activeKind.value = kind }
  function normalizeDimensions() { dimensions.value = optionalInteger(dimensions.value, 65536) }
  function normalizeTopN() { topN.value = optionalInteger(topN.value, 100) }

  async function run() {
    const model = props.model
    const source = provider.value
    if (isRunning.value || blocked.value || !model || !source) return
    const currentGeneration = generation
    const selected = tests.value.filter(test => test.checked)
    normalizeDimensions()
    normalizeTopN()
    const snapshot = {
      provider_name: source.name, model_name: model.name, timeout: props.timeout,
      provider: { name: source.name, base_url: source.base_url, api_key: Array.isArray(source.api_key) ? [...source.api_key] : source.api_key },
      model: { name: model.name, model_identifier: model.model_identifier, api_provider: model.api_provider },
    }
    // Some upstream errors repeat the supplied credential. Never show that value in the dialog.
    const secrets = [source.api_key].flat().filter(Boolean).sort((a, b) => b.length - a.length)
    const redact = (text: string) => secrets.reduce((out, key) => out.split(key).join('••••'), text)
    isRunning.value = true
    for (const test of tests.value) {
      test.status = test.checked ? 'running' : 'idle'
      test.result = null
      test.error = ''
    }
    try {
      await Promise.all(selected.map(async test => {
        const request: ModelTestRequest = { ...snapshot, test_type: test.key, test_prompt: '你好' }
        if (test.key === 'embedding') {
          request.test_prompt = '人工智能改变了世界'
          request.dimensions = dimensions.value || null
        } else if (test.key === 'rerank') {
          request.test_prompt = query.value
          request.top_n = topN.value || null
        }
        try {
          const result = await testModel(request)
          test.result = { ...result, response_text: result.response_text && redact(result.response_text),
            error_message: result.error_message && redact(result.error_message) }
          test.error = test.result.error_message || ''
          test.status = result.success ? 'success' : 'fail'
        } catch (error) {
          test.error = redact(errorText(error))
          test.status = 'fail'
        }
      }))
    } finally {
      if (currentGeneration === generation) isRunning.value = false
    }
  }

  return { activeKind, tests, checkedCount, blocked, batch, isRunning, dimensions, query, topN,
    reset, switchKind, normalizeDimensions, normalizeTopN, run }
}
