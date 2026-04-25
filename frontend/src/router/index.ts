import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: { requiresAuth: true, title: '主页', icon: 'material-symbols:home-outline-rounded' },
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

export default router
