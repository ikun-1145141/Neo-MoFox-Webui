<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppShell from '../components/common/AppShell.vue'
import PageHeader from '../components/common/PageHeader.vue'
import { Icon } from '@iconify/vue'
import { useRouter } from 'vue-router'
import { healthCheck } from '../api/modules/settings'

const router = useRouter()

type HealthStatus = 'loading' | 'healthy' | 'error'
const healthStatus = ref<HealthStatus>('loading')

onMounted(async () => {
  try {
    await healthCheck()
    healthStatus.value = 'healthy'
  } catch {
    healthStatus.value = 'error'
  }
})

const quickLinks = [
  {
    label: '主题设置',
    desc: '自定义颜色、外观主题',
    icon: 'material-symbols:palette-outline-rounded',
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
    icon: 'material-symbols:database-outline-rounded',
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
          <div class="stat-val">—</div>
          <div class="stat-label">今日消息</div>
        </div>
      </div>
      <div class="stat-card">
        <Icon icon="material-symbols:extension-outline-rounded" width="28" height="28" class="stat-icon secondary" />
        <div>
          <div class="stat-val">—</div>
          <div class="stat-label">已加载插件</div>
        </div>
      </div>
    </section>

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
  </AppShell>
</template>

<style scoped>
/* 状态卡片 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 2.5rem;
}
.stat-card {
  background: var(--md-sys-color-surface-container-low);
  border-radius: 1.25rem;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.04);
}
.stat-icon { flex-shrink: 0; }
.stat-icon.success { color: var(--md-sys-color-tertiary, #4caf82); }
.stat-icon.error { color: var(--md-sys-color-error); }
.stat-icon.primary { color: var(--md-sys-color-primary); }
.stat-icon.secondary { color: var(--md-sys-color-secondary); }
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
  background: var(--md-sys-color-surface-container-low);
  border-radius: 1rem;
  border: none;
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: background 0.15s;
  box-shadow: 0px 4px 16px rgba(24, 28, 32, 0.03);
}
.quick-card:hover {
  background: var(--md-sys-color-surface-container-highest);
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
