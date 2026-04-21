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
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      component: () => import('../views/SettingsView.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/settings/theme',
        },
        {
          path: 'theme',
          name: 'settings-theme',
          component: () => import('../views/settings/ThemeView.vue'),
        },
        {
          path: 'general',
          name: 'settings-general',
          component: () => import('../views/settings/GeneralView.vue'),
        },
        {
          path: 'data',
          name: 'settings-data',
          component: () => import('../views/settings/DataView.vue'),
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
