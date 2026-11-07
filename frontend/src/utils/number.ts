/**
 * @file number.ts
 * @description 数字输入辅助函数
 */

/**
 * 将数值收敛到 [min, max] 区间内。
 * 无法解析为有限数字时回退到 min（未提供时回退到 0）。
 */
export function clampNumber(
  value: unknown,
  min?: number | null,
  max?: number | null,
): number {
  const parsed = typeof value === 'number' ? value : Number(value)
  let result = Number.isFinite(parsed) ? parsed : (min ?? 0)

  if (min != null && result < min) result = min
  if (max != null && result > max) result = max

  return result
}
