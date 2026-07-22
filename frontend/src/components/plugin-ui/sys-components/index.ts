/**
 * 插件 UI 系统组件（sys-*）统一导出入口。
 *
 * 本目录是「无状态、模式中立」的组件源 —— 不论是 XML 声明式轨道，
 * 还是 HTML 自由式轨道，都从同一套 SFC 取用：
 *
 * - XML 轨：由 `src/utils/plugin-ui/xml/xml-component-registry.ts`
 *   负责把每个 SFC 注册到 XML 标签 → Vue 组件的映射表。
 * - HTML 轨：由 `src/utils/plugin-ui/html/custom-element-registry.ts`
 *   负责用 `defineCustomElement` 把每个 SFC 包装为自定义元素并
 *   `customElements.define('sys-*', ...)`。
 *
 * 本文件本身只做两件事：
 *   1. side-effect import `shared-motion.css`（让 MD3 motion 变量与
 *      通用 keyframes 在主站和 Shadow DOM 中均生效）。
 *   2. 纯 re-export 所有 SFC，供上述两个 registry 引用，并方便
 *      IDE 在其他位置按名导入。
 *
 * 不在此处维护任何注册表 —— 注册逻辑是「模式相关」的，归各自
 * 模式目录所有。这是「无状态/不屈服于任一模式」原则的体现。
 */

import './shared-motion.css'

// === 布局组件（Layout） ===

export { default as SysVbox } from './SysVbox.vue'
export { default as SysHbox } from './SysHbox.vue'
export { default as SysGrid } from './SysGrid.vue'
export { default as SysCard } from './SysCard.vue'
export { default as SysTabs } from './SysTabs.vue'
export { default as SysDialog } from './SysDialog.vue'
export { default as SysDivider } from './SysDivider.vue'
export { default as SysSpacer } from './SysSpacer.vue'

// === 基础组件（Basic） ===

export { default as SysText } from './SysText.vue'
export { default as SysInput } from './SysInput.vue'
export { default as SysTextarea } from './SysTextarea.vue'
export { default as SysSelect } from './SysSelect.vue'
export { default as SysSwitch } from './SysSwitch.vue'
export { default as SysSlider } from './SysSlider.vue'
export { default as SysDatePicker } from './SysDatePicker.vue'
export { default as SysButton } from './SysButton.vue'
export { default as SysIconButton } from './SysIconButton.vue'
export { default as SysIcon } from './SysIcon.vue'
export { default as SysTag } from './SysTag.vue'
export { default as SysBadge } from './SysBadge.vue'

// === 高级组件（Advanced） ===

export { default as SysTable } from './SysTable.vue'
export { default as SysChart } from './SysChart.vue'
export { default as SysForm } from './SysForm.vue'
export { default as SysList } from './SysList.vue'

// === 浮层组件（Overlay） ===

export { default as SysToast } from './SysToast.vue'

// === 类型导出 ===

/** 全部组件标签名（小写），供 registry 使用 */
export const SYS_COMPONENT_TAGS = [
  // 布局
  'vbox', 'hbox', 'grid', 'card', 'tabs', 'dialog', 'divider', 'spacer',
  // 基础
  'sys-text', 'sys-input', 'sys-textarea', 'sys-select', 'sys-switch',
  'sys-slider', 'sys-date-picker', 'sys-button', 'sys-icon-button',
  'sys-icon', 'sys-tag', 'sys-badge',
  // 高级
  'sys-table', 'sys-chart', 'sys-form', 'sys-list',
  // 浮层
  'sys-toast',
] as const

/** 标签名 → 对应 SFC 的导出名（PascalCase） */
export const SYS_TAG_TO_EXPORT_NAME: Record<string, string> = {
  // 布局
  'vbox': 'SysVbox',
  'hbox': 'SysHbox',
  'grid': 'SysGrid',
  'card': 'SysCard',
  'tabs': 'SysTabs',
  'dialog': 'SysDialog',
  'divider': 'SysDivider',
  'spacer': 'SysSpacer',
  // 基础
  'sys-text': 'SysText',
  'sys-input': 'SysInput',
  'sys-textarea': 'SysTextarea',
  'sys-select': 'SysSelect',
  'sys-switch': 'SysSwitch',
  'sys-slider': 'SysSlider',
  'sys-date-picker': 'SysDatePicker',
  'sys-button': 'SysButton',
  'sys-icon-button': 'SysIconButton',
  'sys-icon': 'SysIcon',
  'sys-tag': 'SysTag',
  'sys-badge': 'SysBadge',
  // 高级
  'sys-table': 'SysTable',
  'sys-chart': 'SysChart',
  'sys-form': 'SysForm',
  'sys-list': 'SysList',
  // 浮层
  'sys-toast': 'SysToast',
}
