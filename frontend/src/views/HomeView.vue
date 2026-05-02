<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import { useRouter } from 'vue-router'
import { healthCheck } from '../api/modules/settings'
import { getDashboardOverview } from '../api/modules/dashboard'
import type { DashboardOverview } from '../api/types/dashboard'

const router = useRouter()

type HealthStatus = 'loading' | 'healthy' | 'error'
const healthStatus = ref<HealthStatus>('loading')
const dashboardData = ref<DashboardOverview | null>(null)
const lastUpdate = ref<string>('')

let pollTimer: number | null = null

const fetchData = async () => {
  try {
    await healthCheck()
    healthStatus.value = 'healthy'
    const res = await getDashboardOverview()
    dashboardData.value = res
    lastUpdate.value = new Date(res.updated_at).toLocaleString()
  } catch {
    healthStatus.value = 'error'
  }
}

onMounted(() => {
  fetchData()
  pollTimer = window.setInterval(fetchData, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const quickLinks = [
  {
    label: '主题设置',
    desc: '自定义颜色、外观主题',
    icon: 'material-symbols:format-paint-outline-rounded',
    to: '/settings/theme',
  },
  {
    label: '通用设置',
    desc: '语言、字体与系统行为',
    icon: 'material-symbols:tune-rounded',
    to: '/settings/general',
  },
  {
    label: '数据管理',
    desc: '导出 / 导入配置文件',
    icon: 'material-symbols:storage-rounded',
    to: '/settings/data',
  },
]
</script>

<template>
  <AppShell>
    <PageHeader
      title="主页"
      subtitle="欢迎使用 Neo-MoFox WebUI 管理面板"
      icon="material-symbols:home-outline-rounded"
    />

    <div class="dashboard-layout">
      <div class="main-content">
        <!-- 状态卡片组 -->
        <section class="stat-grid">
          <div class="stat-card">
            <template v-if="healthStatus === 'loading'">
              <Icon icon="material-symbols:progress-activity" width="28" height="28" class="stat-icon spin" style="color: var(--md-sys-color-outline)" />
              <div>
                <div class="stat-val">检测中…</div>
                <div class="stat-label">后端状态</div>
              </div>
            </template>
            <template v-else-if="healthStatus === 'healthy'">
              <Icon icon="material-symbols:check-circle-outline-rounded" width="28" height="28" class="stat-icon success" />
              <div>
                <div class="stat-val">运行中</div>
                <div class="stat-label">后端状态</div>
              </div>
            </template>
            <template v-else>
              <Icon icon="material-symbols:cancel-outline-rounded" width="28" height="28" class="stat-icon error" />
              <div>
                <div class="stat-val">未连接</div>
                <div class="stat-label">后端状态</div>
              </div>
            </template>
          </div>
          <div class="stat-card">
            <Icon icon="material-symbols:message-outline-rounded" width="28" height="28" class="stat-icon primary" />
            <div>
              <div class="stat-val">{{ dashboardData?.business.messages.today_total ?? '—' }}</div>
              <div class="stat-label">今日消息</div>
            </div>
          </div>
          <div class="stat-card">
            <Icon icon="material-symbols:extension-outline-rounded" width="28" height="28" class="stat-icon secondary" />
            <div>
              <div class="stat-val">{{ dashboardData?.business.plugins.loaded_count ?? '—' }}</div>
              <div class="stat-label">已加载插件</div>
            </div>
          </div>
          <div class="stat-card">
            <Icon icon="material-symbols:widgets-outline-rounded" width="28" height="28" class="stat-icon tertiary" />
            <div>
              <div class="stat-val">{{ dashboardData?.business.components.total_count ?? '—' }}</div>
              <div class="stat-label">注册组件</div>
            </div>
          </div>
        </section>

        <!-- 详细数据面板 -->
        <section class="panels-grid" v-if="dashboardData">
          <div class="data-panel">
            <div class="panel-header">
              <Icon icon="material-symbols:memory-rounded" width="24" height="24" />
              <h3>运行总览</h3>
            </div>
            <div class="panel-content">
              <div class="data-item">
                <span>活跃任务</span>
                <strong>{{ dashboardData.runtime.task.active_tasks }} / {{ dashboardData.runtime.task.total_tasks }}</strong>
              </div>
              <div class="data-item">
                <span>协程池守护</span>
                <strong>{{ dashboardData.runtime.task.daemon_tasks }}</strong>
              </div>
              <div class="data-item">
                <span>事件订阅</span>
                <strong>{{ dashboardData.runtime.event.total_subscriptions }}</strong>
              </div>
              <div class="data-item">
                <span>调度任务成功率</span>
                <strong>{{ (dashboardData.runtime.scheduler.success_rate * 100).toFixed(1) }}%</strong>
              </div>
            </div>
          </div>

          <div class="data-panel">
            <div class="panel-header">
              <Icon icon="material-symbols:smart-toy-outline-rounded" width="24" height="24" />
              <h3>LLM 数据</h3>
            </div>
            <div class="panel-content">
              <div class="data-item">
                <span>总请求数</span>
                <strong>{{ dashboardData.llm.total_requests }}</strong>
              </div>
              <div class="data-item">
                <span>成功率</span>
                <strong>{{ (dashboardData.llm.success_rate * 100).toFixed(1) }}%</strong>
              </div>
              <div class="data-item">
                <span>输入 Token</span>
                <strong>{{ dashboardData.llm.total_tokens_in }}</strong>
              </div>
              <div class="data-item">
                <span>输出 Token</span>
                <strong>{{ dashboardData.llm.total_tokens_out }}</strong>
              </div>
              <div class="data-item">
                <span>总花费</span>
                <strong>{{ dashboardData.llm.total_cost.toFixed(4) }}</strong>
              </div>
            </div>
          </div>
        </section>
        
        <div class="update-time" v-if="lastUpdate">
          最后更新时间：{{ lastUpdate }}
        </div>
      </div>

      <aside class="side-content">
        <!-- 快速入口 -->
        <section class="quick-section">
          <h2 class="section-title">快速入口</h2>
          <div class="quick-grid">
            <button
              v-for="link in quickLinks"
              :key="link.to"
              class="quick-card"
              @click="router.push(link.to)"
            >
              <div class="quick-icon">
                <Icon :icon="link.icon" width="24" height="24" />
              </div>
              <div class="quick-text">
                <span class="quick-label">{{ link.label }}</span>
                <span class="quick-desc">{{ link.desc }}</span>
              </div>
              <Icon icon="material-symbols:arrow-forward-ios-rounded" width="16" height="16" class="quick-arrow" />
            </button>
          </div>
        </section>
      </aside>
    </div>
  </AppShell>
</template>

<style scoped>
.dashboard-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media (min-width: 1024px) {
  .dashboard-layout {
    grid-template-columns: 1fr 320px;
  }
}

/* 状态卡片 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}
.stat-card {
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 86%, transparent);
  border-radius: 1.25rem;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(8px);
}
.stat-icon { flex-shrink: 0; }
.stat-icon.success { color: var(--md-sys-color-tertiary, #4caf82); }
.stat-icon.error { color: var(--md-sys-color-error); }
.stat-icon.primary { color: var(--md-sys-color-primary); }
.stat-icon.secondary { color: var(--md-sys-color-secondary); }
.stat-icon.tertiary { color: var(--md-sys-color-tertiary); }
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.stat-val {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  color: var(--md-sys-color-on-surface);
}
.stat-label {
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant);
  margin-top: 0.125rem;
}

/* 数据面板 */
.panels-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}
@media (min-width: 768px) {
  .panels-grid {
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  }
}
.data-panel {
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 86%, transparent);
  border-radius: 1.25rem;
  padding: 1.5rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
  backdrop-filter: blur(8px);
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  color: var(--md-sys-color-primary);
}
.panel-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}
.panel-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.data-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
}
.data-item:last-child {
  border-bottom: none;
}
.data-item span {
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.9375rem;
}
.data-item strong {
  color: var(--md-sys-color-on-surface);
  font-size: 0.9375rem;
}

.update-time {
  text-align: right;
  font-size: 0.75rem;
  color: var(--md-sys-color-on-surface-variant);
  margin-top: 1rem;
}

/* 快速入口 */
.section-title {
  margin: 0 0 1rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}
.quick-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.quick-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: color-mix(in srgb, var(--md-sys-color-surface-container-low) 86%, transparent);
  border-radius: 1rem;
  border: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: background 0.15s;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.03);
  backdrop-filter: blur(8px);
}
.quick-card:hover {
  background: color-mix(in srgb, var(--md-sys-color-surface-container-highest) 92%, transparent);
}
.quick-icon {
  width: 44px;
  height: 44px;
  border-radius: 0.875rem;
  background: var(--md-sys-color-primary-container);
  color: var(--md-sys-color-on-primary-container);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.quick-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}
.quick-label {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}
.quick-desc {
  font-size: 0.8125rem;
  color: var(--md-sys-color-on-surface-variant);
}
.quick-arrow {
  color: var(--md-sys-color-on-surface-variant);
  flex-shrink: 0;
}
</style>
