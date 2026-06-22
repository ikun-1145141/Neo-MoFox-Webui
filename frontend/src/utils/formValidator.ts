/**
 * Form Validator for UI Schema
 *
 * 对插件页面表单字段执行声明式校验，规则来自 XML 字段标签的属性
 * （如 `required`、`pattern`、`min-length`、`max-length`、`min`、`max`、`type`）。
 *
 * 校验流程（参考设计文档 7.4）：
 * 1. required 字段非空校验；
 * 2. pattern 正则校验（含 email/url/tel 内置规则）；
 * 3. min-length / max-length 长度校验；
 * 4. min / max 数值范围校验（仅 type=number）。
 *
 * 失败时使用字段自带的 `error-message`（若有）作为提示文案。
 */
import { getValueByPath } from './dataStore'
import type { UiNode } from './xmlParser'

/** 单个字段的校验规则。 */
export interface FieldRule {
  /** 字段标识符（来自 `id`）。 */
  id: string
  /** 标签文本（用于默认错误提示）。 */
  label?: string
  /** 数据绑定路径（来自 `data-bind`）。 */
  dataBind?: string
  /** 输入类型（text/number/email/url/tel 等）。 */
  type?: string
  /** 是否必填。 */
  required?: boolean
  minLength?: number
  maxLength?: number
  min?: number
  max?: number
  /** 自定义正则表达式（字符串形式）。 */
  pattern?: string
  /** 自定义错误提示。 */
  errorMessage?: string
}

/** 单个字段的校验错误。 */
export interface ValidationError {
  /** 出错字段的 id。 */
  fieldId: string
  /** 错误提示文案。 */
  message: string
}

/** 校验结果。 */
export interface ValidationResult {
  /** 是否全部通过。 */
  valid: boolean
  /** 错误列表（valid 为 true 时为空）。 */
  errors: ValidationError[]
}

/** 含 `data-bind` 且参与表单校验的字段标签集合。 */
const FIELD_TAGS = new Set<string>([
  'input-field',
  'textarea',
  'select',
  'switch',
  'slider',
  'date-picker',
  'radio-group',
  'checkbox',
  'json-editor',
  'code-editor',
  'rating',
])

/** 内置类型对应的正则校验规则。 */
const BUILTIN_PATTERNS: Record<string, RegExp> = {
  email: /^[^@\s]+@[^@\s]+\.[^@\s]+$/,
  url: /^https?:\/\/[^\s]+$/i,
  tel: /^\+?[0-9\-\s]{6,20}$/,
}

/** 将属性字符串解析为布尔值（`"true"` → true）。 */
function parseBool(value: string | undefined): boolean {
  return value === 'true' || value === ''
}

/** 将属性字符串解析为数字，失败返回 undefined。 */
function parseNum(value: string | undefined): number | undefined {
  if (value === undefined || value === '') return undefined
  const n = Number(value)
  return Number.isNaN(n) ? undefined : n
}

/**
 * 从节点树中递归收集所有可校验字段的规则。
 *
 * @param nodes UI 节点列表（通常为 ParsedUiPage.layout）
 * @returns 字段规则列表
 */
export function collectFieldRules(nodes: UiNode[]): FieldRule[] {
  const rules: FieldRule[] = []

  const walk = (node: UiNode): void => {
    // template 子树为 Vue 模板，不参与字段收集
    if (node.tag === 'template') return

    if (FIELD_TAGS.has(node.tag) && node.attrs.id) {
      const a = node.attrs
      rules.push({
        id: a.id,
        label: a.label,
        dataBind: a['data-bind'],
        type: a.type,
        required: parseBool(a.required),
        minLength: parseNum(a['min-length']),
        maxLength: parseNum(a['max-length']),
        min: parseNum(a.min),
        max: parseNum(a.max),
        pattern: a.pattern,
        errorMessage: a['error-message'],
      })
    }

    for (const child of node.children) {
      walk(child)
    }
  }

  for (const node of nodes) {
    walk(node)
  }
  return rules
}

/** 判断值是否为空（用于 required 校验）。 */
function isEmpty(value: any): boolean {
  return value === undefined || value === null || value === ''
}

/** 生成字段的默认显示名（优先 label，其次 id）。 */
function fieldName(rule: FieldRule): string {
  return rule.label || rule.id
}

/**
 * 校验单个字段，返回错误信息或 null（通过）。
 *
 * @param rule 字段规则
 * @param value 字段当前值
 */
export function validateField(rule: FieldRule, value: any): string | null {
  // 1. required 非空校验
  if (rule.required && isEmpty(value)) {
    return rule.errorMessage || `${fieldName(rule)}不能为空`
  }

  // 值为空且非必填时，跳过后续校验
  if (isEmpty(value)) return null

  const strValue = String(value)

  // 2. 长度校验
  if (rule.minLength !== undefined && strValue.length < rule.minLength) {
    return rule.errorMessage || `${fieldName(rule)}长度不能少于 ${rule.minLength} 个字符`
  }
  if (rule.maxLength !== undefined && strValue.length > rule.maxLength) {
    return rule.errorMessage || `${fieldName(rule)}长度不能超过 ${rule.maxLength} 个字符`
  }

  // 3. 数值范围校验
  if (rule.type === 'number') {
    const num = Number(value)
    if (Number.isNaN(num)) {
      return rule.errorMessage || `${fieldName(rule)}必须为数字`
    }
    if (rule.min !== undefined && num < rule.min) {
      return rule.errorMessage || `${fieldName(rule)}不能小于 ${rule.min}`
    }
    if (rule.max !== undefined && num > rule.max) {
      return rule.errorMessage || `${fieldName(rule)}不能大于 ${rule.max}`
    }
  }

  // 4. 内置类型正则校验（email/url/tel）
  const builtin = rule.type ? BUILTIN_PATTERNS[rule.type] : undefined
  if (builtin && !builtin.test(strValue)) {
    return rule.errorMessage || `${fieldName(rule)}格式不正确`
  }

  // 5. 自定义正则校验
  if (rule.pattern) {
    try {
      const re = new RegExp(rule.pattern)
      if (!re.test(strValue)) {
        return rule.errorMessage || `${fieldName(rule)}格式不正确`
      }
    } catch {
      // 非法正则视为不校验，避免阻塞表单
    }
  }

  return null
}

/**
 * 根据字段规则与 dataStore 校验整个表单。
 *
 * @param rules 字段规则列表（来自 collectFieldRules）
 * @param store 页面级 dataStore，按各字段的 data-bind 路径取值
 * @returns 校验结果
 */
export function validateForm(
  rules: FieldRule[],
  store: Record<string, any>,
): ValidationResult {
  const errors: ValidationError[] = []

  for (const rule of rules) {
    const value = rule.dataBind ? getValueByPath(store, rule.dataBind) : undefined
    const error = validateField(rule, value)
    if (error) {
      errors.push({ fieldId: rule.id, message: error })
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}
