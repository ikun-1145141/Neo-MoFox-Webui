<!--
  @file UIButton.vue
  @description 按钮组件，支持点击执行 API 请求、触发声明式动作和确认弹窗。
  消费共享工具：dataStore（getValueByPath / setValueByPath）、apiExecutor（executeApiCall / resolveEndpoint / parseActions / resolveRequestData）。
-->
<template>
  <button
    :class="['ui-button', `btn-${type}`, `btn-${size}`]"
    :disabled="node.attrs.disabled === 'true' || loading"
    @click="handleClick"
  >
    <span v-if="loading" class="btn-spinner"></span>
    <span v-else-if="node.attrs.icon" class="material-symbols-outlined btn-icon">
      {{ node.attrs.icon }}
    </span>
    <span class="btn-label">
      <slot>{{ evaluate(node.text || '') }}</slot>
    </span>
  </button>
</template>

<script setup lang="ts">
import { ref, computed, inject, nextTick } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import { executeApiCall, resolveRequestData, replacePathParams } from '@/utils/apiExecutor'
import { dialog } from '@/utils/dialog'
import { useToastStore } from '@/utils/toast'

interface Props {
  node: UiNode
  store?: Record<string, any>
  apiBase?: string
}

const props = defineProps<Props>()

const toast = useToastStore()

const dataStore = props.store || inject<any>('uiSchemaDataStore')
const evaluate = inject<any>('uiSchemaEvaluate')
const executeActions = inject<any>('uiSchemaExecuteActions')
const localContext = inject<any>('uiSchemaLocalContext', {})
const injectedApiBase = inject<string>('uiSchemaApiBase', '')
const pluginName = inject<string | null>('uiSchemaPluginName', null)

const loading = ref(false)

const type = computed(() => props.node.attrs.type || 'primary')
const size = computed(() => props.node.attrs.size || 'normal')

async function handleClick() {
  const attrs = props.node.attrs
  const confirmMsg = attrs['confirm-message']

  // 1. 确认弹窗
  if (confirmMsg) {
    const confirmed = await dialog.confirm(evaluate(confirmMsg))
    if (!confirmed) return
  }

  // 2. 表单校验（如果是 POST/PUT 提交表单）
  const method = attrs['api-method']?.toUpperCase()
  if (method === 'POST' || method === 'PUT') {
    if (dataStore) {
      dataStore.validationTrigger = (dataStore.validationTrigger || 0) + 1
      await nextTick()
      if (dataStore.errors && Object.keys(dataStore.errors).length > 0) {
        toast.show('请先修正表单中的错误', 'error')
        return
      }
    }
  }

  // 3. 执行 API 请求
  const endpoint = attrs['api-endpoint']
  if (endpoint) {
    loading.value = true
    try {
      const apiBaseVal = props.apiBase || injectedApiBase

      // 路径参数替换
      const pathContext: Record<string, any> = {}
      if (localContext.row) {
        Object.assign(pathContext, localContext.row)
      }
      const finalEndpoint = replacePathParams(endpoint, pathContext)

      // 解析请求体数据来源
      const dataFrom = attrs['api-data-from']
      let requestData: any = undefined
      if (dataFrom) {
        if (dataFrom === 'row') {
          requestData = localContext.row
        } else {
          requestData = resolveRequestData(dataStore, dataFrom)
        }
      }

      const res = await executeApiCall({
        endpoint: finalEndpoint,
        method: (method as any) || 'GET',
        apiBase: apiBaseVal,
        data: requestData,
        pluginName,
      })

      // 将响应数据存入 dataStore.response
      if (dataStore) {
        dataStore.response = res
      }

      // 触发成功动作
      if (attrs['on-success']) {
        executeActions(attrs['on-success'], { row: localContext.row })
      }
    } catch (e: any) {
      console.error('API execution failed:', e)
      // 触发失败动作
      if (attrs['on-error']) {
        executeActions(attrs['on-error'], { row: localContext.row, error: e })
      }
    } finally {
      loading.value = false
    }
    return
  }

  // 4. 执行直接动作（如 action="open-dialog:createUserDialog"）
  const directAction = attrs.action
  if (directAction) {
    executeActions(directAction, { row: localContext.row })
  }
}
</script>

<style scoped>
.ui-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: inherit;
  font-weight: 500;
  border-radius: 100px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
  box-sizing: border-box;
}

/* 尺寸样式 */
.btn-small {
  padding: 6px 16px;
  font-size: 12px;
  height: 32px;
}

.btn-normal {
  padding: 10px 24px;
  font-size: 14px;
  height: 40px;
}

.btn-large {
  padding: 14px 32px;
  font-size: 16px;
  height: 48px;
}

/* 类型样式 */
.btn-primary {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.btn-primary:hover:not(:disabled) {
  box-shadow: var(--md-sys-elevation-1);
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
}

.btn-secondary {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  border: 1px solid var(--md-sys-color-outline-variant);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-high);
}

.btn-danger {
  background: var(--md-sys-color-error);
  color: var(--md-sys-color-on-error);
}

.btn-danger:hover:not(:disabled) {
  box-shadow: var(--md-sys-elevation-1);
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.btn-text {
  background: transparent;
  color: var(--md-sys-color-primary);
  border-radius: 8px;
}

.btn-text.btn-small {
  padding: 4px 8px;
}

.btn-text.btn-normal {
  padding: 8px 12px;
}

.btn-text:hover:not(:disabled) {
  background: var(--md-sys-color-surface-container-low);
}

.ui-button:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 18px;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
