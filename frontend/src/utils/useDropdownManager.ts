/**
 * @file useDropdownManager.ts
 * @description 全局下拉框管理器
 * 
 * 功能：
 * - 跟踪所有打开的下拉框实例
 * - 确保同时只有一个下拉框打开
 * - 提供关闭所有下拉框的方法
 */

// 全局下拉框实例集合
const openDropdowns = new Set<{ close: () => void }>()

/**
 * 注册一个下拉框实例
 */
export function registerDropdown(instance: { close: () => void }) {
  openDropdowns.add(instance)
}

/**
 * 注销一个下拉框实例
 */
export function unregisterDropdown(instance: { close: () => void }) {
  openDropdowns.delete(instance)
}

/**
 * 关闭除了指定实例外的所有下拉框
 */
export function closeOtherDropdowns(currentInstance: { close: () => void }) {
  openDropdowns.forEach((instance) => {
    if (instance !== currentInstance) {
      instance.close()
    }
  })
}

/**
 * 关闭所有下拉框
 */
export function closeAllDropdowns() {
  openDropdowns.forEach((instance) => {
    instance.close()
  })
}
