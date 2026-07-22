/**
 * HTML 轨自定义元素注册表。
 *
 * 把 `sys-components/` 下的 SFC 用 Vue 的 `defineCustomElement`
 * 包装为自定义元素并 `customElements.define('sys-*', ...)`。
 *
 * 与 `xml/xml-component-registry.ts` 相对 —— 这里注册的是
 * 「自定义元素」（Web Component，用于 HTML 沙箱），后者注册的是
 * 「Vue 组件」（用于 XML 渲染器内部 h() 调用）。
 *
 * 两者共享同一套 SFC 源。
 *
 * 命名约束差异：
 * - XML 轨用裸名（`vbox`/`card`/`hbox`...），因 XML 走 Vue h() 调用，
 *   不经过 `customElements.define()`，不受 HTML 自定义元素命名约束。
 * - HTML 轨必须含连字符 —— `customElements.define('vbox', ...)`
 *   会抛 SyntaxError。故布局类在 HTML 轨一律注册为 `sys-*` 前缀
 *   （`sys-vbox` / `sys-card` / `sys-hbox`...）。
 *
 * `customElements.define` 是全局的（不受 Shadow DOM 限制），
 * 所以只需在应用启动时调用一次。多次调用是幂等的。
 */

import { defineCustomElement, type Component } from 'vue'
import * as SysComponents from '../../../components/plugin-ui/sys-components'
import { SYS_COMPONENT_TAGS } from '../../../components/plugin-ui/sys-components'

/**
 * Material Symbols 基础 CSS（注入到每个 sys-* 自定义元素的 shadow root）。
 *
 * @font-face 声明是全局的（天然穿透 shadow DOM），由 index.html 的
 * <link rel="stylesheet" href="/material-symbols/index.css"> 加载。
 * 但 .material-symbols-rounded 类样式（font-family / font-size / display 等）
 * 不穿透 shadow DOM —— 必须在每个自定义元素 shadow root 内重新声明，
 * 否则 SFC 内 <span class="material-symbols-rounded"> 渲染为纯文本而非图标。
 */
const MATERIAL_SYMBOLS_BASE_CSS = `
.material-symbols-rounded,
.material-symbols-outlined,
.material-symbols-sharp {
  font-weight: normal;
  font-style: normal;
  font-size: 24px;
  line-height: 1;
  letter-spacing: normal;
  text-transform: none;
  display: inline-block;
  white-space: nowrap;
  word-wrap: normal;
  direction: ltr;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  font-feature-settings: "liga";
}
.material-symbols-rounded {
  font-family: "Material Symbols Rounded";
}
.material-symbols-outlined {
  font-family: "Material Symbols Outlined";
}
.material-symbols-sharp {
  font-family: "Material Symbols Sharp";
}
`

/** 已注册过的 tag 集合，用于 hasPluginUICustomElement 查询 */
const registeredTags = new Set<string>()

/**
 * 把 Vue SFC 包装为 Vue CustomElement。
 *
 * 注：SFC 中 `defineEmits` 声明的事件会自动以 `CustomEvent` 形式
 * 派发到自定义元素上，事件名为 emit 时的小写连字符形式。
 * 例如 `emit('update:open', v)` → 自定义元素派发 `update:open` 事件，
 * 监听方式为 `el.addEventListener('update:open', e => e.detail)`。
 */
function wrapAsCustomElement(_tagName: string, component: Component): CustomElementConstructor {
  // Vue 3 的 defineCustomElement 接收与 defineComponent 一致的组件选项，
  // SFC 默认导出符合该格式。
  // 注：在 vite features.customElement 模式下，SFC <style> 收集到
  // component.styles 数组，defineCustomElement 会把它们注入 shadow root。
  // 我们额外追加 Material Symbols 基础 CSS，使图标在 shadow root 内可用。
  const comp = component as any
  const existingStyles: string[] = Array.isArray(comp.styles) ? comp.styles : []
  return defineCustomElement({
    ...comp,
    styles: [MATERIAL_SYMBOLS_BASE_CSS, ...existingStyles],
  } as any)
}

/**
 * 注册全部 sys-* 自定义元素。
 *
 * 幂等：多次调用只注册一次。
 */
export function registerAllPluginUICustomElements(): void {
  const components: Record<string, Component> = {
    // 布局（HTML 轨注册为 sys-* 前缀，因 customElements.define 必须含连字符）
    'sys-vbox': SysComponents.SysVbox,
    'sys-hbox': SysComponents.SysHbox,
    'sys-grid': SysComponents.SysGrid,
    'sys-card': SysComponents.SysCard,
    'sys-tabs': SysComponents.SysTabs,
    'sys-dialog': SysComponents.SysDialog,
    'sys-divider': SysComponents.SysDivider,
    'sys-spacer': SysComponents.SysSpacer,
    // 基础
    'sys-text': SysComponents.SysText,
    'sys-input': SysComponents.SysInput,
    'sys-textarea': SysComponents.SysTextarea,
    'sys-select': SysComponents.SysSelect,
    'sys-switch': SysComponents.SysSwitch,
    'sys-slider': SysComponents.SysSlider,
    'sys-date-picker': SysComponents.SysDatePicker,
    'sys-button': SysComponents.SysButton,
    'sys-icon-button': SysComponents.SysIconButton,
    'sys-icon': SysComponents.SysIcon,
    'sys-tag': SysComponents.SysTag,
    'sys-badge': SysComponents.SysBadge,
    // 高级
    'sys-table': SysComponents.SysTable,
    'sys-chart': SysComponents.SysChart,
    'sys-form': SysComponents.SysForm,
    'sys-list': SysComponents.SysList,
    // 浮层
    'sys-toast': SysComponents.SysToast,
  }

  for (const tagName of SYS_COMPONENT_TAGS) {
    if (registeredTags.has(tagName)) continue
    const component = components[tagName]
    if (!component) {
      console.warn(`[PluginUI] 未找到 ${tagName} 对应的 SFC 导出，跳过注册`)
      continue
    }
    if (customElements.get(tagName)) {
      // 已被其他模块注册（可能是热更新场景）
      registeredTags.add(tagName)
      continue
    }
    try {
      const ctor = wrapAsCustomElement(tagName, component)
      customElements.define(tagName, ctor)
      registeredTags.add(tagName)
    } catch (e) {
      console.error(`[PluginUI] 注册自定义元素 <${tagName}> 失败:`, e)
    }
  }
}

/**
 * 检查指定 tag 是否已注册。
 */
export function hasPluginUICustomElement(tagName: string): boolean {
  return registeredTags.has(tagName.toLowerCase())
}
