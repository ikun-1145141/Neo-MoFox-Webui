/**
 * 安全表达式求值器。
 *
 * 实现一个极简 AST 解释器，用于插件 UI 占位符中的表达式求值。
 * 不使用 eval / new Function，通过递归下降解析器解析并执行受限表达式。
 *
 * 支持：
 * - 标识符 / 点路径访问：user.name
 * - 取反：!expr
 * - 比较运算：> < >= <= == !=
 * - 逻辑运算：&& || !
 * - 字面量：数字、字符串、true/false/null
 * - 内置函数：empty(x) / len(x) / keys(x) / values(x)
 * - 属性访问器：list.length / obj.keys
 */

// === Token 类型 ===

/** 词法 Token 类型 */
type TokenType =
  | 'Number'
  | 'String'
  | 'Boolean'
  | 'Null'
  | 'Identifier'
  | 'Dot'
  | 'LeftParen'
  | 'RightParen'
  | 'LeftBracket'
  | 'RightBracket'
  | 'Not'
  | 'And'
  | 'Or'
  | 'Eq'
  | 'NotEq'
  | 'Gt'
  | 'Gte'
  | 'Lt'
  | 'Lte'
  | 'Plus'
  | 'Minus'
  | 'Star'
  | 'Slash'
  | 'Percent'
  | 'Comma'
  | 'EOF'

/** 词法 Token */
interface Token {
  type: TokenType
  value: string | number | boolean | null
}

// === 词法分析器 ===

/**
 * 将表达式字符串解析为 Token 序列。
 *
 * @param input - 表达式字符串
 * @returns Token 数组
 */
function tokenize(input: string): Token[] {
  const tokens: Token[] = []
  let pos = 0

  while (pos < input.length) {
    const ch = input[pos]

    // 跳过空白
    if (/\s/.test(ch)) {
      pos++
      continue
    }

    // 数字字面量
    if (/\d/.test(ch)) {
      let num = ''
      while (pos < input.length && /[\d.]/.test(input[pos])) {
        num += input[pos]
        pos++
      }
      tokens.push({ type: 'Number', value: parseFloat(num) })
      continue
    }

    // 字符串字面量（单引号或双引号）
    if (ch === "'" || ch === '"') {
      const quote = ch
      pos++
      let str = ''
      while (pos < input.length && input[pos] !== quote) {
        if (input[pos] === '\\' && pos + 1 < input.length) {
          pos++
          const escaped = input[pos]
          if (escaped === 'n') str += '\n'
          else if (escaped === 't') str += '\t'
          else str += escaped
        } else {
          str += input[pos]
        }
        pos++
      }
      pos++ // 跳过结束引号
      tokens.push({ type: 'String', value: str })
      continue
    }

    // 标识符或关键字
    if (/[a-zA-Z_$]/.test(ch)) {
      let ident = ''
      while (pos < input.length && /[a-zA-Z0-9_$]/.test(input[pos])) {
        ident += input[pos]
        pos++
      }
      if (ident === 'true') {
        tokens.push({ type: 'Boolean', value: true })
      } else if (ident === 'false') {
        tokens.push({ type: 'Boolean', value: false })
      } else if (ident === 'null') {
        tokens.push({ type: 'Null', value: null })
      } else {
        tokens.push({ type: 'Identifier', value: ident })
      }
      continue
    }

    // 双字符运算符
    if (pos + 1 < input.length) {
      const two = input[pos] + input[pos + 1]
      if (two === '&&') { tokens.push({ type: 'And', value: '&&' }); pos += 2; continue }
      if (two === '||') { tokens.push({ type: 'Or', value: '||' }); pos += 2; continue }
      if (two === '==') { tokens.push({ type: 'Eq', value: '==' }); pos += 2; continue }
      if (two === '!=') { tokens.push({ type: 'NotEq', value: '!=' }); pos += 2; continue }
      if (two === '>=') { tokens.push({ type: 'Gte', value: '>=' }); pos += 2; continue }
      if (two === '<=') { tokens.push({ type: 'Lte', value: '<=' }); pos += 2; continue }
    }

    // 单字符运算符
    switch (ch) {
      case '.': tokens.push({ type: 'Dot', value: '.' }); pos++; continue
      case '(': tokens.push({ type: 'LeftParen', value: '(' }); pos++; continue
      case ')': tokens.push({ type: 'RightParen', value: ')' }); pos++; continue
      case '[': tokens.push({ type: 'LeftBracket', value: '[' }); pos++; continue
      case ']': tokens.push({ type: 'RightBracket', value: ']' }); pos++; continue
      case '!': tokens.push({ type: 'Not', value: '!' }); pos++; continue
      case '>': tokens.push({ type: 'Gt', value: '>' }); pos++; continue
      case '<': tokens.push({ type: 'Lt', value: '<' }); pos++; continue
      case '+': tokens.push({ type: 'Plus', value: '+' }); pos++; continue
      case '-': tokens.push({ type: 'Minus', value: '-' }); pos++; continue
      case '*': tokens.push({ type: 'Star', value: '*' }); pos++; continue
      case '/': tokens.push({ type: 'Slash', value: '/' }); pos++; continue
      case '%': tokens.push({ type: 'Percent', value: '%' }); pos++; continue
      case ',': tokens.push({ type: 'Comma', value: ',' }); pos++; continue
      default:
        // 跳过不识别的字符
        pos++
    }
  }

  tokens.push({ type: 'EOF', value: null })
  return tokens
}

// === AST 节点类型 ===

/** AST 节点联合类型 */
export type ASTNode =
  | NumberLiteral
  | StringLiteral
  | BooleanLiteral
  | NullLiteral
  | Identifier
  | MemberExpression
  | IndexExpression
  | UnaryExpression
  | BinaryExpression
  | CallExpression

interface NumberLiteral { type: 'NumberLiteral'; value: number }
interface StringLiteral { type: 'StringLiteral'; value: string }
interface BooleanLiteral { type: 'BooleanLiteral'; value: boolean }
interface NullLiteral { type: 'NullLiteral' }
interface Identifier { type: 'Identifier'; name: string }
interface MemberExpression { type: 'MemberExpression'; object: ASTNode; property: string }
interface IndexExpression { type: 'IndexExpression'; object: ASTNode; index: ASTNode }
interface UnaryExpression { type: 'UnaryExpression'; operator: '!' | '-'; operand: ASTNode }
interface BinaryExpression { type: 'BinaryExpression'; operator: string; left: ASTNode; right: ASTNode }
interface CallExpression { type: 'CallExpression'; callee: string; args: ASTNode[] }

// === 递归下降解析器 ===

/**
 * 递归下降解析器，将 Token 序列转为 AST。
 */
class Parser {
  private tokens: Token[]
  private pos: number = 0

  constructor(tokens: Token[]) {
    this.tokens = tokens
  }

  /** 获取当前 Token */
  private current(): Token {
    return this.tokens[this.pos]
  }

  /** 消费当前 Token 并推进指针 */
  private advance(): Token {
    const token = this.tokens[this.pos]
    this.pos++
    return token
  }

  /** 检查当前 Token 是否为指定类型 */
  private check(type: TokenType): boolean {
    return this.current().type === type
  }

  /** 若当前 Token 为指定类型则消费，否则抛错 */
  private expect(type: TokenType): Token {
    if (this.current().type !== type) {
      throw new ExpressionError(
        `期望 ${type}，实际为 ${this.current().type}（值: ${this.current().value}）`
      )
    }
    return this.advance()
  }

  /** 解析入口 */
  parse(): ASTNode {
    const node = this.parseOr()
    if (!this.check('EOF')) {
      throw new ExpressionError(`表达式未完全消费，剩余: ${this.current().value}`)
    }
    return node
  }

  /** 逻辑或 (||) */
  private parseOr(): ASTNode {
    let left = this.parseAnd()
    while (this.check('Or')) {
      this.advance()
      const right = this.parseAnd()
      left = { type: 'BinaryExpression', operator: '||', left, right }
    }
    return left
  }

  /** 逻辑与 (&&) */
  private parseAnd(): ASTNode {
    let left = this.parseEquality()
    while (this.check('And')) {
      this.advance()
      const right = this.parseEquality()
      left = { type: 'BinaryExpression', operator: '&&', left, right }
    }
    return left
  }

  /** 等式比较 (== !=) */
  private parseEquality(): ASTNode {
    let left = this.parseComparison()
    while (this.check('Eq') || this.check('NotEq')) {
      const op = this.advance().value as string
      const right = this.parseComparison()
      left = { type: 'BinaryExpression', operator: op, left, right }
    }
    return left
  }

  /** 关系比较 (> < >= <=) */
  private parseComparison(): ASTNode {
    let left = this.parseAdditive()
    while (
      this.check('Gt') ||
      this.check('Gte') ||
      this.check('Lt') ||
      this.check('Lte')
    ) {
      const op = this.advance().value as string
      const right = this.parseAdditive()
      left = { type: 'BinaryExpression', operator: op, left, right }
    }
    return left
  }

  /** 加减运算 (+ -) */
  private parseAdditive(): ASTNode {
    let left = this.parseMultiplicative()
    while (this.check('Plus') || this.check('Minus')) {
      const op = this.advance().value as string
      const right = this.parseMultiplicative()
      left = { type: 'BinaryExpression', operator: op, left, right }
    }
    return left
  }

  /** 乘除取模 (* / %) */
  private parseMultiplicative(): ASTNode {
    let left = this.parseUnary()
    while (
      this.check('Star') ||
      this.check('Slash') ||
      this.check('Percent')
    ) {
      const op = this.advance().value as string
      const right = this.parseUnary()
      left = { type: 'BinaryExpression', operator: op, left, right }
    }
    return left
  }

  /** 一元运算 (! -) */
  private parseUnary(): ASTNode {
    if (this.check('Not')) {
      this.advance()
      const operand = this.parseUnary()
      return { type: 'UnaryExpression', operator: '!', operand }
    }
    if (this.check('Minus')) {
      this.advance()
      const operand = this.parseUnary()
      return { type: 'UnaryExpression', operator: '-', operand }
    }
    return this.parsePostfix()
  }

  /** 后缀运算：属性访问 (.) 和索引访问 ([]) */
  private parsePostfix(): ASTNode {
    let node = this.parsePrimary()

    while (true) {
      if (this.check('Dot')) {
        this.advance()
        const prop = this.expect('Identifier')
        node = { type: 'MemberExpression', object: node, property: prop.value as string }
      } else if (this.check('LeftBracket')) {
        this.advance()
        const index = this.parseOr()
        this.expect('RightBracket')
        node = { type: 'IndexExpression', object: node, index }
      } else {
        break
      }
    }

    return node
  }

  /** 基础表达式：字面量、标识符、函数调用、括号表达式 */
  private parsePrimary(): ASTNode {
    const token = this.current()

    switch (token.type) {
      case 'Number':
        this.advance()
        return { type: 'NumberLiteral', value: token.value as number }

      case 'String':
        this.advance()
        return { type: 'StringLiteral', value: token.value as string }

      case 'Boolean':
        this.advance()
        return { type: 'BooleanLiteral', value: token.value as boolean }

      case 'Null':
        this.advance()
        return { type: 'NullLiteral' }

      case 'Identifier': {
        const name = token.value as string
        this.advance()

        // 检查是否为函数调用
        if (this.check('LeftParen')) {
          // 仅白名单函数允许调用
          if (!BUILTIN_FUNCTIONS.has(name)) {
            throw new ExpressionError(`不允许调用函数: ${name}，仅支持: ${[...BUILTIN_FUNCTIONS].join(', ')}`)
          }
          this.advance() // 消费 (
          const args: ASTNode[] = []
          if (!this.check('RightParen')) {
            args.push(this.parseOr())
            while (this.check('Comma')) {
              this.advance()
              args.push(this.parseOr())
            }
          }
          this.expect('RightParen')
          return { type: 'CallExpression', callee: name, args }
        }

        return { type: 'Identifier', name }
      }

      case 'LeftParen': {
        this.advance()
        const expr = this.parseOr()
        this.expect('RightParen')
        return expr
      }

      default:
        throw new ExpressionError(`意外的 Token: ${token.type}（值: ${token.value}）`)
    }
  }
}

// === 内置函数白名单 ===

/** 允许在表达式中调用的内置函数集合 */
const BUILTIN_FUNCTIONS = new Set(['empty', 'len', 'keys', 'values', 'str', 'int', 'float', 'bool'])

// === 表达式求值错误 ===

/**
 * 表达式求值错误。
 */
export class ExpressionError extends Error {
  constructor(message: string) {
    super(`[ExpressionEvaluator] ${message}`)
    this.name = 'ExpressionError'
  }
}

// === 变量解析器接口 ===

/**
 * 变量解析器接口。
 * 提供从变量池中按路径获取值的能力。
 */
export interface VariableResolver {
  get(path: string): any
}

// === AST 求值器 ===

/**
 * 对 AST 节点进行求值。
 *
 * @param node - AST 节点
 * @param resolver - 变量解析器
 * @returns 求值结果
 */
function evaluateNode(node: ASTNode, resolver: VariableResolver): any {
  switch (node.type) {
    case 'NumberLiteral':
      return node.value

    case 'StringLiteral':
      return node.value

    case 'BooleanLiteral':
      return node.value

    case 'NullLiteral':
      return null

    case 'Identifier':
      return resolver.get(node.name)

    case 'MemberExpression': {
      const obj = evaluateNode(node.object, resolver)
      if (obj == null) return undefined
      return obj[node.property]
    }

    case 'IndexExpression': {
      const obj = evaluateNode(node.object, resolver)
      const idx = evaluateNode(node.index, resolver)
      if (obj == null) return undefined
      return obj[idx]
    }

    case 'UnaryExpression': {
      const val = evaluateNode(node.operand, resolver)
      if (node.operator === '!') return !val
      if (node.operator === '-') return -val
      return val
    }

    case 'BinaryExpression': {
      const left = evaluateNode(node.left, resolver)
      const right = evaluateNode(node.right, resolver)
      return evaluateBinary(node.operator, left, right)
    }

    case 'CallExpression': {
      const args = node.args.map(arg => evaluateNode(arg, resolver))
      return evaluateBuiltin(node.callee, args)
    }
  }
}

/**
 * 执行二元运算。
 *
 * @param op - 运算符
 * @param left - 左操作数
 * @param right - 右操作数
 * @returns 运算结果
 */
function evaluateBinary(op: string, left: any, right: any): any {
  switch (op) {
    case '+': return left + right
    case '-': return left - right
    case '*': return left * right
    case '/': return right === 0 ? 0 : left / right
    case '%': return right === 0 ? 0 : left % right
    case '==': return left == right
    case '!=': return left != right
    case '>': return left > right
    case '>=': return left >= right
    case '<': return left < right
    case '<=': return left <= right
    case '&&': return left && right
    case '||': return left || right
    default:
      throw new ExpressionError(`未知运算符: ${op}`)
  }
}

/**
 * 执行内置函数调用。
 *
 * @param name - 函数名
 * @param args - 参数列表
 * @returns 调用结果
 */
function evaluateBuiltin(name: string, args: any[]): any {
  switch (name) {
    case 'empty': {
      const val = args[0]
      if (val == null) return true
      if (typeof val === 'string') return val.length === 0
      if (Array.isArray(val)) return val.length === 0
      if (typeof val === 'object') return Object.keys(val).length === 0
      return false
    }

    case 'len': {
      const val = args[0]
      if (val == null) return 0
      if (typeof val === 'string' || Array.isArray(val)) return val.length
      if (typeof val === 'object') return Object.keys(val).length
      return 0
    }

    case 'keys': {
      const val = args[0]
      if (val == null || typeof val !== 'object') return []
      return Object.keys(val)
    }

    case 'values': {
      const val = args[0]
      if (val == null || typeof val !== 'object') return []
      return Object.values(val)
    }

    case 'str': {
      const val = args[0]
      if (val == null) return ''
      return String(val)
    }

    case 'int': {
      const val = args[0]
      const parsed = parseInt(String(val), 10)
      return isNaN(parsed) ? 0 : parsed
    }

    case 'float': {
      const val = args[0]
      const parsed = parseFloat(String(val))
      return isNaN(parsed) ? 0 : parsed
    }

    case 'bool': {
      return Boolean(args[0])
    }

    default:
      throw new ExpressionError(`未知的内置函数: ${name}`)
  }
}

// === 公开 API ===

/**
 * 解析表达式字符串为 AST。
 *
 * @param expression - 表达式字符串
 * @returns AST 根节点
 * @throws ExpressionError 当表达式语法错误时
 */
export function parseExpression(expression: string): ASTNode {
  const tokens = tokenize(expression)
  const parser = new Parser(tokens)
  return parser.parse()
}

/**
 * 对表达式字符串进行求值。
 *
 * @param expression - 表达式字符串
 * @param resolver - 变量解析器，通常为 PluginUIVarStore
 * @returns 表达式结果
 * @throws ExpressionError 当表达式语法错误或求值失败时
 */
export function evaluate(expression: string, resolver: VariableResolver): any {
  const ast = parseExpression(expression)
  return evaluateNode(ast, resolver)
}

/**
 * 安全地对表达式求值，出错时返回默认值。
 *
 * @param expression - 表达式字符串
 * @param resolver - 变量解析器
 * @param defaultValue - 出错时的默认返回值
 * @returns 表达式结果或默认值
 */
export function safeEvaluate(expression: string, resolver: VariableResolver, defaultValue: any = ''): any {
  try {
    return evaluate(expression, resolver)
  } catch {
    return defaultValue
  }
}
