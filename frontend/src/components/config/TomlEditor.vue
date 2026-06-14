<!--
  @file TomlEditor.vue
  @description 统一的 TOML 源码编辑器组件
  
  基于 CodeMirror 6 实现，提供：
  - TOML 语法高亮
  - 实时语法检查（500ms 防抖）
  - 中文错误提示
  - 深色/浅色主题自适应
  - 行号、代码折叠、搜索功能
-->
<template>
  <div class="toml-editor-wrapper">
    <div class="editor-container" ref="editorRef"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { Decoration, WidgetType } from '@codemirror/view'
import { EditorState, Compartment, StateField } from '@codemirror/state'
import { StreamLanguage } from '@codemirror/language'
import { toml } from '@codemirror/legacy-modes/mode/toml'
import { linter, forEachDiagnostic } from '@codemirror/lint'
import { syntaxHighlighting, HighlightStyle } from '@codemirror/language'
import { tags as t } from '@lezer/highlight'
import { lintTOML } from '@/utils/toml-linter'

// ═══ 行尾诊断信息显示（类似 Error Lens）═══
/**
 * 创建诊断信息小部件
 */
class DiagnosticWidget extends WidgetType {
  message: string
  severity: string

  constructor(message: string, severity: string) {
    super()
    this.message = message
    this.severity = severity
  }

  toDOM() {
    const span = document.createElement('span')
    span.className = `diagnostic-widget diagnostic-${this.severity}`
    span.textContent = ` ⚠ ${this.message}`
    span.style.cssText = `
      color: ${this.severity === 'error' ? 'var(--md-sys-color-error)' : 'var(--md-sys-color-tertiary)'};
      font-size: 0.85em;
      font-style: italic;
      opacity: 0.8;
      margin-left: 1em;
      pointer-events: none;
      user-select: none;
    `
    return span
  }

  eq(other: DiagnosticWidget) {
    return other.message === this.message && other.severity === this.severity
  }

  ignoreEvent() {
    return true
  }
}

/**
 * 构建诊断装饰器
 */
function buildDiagnosticDecorations(state: EditorState) {
  const diagnostics: Array<{
    from: number
    message: string
    severity: string
  }> = []

  // 收集所有诊断信息
  forEachDiagnostic(state, (diagnostic, from) => {
    diagnostics.push({
      from,
      message: diagnostic.message,
      severity: diagnostic.severity || 'error',
    })
  })

  // 按行分组诊断信息（每行只显示第一个错误）
  const lineMap = new Map<number, { message: string; severity: string }>()
  diagnostics.forEach(({ from, message, severity }) => {
    const lineNumber = state.doc.lineAt(from).number
    if (!lineMap.has(lineNumber)) {
      lineMap.set(lineNumber, { message, severity })
    }
  })

  // 创建装饰器
  const decorationArray: any[] = []
  lineMap.forEach((diag, lineNumber) => {
    const line = state.doc.line(lineNumber)
    const lineEnd = line.to
    const widget = Decoration.widget({
      widget: new DiagnosticWidget(diag.message, diag.severity),
      side: 1,
    })
    decorationArray.push(widget.range(lineEnd))
  })

  return Decoration.set(decorationArray, true)
}

/**
 * 行尾诊断信息扩展
 */
function inlineDiagnostics() {
  const decorationField = StateField.define({
    create(state) {
      return buildDiagnosticDecorations(state)
    },
    update(decorations, tr) {
      if (tr.docChanged) {
        return buildDiagnosticDecorations(tr.state)
      }
      return decorations
    },
    provide: (f) => EditorView.decorations.from(f),
  })

  return decorationField
}

// Props
interface Props {
  modelValue: string
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

// Refs
const editorRef = ref<HTMLElement | null>(null)
const editorView = shallowRef<EditorView | null>(null)

// Theme
const themeCompartment = new Compartment()
const readonlyCompartment = new Compartment()

/**
 * 创建 Material Design 3 主题
 */
function createM3Theme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'

  return EditorView.theme(
    {
      '&': {
        height: '100%',
        backgroundColor: 'transparent',
        color: 'var(--md-sys-color-on-surface)',
        fontSize: '14px',
        fontFamily: 'Consolas, Monaco, "Courier New", monospace',
      },
      '.cm-content': {
        caretColor: 'var(--md-sys-color-primary)',
        padding: '12px 0',
      },
      '.cm-line': {
        padding: '0 16px',
        lineHeight: '1.6',
      },
      '.cm-cursor, .cm-dropCursor': {
        borderLeftColor: 'var(--md-sys-color-primary)',
        borderLeftWidth: '2px',
      },
      '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
        backgroundColor: isDark
          ? 'rgba(174, 198, 255, 0.15)'
          : 'rgba(0, 88, 189, 0.15)',
      },
      '.cm-activeLine': {
        backgroundColor: isDark
          ? 'rgba(255, 255, 255, 0.05)'
          : 'rgba(0, 0, 0, 0.03)',
      },
      '.cm-activeLineGutter': {
        backgroundColor: 'transparent',
      },
      '.cm-gutters': {
        backgroundColor: 'transparent',
        color: 'var(--md-sys-color-on-surface-variant)',
        border: 'none',
        borderRight: '1px solid var(--md-sys-color-outline-variant)',
        paddingRight: '8px',
      },
      '.cm-lineNumbers .cm-gutterElement': {
        padding: '0 8px 0 12px',
        fontSize: '13px',
      },
      '.cm-foldGutter': {
        width: '20px',
      },
      '.cm-diagnostic-error': {
        borderBottom: '2px wavy var(--md-sys-color-error)',
      },
      '.cm-diagnostic-warning': {
        borderBottom: '2px wavy var(--md-sys-color-tertiary)',
      },
    },
    { dark: isDark }
  )
}

/**
 * 创建语法高亮主题
 */
function createSyntaxHighlighting() {
  return syntaxHighlighting(
    HighlightStyle.define([
      { tag: t.comment, color: 'var(--md-sys-color-on-surface-variant)', fontStyle: 'italic' },
      { tag: t.string, color: 'var(--md-sys-color-tertiary)' },
      { tag: t.number, color: 'var(--md-sys-color-secondary)' },
      { tag: t.bool, color: 'var(--md-sys-color-primary)' },
      { tag: t.null, color: 'var(--md-sys-color-on-surface-variant)', fontStyle: 'italic' },
      { tag: t.keyword, color: 'var(--md-sys-color-primary)', fontWeight: 'bold' },
      { tag: t.operator, color: 'var(--md-sys-color-on-surface)' },
      { tag: t.className, color: 'var(--md-sys-color-secondary)' },
      { tag: t.definition(t.typeName), color: 'var(--md-sys-color-secondary)' },
      { tag: t.typeName, color: 'var(--md-sys-color-secondary)' },
      { tag: t.propertyName, color: 'var(--md-sys-color-on-surface)' },
      { tag: t.function(t.variableName), color: 'var(--md-sys-color-primary)' },
      { tag: t.variableName, color: 'var(--md-sys-color-on-surface)' },
    ])
  )
}

// 创建编辑器
onMounted(() => {
  if (!editorRef.value) return

  const state = EditorState.create({
    doc: props.modelValue,
    extensions: [
      basicSetup,
      StreamLanguage.define(toml),
      themeCompartment.of(createM3Theme()),
      readonlyCompartment.of(EditorView.editable.of(!props.readonly)),
      createSyntaxHighlighting(),
      linter(lintTOML, { delay: 500 }),
      inlineDiagnostics(),
      EditorView.lineWrapping,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const newValue = update.state.doc.toString()
          emit('update:modelValue', newValue)
        }
      }),
    ],
  })

  editorView.value = new EditorView({
    state,
    parent: editorRef.value,
  })
})

// 销毁编辑器
onUnmounted(() => {
  editorView.value?.destroy()
  editorView.value = null
})

// 监听主题变化
const observer = new MutationObserver(() => {
  if (editorView.value) {
    editorView.value.dispatch({
      effects: themeCompartment.reconfigure(createM3Theme()),
    })
  }
})

onMounted(() => {
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  })
})

onUnmounted(() => {
  observer.disconnect()
})

// 监听只读状态变化
watch(
  () => props.readonly,
  (newReadonly) => {
    if (editorView.value) {
      editorView.value.dispatch({
        effects: readonlyCompartment.reconfigure(EditorView.editable.of(!newReadonly)),
      })
    }
  }
)

// 监听外部值变化
watch(
  () => props.modelValue,
  (newValue) => {
    if (editorView.value && newValue !== editorView.value.state.doc.toString()) {
      editorView.value.dispatch({
        changes: {
          from: 0,
          to: editorView.value.state.doc.length,
          insert: newValue,
        },
      })
    }
  }
)
</script>

<style scoped>
.toml-editor-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-container {
  flex: 1;
  overflow: auto;
  background: color-mix(in srgb, var(--md-sys-color-surface) 60%, transparent);
  /* 背景模糊由外层容器控制，避免叠加 */
}

/* CodeMirror 样式覆盖 */
.editor-container :deep(.cm-editor) {
  height: 100%;
  outline: none;
}

.editor-container :deep(.cm-scroller) {
  overflow: auto;
  scrollbar-width: thin;
}

.editor-container :deep(.cm-content) {
  min-height: 100%;
}

.editor-container :deep(.cm-line) {
  padding: 0 16px;
}

/* Lint 错误样式 */
.editor-container :deep(.cm-lintRange-error) {
  background: none;
  text-decoration: underline wavy var(--md-sys-color-error);
}

.editor-container :deep(.cm-lintRange-warning) {
  background: none;
  text-decoration: underline wavy var(--md-sys-color-tertiary);
}

.editor-container :deep(.cm-tooltip-lint) {
  background: var(--md-sys-color-surface-container-high);
  border: 1px solid var(--md-sys-color-outline-variant);
  color: var(--md-sys-color-on-surface);
  border-radius: 8px;
  padding: 8px 12px;
  z-index: 1000;
  position: fixed;
}

.editor-container :deep(.cm-diagnostic-error) {
  border-bottom: 2px wavy var(--md-sys-color-error);
}

.editor-container :deep(.cm-diagnostic-warning) {
  border-bottom: 2px wavy var(--md-sys-color-tertiary);
}
</style>
