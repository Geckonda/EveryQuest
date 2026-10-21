import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import TodayView from '../views/TodayView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    /** Страница только для гостей: вошедшего пользователя отправляем на главную. */
    guestOnly?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'today',
      component: TodayView,
    },
    {
      path: '/quests',
      name: 'quests',
      component: () => import('../views/QuestsView.vue'),
    },
    {
      path: '/calendar',
      name: 'calendar',
      component: () => import('../views/CalendarView.vue'),
    },
    {
      path: '/rewards',
      name: 'rewards',
      component: () => import('../views/RewardsView.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/HistoryView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { guestOnly: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // Первый переход после загрузки страницы: токена в памяти нет — пробуем cookie.
  if (!auth.user && !auth.restoreAttempted) await auth.restore()

  if (to.meta.guestOnly) {
    return auth.user ? { name: 'today' } : true
  }
  if (!auth.user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
