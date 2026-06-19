/**
 * XML 轨内置组件注册表。
 *
 * 提供 XML 标签名到 Vue 组件的映射查找功能。
 * 新增组件时只需在此文件注册映射即可。
 */

import { type Component, defineAsyncComponent } from 'vue'

// === 组件映射表 ===

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

// === 布局组件（Layout） ===

const SysVbox = defineAsyncComponent(() => import('./SysVbox.vue'))
const SysHbox = defineAsyncComponent(() => import('./SysHbox.vue'))
const SysGrid = defineAsyncComponent(() => import('./SysGrid.vue'))
const SysCard = defineAsyncComponent(() => import('./SysCard.vue'))
const SysTabs = defineAsyncComponent(() => import('./SysTabs.vue'))
const SysDialog = defineAsyncComponent(() => import('./SysDialog.vue'))
const SysDivider = defineAsyncComponent(() => import('./SysDivider.vue'))
const SysSpacer = defineAsyncComponent(() => import('./SysSpacer.vue'))

// === 基础组件（Basic） ===

const SysText = defineAsyncComponent(() => import('./SysText.vue'))
const SysInput = defineAsyncComponent(() => import('./SysInput.vue'))
const SysTextarea = defineAsyncComponent(() => import('./SysTextarea.vue'))
const SysSelect = defineAsyncComponent(() => import('./SysSelect.vue'))
const SysSwitch = defineAsyncComponent(() => import('./SysSwitch.vue'))
const SysSlider = defineAsyncComponent(() => import('./SysSlider.vue'))
const SysDatePicker = defineAsyncComponent(() => import('./SysDatePicker.vue'))
const SysButton = defineAsyncComponent(() => import('./SysButton.vue'))
const SysIconButton = defineAsyncComponent(() => import('./SysIconButton.vue'))
const SysIcon = defineAsyncComponent(() => import('./SysIcon.vue'))
const SysTag = defineAsyncComponent(() => import('./SysTag.vue'))
const SysBadge = defineAsyncComponent(() => import('./SysBadge.vue'))

// === 高级组件（Advanced） ===

const SysTable = defineAsyncComponent(() => import('./SysTable.vue'))
const SysChart = defineAsyncComponent(() => import('./SysChart.vue'))
const SysForm = defineAsyncComponent(() => import('./SysForm.vue'))
const SysList = defineAsyncComponent(() => import('./SysList.vue'))

// === 注册所有组件 ===

/** 初始化并注册所有内置 XML 组件 */
export function registerAllXmlComponents(): void {
  // 布局组件
  registerXmlComponent('vbox', SysVbox)
  registerXmlComponent('hbox', SysHbox)
  registerXmlComponent('grid', SysGrid)
  registerXmlComponent('card', SysCard)
  registerXmlComponent('tabs', SysTabs)
  registerXmlComponent('dialog', SysDialog)
  registerXmlComponent('divider', SysDivider)
  registerXmlComponent('spacer', SysSpacer)

  // 基础组件
  registerXmlComponent('sys-text', SysText)
  registerXmlComponent('sys-input', SysInput)
  registerXmlComponent('sys-textarea', SysTextarea)
  registerXmlComponent('sys-select', SysSelect)
  registerXmlComponent('sys-switch', SysSwitch)
  registerXmlComponent('sys-slider', SysSlider)
  registerXmlComponent('sys-date-picker', SysDatePicker)
  registerXmlComponent('sys-button', SysButton)
  registerXmlComponent('sys-icon-button', SysIconButton)
  registerXmlComponent('sys-icon', SysIcon)
  registerXmlComponent('sys-tag', SysTag)
  registerXmlComponent('sys-badge', SysBadge)

  // 高级组件
  registerXmlComponent('sys-table', SysTable)
  registerXmlComponent('sys-chart', SysChart)
  registerXmlComponent('sys-form', SysForm)
  registerXmlComponent('sys-list', SysList)
}

// 模块加载时自动注册
registerAllXmlComponents()
