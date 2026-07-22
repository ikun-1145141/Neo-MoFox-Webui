/**
 * HTML 沙箱核心：Shadow DOM 生命周期管理。
 *
 * 创建流程：
 *   1. host.attachShadow({ mode: 'open' })
 *   2. 注入 MD3 CSS 变量穿透 <style>
 *   3. installFetchProxy（注入 token / X-Plugin-Name）—— 必须在资源加载前
 *   4. 加载 styles → fetch + <style>（<link> 不走 fetch 代理，无法带 Token）
 *   5. fetch(entry_html) → shadowRoot.innerHTML（fetch 已被代理）
 *   6. 幂等注册 sys-* 自定义元素
 *   7. 构建 sys 桥接对象 → window.__plugin_sys_<pageId>
 *   8. 顺序加载并执行 scripts（每个 script 注入 `const sys = ...` 前缀）
 *
 * 销毁流程：
 *   - 还原 fetch / XHR
 *   - 清空 Shadow DOM
 *   - 删除 window sys 引用
 *   - sys.destroy()
 */

import type { Router } from 'vue-router'
import type { PluginUIVarStore } from '../../../stores/plugin-ui-vars'
import type { ApiTemplateEngine } from '../api-template-engine'
import { useToastStore } from '../../../utils/toast'
import { createSysBridge, destroySysBridge, getSysAccessSnippet, type SysBridge } from './sys-bridge'
import { installFetchProxy, type FetchProxyContext } from './fetch-proxy'
import { registerAllPluginUICustomElements } from './custom-element-registry'

export interface HtmlSandboxOptions {
  pluginName: string
  pageId: string
  /** 资源 URL 映射：{ entry: [...], styles: [...], scripts: [...] } */
  assetsUrls: Record<string, string[]>
  store: PluginUIVarStore
  apiEngine: ApiTemplateEngine
  router: Router
}

export interface HtmlSandboxHandle {
  /** 销毁沙箱：还原 fetch/XHR、清空 Shadow DOM、解绑 sys */
  destroy(): void
  /** 当前 sys 桥接对象引用 */
  sys: SysBridge
}

/**
 * 创建 HTML 沙箱。
 *
 * @param host - 挂载 Shadow DOM 的宿主元素
 * @param options - 沙箱配置
 * @returns 沙箱句柄
 */
export async function createHtmlSandbox(
  host: HTMLElement,
  options: HtmlSandboxOptions
): Promise<HtmlSandboxHandle> {
  const { pluginName, pageId, assetsUrls, store, apiEngine, router } = options

  // 1. attachShadow
  //    若已存在 shadowRoot（热更新场景），复用之；否则创建。
  const shadowRoot: ShadowRoot = host.shadowRoot ?? host.attachShadow({ mode: 'open' })

  // 2. 注入 MD3 CSS 变量穿透规则
  //    不能用 all: initial —— 它会清掉所有 CSS 自定义属性（含 MD3 主题变量），
  //    导致 :host 内部 var(--md-sys-color-*) 取不到 :root 的主题值。
  //    Shadow DOM 本身已隔离主文档样式，:host 只需显式继承少数属性即可。
  //
  //    不要在 :host 上重声明 --md-sys-color-*：CSS 规范规定
  //    --x: var(--x, fallback) 是顶层自引用 → 视为 unknown → 用 fallback
  //    作为固定值，反而覆盖了从 :root 继承的动态主题变量。
  //    MD3 变量由 md3theme.ts 动态写入 document.documentElement.style，
  //    CSS 自定义属性天然穿透 shadow DOM，无需在 :host 重复声明。
  const variableBootstrap = document.createElement('style')
  variableBootstrap.textContent = `
    :host {
      display: block;
      /* 仅做 layout + style 隔离，不含 paint。
       * contain:paint 会把超出 :host 盒子的内容裁掉，导致内容超出
       * .html-sandbox-host 高度时无法被外层 overflow:auto 滚动条接管。
       * 配合外层 wrapper/host 使用 min-height:100%（可增长），
       * 让 Shadow 内容自然撑开 host，由 .plugin-page-content 滚动。 */
      contain: layout style;
      font-family: inherit;
      color: inherit;
      line-height: inherit;
      /* 不使用 all: initial —— MD3 CSS 变量需从 :root 自然穿透到 Shadow DOM */
      /* 不在此重声明 --md-sys-color-* —— 自引用会固化 fallback 值，破坏主题切换 */
    }
    /*
     * sys-* 自定义元素默认 display 规则。
     *
     * 自定义元素默认是 display: inline（HTML 规范），其内部 SFC 的
     * <div class="sys-vbox" style="width: 100%"> 等会因父级是 inline 而
     * 塌缩为 0 宽度 —— 整页不可见。这里统一设为 block，让 SFC 内核的
     * flex / grid 布局能在 block 容器中正常撑开。
     *
     * 仅作用于沙箱 Shadow DOM 内的 sys-* 元素，不污染主站。
     */
    sys-vbox, sys-hbox, sys-grid, sys-card, sys-tabs, sys-dialog,
    sys-divider, sys-spacer,
    sys-text, sys-input, sys-textarea, sys-select, sys-switch,
    sys-slider, sys-date-picker, sys-button, sys-icon-button, sys-icon,
    sys-tag, sys-badge, sys-table, sys-chart, sys-form, sys-list,
    sys-toast {
      display: block;
    }
    /*
     * Material Symbols 图标字体。
     *
     * @font-face 本身是全局的（天然穿透 shadow DOM），但如果主文档的
     * <link> 加载失败（如 base 路径不匹配），shadow DOM 内就拿不到字体。
     * 这里在 shadow root 内也声明一次，保证图标一定能渲染。
     * woff2 路径用绝对路径（含 vite base），dev / build 均一致。
     */
    @font-face {
      font-family: "Material Symbols Rounded";
      font-style: normal;
      font-weight: 100 700;
      font-display: block;
      src: url("/material-symbols/material-symbols-rounded.woff2") format("woff2");
    }
    @font-face {
      font-family: "Material Symbols Outlined";
      font-style: normal;
      font-weight: 100 700;
      font-display: block;
      src: url("/material-symbols/material-symbols-outlined.woff2") format("woff2");
    }
    @font-face {
      font-family: "Material Symbols Sharp";
      font-style: normal;
      font-weight: 100 700;
      font-display: block;
      src: url("/material-symbols/material-symbols-sharp.woff2") format("woff2");
    }
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
    .material-symbols-rounded { font-family: "Material Symbols Rounded"; }
    .material-symbols-outlined { font-family: "Material Symbols Outlined"; }
    .material-symbols-sharp { font-family: "Material Symbols Sharp"; }
  `
  shadowRoot.appendChild(variableBootstrap)

  // 3. 安装 fetch 代理（提前到资源加载之前）
  //    - 后端 plugin_ui_asset_router 对 entry/style/script/asset 强制 VerifiedDep
  //    - <link> 不走 window.fetch，浏览器无法注入 X-API-Key，故 styles 改用 fetch + <style>
  //    - 此处的 fetchProxyCtx 复用给 sys 桥接，避免重复构造
  const toastStore = useToastStore()
  const fetchProxyCtx: FetchProxyContext = {
    pluginName,
    getToken: () => sessionStorage.getItem('neo_token'),
    onError: (msg) => toastStore.show(msg, 'error'),
  }
  const uninstallProxy = installFetchProxy(fetchProxyCtx)

  // 4. 加载 styles（fetch 拿 textContent 注入 <style>，自动走代理带 Token）
  const styleUrls = assetsUrls.styles || []
  await Promise.all(
    styleUrls.map((url) => loadStyle(shadowRoot, url))
  )

  // 5. 加载 entry HTML（fetch 已被代理，自动注入 X-API-Key / X-Plugin-Name）
  //    后端 plugin_ui_manager 生成的 key 为 `entry_html`（与注册时的 assets dict 一致）
  const entryUrls = assetsUrls.entry_html || []
  if (entryUrls.length > 0) {
    try {
      const response = await fetch(entryUrls[0])
      const htmlText = await response.text()
      // 解析为 DOM 节点再插入（避免直接 innerHTML 把 <script> 也带进来
      // 提前执行 —— 我们后面手动注入脚本以加入 sys 引用）
      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = htmlText
      // 提取所有非 <script> 节点插入 shadowRoot
      const scriptsToCapture: HTMLScriptElement[] = []
      for (const node of Array.from(tempDiv.childNodes)) {
        if (node.nodeType === Node.ELEMENT_NODE) {
          const el = node as HTMLElement
          if (el.tagName === 'SCRIPT') {
            scriptsToCapture.push(el as HTMLScriptElement)
          } else {
            shadowRoot.appendChild(el)
          }
        } else {
          shadowRoot.appendChild(node.cloneNode(true))
        }
      }
      // 把内联脚本暂存，统一在 sys 注入后执行
      capturedInlineScripts = scriptsToCapture
    } catch (e) {
      console.error('[HtmlSandbox] 加载 entry HTML 失败:', e)
      throw e
    }
  }

  // 6. 幂等注册自定义元素
  registerAllPluginUICustomElements()

  // 7. 构建 sys 桥接（fetch 代理已在 step 3 安装，复用 fetchProxyCtx）
  const sys = createSysBridge({
    store,
    apiEngine,
    pluginName,
    pageId,
    router,
    fetchProxyCtx,
  })

  // 8. 执行脚本：内联 + 外链
  try {
    // 内联脚本（来自 entry HTML 中的 <script>）
    for (const inlineScript of capturedInlineScripts) {
      await executeScript(shadowRoot, inlineScript.textContent || '', pageId, true)
    }
    // 外链脚本（来自 assets_urls.scripts）
    const scriptUrls = assetsUrls.scripts || []
    for (const url of scriptUrls) {
      try {
        const response = await fetch(url)
        const code = await response.text()
        await executeScript(shadowRoot, code, pageId, true)
      } catch (e) {
        console.error(`[HtmlSandbox] 加载脚本失败: ${url}`, e)
      }
    }
  } catch (e) {
    console.error('[HtmlSandbox] 脚本执行失败:', e)
  }

  // 返回句柄
  return {
    sys,
    destroy() {
      try {
        uninstallProxy()
        destroySysBridge(sys, pageId)
        // 清空 Shadow DOM
        while (shadowRoot.firstChild) {
          shadowRoot.removeChild(shadowRoot.firstChild)
        }
      } catch (e) {
        console.error('[HtmlSandbox] 销毁失败:', e)
      }
    },
  }
}

// === 辅助 ===

let capturedInlineScripts: HTMLScriptElement[] = []

async function loadStyle(shadowRoot: ShadowRoot, url: string): Promise<void> {
  // 不能用 <link rel="stylesheet">：浏览器对 <link> 请求不会走 window.fetch，
  // 因此无法注入 X-API-Key / X-Plugin-Name，会被后端 VerifiedDep 拒为 401。
  // 改用 fetch 拿 CSS 文本（自动经过 installFetchProxy 注入鉴权头），注入 <style>。
  try {
    const response = await fetch(url)
    if (!response.ok) {
      console.warn(`[HtmlSandbox] 样式加载失败: ${url} (HTTP ${response.status})`)
      return
    }
    const cssText = await response.text()
    const style = document.createElement('style')
    style.textContent = cssText
    shadowRoot.appendChild(style)
  } catch (e) {
    console.warn(`[HtmlSandbox] 样式加载异常: ${url}`, e)
  }
}

/**
 * 在 Shadow DOM 宿主元素中执行脚本。
 *
 * 不使用 eval —— 通过动态 <script> 注入到 host 的父文档（shadowRoot
 * 不允许直接 appendChild <script> 后执行）。注入前在脚本内容前
 * 预置 `const sys = window.__plugin_sys_<pageId>;` 前缀，使插件
 * 代码能直接引用 sys。
 *
 * @param shadowRoot - 用于把脚本元素附加到 host 外的 fallback 容器
 * @param code - 脚本内容
 * @param pageId - 页面 ID，用于取 sys 引用
 * @param isModule - 是否以 ES Module 方式加载
 */
async function executeScript(
  shadowRoot: ShadowRoot,
  code: string,
  pageId: string,
  isModule = true
): Promise<void> {
  return new Promise((resolve) => {
    const script = document.createElement('script')
    if (isModule) {
      script.type = 'module'
    }
    const prefix = getSysAccessSnippet(pageId)
    script.textContent = `${prefix}\n${code}`
    script.onload = () => resolve()
    script.onerror = (e) => {
      console.error('[HtmlSandbox] 脚本执行错误:', e)
      resolve()
    }
    // 附加到 host 的父文档（不是 shadowRoot 内部）—— 否则不会执行
    const host = shadowRoot.host
    if (host && host.parentElement) {
      host.parentElement.appendChild(script)
    } else {
      document.head.appendChild(script)
    }
    // 模块脚本异步加载，立刻 resolve（onload 在 module 模式下可能不触发）
    if (isModule) {
      setTimeout(resolve, 0)
    }
  })
}
