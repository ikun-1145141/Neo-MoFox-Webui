<!--
  @file ModelEditDialog.vue
  @description 模型配置编辑对话框（供应商/模型/任务通用）
  
  功能：
  - 表单式编辑配置项
  - 支持供应商、模型、任务三种类型
  - 表单验证
  - Material Design 3 样式
-->
<template>
  <Teleport to="body">
    <div v-if="isOpen" class="dialog-overlay" @click="handleOverlayClick">
      <div class="dialog-container" @click.stop>
        <div class="dialog-header">
          <h2>{{ title }}</h2>
          <button type="button" class="close-btn" @click="handleClose">
            <Icon icon="material-symbols:close-rounded" :size="24" />
          </button>
        </div>

        <div class="dialog-body">
          <!-- 供应商表单 -->
          <form v-if="type === 'provider'" class="edit-form" @submit.prevent="handleSubmit">
            <div class="form-field">
              <label for="provider-name">提供商名称 *</label>
              <input
                id="provider-name"
                v-model="formData.name"
                type="text"
                placeholder="例如: OpenAI, SiliconFlow"
                required
              />
            </div>

            <div class="form-field">
              <label for="provider-base-url">Base URL *</label>
              <input
                id="provider-base-url"
                v-model="formData.base_url"
                type="url"
                placeholder="https://api.example.com/v1"
                required
              />
            </div>

            <div class="form-field">
              <label for="provider-api-key">API Key *</label>
              <input
                id="provider-api-key"
                v-model="formData.api_key"
                type="password"
                placeholder="your-api-key"
                required
              />
            </div>

            <div class="form-field">
              <label for="provider-client-type">客户端类型 *</label>
              <select id="provider-client-type" v-model="formData.client_type" required>
                <option value="openai">OpenAI</option>
                <option value="gemini">Gemini</option>
                <option value="bedrock">Bedrock</option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label for="provider-max-retry">最大重试次数</label>
                <input
                  id="provider-max-retry"
                  v-model.number="formData.max_retry"
                  type="number"
                  min="0"
                  max="10"
                />
              </div>

              <div class="form-field">
                <label for="provider-timeout">超时时间（秒）</label>
                <input
                  id="provider-timeout"
                  v-model.number="formData.timeout"
                  type="number"
                  min="1"
                  max="300"
                />
              </div>

              <div class="form-field">
                <label for="provider-retry-interval">重试间隔（秒）</label>
                <input
                  id="provider-retry-interval"
                  v-model.number="formData.retry_interval"
                  type="number"
                  min="1"
                  max="60"
                />
              </div>
            </div>
          </form>

          <!-- 模型表单 -->
          <form v-else-if="type === 'model'" class="edit-form" @submit.prevent="handleSubmit">
            <div class="form-field">
              <label for="model-name">模型名称 *</label>
              <input
                id="model-name"
                v-model="formData.name"
                type="text"
                placeholder="例如: gpt-4, deepseek-v3"
                required
              />
            </div>

            <div class="form-field">
              <label for="model-identifier">模型标识符 *</label>
              <input
                id="model-identifier"
                v-model="formData.model_identifier"
                type="text"
                placeholder="例如: openai/gpt-4"
                required
              />
            </div>

            <div class="form-field">
              <label for="model-provider">所属提供商 *</label>
              <select id="model-provider" v-model="formData.api_provider" required>
                <option v-for="p in providers" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label for="model-price-in">输入价格（¥/M tokens）</label>
                <input
                  id="model-price-in"
                  v-model.number="formData.price_in"
                  type="number"
                  step="0.01"
                  min="0"
                />
              </div>

              <div class="form-field">
                <label for="model-price-out">输出价格（¥/M tokens）</label>
                <input
                  id="model-price-out"
                  v-model.number="formData.price_out"
                  type="number"
                  step="0.01"
                  min="0"
                />
              </div>
            </div>

            <div class="form-field">
              <label for="model-max-context">最大上下文长度</label>
              <input
                id="model-max-context"
                v-model.number="formData.max_context"
                type="number"
                min="1024"
                step="1024"
              />
            </div>

            <div class="form-field checkbox-field">
              <input
                id="model-force-stream"
                v-model="formData.force_stream_mode"
                type="checkbox"
              />
              <label for="model-force-stream">强制流式输出模式</label>
            </div>

            <div class="form-field checkbox-field">
              <input
                id="model-tool-call-compat"
                v-model="formData.tool_call_compat"
                type="checkbox"
              />
              <label for="model-tool-call-compat">Tool Call 兼容模式</label>
            </div>

            <div class="form-field checkbox-field">
              <input
                id="model-anti-truncation"
                v-model="formData.anti_truncation"
                type="checkbox"
              />
              <label for="model-anti-truncation">启用反截断</label>
            </div>
          </form>

          <!-- 任务表单 -->
          <form v-else-if="type === 'task'" class="edit-form" @submit.prevent="handleSubmit">
            <div class="form-field">
              <label for="task-name">任务名称 *</label>
              <input
                id="task-name"
                v-model="formData.name"
                type="text"
                placeholder="例如: utils, vlm, embedding"
                required
                :disabled="mode === 'edit'"
              />
              <span v-if="mode === 'edit'" class="field-hint">任务名称不可修改</span>
            </div>

            <div class="form-field">
              <label for="task-models">模型列表 *</label>
              <div class="model-list-editor">
                <div
                  v-for="(_, idx) in formData.model_list"
                  :key="idx"
                  class="model-list-item"
                >
                  <input
                    v-model="formData.model_list[idx]"
                    type="text"
                    placeholder="模型名称"
                    required
                  />
                  <button
                    type="button"
                    class="remove-btn"
                    @click="removeModel(Number(idx))"
                    :disabled="formData.model_list.length === 1"
                  >
                    <Icon icon="material-symbols:close-rounded" :size="18" />
                  </button>
                </div>
                <button type="button" class="add-model-btn" @click="addModel">
                  <Icon icon="material-symbols:add-rounded" :size="18" />
                  <span>添加模型</span>
                </button>
              </div>
            </div>

            <div class="form-row">
              <div class="form-field">
                <label for="task-max-tokens">最大 Tokens</label>
                <input
                  id="task-max-tokens"
                  v-model.number="formData.max_tokens"
                  type="number"
                  min="1"
                  step="1"
                />
              </div>

              <div class="form-field">
                <label for="task-temperature">温度</label>
                <input
                  id="task-temperature"
                  v-model.number="formData.temperature"
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                />
              </div>
            </div>
          </form>
        </div>

        <div class="dialog-footer">
          <button type="button" class="cancel-btn" @click="handleClose">
            取消
          </button>
          <button type="button" class="submit-btn" @click="handleSubmit">
            {{ mode === 'add' ? '添加' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Icon from '../common/Icon.vue'

// Props
interface Props {
  isOpen: boolean
  type: 'provider' | 'model' | 'task'
  mode: 'add' | 'edit'
  data?: Record<string, any>
  providers?: string[] // 模型编辑时需要的提供商列表
}

const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  type: 'provider',
  mode: 'add',
  data: () => ({}),
  providers: () => [],
})

// Emits
const emit = defineEmits<{
  close: []
  submit: [data: Record<string, any>]
}>()

// 表单数据
const formData = ref<Record<string, any>>({})

// 标题
const title = ref('')

// 监听 props 变化初始化表单
watch(
  () => [props.isOpen, props.type, props.mode, props.data],
  () => {
    if (props.isOpen) {
      initForm()
    }
  },
  { immediate: true }
)

function initForm() {
  // 设置标题
  if (props.type === 'provider') {
    title.value = props.mode === 'add' ? '添加供应商' : '编辑供应商'
  } else if (props.type === 'model') {
    title.value = props.mode === 'add' ? '添加模型' : '编辑模型'
  } else {
    title.value = props.mode === 'add' ? '添加任务' : '编辑任务'
  }

  // 初始化表单数据
  if (props.mode === 'add') {
    if (props.type === 'provider') {
      formData.value = {
        name: '',
        base_url: '',
        api_key: '',
        client_type: 'openai',
        max_retry: 3,
        timeout: 30,
        retry_interval: 10,
      }
    } else if (props.type === 'model') {
      formData.value = {
        name: '',
        model_identifier: '',
        api_provider: props.providers[0] || '',
        price_in: 0.0,
        price_out: 0.0,
        force_stream_mode: false,
        max_context: 32768,
        tool_call_compat: false,
        extra_params: {},
        anti_truncation: false,
      }
    } else {
      formData.value = {
        name: '',
        model_list: [''],
        max_tokens: 4096,
        temperature: 0.7,
      }
    }
  } else {
    // 编辑模式：复制现有数据
    formData.value = JSON.parse(JSON.stringify(props.data))
    
    // 任务类型特殊处理：确保 model_list 是数组
    if (props.type === 'task' && !Array.isArray(formData.value.model_list)) {
      formData.value.model_list = []
    }
  }
}

// 任务：添加模型
function addModel() {
  if (!formData.value.model_list) {
    formData.value.model_list = []
  }
  formData.value.model_list.push('')
}

// 任务：移除模型
function removeModel(index: number) {
  if (formData.value.model_list && formData.value.model_list.length > 1) {
    formData.value.model_list.splice(index, 1)
  }
}

// 处理关闭
function handleClose() {
  emit('close')
}

// 处理遮罩点击
function handleOverlayClick() {
  handleClose()
}

// 处理提交
function handleSubmit() {
  // 简单验证
  if (props.type === 'provider') {
    if (!formData.value.name || !formData.value.base_url || !formData.value.api_key) {
      alert('请填写必填字段')
      return
    }
  } else if (props.type === 'model') {
    if (!formData.value.name || !formData.value.model_identifier || !formData.value.api_provider) {
      alert('请填写必填字段')
      return
    }
  } else if (props.type === 'task') {
    if (!formData.value.name || !formData.value.model_list || formData.value.model_list.length === 0) {
      alert('请填写必填字段')
      return
    }
    // 移除空的模型名称
    formData.value.model_list = formData.value.model_list.filter((m: string) => m.trim())
    if (formData.value.model_list.length === 0) {
      alert('至少需要一个模型')
      return
    }
  }

  emit('submit', formData.value)
}
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
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.3s;
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
  color: var(--md-sys-color-on-surface);
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
.form-field input[type="url"],
.form-field input[type="password"],
.form-field input[type="number"],
.form-field select {
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
.form-field select:focus {
  outline: none;
  border-color: var(--md-sys-color-primary);
  box-shadow: 0 0 0 2px var(--md-sys-color-primary-container);
}

.form-field input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.checkbox-field {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.checkbox-field input[type="checkbox"] {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.checkbox-field label {
  margin: 0;
  cursor: pointer;
}

.model-list-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-list-item {
  display: flex;
  gap: 8px;
}

.model-list-item input {
  flex: 1;
}

.remove-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.remove-btn:hover:not(:disabled) {
  background: var(--md-sys-color-error);
  color: var(--md-sys-color-on-error);
}

.remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-model-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.add-model-btn:hover {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

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
