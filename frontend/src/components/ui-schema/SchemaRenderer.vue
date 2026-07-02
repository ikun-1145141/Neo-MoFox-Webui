<!--
  @file SchemaRenderer.vue
  @description UI Schema 渲染引擎，解析 XML 并递归渲染组件树。
  消费共享工具：xmlParser（parseUiPage）、dataStore（createDataStore / getValueByPath / setValueByPath）、
  apiExecutor（resolveEndpoint / parseActions / executeApiCall）。
-->
<template>
  <div class="ui-schema-renderer" v-if="effectiveNode">
    <!-- 如果是根节点 ui-page，渲染页面头部和布局 -->
    <div v-if="effectiveNode.tag === 'ui-page'" class="ui-page-wrapper">
      <div v-if="pageMetadata" class="ui-page-header">
        <div class="title-row">
          <Icon v-if="pageMetadata.icon" :icon="pageMetadata.icon" width="32" height="32" class="header-icon" />
          <h1 class="page-title">{{ pageMetadata.title }}</h1>
        </div>
        <p v-if="pageMetadata.description" class="page-description">{{ pageMetadata.description }}</p>
      </div>

      <!-- 渲染布局子节点 -->
      <div class="ui-page-content">
        <SchemaRenderer
          v-for="(child, index) in layoutChildren"
          :key="index"
          :node="child"
          :store="store"
          :api-base="effectiveApiBase"
        />
      </div>
    </div>

    <!-- 否则，渲染单个节点 -->
    <div v-else class="ui-node-wrapper">
      <component
        :is="getComponent(effectiveNode.tag)"
        v-if="isRegisteredComponent(effectiveNode.tag)"
        :node="effectiveNode"
        :store="store"
        :api-base="effectiveApiBase"
      />
      <div v-else-if="effectiveNode.tag === 'text'" :style="effectiveNode.attrs.style" class="ui-text">
        {{ evaluate(effectiveNode.text || '') }}
      </div>
      <!-- template 节点：使用 v-html 渲染原始 HTML（含 Vue 模板语法） -->
      <div v-else-if="effectiveNode.tag === 'template'" class="ui-template" v-html="effectiveNode.rawTemplate || ''"></div>
      <!-- 回退到标准 HTML 标签 -->
      <component
        :is="effectiveNode.tag"
        v-else
        v-bind="getHtmlAttributes(effectiveNode.attrs)"
      >
        <template v-if="effectiveNode.text">{{ evaluate(effectiveNode.text) }}</template>
        <SchemaRenderer
          v-for="(child, index) in effectiveNode.children"
          :key="index"
          :node="child"
          :store="store"
          :api-base="effectiveApiBase"
        />
      </component>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, provide, inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToastStore } from '@/utils/toast'
import { parseUiPage, type UiNode, type UiPageMetadata, type ParsedUiPage } from '@/utils/xmlParser'
import { getValueByPath, setValueByPath, createDataStore } from '@/utils/dataStore'
import { resolveEndpoint, parseActions } from '@/utils/apiExecutor'

// 静态导入所有预设组件
import UIContainer from './UIContainer.vue'
import UIInputField from './UIInputField.vue'
import UITextarea from './UITextarea.vue'
import UISelect from './UISelect.vue'
import UISwitch from './UISwitch.vue'
import UISlider from './UISlider.vue'
import UIDatePicker from './UIDatePicker.vue'
import UIButton from './UIButton.vue'
import UIDialog from './UIDialog.vue'
import UIDataTable from './UIDataTable.vue'
import UICard from './UICard.vue'
import UITag from './UITag.vue'
import UITabs from './UITabs.vue'
import UILineChart from './UILineChart.vue'
import UIBarChart from './UIBarChart.vue'
import UIPieChart from './UIPieChart.vue'

const TAG_MAP: Record<string, any> = {
  container: UIContainer,
  'input-field': UIInputField,
  textarea: UITextarea,
  select: UISelect,
  switch: UISwitch,
  slider: UISlider,
  'date-picker': UIDatePicker,
  button: UIButton,
  dialog: UIDialog,
  'data-table': UIDataTable,
  card: UICard,
  tag: UITag,
  tabs: UITabs,
  'line-chart': UILineChart,
  'bar-chart': UIBarChart,
  'pie-chart': UIPieChart,
}

interface Props {
  xml?: string
  node?: UiNode
  /** 页面级数据存储；未传入时自动创建 */
  store?: Record<string, any>
  /** API 基础路径前缀（来自 <metadata><api-base>） */
  apiBase?: string
  /** 发起 API 请求的插件名称（设计文档 8.2，用于注入 X-Plugin-Name 头） */
  pluginName?: string
}

const props = withDefaults(defineProps<Props>(), {})

const router = useRouter()
const toast = useToastStore()

// ========== 数据存储 ==========

// 优先使用 prop 传入的 store，其次使用父级注入，最后自建
const parentStore = inject<Record<string, any> | null>('uiSchemaDataStore', null)
const store = props.store || parentStore || createDataStore()

if (!props.store && !parentStore) {
  provide('uiSchemaDataStore', store)
}

// 注入本地上下文（如表格行 row、索引 index 等）
const localContext = inject<any>('uiSchemaLocalContext', {})

// ========== XML 解析 & 节点树 ==========

const parsedPage = ref<ParsedUiPage | null>(null)

// 监听 xml 或 node 变化
watch(
  () => [props.xml, props.node],
  () => {
    if (props.node) {
      parsedPage.value = null
    } else if (props.xml) {
      try {
        parsedPage.value = parseUiPage(props.xml)
      } catch (e) {
        console.error('Failed to parse UI XML:', e)
        parsedPage.value = null
      }
    } else {
      parsedPage.value = null
    }
  },
  { immediate: true, deep: true },
)

// 当前生效的节点
const effectiveNode = computed<UiNode | null>(() => {
  if (props.node) return props.node
  if (parsedPage.value) return parsedPage.value.root
  return null
})

// 页面元数据
const pageMetadata = computed<UiPageMetadata | null>(() => {
  if (!parsedPage.value) return null
  return parsedPage.value.metadata
})

// 布局子节点
const layoutChildren = computed<UiNode[]>(() => {
  if (parsedPage.value) return parsedPage.value.layout
  return []
})

// API 基础路径：prop > metadata > inject
const injectedApiBase = inject<string | null>('uiSchemaApiBase', null)
const effectiveApiBase = computed(() => {
  if (props.apiBase) return props.apiBase
  if (pageMetadata.value?.apiBase) return pageMetadata.value.apiBase
  return injectedApiBase || ''
})

provide('uiSchemaApiBase', effectiveApiBase)

// 插件名称：prop（页面顶层传入）> inject（递归子节点继承）。
// 用于在 API 请求头注入 X-Plugin-Name（设计文档 8.2）。
const injectedPluginName = inject<string | null>('uiSchemaPluginName', null)
const effectivePluginName = props.pluginName || injectedPluginName || null
provide('uiSchemaPluginName', effectivePluginName)

// ========== 组件映射 ==========

function isRegisteredComponent(tag: string): boolean {
  return tag in TAG_MAP
}

function getComponent(tag: string): any {
  return TAG_MAP[tag]
}

// 转换 HTML 属性，排除 Vue 专有或自定义属性
function getHtmlAttributes(attrs: Record<string, string>): Record<string, string> {
  const result: Record<string, string> = {}
  for (const [key, val] of Object.entries(attrs)) {
    if (key.startsWith(':') || key.startsWith('@') || key === 'data-bind') {
      continue
    }
    result[key] = val
  }
  return result
}

// ========== 表达式求值 ==========

function evaluate(expr: string, extraContext: any = {}): any {
  if (typeof expr !== 'string') return expr
  const mergedContext = {
    ...store,
    ...localContext,
    ...extraContext,
  }

  // 1. 完全匹配 {{ expression }}
  const singleMatch = expr.trim().match(/^\{\{\s*(.*?)\s*\}\}$/)
  if (singleMatch) {
    const code = singleMatch[1]
    try {
      const keys = Object.keys(mergedContext)
      const values = Object.values(mergedContext)
      const fn = new Function(...keys, `return (${code})`)
      return fn(...values)
    } catch (e) {
      console.warn('Failed to evaluate expression:', code, e)
      return undefined
    }
  }

  // 2. 字符串插值
  return expr.replace(/\{\{\s*(.*?)\s*\}\}/g, (_, code) => {
    try {
      const keys = Object.keys(mergedContext)
      const values = Object.values(mergedContext)
      const fn = new Function(...keys, `return (${code})`)
      return fn(...values)
    } catch (e) {
      console.warn('Failed to evaluate expression:', code, e)
      return ''
    }
  })
}

provide('uiSchemaEvaluate', evaluate)
provide('uiSchemaGetValue', getValueByPath)
provide('uiSchemaSetValue', setValueByPath)

// ========== 声明式动作执行 ==========

function executeActions(actionsStr: string, context: any = {}) {
  if (!actionsStr) return
  const actions = parseActions(actionsStr)

  for (const action of actions) {
    const evaluatedArg = evaluate(action.arg, context)

    switch (action.type) {
      case 'show-toast':
        toast.show(evaluatedArg || '操作成功', 'success')
        break
      case 'refresh-table':
        if (evaluatedArg) {
          if (!store.tables[evaluatedArg]) {
            store.tables[evaluatedArg] = { refreshTrigger: 0 }
          }
          store.tables[evaluatedArg].refreshTrigger++
        }
        break
      case 'open-dialog':
        if (evaluatedArg) {
          store.dialogs[evaluatedArg] = true
        }
        break
      case 'close-dialog':
        if (evaluatedArg) {
          store.dialogs[evaluatedArg] = false
        } else {
          const currentDialogId = context.dialogId || localContext.dialogId
          if (currentDialogId) {
            store.dialogs[currentDialogId] = false
          }
        }
        break
      case 'navigate':
        if (evaluatedArg) {
          router.push(evaluatedArg)
        }
        break
      case 'reload-page':
        window.location.reload()
        break
      default:
        console.warn('Unknown action type:', action.type)
    }
  }
}

provide('uiSchemaExecuteActions', executeActions)
provide('uiSchemaResolveEndpoint', (endpoint: string) =>
  resolveEndpoint(endpoint, effectiveApiBase.value),
)
</script>

<style scoped>
.ui-schema-renderer {
  width: 100%;
}

.ui-page-wrapper {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ui-page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  color: var(--md-sys-color-primary);
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--md-sys-color-on-background);
  margin: 0;
}

.page-description {
  font-size: 14px;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0;
}

.ui-page-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ui-node-wrapper {
  width: 100%;
}

.ui-text {
  font-family: inherit;
}

.ui-template {
  width: 100%;
  font-family: inherit;
}
</style>
