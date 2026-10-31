<!--
  @file ModelTestDialog.vue
  @description 模型测试对话框（LLM / 嵌入 / 重排序）
  
  功能：
  - 左侧选择模型种类（大模型 / 嵌入 / 重排序）
  - 右侧展示该种类专属的测试项与参数
  - 点击"开始测试"后并行执行所有勾选项，实时显示每项状态与结果
  - 测试期间所有按钮置灰，全部完成后才允许关闭
  - Material Design 3 样式
-->
<template>
  <Teleport to="body">
    <div v-if="isOpen" class="dialog-overlay" @click="handleOverlayClick">
      <div class="dialog-container" @click.stop>
        <div class="dialog-header">
          <div class="dialog-title">
            <h2>{{ t('modelTestDialog.title') }}</h2>
            <p class="subtitle">{{ modelName }}</p>
          </div>
          <button
            type="button"
            class="close-btn"
            :disabled="isRunning"
            :title="t('modelTestDialog.close')"
            @click="handleClose"
          >
            <Icon icon="material-symbols:close-rounded" :size="24" />
          </button>
        </div>

        <div class="dialog-body">
          <!-- 左侧：模型种类 -->
          <div class="type-sidebar">
            <button
              v-for="type in modelTypes"
              :key="type.key"
              type="button"
              class="type-btn"
              :class="{ active: activeType === type.key }"
              :disabled="isRunning"
              @click="switchType(type.key)"
            >
              <Icon :icon="type.icon" :size="20" />
              <span>{{ type.label }}</span>
            </button>
          </div>

          <!-- 右侧：对应测试项 -->
          <div class="test-panel">
            <p v-if="hint" class="hint" :class="{ error: hintError }">
              <Icon icon="material-symbols:info-outline-rounded" :size="16" />
              <span>{{ hint }}</span>
            </p>

            <!-- LLM 测试项 -->
            <template v-if="activeType === 'llm'">
              <div class="test-item" v-for="test in llmTests" :key="test.key">
                <label class="test-row" :class="{ disabled: isRunning }">
                  <input
                    type="checkbox"
                    v-model="test.checked"
                    :disabled="isRunning"
                  />
                  <span class="checkbox-box">
                    <Icon v-show="test.checked" icon="material-symbols:check-rounded" :size="16" />
                  </span>
                  <Icon :icon="test.icon" :size="20" class="test-icon" />
                  <span class="test-info">
                    <span class="test-name">{{ test.label }}</span>
                    <span class="test-desc">{{ test.desc }}</span>
                  </span>
                </label>
                <div class="test-extra">
                  <TestResultRow :test="test" :is-running="isRunning" />
                </div>
                <p v-if="test.key === 'vlm'" class="vlm-hint">
                  <Icon icon="material-symbols:info-outline-rounded" :size="15" />
                  <span>{{ t('modelTestDialog.llm.vlmImageHint') }}</span>
                </p>
              </div>
            </template>

            <!-- 嵌入测试项 -->
            <template v-else-if="activeType === 'embedding'">
              <div class="test-item" v-for="test in embeddingTests" :key="test.key">
                <label class="test-row" :class="{ disabled: isRunning }">
                  <input
                    type="checkbox"
                    v-model="test.checked"
                    :disabled="isRunning"
                  />
                  <span class="checkbox-box">
                    <Icon v-show="test.checked" icon="material-symbols:check-rounded" :size="16" />
                  </span>
                  <Icon :icon="test.icon" :size="20" class="test-icon" />
                  <span class="test-info">
                    <span class="test-name">{{ test.label }}</span>
                    <span class="test-desc">{{ test.desc }}</span>
                  </span>
                </label>
                <div class="test-extra">
                  <TestResultRow :test="test" :is-running="isRunning" />
                </div>
              </div>
              <div class="option-field">
                <label for="embedding-dim">{{ t('modelTestDialog.embedding.dimensionLabel') }}</label>
                <input
                  id="embedding-dim"
                  v-model.number="embeddingDimensions"
                  type="number"
                  min="1"
                  max="65536"
                  :disabled="isRunning"
                  :placeholder="t('modelTestDialog.embedding.dimensionPlaceholder')"
                />
                <p class="field-hint">{{ t('modelTestDialog.embedding.dimensionHint') }}</p>
              </div>
            </template>

            <!-- 重排序测试项 -->
            <template v-else>
              <div class="test-item" v-for="test in rerankTests" :key="test.key">
                <label class="test-row" :class="{ disabled: isRunning }">
                  <input
                    type="checkbox"
                    v-model="test.checked"
                    :disabled="isRunning"
                  />
                  <span class="checkbox-box">
                    <Icon v-show="test.checked" icon="material-symbols:check-rounded" :size="16" />
                  </span>
                  <Icon :icon="test.icon" :size="20" class="test-icon" />
                  <span class="test-info">
                    <span class="test-name">{{ test.label }}</span>
                    <span class="test-desc">{{ test.desc }}</span>
                  </span>
                </label>
                <div class="test-extra">
                  <TestResultRow :test="test" :is-running="isRunning" />
                </div>
              </div>
              <div class="option-row">
                <div class="option-field">
                  <label for="rerank-query">{{ t('modelTestDialog.rerank.queryLabel') }}</label>
                  <input
                    id="rerank-query"
                    v-model="rerankQuery"
                    type="text"
                    :disabled="isRunning"
                    :placeholder="t('modelTestDialog.rerank.queryPlaceholder')"
                  />
                </div>
                <div class="option-field narrow">
                  <label for="rerank-topn">{{ t('modelTestDialog.rerank.topNLabel') }}</label>
                  <input
                    id="rerank-topn"
                    v-model.number="rerankTopN"
                    type="number"
                    min="1"
                    max="100"
                    :disabled="isRunning"
                  />
                </div>
              </div>
            </template>
          </div>
        </div>

        <div class="dialog-footer">
          <div class="footer-status" v-if="summaryMessage">
            <Icon :icon="summaryIcon" :size="18" />
            <span>{{ summaryMessage }}</span>
          </div>
          <button
            type="button"
            class="cancel-btn"
            :disabled="isRunning"
            @click="handleClose"
          >
            {{ t('modelTestDialog.close') }}
          </button>
          <button
            type="button"
            class="submit-btn"
            :disabled="isRunning"
            @click="runTests"
          >
            <Icon
              v-if="!isRunning"
              icon="material-symbols:play-arrow-rounded"
              :size="20"
            />
            <Icon
              v-else
              icon="material-symbols:progress-activity"
              :size="20"
              class="spinning"
            />
            <span>{{ isRunning ? t('modelTestDialog.running') : t('modelTestDialog.testButton') }}</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { isAxiosError } from 'axios'
import { useI18n } from '@/utils/i18n'
import Icon from '../common/Icon.vue'
import TestResultRow from './ModelTestDialogResult.vue'
import { testModel as apiTestModel } from '@/api/modules/config'
import type { ModelKind, TestItem, LLMTestKey } from './modelTestDialogTypes'
import type { ModelTestRequest } from '@/api/types/config'

const { t } = useI18n()

// Props
interface Props {
  isOpen: boolean
  model: Record<string, any> | null
  providers: Record<string, any>[] // 当前页面供应商列表（含未保存的编辑值）
  timeout?: number
}

const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  model: null,
  providers: () => [],
  timeout: 30,
})

// Emits
const emit = defineEmits<{
  close: []
}>()

// ===== 状态 =====
const activeType = ref<ModelKind>('llm')
const isRunning = ref(false)
const hint = ref('')
const hintError = ref(false)

// LLM 测试项
const llmTests = ref<TestItem[]>([])
// 嵌入测试项
const embeddingTests = ref<TestItem[]>([])
// 重排序测试项
const rerankTests = ref<TestItem[]>([])

// 输入项
const embeddingDimensions = ref<number>(0)
const rerankQuery = ref('中国最热门的旅游城市')
const rerankTopN = ref(2)

// 模型种类定义
const modelTypes = computed(() => [
  { key: 'llm' as const, label: t('modelTestDialog.types.llm'), icon: 'material-symbols:model-training-outline-rounded' },
  { key: 'embedding' as const, label: t('modelTestDialog.types.embedding'), icon: 'material-symbols:data-object-outline-rounded' },
  { key: 'rerank' as const, label: t('modelTestDialog.types.rerank'), icon: 'material-symbols:swap-vert-rounded' },
])

// 模型显示名
const modelName = computed(() => props.model?.name || t('modelTestDialog.unknownModel'))

// 测试小结
const summaryMessage = computed(() => {
  const tests = currentTests.value
  if (!tests.some(t => t.status !== 'idle')) return ''
  const done = tests.filter(t => t.status === 'success' || t.status === 'fail')
  if (done.length === 0) return ''
  const successCount = tests.filter(t => t.status === 'success').length
  const failCount = tests.filter(t => t.status === 'fail').length
  if (isRunning.value) {
    return t('modelTestDialog.summary.running', { done: String(done.length), total: String(tests.filter(t => t.checked).length) })
  }
  return successCount > 0 && failCount === 0
    ? t('modelTestDialog.summary.allPassed', { count: String(successCount) })
    : t('modelTestDialog.summary.done', { success: String(successCount), fail: String(failCount) })
})

const summaryIcon = computed(() => {
  const tests = currentTests.value
  const failCount = tests.filter(t => t.status === 'fail').length
  if (isRunning.value) return 'material-symbols:sync-rounded'
  return failCount > 0
    ? 'material-symbols:error-outline-rounded'
    : 'material-symbols:check-circle-outline-rounded'
})

const currentTests = computed<TestItem[]>(() => {
  if (activeType.value === 'llm') return llmTests.value
  if (activeType.value === 'embedding') return embeddingTests.value
  return rerankTests.value
})

// ===== 初始化测试项 =====
function resetTests() {
  llmTests.value = [
    {
      key: 'chat', label: t('modelTestDialog.llm.chat'), desc: t('modelTestDialog.llm.chatDesc'),
      icon: 'material-symbols:chat-outline-rounded', checked: true,
      status: 'idle', result: null, error: '',
    },
    {
      key: 'stream', label: t('modelTestDialog.llm.stream'), desc: t('modelTestDialog.llm.streamDesc'),
      icon: 'material-symbols:stream-rounded', checked: true,
      status: 'idle', result: null, error: '',
    },
    {
      key: 'tool_call', label: t('modelTestDialog.llm.toolCall'), desc: t('modelTestDialog.llm.toolCallDesc'),
      icon: 'material-symbols:handyman-outline-rounded', checked: true,
      status: 'idle', result: null, error: '',
    },
    {
      key: 'vlm', label: t('modelTestDialog.llm.vlm'), desc: t('modelTestDialog.llm.vlmDesc'),
      icon: 'material-symbols:image-outline-rounded', checked: false,
      status: 'idle', result: null, error: '',
    },
  ]
  embeddingTests.value = [
    {
      key: 'embedding', label: t('modelTestDialog.embedding.standard'), desc: t('modelTestDialog.embedding.standardDesc'),
      icon: 'material-symbols:view-in-ar-outline-rounded', checked: true,
      status: 'idle', result: null, error: '',
    },
  ]
  rerankTests.value = [
    {
      key: 'rerank', label: t('modelTestDialog.rerank.standard'), desc: t('modelTestDialog.rerank.standardDesc'),
      icon: 'material-symbols:list-alt-outline-rounded', checked: true,
      status: 'idle', result: null, error: '',
    },
  ]
  // 根据模型名猜测类型
  const identifier = String(props.model?.model_identifier || props.model?.name || '').toLowerCase()
  if (/(embed|bge|text-embedding)/.test(identifier)) {
    activeType.value = 'embedding'
  } else if (/rerank|re-rank|rank/.test(identifier)) {
    activeType.value = 'rerank'
  } else {
    activeType.value = 'llm'
  }
}

function switchType(type: ModelKind) {
  activeType.value = type
  hint.value = ''
  hintError.value = false
}

// ===== 构建请求快照 =====
function buildSnapshot(request: Partial<ModelTestRequest>): ModelTestRequest {
  const model = props.model
  const provider = props.providers.find(p => String(p?.name) === String(model?.api_provider))

  if (!model) {
    throw { notFound: true, message: (t('modelTestDialog.unknownModel') as string) }
  }

  if (!provider) {
    throw { notFound: true, message: (t('modelTestDialog.errors.providerNotFound') as string) + `: ${model?.api_provider}` }
  }

  return {
    ...request,
    provider_name: provider.name,
    model_name: model.name,
    provider: {
      name: provider.name,
      base_url: provider.base_url,
      api_key: Array.isArray(provider.api_key) ? [...provider.api_key] : provider.api_key,
    },
    model: {
      name: model.name,
      model_identifier: model.model_identifier,
      api_provider: model.api_provider,
    },
    test_prompt: request.test_prompt ?? '你好',
    timeout: props.timeout,
  }
}

// ===== 执行测试 =====
async function runTests() {
  if (isRunning.value) return
  if (!props.model) return

  const tests = currentTests.value
  const selected = tests.filter(t => t.checked)
  if (selected.length === 0) {
    hint.value = t('modelTestDialog.errors.noTestSelected')
    hintError.value = true
    return
  }

  const providerExists = props.providers.some(
    p => String(p?.name) === String(props.model?.api_provider)
  )
  if (!providerExists) {
    hint.value = (t('modelTestDialog.errors.providerNotFound') as string) + `: ${props.model?.api_provider}`
    hintError.value = true
    return
  }

  hint.value = ''
  hintError.value = false
  isRunning.value = true

  // 重置勾选项状态，未勾选项保持未测试
  selected.forEach(test => {
    test.status = 'running'
    test.result = null
    test.error = ''
  })

  const tasks = selected.map((test) => runSingleTest(test))
  await Promise.allSettled(tasks)

  isRunning.value = false
}

async function runSingleTest(test: TestItem) {
  try {
    let request: ModelTestRequest
    if (activeType.value === 'llm') {
      // LLM 测试项统一使用后端默认提示词，无需前端提供测试提示词
      request = buildSnapshot({
        test_type: test.key as LLMTestKey,
      })
    } else if (activeType.value === 'embedding') {
      request = buildSnapshot({
        test_type: 'embedding',
        test_prompt: '人工智能改变了世界',
        dimensions: embeddingDimensions.value || null,
      })
    } else {
      request = buildSnapshot({
        test_type: 'rerank',
        test_prompt: rerankQuery.value,
        top_n: rerankTopN.value || null,
      })
    }

    const result = await apiTestModel(request)
    test.status = result.success ? 'success' : 'fail'
    test.result = result
    if (!result.success) {
      test.error = result.error_message || t('modelTestDialog.errors.failed')
    }
  } catch (error: unknown) {
    test.status = 'fail'
    test.result = null
    if (error && typeof error === 'object' && 'notFound' in error) {
      test.error = (error as any).message
    } else {
      const message = isAxiosError(error)
        ? error.response?.data?.message ?? error.response?.data?.detail ?? error.message
        : error && typeof error === 'object' && 'message' in error ? error.message : null
      test.error = typeof message === 'string' ? message : t('modelTestDialog.errors.failed')
    }
  }
}

// ===== 关闭 =====
function handleClose() {
  if (isRunning.value) return
  emit('close')
}

function handleOverlayClick() {
  if (isRunning.value) return
  emit('close')
}

// 重置状态
watch(() => props.isOpen, (open) => {
  if (open) {
    resetTests()
    isRunning.value = false
    hint.value = ''
    hintError.value = false
  }
}, { immediate: true })
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.dialog-container {
  background: var(--md-sys-color-surface);
  border-radius: 16px;
  width: min(92vw, 860px);
  /* 固定高度：切换模型种类（项数不同）时弹窗高度保持不变，内容在内部滚动 */
  height: min(50vh, 620px);
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.3s;
  overflow: hidden;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  flex-shrink: 0;
}

.dialog-title {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.dialog-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.subtitle {
  margin: 2px 0 0 0;
  font-size: 13px;
  color: var(--md-sys-color-on-surface-variant);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
}

.close-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dialog-body {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

/* 左侧导航 */
.type-sidebar {
  width: 180px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  background: var(--md-sys-color-surface-container);
  border-right: 1px solid var(--md-sys-color-outline-variant);
  overflow-y: auto;
}

.type-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  font-size: 14px;
  font-weight: 500;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  text-align: left;
}

.type-btn:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
}

.type-btn.active {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  font-weight: 600;
}

.type-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 右侧测试面板 */
.test-panel {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 10px 14px;
  font-size: 13px;
  border-radius: 8px;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface-variant);
}

.hint.error {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.test-item {
  background: var(--md-sys-color-surface-container);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  padding: 14px 16px;
}

.test-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.test-row.disabled {
  cursor: not-allowed;
  opacity: 0.85;
}

.test-row input[type="checkbox"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-box {
  position: relative;
  width: 20px;
  height: 20px;
  margin-top: 2px;
  border: 2px solid var(--md-sys-color-outline);
  border-radius: 4px;
  background: var(--md-sys-color-surface);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.checkbox-box :deep(svg) {
  opacity: 0;
  transform: scale(0);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--md-sys-color-on-primary);
}

.test-row input[type="checkbox"]:checked + .checkbox-box {
  background: var(--md-sys-color-primary);
  border-color: var(--md-sys-color-primary);
}

.test-row input[type="checkbox"]:checked + .checkbox-box :deep(svg) {
  opacity: 1;
  transform: scale(1);
}

.test-row:hover .checkbox-box {
  border-color: var(--md-sys-color-primary);
}

.test-row input:disabled + .checkbox-box {
  opacity: 0.5;
}

.test-icon {
  color: var(--md-sys-color-primary);
  flex-shrink: 0;
}

.test-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.test-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.test-desc {
  font-size: 12px;
  line-height: 1.4;
  color: var(--md-sys-color-on-surface-variant);
}

.test-extra {
  margin-top: 10px;
}

/* 参数输入 */
.option-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-row {
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: 12px;
}

.option-field label {
  font-size: 13px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
}

.option-field input {
  padding: 10px 14px;
  font-size: 14px;
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 8px;
  font-family: inherit;
  transition: all 0.2s;
}

.option-field input:focus {
  outline: none;
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 2px var(--md-sys-color-primary-container);
}

.option-field input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-hint {
  margin: 0;
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  line-height: 1.4;
}

/* VLM 测试提示：说明测试发送的是红色正方形图片 */
.vlm-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 10px 2px 0 2px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--md-sys-color-on-secondary-container);
  background: var(--md-sys-color-secondary-container);
}

.vlm-hint .iconify {
  flex-shrink: 0;
}

/* 底部操作区 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--md-sys-color-outline-variant);
  flex-shrink: 0;
}

.footer-status {
  margin-right: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--md-sys-color-on-surface-variant);
}

.cancel-btn,
.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 2.5rem;
  padding: 0 1.25rem;
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  gap: 6px;
}

.cancel-btn {
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
}

.cancel-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--md-sys-color-surface-container) 60%, transparent);
  color: var(--md-sys-color-on-surface);
}

.submit-btn {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.submit-btn:hover:not(:disabled) {
  box-shadow: 0 2px 8px rgba(0, 88, 189, 0.3);
  transform: translateY(-1px);
}

.submit-btn:disabled,
.cancel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .dialog-container {
    width: 95vw;
    height: 78vh;
    max-height: 78vh;
  }

  .dialog-body {
    flex-direction: column;
  }

  .type-sidebar {
    width: 100%;
    flex-direction: row;
    border-right: none;
    border-bottom: 1px solid var(--md-sys-color-outline-variant);
    padding: 10px 12px;
    overflow-x: auto;
  }

  .type-btn {
    flex-shrink: 0;
    padding: 10px 14px;
  }

  .test-panel {
    padding: 16px;
  }

  .option-row {
    grid-template-columns: 1fr;
  }

  .dialog-footer {
    flex-wrap: wrap;
  }

  .footer-status {
    width: 100%;
    margin-right: 0;
  }
}
</style>