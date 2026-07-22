/**
 * Demo HTML Plugin - 交互脚本
 *
 * 由 HTML 沙箱通过 fetch 加载、executeScript 注入执行。
 * 执行前沙箱自动注入 `const sys = window.__plugin_sys_<pageId>;` 前缀，
 * 因此本脚本可直接使用 sys.* 桥接对象。
 *
 * DOM 元素在沙箱 Shadow DOM 内，需通过 host.shadowRoot 查询。
 */

// 沙箱 Shadow DOM 内的元素查询
const host = document.querySelector('.html-sandbox-host')
const root = host?.shadowRoot
if (!root) {
  console.error('[demo-html] 未找到沙箱 shadowRoot')
} else {
  const $ = (sel) => root.querySelector(sel)
  const $$ = (sel) => root.querySelectorAll(sel)

  // ========== 1. sys.vars 计数器 ==========
  sys.vars.counter = sys.vars.counter ?? 0

  function updateCounterDisplay() {
    const display = $('#counter-display')
    const raw = $('#counter-raw')
    if (display) display.textContent = String(sys.vars.counter)
    if (raw) raw.textContent = String(sys.vars.counter)
  }

  $('#inc-btn')?.addEventListener('click', () => {
    sys.vars.counter++
    updateCounterDisplay()
    flashElement('#counter-display', 'counter-pulse')
  })

  $('#dec-btn')?.addEventListener('click', () => {
    sys.vars.counter--
    updateCounterDisplay()
    flashElement('#counter-display', 'counter-pulse')
  })

  $('#reset-btn')?.addEventListener('click', () => {
    sys.vars.counter = 0
    updateCounterDisplay()
    sys.ui.toast('计数器已重置', 'info')
  })

  updateCounterDisplay()

  // ========== 2. sys.request + sys-table 任务管理 ==========
  async function loadTasks() {
    try {
      const tasks = await sys.request('/demo-html/tasks')
      const table = $('#task-table')
      if (table) {
        table.data = tasks
      }
      const countEl = $('#task-count')
      if (countEl) {
        countEl.textContent = `共 ${tasks.length} 条任务`
      }
    } catch (e) {
      console.error('[demo-html] 加载任务失败:', e)
      sys.ui.toast('加载任务失败', 'error')
    }
  }

  $('#add-task-btn')?.addEventListener('click', async () => {
    const input = $('#task-input')
    const select = $('#priority-select')
    const title = input?.value || input?.getAttribute('value') || ''
    const priority = select?.value || select?.getAttribute('value') || 'medium'

    if (!title.trim()) {
      sys.ui.toast('请输入任务标题', 'warn')
      return
    }

    try {
      await sys.request('/demo-html/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), priority }),
      })
      if (input) input.value = ''
      await loadTasks()
      sys.ui.toast('任务创建成功', 'success')
    } catch (e) {
      console.error('[demo-html] 创建任务失败:', e)
      sys.ui.toast('创建任务失败', 'error')
    }
  })

  $('#refresh-tasks-btn')?.addEventListener('click', async () => {
    await loadTasks()
    sys.ui.toast('任务列表已刷新', 'info')
  })

  $('#show-stats-btn')?.addEventListener('click', async () => {
    try {
      const stats = await sys.request('/demo-html/stats')
      sys.ui.toast(
        `总计 ${stats.total}，完成 ${stats.done}，待办 ${stats.pending}`,
        'info'
      )
    } catch (e) {
      sys.ui.toast('获取统计失败', 'error')
    }
  })

  loadTasks()

  // ========== 3. sys-chart 图表 ==========
  async function loadChart() {
    try {
      const data = await sys.request('/demo-html/metrics')
      const chart = $('#metrics-chart')
      if (chart) {
        chart.data = data
      }
      const status = $('#chart-status')
      if (status) {
        status.textContent = `已加载 ${data.series?.length || 0} 条数据线`
      }
    } catch (e) {
      console.error('[demo-html] 加载图表失败:', e)
      const status = $('#chart-status')
      if (status) status.textContent = '加载失败'
    }
  }

  $('#refresh-chart-btn')?.addEventListener('click', async () => {
    const status = $('#chart-status')
    if (status) status.textContent = '加载中...'
    await loadChart()
    sys.ui.toast('图表已刷新', 'success')
  })

  loadChart()

  // ========== 4. sys.ui Toast 通知 ==========
  $('#toast-info-btn')?.addEventListener('click', () => {
    sys.ui.toast('这是一条 Info 通知', 'info')
  })

  $('#toast-success-btn')?.addEventListener('click', () => {
    sys.ui.toast('操作成功完成！', 'success')
  })

  $('#toast-error-btn')?.addEventListener('click', () => {
    sys.ui.toast('发生错误，请重试', 'error')
  })

  // ========== 5. sys.ui 对话框 ==========
  $('#alert-btn')?.addEventListener('click', async () => {
    await sys.ui.alert('这是一个 Alert 对话框，用于告知用户重要信息。')
  })

  $('#confirm-btn')?.addEventListener('click', async () => {
    const ok = await sys.ui.confirm('确认要执行此操作吗？')
    if (ok) {
      sys.ui.toast('用户确认了操作', 'success')
    } else {
      sys.ui.toast('用户取消了操作', 'info')
    }
  })

  $('#open-dialog-btn')?.addEventListener('click', () => {
    sys.ui.dialog.open('custom-dialog')
  })

  $('#dialog-cancel-btn')?.addEventListener('click', () => {
    sys.ui.dialog.close('custom-dialog')
  })

  $('#dialog-confirm-btn')?.addEventListener('click', () => {
    const input = $('#dialog-input')
    const val = input?.value || input?.getAttribute('value') || ''
    sys.ui.dialog.close('custom-dialog')
    sys.ui.toast(`对话框确认：${val || '（空）'}`, 'success')
  })

  // ========== 6. sys.bus 事件总线 ==========
  const eventLog = $('#event-log')

  sys.bus.on('demo:event', (payload) => {
    if (eventLog) {
      eventLog.textContent = `事件日志：收到 "${payload}"`
      flashElement('#event-log', 'event-log-flash')
    }
    sys.ui.toast(`事件已接收：${payload}`, 'info')
  })

  $('#emit-event-btn')?.addEventListener('click', () => {
    const input = $('#event-input')
    const payload = input?.value || input?.getAttribute('value') || '(无内容)'
    sys.bus.emit('demo:event', payload)
  })

  // ========== 7. 系统信息 ==========
  const themeInfo = $('#theme-info')
  if (themeInfo) {
    themeInfo.textContent = `模式: ${sys.theme.mode}，主色: ${sys.theme.primary}`
  }

  const globalInfo = $('#global-info')
  if (globalInfo) {
    const g = sys.global
    const keys = Object.keys(g)
    globalInfo.textContent = keys.length > 0
      ? `${keys.join(', ')}（共 ${keys.length} 项）`
      : '（无全局变量）'
  }

  const formatDemo = $('#format-demo')
  if (formatDemo) {
    const now = new Date().toISOString()
    formatDemo.textContent = `${sys.format.date(now)} | ${sys.format.number(1234567.89)} | ${sys.format.currency(99.99)}`
  }

  const routeInfo = $('#route-info')
  if (routeInfo) {
    routeInfo.textContent = sys.route.current
  }

  $('#route-back-btn')?.addEventListener('click', () => {
    sys.route.back()
  })

  // ========== 辅助：元素闪烁动画 ==========
  function flashElement(selector, className) {
    const el = $(selector)
    if (!el) return
    el.classList.remove(className)
    void el.offsetWidth
    el.classList.add(className)
  }

  console.log('[demo-html] 脚本初始化完成')
}
