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
    <!-- 自定义搜索栏 -->
    <div v-if="showSearch" class="search-bar">
      <div class="search-input-group">
        <Icon icon="material-symbols:search-rounded" :size="18" class="search-icon" />
        <input 
          ref="searchInputRef"
          v-model="searchQuery" 
          type="text" 
          placeholder="搜索..." 
          @keydown.enter="findNextMatch"
          @keydown.esc="closeSearch"
          @input="onSearchInput"
        />
        <span v-if="searchQuery" class="search-count">
          {{ matchCount > 0 ? currentMatchIndex + 1 : 0 }} / {{ matchCount }}
        </span>
      </div>
      <div class="search-actions">
        <button class="icon-btn" @click="findPrevMatch" title="上一个 (Shift+Enter)" :disabled="matchCount === 0">
          <Icon icon="material-symbols:keyboard-arrow-up-rounded" :size="20" />
        </button>
        <button class="icon-btn" @click="findNextMatch" title="下一个 (Enter)" :disabled="matchCount === 0">
          <Icon icon="material-symbols:keyboard-arrow-down-rounded" :size="20" />
        </button>
        <div class="divider"></div>
        <button class="icon-btn" @click="closeSearch" title="关闭 (Esc)">
          <Icon icon="material-symbols:close-rounded" :size="20" />
        </button>
      </div>
    </div>
    <div class="editor-container" ref="editorRef"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, shallowRef, nextTick } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { Decoration, WidgetType, keymap } from '@codemirror/view'
import { EditorState, Compartment, StateField, StateEffect, Prec } from '@codemirror/state'
import { StreamLanguage } from '@codemirror/language'
import { toml } from '@codemirror/legacy-modes/mode/toml'
import { linter, forEachDiagnostic } from '@codemirror/lint'
import { syntaxHighlighting, HighlightStyle } from '@codemirror/language'
import { tags as t } from '@lezer/highlight'
import { lintTOML } from '@/utils/toml-linter'
import { SearchQuery } from '@codemirror/search'
import Icon from '@/components/common/Icon.vue'

// ═══ 自定义搜索状态 ═══
const showSearch = ref(false)
const searchQuery = ref('')
const searchInputRef = ref<HTMLInputElement | null>(null)
const matchCount = ref(0)
const currentMatchIndex = ref(0)
const searchMatches = ref<{from: number, to: number}[]>([])

// 搜索高亮装饰器
const searchHighlightEffect = StateEffect.define<{from: number, to: number}[]>()
const searchHighlightField = StateField.define<any>({
  create() {
    return Decoration.none
  },
  update(decorations, tr) {
    decorations = decorations.map(tr.changes)
    for (let e of tr.effects) {
      if (e.is(searchHighlightEffect)) {
        const decos = e.value.map(m => Decoration.mark({class: 'cm-searchMatch'}).range(m.from, m.to))
        return Decoration.set(decos, true)
      }
    }
    return decorations
  },
  provide: f => EditorView.decorations.from(f)
})

// 当前选中搜索结果高亮
const currentMatchEffect = StateEffect.define<{from: number, to: number} | null>()
const currentMatchField = StateField.define<any>({
  create() {
    return Decoration.none
  },
  update(decorations, tr) {
    decorations = decorations.map(tr.changes)
    for (let e of tr.effects) {
      if (e.is(currentMatchEffect)) {
        if (e.value) {
          return Decoration.set([Decoration.mark({class: 'cm-searchMatch-selected'}).range(e.value.from, e.value.to)], true)
        } else {
          return Decoration.none
        }
      }
    }
    return decorations
  },
  provide: f => EditorView.decorations.from(f)
})

// 搜索快捷键
const customSearchKeymap = Prec.highest(keymap.of([
  {
    key: 'Mod-f',
    run: () => {
      openSearch()
      return true
    },
  },
  {
    key: 'F3',
    run: () => {
      findNextMatch()
      return true
    },
  },
  {
    key: 'Shift-F3',
    run: () => {
      findPrevMatch()
      return true
    },
  },
]))

function openSearch() {
  showSearch.value = true
  nextTick(() => {
    searchInputRef.value?.focus()
    if (searchQuery.value) {
      searchInputRef.value?.select()
      performSearch()
    }
  })
}

function closeSearch() {
  showSearch.value = false
  clearSearch()
  editorView.value?.focus()
}

function onSearchInput() {
  performSearch()
}

function clearSearch() {
  matchCount.value = 0
  currentMatchIndex.value = 0
  searchMatches.value = []
  if (editorView.value) {
    editorView.value.dispatch({
      effects: [
        searchHighlightEffect.of([]),
        currentMatchEffect.of(null)
      ]
    })
  }
}

function performSearch() {
  if (!editorView.value || !searchQuery.value) {
    clearSearch()
    return
  }

  const state = editorView.value.state
  const query = new SearchQuery({search: searchQuery.value})
  const cursor = query.getCursor(state)
  
  const matches: {from: number, to: number}[] = []
  let match = cursor.next()
  while (!match.done) {
    matches.push({from: match.value.from, to: match.value.to})
    match = cursor.next()
  }

  searchMatches.value = matches
  matchCount.value = matches.length
  
  if (matches.length > 0) {
    // 尝试保持当前选中的索引，如果超出范围则重置为0
    if (currentMatchIndex.value >= matches.length) {
      currentMatchIndex.value = 0
    }
    updateSearchHighlight()
  } else {
    currentMatchIndex.value = 0
    editorView.value.dispatch({
      effects: [
        searchHighlightEffect.of([]),
        currentMatchEffect.of(null)
      ]
    })
  }
}

function updateSearchHighlight() {
  if (!editorView.value || searchMatches.value.length === 0) return

  const currentMatch = searchMatches.value[currentMatchIndex.value]
  
  editorView.value.dispatch({
    effects: [
      searchHighlightEffect.of(searchMatches.value),
      currentMatchEffect.of(currentMatch)
    ],
    selection: {anchor: currentMatch.from, head: currentMatch.to},
    scrollIntoView: true
  })
}

function findNextMatch() {
  if (matchCount.value === 0) return
  currentMatchIndex.value = (currentMatchIndex.value + 1) % matchCount.value
  updateSearchHighlight()
}

function findPrevMatch() {
  if (matchCount.value === 0) return
  currentMatchIndex.value = (currentMatchIndex.value - 1 + matchCount.value) % matchCount.value
  updateSearchHighlight()
}

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
      searchHighlightField,
      currentMatchField,
      customSearchKeymap,
      EditorView.lineWrapping,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const newValue = update.state.doc.toString()
          emit('update:modelValue', newValue)
          if (showSearch.value) {
            performSearch()
          }
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
  position: relative;
}

.search-bar {
  position: absolute;
  top: 8px;
  right: 24px;
  z-index: 10;
  display: flex;
  align-items: center;
  background: var(--md-sys-color-surface-container-high);
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  padding: 4px 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  gap: 8px;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from { transform: translateY(-10px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.search-input-group {
  display: flex;
  align-items: center;
  background: var(--md-sys-color-surface);
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 4px;
  padding: 2px 8px;
  min-width: 200px;
}

.search-input-group:focus-within {
  border-color: var(--md-sys-color-primary);
}

.search-icon {
  color: var(--md-sys-color-on-surface-variant);
  margin-right: 4px;
}

.search-input-group input {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--md-sys-color-on-surface);
  font-size: 13px;
  outline: none;
  width: 100px;
}

.search-count {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  margin-left: 8px;
  white-space: nowrap;
}

.search-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn:hover:not(:disabled) {
  background: var(--md-sys-color-surface-variant);
  color: var(--md-sys-color-on-surface);
}

.icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.divider {
  width: 1px;
  height: 16px;
  background: var(--md-sys-color-outline-variant);
  margin: 0 4px;
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

/* 搜索高亮样式 */
.editor-container :deep(.cm-searchMatch) {
  background-color: rgba(255, 213, 0, 0.4);
}

.editor-container :deep(.cm-searchMatch-selected) {
  background-color: rgba(255, 140, 0, 0.6);
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
