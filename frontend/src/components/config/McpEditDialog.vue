<!--
  @file McpEditDialog.vue
  @description MCP 服务配置编辑对话框
-->
<template>
  <Teleport to="body">
    <div v-if="isOpen" class="dialog-overlay" @click="handleClose">
      <div class="dialog-container" @click.stop>
        <div class="dialog-header">
          <h2>{{ title }}</h2>
          <button type="button" class="close-btn" @click="handleClose">
            <Icon icon="material-symbols:close-rounded" :size="24" />
          </button>
        </div>

        <div class="dialog-body">
          <form class="edit-form" @submit.prevent="handleSubmit">
            <div class="form-field">
              <label for="mcp-name">服务名称 *</label>
              <input
                id="mcp-name"
                v-model="formData.name"
                type="text"
                placeholder="例如: fetch"
                required
                :disabled="mode === 'edit'"
              />
              <span v-if="mode === 'edit'" class="field-hint">服务名称不可修改</span>
            </div>

            <template v-if="type === 'stdio'">
              <div class="form-field">
                <label for="mcp-command">命令 *</label>
                <input id="mcp-command" v-model="formData.command" type="text" placeholder="例如: npx / uvx" required />
              </div>

              <div class="form-field">
                <label for="mcp-args">参数</label>
                <p class="field-description">每行一个参数，会保存为 args 数组</p>
                <textarea id="mcp-args" v-model="argsText" rows="5" placeholder="-y&#10;@modelcontextprotocol/server-example" />
              </div>

              <div class="form-field">
                <label for="mcp-env">环境变量</label>
                <p class="field-description">每行一个 KEY=VALUE</p>
                <textarea id="mcp-env" v-model="envText" rows="4" placeholder="API_KEY=xxx" />
              </div>
            </template>

            <template v-else>
              <div class="form-field">
                <label for="mcp-url">URL *</label>
                <input id="mcp-url" v-model="formData.url" type="text" placeholder="http://localhost:3000/sse" required />
              </div>

              <div class="form-field">
                <label for="mcp-params">连接参数</label>
                <p class="field-description">可选 JSON 对象；留空时直接保存为 URL 字符串</p>
                <textarea id="mcp-params" v-model="paramsText" rows="5" placeholder='{"headers":{"Authorization":"Bearer xxx"}}' />
              </div>
            </template>
          </form>
        </div>

        <div class="dialog-footer">
          <button type="button" class="cancel-btn" @click="handleClose">取消</button>
          <button type="button" class="submit-btn" @click="handleSubmit">{{ mode === 'add' ? '添加' : '保存' }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Icon from '../common/Icon.vue'

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
const paramsText = ref('')

const title = computed(() => `${props.mode === 'add' ? '添加' : '编辑'} MCP 服务`)

watch(
  () => [props.isOpen, props.type, props.mode, props.data],
  () => {
    if (!props.isOpen) return
    const data = props.data || {}
    formData.value = {
      name: data.name || '',
      command: data.command || '',
      url: data.url || (typeof data.value === 'string' ? data.value : ''),
    }
    argsText.value = Array.isArray(data.args) ? data.args.join('\n') : ''
    envText.value = data.env && typeof data.env === 'object'
      ? Object.entries(data.env).map(([key, value]) => `${key}=${value}`).join('\n')
      : ''
    paramsText.value = data.params ? JSON.stringify(data.params, null, 2) : ''
  },
  { immediate: true, deep: true }
)

function parseEnv() {
  const env: Record<string, string> = {}
  envText.value.split('\n').map((line) => line.trim()).filter(Boolean).forEach((line) => {
    const separatorIndex = line.indexOf('=')
    if (separatorIndex > 0) {
      env[line.slice(0, separatorIndex).trim()] = line.slice(separatorIndex + 1).trim()
    }
  })
  return env
}

function handleClose() {
  emit('close')
}

function handleSubmit() {
  if (!formData.value.name) return

  if (props.type === 'stdio') {
    const result: Record<string, any> = {
      name: formData.value.name,
      command: formData.value.command,
    }
    const args = argsText.value.split('\n').map((line) => line.trim()).filter(Boolean)
    const env = parseEnv()
    if (args.length > 0) result.args = args
    if (Object.keys(env).length > 0) result.env = env
    emit('submit', result)
    return
  }

  const result: Record<string, any> = {
    name: formData.value.name,
    value: formData.value.url,
  }
  if (paramsText.value.trim()) {
    result.value = {
      url: formData.value.url,
      ...JSON.parse(paramsText.value),
    }
  }
  emit('submit', result)
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
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
}

.dialog-container {
  width: min(720px, calc(100vw - 32px));
  max-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  border-radius: 24px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.22);
  overflow: hidden;
}

.dialog-header,
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.dialog-footer {
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid var(--md-sys-color-outline-variant);
  border-bottom: none;
}

.dialog-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.dialog-body {
  padding: 24px;
  overflow-y: auto;
}

.edit-form,
.form-field {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  gap: 8px;
}

label {
  font-size: 14px;
  font-weight: 600;
}

input,
textarea {
  padding: 12px 14px;
  font: inherit;
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-container);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
}

textarea {
  resize: vertical;
  font-family: Consolas, Monaco, monospace;
}

.field-description,
.field-hint {
  margin: 0;
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
}

.close-btn,
.cancel-btn,
.submit-btn {
  border: none;
  font: inherit;
  cursor: pointer;
}

.close-btn {
  display: flex;
  padding: 6px;
  color: var(--md-sys-color-on-surface-variant);
  background: transparent;
  border-radius: 50%;
}

.cancel-btn,
.submit-btn {
  padding: 10px 20px;
  border-radius: 20px;
  font-weight: 600;
}

.cancel-btn {
  color: var(--md-sys-color-primary);
  background: transparent;
}

.submit-btn {
  color: var(--md-sys-color-on-primary);
  background: var(--md-sys-color-primary);
}
</style>
