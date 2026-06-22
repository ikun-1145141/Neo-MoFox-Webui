<!--
  @file UIDialog.vue
  @description 对话框组件，通过 dataStore.dialogs[id] 控制显示/隐藏。
  消费共享工具：dataStore。
-->
<template>
  <Teleport to="body">
    <div v-if="visible" class="ui-dialog-overlay" @click.self="handleClose">
      <div class="ui-dialog-container" :style="{ width: node.attrs.width || '500px' }">
        <!-- 对话框头部 -->
        <div class="ui-dialog-header">
          <h2 class="dialog-title">{{ evaluate(node.attrs.title || '提示') }}</h2>
          <button class="close-btn" @click="handleClose">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <!-- 对话框内容 -->
        <div class="ui-dialog-content">
          <SchemaRenderer
            v-for="(child, index) in contentChildren"
            :key="index"
            :node="child"
            :store="store"
            :api-base="apiBase"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, inject, provide } from 'vue'
import type { UiNode } from '@/utils/xmlParser'
import SchemaRenderer from './SchemaRenderer.vue'

interface Props {
  node: UiNode
  store?: Record<string, any>
  apiBase?: string
}

const props = defineProps<Props>()

const dataStore = props.store || inject<any>('uiSchemaDataStore')
const evaluate = inject<any>('uiSchemaEvaluate')

// 通过 dataStore.dialogs[id] 双向绑定显示状态
const visible = computed({
  get: () => !!dataStore?.dialogs?.[props.node.attrs.id],
  set: (val) => {
    if (dataStore) {
      if (!dataStore.dialogs) {
        dataStore.dialogs = {}
      }
      dataStore.dialogs[props.node.attrs.id] = val
    }
  },
})

// 过滤掉可能存在的非内容节点，直接渲染子节点
const contentChildren = computed(() => props.node.children)

function handleClose() {
  visible.value = false
}

// 提供当前对话框 ID，供子组件（如关闭按钮）使用
provide('uiSchemaDialogId', props.node.attrs.id)
</script>

<style scoped>
.ui-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.ui-dialog-container {
  background: var(--md-sys-color-surface-container-high);
  border-radius: 28px;
  box-shadow: var(--md-sys-elevation-3);
  display: flex;
  flex-direction: column;
  max-height: 85vh;
  box-sizing: border-box;
  animation: scaleUp 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.ui-dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px;
}

.dialog-title {
  font-size: 24px;
  font-weight: 400;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--md-sys-color-on-surface-variant);
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.close-btn:hover {
  background: var(--md-sys-color-surface-container-highest);
}

.ui-dialog-content {
  padding: 0 24px 24px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@keyframes scaleUp {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
