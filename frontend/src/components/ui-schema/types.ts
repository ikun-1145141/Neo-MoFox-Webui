/**
 * UI Schema 组件类型 — 统一从 xmlParser 导出规范类型。
 *
 * 组件内部统一使用 `UiNode`（attrs / text 字段），
 * 不再维护本地 UINode（attributes / content 字段）。
 */
export type { UiNode, UiPageMetadata, ParsedUiPage } from '@/utils/xmlParser'
