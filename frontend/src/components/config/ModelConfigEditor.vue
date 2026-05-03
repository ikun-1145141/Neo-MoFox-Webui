<!--
  @file ModelConfigEditor.vue
  @description 模型配置专用编辑器
  
  功能：
  - 顶栏标签切换：供应商配置、模型配置、任务配置
  - 列表式管理：添加/编辑/删除配置项
  - 代码模式：切换到 TOML 编辑器
  - 测试功能：供应商和模型连通性测试
  - Material Design 3 样式
-->
<template>
  <div class="model-config-editor">
    <!-- 工具栏 -->
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <h2 class="config-title">{{ title }}</h2>
        <span v-if="configPath" class="config-path">{{ configPath }}</span>
      </div>

      <div class="toolbar-right">
        <!-- 模式切换按钮 -->
        <button
          type="button"
          class="mode-toggle-btn"
          @click="toggleEditMode"
          :title="isCodeMode ? '切换到表单模式' : '切换到代码模式'"
        >
          <Icon
            :icon="isCodeMode ? 'material-symbols:edit-note-rounded' : 'material-symbols:code-rounded'"
            :size="20"
          />
          <span>{{ isCodeMode ? '表单模式' : '代码模式' }}</span>
        </button>

        <!-- 保存按钮 -->
        <button
          type="button"
          class="save-btn"
          @click="handleSave"
          :disabled="isSaving || !hasChanges"
          :title="hasChanges ? '保存更改' : '无更改'"
        >
          <Icon
            v-if="!isSaving"
            icon="material-symbols:save-outline-rounded"
            :size="20"
          />
          <Icon
            v-else
            icon="material-symbols:progress-activity"
            :size="20"
            class="spinning"
          />
          <span>{{ isSaving ? '保存中...' : '保存' }}</span>
        </button>
      </div>
    </div>

    <!-- 编辑器内容 -->
    <div class="editor-content">
      <!-- 代码模式 -->
      <TomlEditor
        v-if="isCodeMode"
        v-model="codeContent"
        :readonly="readonly"
      />

      <!-- 表单模式 -->
      <div v-else class="form-mode">
        <!-- 顶部标签栏 -->
        <div class="tab-bar">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="tab-button"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            <Icon :icon="tab.icon" :size="20" />
            <span>{{ tab.label }}</span>
          </button>
        </div>

        <!-- 标签内容 -->
        <div class="tab-content">
          <!-- 供应商配置 -->
          <div v-if="activeTab === 'providers'" class="config-section">
            <div class="section-header">
              <h3>API 提供商列表</h3>
              <button type="button" class="add-btn" @click="addProvider">
                <Icon icon="material-symbols:add-rounded" :size="20" />
                <span>添加供应商</span>
              </button>
            </div>

            <div class="config-list">
              <div
                v-for="(provider, idx) in localData.api_providers"
                :key="idx"
                class="config-card provider-card"
              >
                <div class="card-header">
                  <div class="card-title">
                    <Icon icon="material-symbols:cloud-rounded" :size="24" />
                    <span>{{ provider.name || '未命名供应商' }}</span>
                  </div>
                  <div class="card-actions">
                    <button type="button" class="icon-btn" @click="testProvider(provider, String(idx))" :disabled="testingProviders.has(String(idx))" :title="'测试连通性'">
                      <Icon v-if="!testingProviders.has(String(idx))" icon="material-symbols:play-arrow-rounded" :size="20" />
                      <Icon v-else icon="material-symbols:progress-activity" :size="20" class="spinning" />
                    </button>
                    <button type="button" class="icon-btn" @click="editProvider(idx)" :title="'编辑'">
                      <Icon icon="material-symbols:edit-outline-rounded" :size="20" />
                    </button>
                    <button type="button" class="icon-btn danger" @click="deleteProvider(idx)" :title="'删除'">
                      <Icon icon="material-symbols:delete-outline-rounded" :size="20" />
                    </button>
                  </div>
                </div>

                <div class="card-body">
                  <div class="info-grid">
                    <div class="info-item">
                      <span class="label">Base URL:</span>
                      <span class="value">{{ provider.base_url }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">客户端类型:</span>
                      <span class="value">{{ provider.client_type }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">超时:</span>
                      <span class="value">{{ provider.timeout }}s</span>
                    </div>
                    <div class="info-item">
                      <span class="label">重试次数:</span>
                      <span class="value">{{ provider.max_retry }}</span>
                    </div>
                  </div>

                  <!-- 测试结果 -->
                  <div v-if="testResults.providers.has(String(idx))" class="test-result" :class="testResults.providers.get(String(idx))!.success ? 'success' : 'error'">
                    <Icon :icon="testResults.providers.get(String(idx))!.success ? 'material-symbols:check-circle-outline-rounded' : 'material-symbols:error-outline-rounded'" :size="18" />
                    <span>{{ testResults.providers.get(String(idx))!.message }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 模型配置 -->
          <div v-if="activeTab === 'models'" class="config-section">
            <div class="section-header">
              <h3>模型列表</h3>
              <button type="button" class="add-btn" @click="addModel">
                <Icon icon="material-symbols:add-rounded" :size="20" />
                <span>添加模型</span>
              </button>
            </div>

            <div class="config-list">
              <div
                v-for="(model, idx) in localData.models"
                :key="idx"
                class="config-card model-card"
              >
                <div class="card-header">
                  <div class="card-title">
                    <Icon icon="material-symbols:smart-toy-outline-rounded" :size="24" />
                    <span>{{ model.name || '未命名模型' }}</span>
                  </div>
                  <div class="card-actions">
                    <button type="button" class="icon-btn" @click="testModel(model, String(idx))" :disabled="testingModels.has(String(idx))" :title="'测试连通性'">
                      <Icon v-if="!testingModels.has(String(idx))" icon="material-symbols:play-arrow-rounded" :size="20" />
                      <Icon v-else icon="material-symbols:progress-activity" :size="20" class="spinning" />
                    </button>
                    <button type="button" class="icon-btn" @click="editModel(idx)" :title="'编辑'">
                      <Icon icon="material-symbols:edit-outline-rounded" :size="20" />
                    </button>
                    <button type="button" class="icon-btn danger" @click="deleteModel(idx)" :title="'删除'">
                      <Icon icon="material-symbols:delete-outline-rounded" :size="20" />
                    </button>
                  </div>
                </div>

                <div class="card-body">
                  <div class="info-grid">
                    <div class="info-item">
                      <span class="label">标识符:</span>
                      <span class="value">{{ model.model_identifier }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">提供商:</span>
                      <span class="value">{{ model.api_provider }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">输入价格:</span>
                      <span class="value">¥{{ model.price_in }}/M tokens</span>
                    </div>
                    <div class="info-item">
                      <span class="label">输出价格:</span>
                      <span class="value">¥{{ model.price_out }}/M tokens</span>
                    </div>
                    <div class="info-item">
                      <span class="label">上下文长度:</span>
                      <span class="value">{{ model.max_context }} tokens</span>
                    </div>
                  </div>

                  <!-- 测试结果 -->
                  <div v-if="testResults.models.has(String(idx))" class="test-result" :class="testResults.models.get(String(idx))!.success ? 'success' : 'error'">
                    <Icon :icon="testResults.models.get(String(idx))!.success ? 'material-symbols:check-circle-outline-rounded' : 'material-symbols:error-outline-rounded'" :size="18" />
                    <div class="result-content">
                      <p class="result-message">
                        {{ testResults.models.get(String(idx))!.success ? `连接成功！延迟：${testResults.models.get(String(idx))!.latency_ms?.toFixed(0)} ms` : `连接失败：${testResults.models.get(String(idx))!.error_message}` }}
                      </p>
                      <p v-if="testResults.models.get(String(idx))!.response_text" class="result-response">
                        响应：{{ testResults.models.get(String(idx))!.response_text }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 任务配置 -->
          <div v-if="activeTab === 'tasks'" class="config-section">
            <div class="section-header">
              <h3>任务配置列表</h3>
              <button type="button" class="add-btn" @click="addTask">
                <Icon icon="material-symbols:add-rounded" :size="20" />
                <span>添加任务</span>
              </button>
            </div>

            <div class="config-list">
              <div
                v-for="(task, tname) in localData.model_tasks"
                :key="tname"
                class="config-card task-card"
              >
                <div class="card-header">
                  <div class="card-title">
                    <Icon icon="material-symbols:task-alt-rounded" :size="24" />
                    <span>{{ tname }}</span>
                  </div>
                  <div class="card-actions">
                    <button type="button" class="icon-btn" @click="editTask(String(tname))" :title="'编辑'">
                      <Icon icon="material-symbols:edit-outline-rounded" :size="20" />
                    </button>
                    <button type="button" class="icon-btn danger" @click="deleteTask(String(tname))" :title="'删除'">
                      <Icon icon="material-symbols:delete-outline-rounded" :size="20" />
                    </button>
                  </div>
                </div>

                <div class="card-body">
                  <div class="info-grid">
                    <div class="info-item">
                      <span class="label">模型列表:</span>
                      <span class="value">{{ (task as any).model_list?.join(', ') || '-' }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">最大 Tokens:</span>
                      <span class="value">{{ (task as any).max_tokens || '-' }}</span>
                    </div>
                    <div class="info-item">
                      <span class="label">温度:</span>
                      <span class="value">{{ (task as any).temperature || '-' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMessage" class="error-banner">
      <Icon icon="material-symbols:error-outline-rounded" :size="20" />
      <span>{{ errorMessage }}</span>
      <button type="button" @click="errorMessage = ''" class="close-btn">
        <Icon icon="material-symbols:close-rounded" :size="16" />
      </button>
    </div>

    <!-- 编辑对话框 -->
    <ModelEditDialog
      :is-open="dialog.isOpen"
      :type="dialog.type"
      :mode="dialog.mode"
      :data="dialog.data"
      :providers="providerNames"
      @close="closeDialog"
      @submit="handleDialogSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { parse as parseToml } from 'toml'
import Icon from '../common/Icon.vue'
import TomlEditor from './TomlEditor.vue'
import ModelEditDialog from './ModelEditDialog.vue'
import { testModel as apiTestModel, getRawConfig } from '@/api/modules/config'
import type { SectionSchema, ModelTestResult } from '@/api/types/config'

// Props
interface Props {
  title: string
  configPath?: string
  schema: SectionSchema[]
  modelValue: Record<string, any>
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
  save: [data: Record<string, any>]
}>()

// ===== 状态管理 =====

// 编辑模式
const isCodeMode = ref(false)

// 当前激活的标签
const activeTab = ref<'providers' | 'models' | 'tasks'>('providers')

// 标签定义
const tabs = [
  { key: 'providers' as const, label: '供应商配置', icon: 'material-symbols:cloud-rounded' },
  { key: 'models' as const, label: '模型配置', icon: 'material-symbols:smart-toy-outline-rounded' },
  { key: 'tasks' as const, label: '任务配置', icon: 'material-symbols:task-alt-rounded' },
]

// 本地数据（表单数据）
const localData = ref<Record<string, any>>({
  api_providers: [],
  models: [],
  model_tasks: {},
  ...props.modelValue,
})

// 代码内容
const codeContent = ref('')

// 原始数据
const originalData = ref<Record<string, any>>({})

// 保存状态
const isSaving = ref(false)
const errorMessage = ref('')

// 测试状态（使用 string 键以兼容 v-for index）
const testingProviders = ref(new Set<string>())
const testingModels = ref(new Set<string>())
const testResults = ref<{
  providers: Map<string, { success: boolean; message: string }>
  models: Map<string, ModelTestResult>
}>({
  providers: new Map(),
  models: new Map(),
})

// 是否有变更
const hasChanges = computed(() => {
  const currentJson = JSON.stringify(localData.value)
  const originalJson = JSON.stringify(originalData.value)
  const changed = currentJson !== originalJson
  console.log('[ModelConfigEditor] hasChanges 检测:', {
    changed,
    currentDataKeys: Object.keys(localData.value),
    originalDataKeys: Object.keys(originalData.value),
    currentProvidersCount: localData.value.api_providers?.length,
    originalProvidersCount: originalData.value.api_providers?.length,
  })
  return changed
})

// 提供商名称列表
const providerNames = computed(() => {
  return localData.value.api_providers?.map((p: any) => p.name) || []
})

// 对话框状态
const dialog = ref<{
  isOpen: boolean
  type: 'provider' | 'model' | 'task'
  mode: 'add' | 'edit'
  data: Record<string, any>
  editIndex?: number | string
}>({
  isOpen: false,
  type: 'provider',
  mode: 'add',
  data: {},
})

// ===== 初始化 =====

// 初始化时加载原始 TOML
onMounted(async () => {
  console.log('[ModelConfigEditor] 组件挂载，开始加载原始 TOML')
  try {
    const rawToml = await getRawConfig('model')
    codeContent.value = rawToml
    console.log('[ModelConfigEditor] 原始 TOML 加载成功，长度:', rawToml.length)
  } catch (error: any) {
    console.error('[ModelConfigEditor] 加载原始 TOML 失败:', error)
    errorMessage.value = error.message
  }
})

watch(
  () => props.modelValue,
  (newValue) => {
    console.log('[ModelConfigEditor] props.modelValue 变化:', {
      newValueKeys: Object.keys(newValue),
      providersCount: newValue.api_providers?.length,
      modelsCount: newValue.models?.length,
    })
    
    // 深拷贝以避免共享引用
    localData.value = JSON.parse(JSON.stringify({
      api_providers: [],
      models: [],
      model_tasks: {},
      ...newValue,
    }))
    originalData.value = JSON.parse(JSON.stringify(localData.value))
    
    console.log('[ModelConfigEditor] 已更新 localData 和 originalData（深拷贝）')
  },
  { immediate: true, deep: true }
)

// ===== 模式切换 =====

async function toggleEditMode() {
  if (isCodeMode.value) {
    // 从代码模式切换到表单模式
    try {
      const parsed = parseToml(codeContent.value)
      localData.value = {
        api_providers: [],
        models: [],
        model_tasks: {},
        ...parsed,
      }
      errorMessage.value = ''
      isCodeMode.value = false
    } catch (error: any) {
      errorMessage.value = `TOML 解析失败: ${error.message}`
    }
  } else {
    // 从表单模式切换到代码模式
    try {
      // 从后端重新加载原始 TOML
      const rawToml = await getRawConfig('model')
      codeContent.value = rawToml
      errorMessage.value = ''
      isCodeMode.value = true
    } catch (error: any) {
      errorMessage.value = `加载原始 TOML 失败: ${error.message}`
    }
  }
}

// ===== 保存 =====

async function handleSave() {
  console.log('[ModelConfigEditor] handleSave 被调用', {
    isSaving: isSaving.value,
    hasChanges: hasChanges.value,
    isCodeMode: isCodeMode.value,
  })

  if (isSaving.value || !hasChanges.value) {
    console.log('[ModelConfigEditor] 保存被阻止:', {
      reason: isSaving.value ? '正在保存中' : '没有变更',
    })
    return
  }

  try {
    isSaving.value = true
    errorMessage.value = ''

    let dataToSave: Record<string, any>

    if (isCodeMode.value) {
      try {
        dataToSave = parseToml(codeContent.value)
        console.log('[ModelConfigEditor] 代码模式: TOML 解析成功')
      } catch (error: any) {
        console.error('[ModelConfigEditor] TOML 解析失败:', error)
        errorMessage.value = `TOML 格式错误: ${error.message}`
        return
      }
    } else {
      dataToSave = localData.value
      console.log('[ModelConfigEditor] 表单模式: 使用 localData', {
        providersCount: dataToSave.api_providers?.length,
        modelsCount: dataToSave.models?.length,
        tasksCount: Object.keys(dataToSave.model_tasks || {}).length,
      })
    }

    console.log('[ModelConfigEditor] 准备发出 save 事件:', {
      dataKeys: Object.keys(dataToSave),
    })

    // 只发出 save 事件，不发出 update:modelValue
    // 父组件保存成功后会更新 props.modelValue，触发 watch，更新 originalData
    emit('save', dataToSave)
    
    console.log('[ModelConfigEditor] save 事件已发出')
  } catch (error: any) {
    console.error('[ModelConfigEditor] 保存过程出错:', error)
    errorMessage.value = `保存失败: ${error.message}`
  } finally {
    isSaving.value = false
  }
}

// ===== 供应商管理 =====

function addProvider() {
  dialog.value = {
    isOpen: true,
    type: 'provider',
    mode: 'add',
    data: {},
  }
}

function editProvider(index: string | number) {
  const idx = Number(index)
  dialog.value = {
    isOpen: true,
    type: 'provider',
    mode: 'edit',
    data: localData.value.api_providers[idx],
    editIndex: idx,
  }
}

function deleteProvider(index: string | number) {
  if (confirm('确定要删除此供应商吗？')) {
    localData.value.api_providers.splice(Number(index), 1)
  }
}

async function testProvider(provider: any, index: string | number) {
  const idx = String(index)
  if (testingProviders.value.has(idx)) return

  try {
    testingProviders.value.add(idx)
    testResults.value.providers.delete(idx)

    // 简单测试：检查是否有对应的模型
    const hasModels = localData.value.models.some((m: any) => m.api_provider === provider.name)

    if (!hasModels) {
      testResults.value.providers.set(idx, {
        success: false,
        message: '该供应商下没有配置模型',
      })
    } else {
      testResults.value.providers.set(idx, {
        success: true,
        message: '配置验证通过',
      })
    }
  } catch (error: any) {
    testResults.value.providers.set(idx, {
      success: false,
      message: error.message || '测试失败',
    })
  } finally {
    testingProviders.value.delete(idx)
  }
}

// ===== 模型管理 =====

function addModel() {
  dialog.value = {
    isOpen: true,
    type: 'model',
    mode: 'add',
    data: {},
  }
}

function editModel(index: string | number) {
  const idx = Number(index)
  dialog.value = {
    isOpen: true,
    type: 'model',
    mode: 'edit',
    data: localData.value.models[idx],
    editIndex: idx,
  }
}

function deleteModel(index: string | number) {
  if (confirm('确定要删除此模型吗？')) {
    localData.value.models.splice(Number(index), 1)
  }
}

async function testModel(model: any, index: string | number) {
  const idx = String(index)
  if (testingModels.value.has(idx)) return

  try {
    testingModels.value.add(idx)
    testResults.value.models.delete(idx)

    const provider = localData.value.api_providers.find((p: any) => p.name === model.api_provider)

    if (!provider) {
      testResults.value.models.set(idx, {
        success: false,
        error_message: `未找到提供商: ${model.api_provider}`,
        model_identifier: model.model_identifier,
        provider_base_url: '',
      })
      return
    }

    const result = await apiTestModel({
      provider_name: model.api_provider,
      model_name: model.name,
      test_prompt: '你好',
      timeout: 30,
    })

    testResults.value.models.set(idx, result)
  } catch (error: any) {
    testResults.value.models.set(idx, {
      success: false,
      error_message: error.message || '测试请求失败',
      model_identifier: model.model_identifier,
      provider_base_url: '',
    })
  } finally {
    testingModels.value.delete(idx)
  }
}

// ===== 任务管理 =====

function addTask() {
  dialog.value = {
    isOpen: true,
    type: 'task',
    mode: 'add',
    data: {},
  }
}

function editTask(taskName: string) {
  const taskData = localData.value.model_tasks[taskName]
  dialog.value = {
    isOpen: true,
    type: 'task',
    mode: 'edit',
    data: { name: taskName, ...taskData },
    editIndex: taskName,
  }
}

function deleteTask(taskName: string) {
  if (confirm(`确定要删除任务 ${taskName} 吗？`)) {
    delete localData.value.model_tasks[taskName]
  }
}

// ===== 对话框管理 =====

function closeDialog() {
  dialog.value.isOpen = false
}

function handleDialogSubmit(data: Record<string, any>) {
  console.log('[ModelConfigEditor] handleDialogSubmit 被调用:', {
    type: dialog.value.type,
    mode: dialog.value.mode,
    data,
  })

  if (dialog.value.type === 'provider') {
    if (dialog.value.mode === 'add') {
      localData.value.api_providers.push(data)
      console.log('[ModelConfigEditor] 添加供应商成功')
    } else {
      const idx = dialog.value.editIndex as number
      localData.value.api_providers[idx] = data
      console.log('[ModelConfigEditor] 编辑供应商成功, index:', idx)
    }
  } else if (dialog.value.type === 'model') {
    if (dialog.value.mode === 'add') {
      localData.value.models.push(data)
      console.log('[ModelConfigEditor] 添加模型成功')
    } else {
      const idx = dialog.value.editIndex as number
      localData.value.models[idx] = data
      console.log('[ModelConfigEditor] 编辑模型成功, index:', idx)
    }
  } else if (dialog.value.type === 'task') {
    const taskName = data.name
    const { name, ...taskData } = data
    
    if (dialog.value.mode === 'add') {
      if (localData.value.model_tasks[taskName]) {
        alert('任务名称已存在')
        console.warn('[ModelConfigEditor] 任务名称已存在:', taskName)
        return
      }
      localData.value.model_tasks[taskName] = taskData
      console.log('[ModelConfigEditor] 添加任务成功:', taskName)
    } else {
      const oldName = dialog.value.editIndex as string
      if (oldName !== taskName) {
        // 任务名称不应该改变，但如果改了就删除旧的
        delete localData.value.model_tasks[oldName]
        console.log('[ModelConfigEditor] 删除旧任务名:', oldName)
      }
      localData.value.model_tasks[taskName] = taskData
      console.log('[ModelConfigEditor] 编辑任务成功:', taskName)
    }
  }
  
  console.log('[ModelConfigEditor] 对话框提交后 localData 状态:', {
    providersCount: localData.value.api_providers?.length,
    modelsCount: localData.value.models?.length,
    tasksCount: Object.keys(localData.value.model_tasks || {}).length,
  })
  
  closeDialog()
}
</script>

<style scoped>
.model-config-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--md-sys-color-surface);
}

/* ===== 工具栏 ===== */
.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--md-sys-color-surface-container-low);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.config-path {
  font-size: 12px;
  color: var(--md-sys-color-outline);
  padding: 4px 8px;
  background: var(--md-sys-color-surface-container);
  border-radius: 4px;
}

.toolbar-right {
  display: flex;
  gap: 12px;
}

.mode-toggle-btn,
.save-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.mode-toggle-btn {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
}

.mode-toggle-btn:hover {
  background: var(--md-sys-color-secondary);
  color: var(--md-sys-color-on-secondary);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.save-btn {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
}

.save-btn:hover:not(:disabled) {
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== 编辑器内容 ===== */
.editor-content {
  flex: 1;
  overflow: hidden;
}

/* ===== 表单模式 ===== */
.form-mode {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tab-bar {
  display: flex;
  background: var(--md-sys-color-surface-container-low);
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  padding: 0 24px;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  font-size: 14px;
  font-weight: 500;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  position: relative;
}

.tab-button:hover {
  background: var(--md-sys-color-surface-container);
  color: var(--md-sys-color-on-surface);
}

.tab-button.active {
  color: var(--md-sys-color-primary);
  border-bottom-color: var(--md-sys-color-primary);
}

/* ===== 标签内容 ===== */
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.config-section {
  max-width: 1200px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.add-btn:hover {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

/* ===== 配置列表 ===== */
.config-list {
  display: grid;
  gap: 16px;
}

.config-card {
  background: var(--md-sys-color-surface-container);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s;
}

.config-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.card-actions {
  display: flex;
  gap: 8px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: var(--md-sys-color-surface-container-high);
  color: var(--md-sys-color-on-surface);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  transform: scale(1.1);
}

.icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon-btn.danger:hover {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  font-weight: 500;
  color: var(--md-sys-color-on-surface-variant);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-item .value {
  font-size: 14px;
  color: var(--md-sys-color-on-surface);
  word-break: break-all;
}

/* ===== 测试结果 ===== */
.test-result {
  margin-top: 12px;
  padding: 12px;
  border-radius: 8px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  line-height: 1.5;
}

.test-result.success {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
  border: 1px solid var(--md-sys-color-tertiary);
}

.test-result.error {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
  border: 1px solid var(--md-sys-color-error);
}

.result-content {
  flex: 1;
}

.result-message {
  margin: 0 0 6px 0;
  font-weight: 500;
}

.result-response {
  margin: 0;
  opacity: 0.8;
  font-style: italic;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== 错误横幅 ===== */
.error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
  border-top: 1px solid var(--md-sys-color-error);
  font-size: 14px;
}

.error-banner .close-btn {
  margin-left: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: transparent;
  color: inherit;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
}

.error-banner .close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

/* ===== 动画 ===== */
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
</style>
