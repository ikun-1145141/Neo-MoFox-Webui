/**
 * MD3 Material Color Utilities 封装
 * 用于从壁纸/自定义颜色提取 MD3 色彩方案，应用为 CSS 变量
 */
import {
  argbFromHex,
  themeFromSourceColor,
  applyTheme,
} from '@material/material-color-utilities'

export function applyMd3Theme(sourceHex: string, dark: boolean) {
  const theme = themeFromSourceColor(argbFromHex(sourceHex))
  applyTheme(theme, { target: document.body, dark })
}

export function hexFromArgb(argb: number): string {
  const r = (argb >> 16) & 0xff
  const g = (argb >> 8) & 0xff
  const b = argb & 0xff
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`
}
