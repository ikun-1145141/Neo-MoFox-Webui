/**
 * XML 轨组件注册表。
 *
 * 维护 XML 标签名 → Vue 组件的映射，供 `xml-renderer.ts` 在
 * 遍历 DOM 树时按标签名查找对应的 Vue 组件。
 *
 * 与 `html/custom-element-registry.ts` 相对 —— 这里注册的是
 * 「Vue 组件」（用于 XML 渲染器内部 h() 调用），后者注册的是
 * 「自定义元素」（用于 HTML 沙箱中的 Web Component）。
 *
 * 两者共享同一套 SFC 源（`components/plugin-ui/sys-components/`）。
 */

import { type Component } from 'vue'
import * as SysComponents from '../../../components/plugin-ui/sys-components'

// === 注册表 ===

/** XML 标签名 → Vue 组件的映射表 */
const componentRegistry = new Map<string, Component>()

/**
 * 注册一个 XML 组件映射。
 *
 * @param tagName - XML 标签名（小写）
 * @param component - Vue 组件
 */
export function registerXmlComponent(tagName: string, component: Component): void {
  componentRegistry.set(tagName.toLowerCase(), component)
}

/**
 * 根据 XML 标签名获取对应的 Vue 组件。
 *
 * @param tagName - XML 标签名
 * @returns Vue 组件或 null（未注册）
 */
export function getXmlComponent(tagName: string): Component | null {
  return componentRegistry.get(tagName.toLowerCase()) || null
}

/**
 * 检查指定标签是否已注册。
 *
 * @param tagName - XML 标签名
 * @returns 是否已注册
 */
export function hasXmlComponent(tagName: string): boolean {
  return componentRegistry.has(tagName.toLowerCase())
}

// === 内置组件批量注册 ===

/**
 * 初始化并注册所有内置 XML 组件。
 *
 * 把 `sys-components/` 下的所有 SFC 注册到 XML 标签映射表。
 */
export function registerAllXmlComponents(): void {
  // 布局组件
  registerXmlComponent('vbox', SysComponents.SysVbox)
  registerXmlComponent('hbox', SysComponents.SysHbox)
  registerXmlComponent('grid', SysComponents.SysGrid)
  registerXmlComponent('card', SysComponents.SysCard)
  registerXmlComponent('tabs', SysComponents.SysTabs)
  registerXmlComponent('dialog', SysComponents.SysDialog)
  registerXmlComponent('divider', SysComponents.SysDivider)
  registerXmlComponent('spacer', SysComponents.SysSpacer)

  // 基础组件
  registerXmlComponent('sys-text', SysComponents.SysText)
  registerXmlComponent('sys-input', SysComponents.SysInput)
  registerXmlComponent('sys-textarea', SysComponents.SysTextarea)
  registerXmlComponent('sys-select', SysComponents.SysSelect)
  registerXmlComponent('sys-switch', SysComponents.SysSwitch)
  registerXmlComponent('sys-slider', SysComponents.SysSlider)
  registerXmlComponent('sys-date-picker', SysComponents.SysDatePicker)
  registerXmlComponent('sys-button', SysComponents.SysButton)
  registerXmlComponent('sys-icon-button', SysComponents.SysIconButton)
  registerXmlComponent('sys-icon', SysComponents.SysIcon)
  registerXmlComponent('sys-tag', SysComponents.SysTag)
  registerXmlComponent('sys-badge', SysComponents.SysBadge)

  // 高级组件
  registerXmlComponent('sys-table', SysComponents.SysTable)
  registerXmlComponent('sys-chart', SysComponents.SysChart)
  registerXmlComponent('sys-form', SysComponents.SysForm)
  registerXmlComponent('sys-list', SysComponents.SysList)

  // 浮层组件
  registerXmlComponent('sys-toast', SysComponents.SysToast)
}

// 模块加载时自动注册
registerAllXmlComponents()
