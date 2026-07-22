/**
 * HTML 沙箱核心：Shadow DOM 生命周期管理。
 *
 * 创建流程：
 *   1. host.attachShadow({ mode: 'open' })
 *   2. 注入 MD3 CSS 变量穿透 <style>
 *   3. 加载 styles → <link>
 *   4. fetch(entry_html) → shadowRoot.innerHTML
 *   5. 幂等注册 sys-* 自定义元素
 *   6. 构建 sys 桥接对象 → window.__plugin_sys_<pageId>
 *   7. installFetchProxy（注入 token / X-Plugin-Name / BaseResponse 解包）
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
  //    :host 默认继承主站所有自定义属性（CSS 变量天然穿透 shadow boundary）
  //    这里仅声明一个 fallback，避免插件 CSS 中 var() 拿不到值时崩溃
  const variableBootstrap = document.createElement('style')
  variableBootstrap.textContent = `
    :host {
      all: initial;
      display: block;
      contain: content;
      /* 让 MD3 颜色变量穿透（all: initial 会清除继承，需重新声明继承） */
      font-family: inherit;
      color: inherit;
      line-height: inherit;
      /* MD3 CSS 变量天然穿透 Shadow DOM，无需额外声明 */
    }
    /* 提供一套基础的 MD3 兜底色，避免插件 CSS var() 取不到值 */
    :root, :host {
      --md-sys-color-primary: var(--md-sys-color-primary, #0058bd);
      --md-sys-color-on-primary: var(--md-sys-color-on-primary, #ffffff);
      --md-sys-color-surface: var(--md-sys-color-surface, #fffaf0);
      --md-sys-color-on-surface: var(--md-sys-color-on-surface, #1a1b20);
      --md-sys-color-on-surface-variant: var(--md-sys-color-on-surface-variant, #44474e);
      --md-sys-color-outline: var(--md-sys-color-outline, #74767f);
      --md-sys-color-outline-variant: var(--md-sys-color-outline-variant, #cac4d0);
      --md-sys-color-error: var(--md-sys-color-error, #ba1a1a);
    }
  `
  shadowRoot.appendChild(variableBootstrap)

  // 3. 加载 styles
  const styleUrls = assetsUrls.styles || []
  await Promise.all(
    styleUrls.map((url) => loadStyle(shadowRoot, url))
  )

  // 4. 加载 entry HTML
  const entryUrls = assetsUrls.entry || []
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

  // 5. 幂等注册自定义元素
  registerAllPluginUICustomElements()

  // 6. 构建 sys 桥接
  const toastStore = useToastStore()
  const fetchProxyCtx: FetchProxyContext = {
    pluginName,
    getToken: () => sessionStorage.getItem('neo_token'),
    onError: (msg) => toastStore.show(msg, 'error'),
  }
  const sys = createSysBridge({
    store,
    apiEngine,
    pluginName,
    pageId,
    router,
    fetchProxyCtx,
  })

  // 7. 安装 fetch 代理
  const uninstallProxy = installFetchProxy(fetchProxyCtx)

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
  return new Promise((resolve) => {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = url
    link.onload = () => resolve()
    link.onerror = () => {
      console.warn(`[HtmlSandbox] 样式加载失败: ${url}`)
      resolve()
    }
    shadowRoot.appendChild(link)
  })
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
