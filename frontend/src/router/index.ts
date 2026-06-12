import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false, title: '登录' },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: { requiresAuth: true, title: '主页', icon: 'material-symbols:home-outline-rounded' },
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('../views/ConfigView.vue'),
      meta: { requiresAuth: true, title: '配置管理', icon: 'material-symbols:settings-outline-rounded' },
    },
    {
      path: '/config/plugins',
      name: 'config-plugins',
      component: () => import('../views/PluginConfigView.vue'),
      meta: { requiresAuth: true, title: '插件配置', icon: 'material-symbols:extension-outline-rounded' },
    },
    {
      path: '/plugins',
      name: 'plugins',
      component: () => import('../views/PluginsView.vue'),
      meta: { requiresAuth: true, title: '插件管理', icon: 'material-symbols:extension-outline-rounded' },
    },
    {
      path: '/plugins/:name',
      name: 'plugin-detail',
      component: () => import('../views/PluginDetailView.vue'),
      meta: { requiresAuth: true, title: '插件详情', icon: 'material-symbols:extension-outline-rounded' },
    },
    {
      path: '/llm-metrics',
      name: 'llm-metrics',
      component: () => import('../views/llm-metrics/LLMMetricsView.vue'),
      meta: { requiresAuth: true, title: 'LLM 统计', icon: 'material-symbols:bar-chart-rounded' },
    },
    {
      path: '/request-inspector',
      name: 'request-inspector',
      component: () => import('../views/RequestInspectorView.vue'),
      meta: { requiresAuth: true, title: '请求体检视器', icon: 'material-symbols:plagiarism-outline-rounded' },
    },
    {
      path: '/logs',
      name: 'logs',
      component: () => import('../views/LogView.vue'),
      meta: { requiresAuth: true, title: '日志查看', icon: 'material-symbols:terminal-rounded' },
    },
    {
      path: '/settings',
      component: () => import('../views/SettingsView.vue'),
      meta: { requiresAuth: true, title: '设置', icon: 'material-symbols:settings-outline-rounded' },
      children: [
        {
          path: '',
          redirect: '/settings/theme',
        },
        {
          path: 'theme',
          name: 'settings-theme',
          component: () => import('../views/settings/ThemeView.vue'),
          meta: { requiresAuth: true, title: '主题设置', icon: 'material-symbols:format-paint-outline-rounded' },
        },
        {
          path: 'general',
          name: 'settings-general',
          component: () => import('../views/settings/GeneralView.vue'),
          meta: { requiresAuth: true, title: '通用设置', icon: 'material-symbols:tune-rounded' },
        },
        {
          path: 'data',
          name: 'settings-data',
          component: () => import('../views/settings/DataView.vue'),
          meta: { requiresAuth: true, title: '数据管理', icon: 'material-symbols:storage-rounded' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// 路由守卫：未登录重定向到 /login
router.beforeEach((to) => {
  const token = sessionStorage.getItem('neo_token')
  if (to.meta.requiresAuth && !token) {
    return { name: 'login' }
  }
  if (to.name === 'login' && token) {
    return { name: 'home' }
  }
})

// 路由后置守卫：更新页面标题
router.afterEach((to) => {
  const baseTitle = 'Neo-MoFox-WebUI'
  const pageTitle = to.meta.title as string | undefined
  
  // 类似 VitePress 的标题格式：页面标题 | 站点名称
  if (pageTitle) {
    document.title = `${pageTitle} | ${baseTitle}`
  } else {
    document.title = baseTitle
  }
})

export default router
