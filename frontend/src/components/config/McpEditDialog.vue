<!--
  @file McpEditDialog.vue
  @description MCP 服务配置编辑对话框

  功能：
  - 表单式编辑 Stdio / SSE / Streamable HTTP 类型的 MCP 服务
  - 支持 instructions、defer_loading、headers、timeout 等完整字段
  - Material Design 3 样式
-->
<template>
  <Teleport to="body">
    <div v-if="isOpen" class="dialog-overlay" @click="handleClose">
      <div class="dialog-container" @click.stop>
        <div class="dialog-header">
          <h2>{{ t(`mcpEditDialog.title.${mode}`) }}</h2>
          <button type="button" class="close-btn" @click="handleClose">
            <Icon icon="material-symbols:close-rounded" :size="24" />
          </button>
        </div>

        <div class="dialog-body">
          <form class="edit-form" @submit.prevent="handleSubmit">
            <!-- 服务名称 -->
            <div class="form-field">
              <label for="mcp-name">{{ t('mcpEditDialog.fields.name') }} *</label>
              <input
                id="mcp-name"
                v-model="formData.name"
                type="text"
                :placeholder="t('mcpEditDialog.fields.namePlaceholder')"
                required
                :disabled="mode === 'edit'"
              />
              <span v-if="mode === 'edit'" class="field-hint">{{ t('mcpEditDialog.fields.nameHint') }}</span>
            </div>

            <!-- Stdio 专有字段 -->
            <template v-if="type === 'stdio'">
              <div class="form-field">
                <label for="mcp-command">{{ t('mcpEditDialog.fields.command') }} *</label>
                <input
                  id="mcp-command"
                  v-model="formData.command"
                  type="text"
                  :placeholder="t('mcpEditDialog.fields.commandPlaceholder')"
                  required
                />
              </div>

              <div class="form-field">
                <label for="mcp-args">{{ t('mcpEditDialog.fields.args') }}</label>
                <p class="field-description">{{ t('mcpEditDialog.fields.argsDesc') }}</p>
                <textarea
                  id="mcp-args"
                  v-model="argsText"
                  rows="4"
                  :placeholder="t('mcpEditDialog.fields.argsPlaceholder')"
                />
              </div>

              <div class="form-field">
                <label for="mcp-env">{{ t('mcpEditDialog.fields.env') }}</label>
                <p class="field-description">{{ t('mcpEditDialog.fields.envDesc') }}</p>
                <textarea
                  id="mcp-env"
                  v-model="envText"
                  rows="3"
                  placeholder="API_KEY=xxx"
                />
              </div>
            </template>

            <!-- SSE / Streamable 专有字段 -->
            <template v-else>
              <div class="form-field">
                <label for="mcp-url">{{ t('mcpEditDialog.fields.url') }} *</label>
                <input
                  id="mcp-url"
                  v-model="formData.url"
                  type="text"
                  :placeholder="t('mcpEditDialog.fields.urlPlaceholder')"
                  required
                />
              </div>

              <div class="form-field">
                <label for="mcp-headers">{{ t('mcpEditDialog.fields.headers') }}</label>
                <p class="field-description">{{ t('mcpEditDialog.fields.headersDesc') }}</p>
                <textarea
                  id="mcp-headers"
                  v-model="headersText"
                  rows="3"
                  placeholder="Authorization=Bearer xxx"
                />
              </div>

              <div class="form-row">
                <div class="form-field">
                  <label for="mcp-timeout">{{ t('mcpEditDialog.fields.timeout') }}</label>
                  <input
                    id="mcp-timeout"
                    v-model.number="formData.timeout"
                    type="number"
                    min="1"
                    max="300"
                    placeholder="30"
                  />
                </div>
              </div>
            </template>

            <!-- 公共字段：Instructions -->
            <div class="form-field">
              <label for="mcp-instructions">{{ t('mcpEditDialog.fields.instructions') }}</label>
              <p class="field-description">{{ t('mcpEditDialog.fields.instructionsDesc') }}</p>
              <textarea
                id="mcp-instructions"
                v-model="formData.instructions"
                rows="3"
                placeholder=""
              />
            </div>

            <!-- 公共字段：Defer Loading -->
            <div class="form-field checkbox-field">
              <label class="custom-checkbox">
                <input
                  id="mcp-defer-loading"
                  v-model="formData.defer_loading"
                  type="checkbox"
                />
                <span class="checkbox-box">
                  <Icon v-show="formData.defer_loading" icon="material-symbols:check-rounded" :size="16" />
                </span>
                <span class="checkbox-label">{{ t('mcpEditDialog.fields.deferLoading') }}</span>
              </label>
              <p class="field-description checkbox-desc">{{ t('mcpEditDialog.fields.deferLoadingDesc') }}</p>
            </div>
          </form>
        </div>

        <div class="dialog-footer">
          <button type="button" class="cancel-btn" @click="handleClose">
            {{ t('mcpEditDialog.actions.cancel') }}
          </button>
          <button type="button" class="submit-btn" @click="handleSubmit">
            {{ mode === 'add' ? t('mcpEditDialog.actions.add') : t('mcpEditDialog.actions.save') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from '@/utils/i18n'
import { useDialogStore } from '@/utils/dialog'
import Icon from '../common/Icon.vue'

const { t } = useI18n()
const dialogStore = useDialogStore()

type McpTab = 'stdio' | 'sse' | 'streamable'

interface Props {
  isOpen: boolean
  type: McpTab
  mode: 'add' | 'edit'
  data?: Record<string, any>
}

const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  type: 'stdio',
  mode: 'add',
  data: () => ({}),
})

const emit = defineEmits<{
  close: []
  submit: [data: Record<string, any>]
}>()

const formData = ref<Record<string, any>>({})
const argsText = ref('')
const envText = ref('')
const headersText = ref('')

watch(
  () => [props.isOpen, props.type, props.mode, props.data],
  () => {
    if (!props.isOpen) return
    initForm()
  },
  { immediate: true, deep: true }
)

function initForm() {
  const data = props.data || {}

  if (props.type === 'stdio') {
    formData.value = {
      name: data.name || '',
      command: data.command || '',
      instructions: data.instructions || '',
      defer_loading: data.defer_loading ?? true,
    }
    argsText.value = Array.isArray(data.args) ? data.args.join('\n') : ''
    envText.value = data.env && typeof data.env === 'object'
      ? Object.entries(data.env).map(([k, v]) => `${k}=${v}`).join('\n')
      : ''
  } else {
    // SSE / Streamable
    const isObject = typeof data.value === 'object' && data.value !== null
    const urlValue = isObject ? data.value?.url : (typeof data.value === 'string' ? data.value : '')
    // If data was spread from object value (edit mode from McpConfigEditor)
    const url = data.url || urlValue || ''
    const headers = isObject ? data.value?.headers : (data.headers || null)
    const timeout = isObject ? data.value?.timeout : (data.timeout || null)
    const instructions = isObject ? data.value?.instructions : (data.instructions || '')
    const deferLoading = isObject ? data.value?.defer_loading : (data.defer_loading ?? true)

    formData.value = {
      name: data.name || '',
      url,
      timeout: timeout || '',
      instructions: instructions || '',
      defer_loading: deferLoading ?? true,
    }
    headersText.value = headers && typeof headers === 'object'
      ? Object.entries(headers).map(([k, v]) => `${k}=${v}`).join('\n')
      : ''
  }
}

function parseKeyValueText(text: string): Record<string, string> {
  const result: Record<string, string> = {}
  text.split('\n').map(l => l.trim()).filter(Boolean).forEach(line => {
    const idx = line.indexOf('=')
    if (idx > 0) {
      result[line.slice(0, idx).trim()] = line.slice(idx + 1).trim()
    }
  })
  return result
}

function handleClose() {
  emit('close')
}

async function handleSubmit() {
  if (!formData.value.name) {
    await dialogStore.alert(t('mcpEditDialog.errors.requiredFields'))
    return
  }

  if (props.type === 'stdio') {
    if (!formData.value.command) {
      await dialogStore.alert(t('mcpEditDialog.errors.requiredFields'))
      return
    }

    const result: Record<string, any> = {
      name: formData.value.name,
      command: formData.value.command,
    }
    const args = argsText.value.split('\n').map(l => l.trim()).filter(Boolean)
    const env = parseKeyValueText(envText.value)
    if (args.length > 0) result.args = args
    if (Object.keys(env).length > 0) result.env = env
    if (formData.value.instructions) result.instructions = formData.value.instructions
    if (formData.value.defer_loading !== undefined) result.defer_loading = formData.value.defer_loading

    emit('submit', result)
    return
  }

  // SSE / Streamable
  if (!formData.value.url) {
    await dialogStore.alert(t('mcpEditDialog.errors.requiredFields'))
    return
  }

  const headers = parseKeyValueText(headersText.value)
  const hasExtra = Object.keys(headers).length > 0
    || (formData.value.timeout && formData.value.timeout > 0)
    || formData.value.instructions
    || formData.value.defer_loading === false

  if (!hasExtra) {
    // Simple URL string
    emit('submit', { name: formData.value.name, value: formData.value.url })
    return
  }

  // Object value with details
  const valueObj: Record<string, any> = { url: formData.value.url }
  if (Object.keys(headers).length > 0) valueObj.headers = headers
  if (formData.value.timeout && formData.value.timeout > 0) valueObj.timeout = formData.value.timeout
  if (formData.value.instructions) valueObj.instructions = formData.value.instructions
  if (formData.value.defer_loading !== undefined) valueObj.defer_loading = formData.value.defer_loading

  emit('submit', { name: formData.value.name, value: valueObj })
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.dialog-container {
  width: min(680px, calc(100vw - 48px));
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.3s cubic-bezier(0.2, 0, 0, 1);
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
}

.dialog-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
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

.close-btn:hover {
  background: var(--md-sys-color-surface-container-highest);
  color: var(--md-sys-color-on-surface);
}

.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-field label {
  font-size: 14px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface);
}

.form-field input[type="text"],
.form-field input[type="number"],
.form-field textarea {
  padding: 12px 16px;
  font-size: 14px;
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 8px;
  font-family: inherit;
  transition: all 0.2s;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 2px var(--md-sys-color-primary-container);
}

.form-field input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-field textarea {
  resize: vertical;
  min-height: 72px;
  line-height: 1.5;
  font-family: 'Cascadia Code', Consolas, Monaco, monospace;
}

.field-description {
  font-size: 13px;
  color: var(--md-sys-color-on-surface-variant);
  margin: -4px 0 4px 0;
  line-height: 1.4;
}

.field-hint {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

/* Checkbox */
.checkbox-field {
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
}

.custom-checkbox {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
}

.custom-checkbox input[type="checkbox"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-box {
  position: relative;
  width: 20px;
  height: 20px;
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

.custom-checkbox input[type="checkbox"]:checked + .checkbox-box {
  background: var(--md-sys-color-primary);
  border-color: var(--md-sys-color-primary);
}

.custom-checkbox input[type="checkbox"]:checked + .checkbox-box :deep(svg) {
  opacity: 1;
  transform: scale(1);
}

.custom-checkbox:hover .checkbox-box {
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 8px color-mix(in srgb, var(--md-sys-color-primary) 12%, transparent);
}

.checkbox-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface);
}

.checkbox-desc {
  width: 100%;
  margin: 4px 0 0 32px;
}

/* Footer */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--md-sys-color-outline-variant);
}

.cancel-btn,
.submit-btn {
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.cancel-btn {
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
}

.cancel-btn:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.submit-btn {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.submit-btn:hover {
  box-shadow: 0 2px 8px rgba(0, 88, 189, 0.3);
  transform: translateY(-1px);
}
</style>
