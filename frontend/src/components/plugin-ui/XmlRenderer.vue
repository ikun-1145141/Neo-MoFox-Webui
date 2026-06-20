<script setup lang="ts">
/**
 * XML 渲染器 Vue 组件。
 *
 * 接收 XML 字符串，通过 xml-renderer.ts 转换为 Vue VNode 树进行渲染。
 * 管理 <definitions> 预处理、变量池初始化、管道上下文构建。
 */
import { ref, computed, watch, onUnmounted, type VNode } from 'vue'
import { useRouter } from 'vue-router'
import type { PluginUIVarStore } from '../../stores/plugin-ui-vars'
import { parseXml, processDefinitions, renderElementToVNodes, type XmlRenderContext } from '../../utils/plugin-ui/xml-renderer'
import { ApiTemplateEngine } from '../../utils/plugin-ui/api-template-engine'
import type { PipeContext } from '../../utils/plugin-ui/pipe-executor'
import { useToastStore } from '../../utils/toast'
import { useDialogStore } from '../../utils/dialog'

const props = defineProps<{
  /** XML 字符串 */
  xml: string
  /** 变量池 Store */
  store: PluginUIVarStore
  /** 插件名称 */
  pluginName: string
  /** 是否为移动端 */
  isMobile?: boolean
}>()

const emit = defineEmits<{
  /** XML 解析错误 */
  (e: 'error', message: string): void
}>()

const router = useRouter()

// === API 模板引擎 ===
const apiEngine = new ApiTemplateEngine(props.store)

// === 事件总线（page 级） ===
const busListeners = new Map<string, Set<(...args: any[]) => void>>()

function busEmit(event: string, payload?: any): void {
  const listeners = busListeners.get(event)
  if (listeners) {
    for (const fn of listeners) {
      fn(payload)
    }
  }
}

// === 组件 refresh 注册表 ===
const refreshRegistry = new Map<string, () => void>()

function refreshComponent(componentId: string): void {
  const fn = refreshRegistry.get(componentId)
  if (fn) fn()
}

// === 管道执行上下文 ===
const toastStore = useToastStore()
const dialogStore = useDialogStore()

const pipeContext: PipeContext = {
  store: props.store,
  apiEngine,
  router,
  pluginName: props.pluginName,
  notify: (message: string, level?: 'info' | 'success' | 'warning' | 'error') => {
    // 将 warning 映射到 toast 支持的 type
    const typeMap: Record<string, 'info' | 'success' | 'error'> = {
      info: 'info',
      success: 'success',
      warning: 'info',
      error: 'error',
    }
    toastStore.show(message, typeMap[level || 'info'] || 'info')
  },
  confirm: (message: string): Promise<boolean> => {
    return dialogStore.confirm(message)
  },
  busEmit,
  refreshComponent,
}

// === 渲染核心 ===
const renderError = ref<string | null>(null)
const renderKey = ref(0)

const vnodes = computed<VNode[]>(() => {
  // 依赖 renderKey 触发重渲染
  void renderKey.value

  const xmlStr = props.xml
  if (!xmlStr) return []

  // 解析 XML
  const result = parseXml(xmlStr)
  if (!result.success || !result.document) {
    renderError.value = result.error
    emit('error', result.error || 'XML 解析失败')
    return []
  }

  renderError.value = null
  const doc = result.document

  // 处理 <definitions>
  const templates = processDefinitions(doc, props.store, apiEngine)

  // 构建渲染上下文
  const context: XmlRenderContext = {
    store: props.store,
    apiEngine,
    pipeContext,
    templates,
    isMobile: props.isMobile ?? false,
  }

  // 渲染根元素
  const root = doc.documentElement
  return renderElementToVNodes(root, context)
})

// === 自动执行 autoFetch API ===
// 注意：监听 props.xml 而非 vnodes。因为 vnodes computed 内部通过
// store.get() 读取了变量池，若监听 vnodes，executeAutoFetch 写入
// api.*.pending 等状态会导致 vnodes 重算，进而再次触发 watch，形成无限循环。
// 此处手动访问 vnodes.value 强制 computed 求值，确保 processDefinitions
// 已将 <api> 模板注册到 apiEngine 后再执行 autoFetch。
watch(
  () => props.xml,
  () => {
    void vnodes.value
    apiEngine.executeAutoFetch()
  },
  { immediate: true }
)

// === 清理 ===
onUnmounted(() => {
  apiEngine.destroy()
  busListeners.clear()
  refreshRegistry.clear()
})
</script>

<template>
  <div class="xml-renderer">
    <!-- 解析错误状态 -->
    <div v-if="renderError" class="xml-renderer-error">
      <span class="material-symbols-rounded">error</span>
      <div class="xml-renderer-error-content">
        <p class="xml-renderer-error-title">XML 解析失败</p>
        <pre class="xml-renderer-error-detail">{{ renderError }}</pre>
      </div>
    </div>

    <!-- 正常渲染 -->
    <template v-else>
      <component
        v-for="(vnode, index) in vnodes"
        :key="index"
        :is="() => vnode"
      />
    </template>
  </div>
</template>

<style scoped>
.xml-renderer {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.xml-renderer-error {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 12px;
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.xml-renderer-error .material-symbols-rounded {
  font-size: 24px;
  flex-shrink: 0;
}

.xml-renderer-error-content {
  flex: 1;
  min-width: 0;
}

.xml-renderer-error-title {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.xml-renderer-error-detail {
  margin: 0;
  padding: 0.5rem;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.05);
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow: auto;
}
</style>
