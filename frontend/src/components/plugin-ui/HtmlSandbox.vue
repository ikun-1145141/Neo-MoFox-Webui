<script setup lang="ts">
/**
 * HtmlSandbox - HTML 沙箱 Vue 包装组件。
 *
 * 在 onMounted 时调用 createHtmlSandbox，onUnmounted 时销毁。
 * 三态 UI：loading / error / ready。
 */
import { ref, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import type { PageDetail, PageSchemaResponse } from '../../api/types/plugin-ui'
import type { PluginUIVarStore } from '../../stores/plugin-ui-vars'
import { ApiTemplateEngine } from '../../utils/plugin-ui/api-template-engine'
import {
  createHtmlSandbox,
  type HtmlSandboxHandle,
} from '../../utils/plugin-ui/html/html-sandbox'

const props = defineProps<{
  /** 页面详情 */
  detail: PageDetail
  /** 页面 schema */
  schema: PageSchemaResponse
  /** 变量池 Store */
  store: PluginUIVarStore
}>()

const emit = defineEmits<{
  (e: 'ready'): void
  (e: 'error', message: string): void
}>()

const router = useRouter()
const hostRef = ref<HTMLDivElement | null>(null)
const status = ref<'loading' | 'ready' | 'error'>('loading')
const errorMsg = ref('')
const handle = shallowRef<HtmlSandboxHandle | null>(null)

async function setup() {
  // 清理旧的
  if (handle.value) {
    handle.value.destroy()
    handle.value = null
  }
  if (!hostRef.value || !props.schema.assets_urls) {
    status.value = 'error'
    errorMsg.value = 'HTML 资源 URL 为空'
    return
  }
  status.value = 'loading'
  errorMsg.value = ''
  try {
    const apiEngine = new ApiTemplateEngine(props.store)
    handle.value = await createHtmlSandbox(hostRef.value, {
      pluginName: props.detail.plugin_name,
      pageId: props.detail.page_id,
      assetsUrls: props.schema.assets_urls,
      store: props.store,
      apiEngine,
      router,
    })
    status.value = 'ready'
    emit('ready')
  } catch (e: any) {
    status.value = 'error'
    errorMsg.value = e?.message || 'HTML 沙箱加载失败'
    emit('error', errorMsg.value)
    console.error('[HtmlSandbox] 加载失败:', e)
  }
}

onMounted(setup)
onUnmounted(() => {
  handle.value?.destroy()
  handle.value = null
})

watch(
  () => props.schema,
  () => setup()
)
</script>

<template>
  <div class="html-sandbox-wrapper">
    <Transition name="sys-fade">
      <div
        v-if="status === 'loading'"
        class="html-sandbox-loading"
      >
        <span class="material-symbols-rounded sys-spinner">progress_activity</span>
        <p>正在加载 HTML 沙箱...</p>
      </div>
    </Transition>
    <Transition name="sys-fade">
      <div
        v-if="status === 'error'"
        class="html-sandbox-error"
      >
        <span class="material-symbols-rounded">error_outline</span>
        <p>{{ errorMsg }}</p>
      </div>
    </Transition>
    <div
      ref="hostRef"
      class="html-sandbox-host"
      :data-status="status"
    />
  </div>
</template>

<style scoped>
.html-sandbox-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  min-height: 200px;
}

.html-sandbox-host {
  width: 100%;
  height: 100%;
}

.html-sandbox-loading,
.html-sandbox-error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  background: var(--md-sys-color-surface-container-lowest, #ffffff);
  border: 1px dashed var(--md-sys-color-outline-variant, #cac4d0);
  border-radius: 12px;
  color: var(--md-sys-color-on-surface-variant, #44474e);
}

.html-sandbox-loading .material-symbols-rounded {
  font-size: 32px;
  color: var(--md-sys-color-primary, #0058bd);
}

.html-sandbox-error .material-symbols-rounded {
  font-size: 40px;
  color: var(--md-sys-color-error, #ba1a1a);
  opacity: 0.8;
  animation: sys-shake 0.5s var(--md-sys-motion-emphasized);
}

.html-sandbox-loading p,
.html-sandbox-error p {
  margin: 0;
  font-size: 0.875rem;
}
</style>
