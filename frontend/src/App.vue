<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  NButton,
  NConfigProvider,
  NDialogProvider,
  NMessageProvider,
  darkTheme,
  dateRuRU,
  ruRU,
  useOsTheme,
} from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { darkOverrides, lightOverrides } from '@/theme'
import PurseBadge from '@/components/PurseBadge.vue'
import SessionTimer from '@/components/SessionTimer.vue'
import { useSessionsStore } from '@/stores/sessions'

const auth = useAuthStore()
const sessions = useSessionsStore()
const route = useRoute()
const router = useRouter()
const osTheme = useOsTheme()
const isDark = computed(() => osTheme.value === 'dark')
const theme = computed(() => (isDark.value ? darkTheme : null))
const overrides = computed(() => (isDark.value ? darkOverrides : lightOverrides))

const navItems = [
  { to: '/', label: 'Квесты' },
  { to: '/rewards', label: 'Таверна' },
  { to: '/history', label: 'Летопись' },
  { to: '/settings', label: 'Настройки' },
]

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}

// Идущие траты — сразу после входа: таймер в шапке виден на любой странице.
watch(
  () => auth.user?.id,
  (id) => {
    if (id) sessions.load().catch(() => {})
  },
  { immediate: true },
)

// Вернулись во вкладку — баланс мог измениться (штрафы, другое устройство),
// а трату могли заказать или закончить на телефоне.
function onVisibilityChange() {
  if (document.visibilityState !== 'visible' || !auth.user) return
  auth.fetchMe().catch(() => {})
  sessions.load().catch(() => {})
}
onMounted(() => document.addEventListener('visibilitychange', onVisibilityChange))
onUnmounted(() => document.removeEventListener('visibilitychange', onVisibilityChange))
</script>

<template>
  <NConfigProvider
    :theme="theme"
    :theme-overrides="overrides"
    :locale="ruRU"
    :date-locale="dateRuRU"
  >
    <!-- Сообщения снизу: сверху они закрывали бы кошелёк и его анимацию. -->
    <NMessageProvider placement="bottom">
      <NDialogProvider>
        <header class="sign">
          <div class="sign-row">
            <RouterLink to="/" class="logo">
              <svg class="emblem" viewBox="0 0 24 24" aria-hidden="true">
                <!-- Кружка эля -->
                <path
                  d="M5 6h10v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2zM15 9h2.5a2.5 2.5 0 0 1 0 5H15"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linejoin="round"
                />
                <path
                  d="M4.5 6.5c0-2 1.6-3 3-2.5 0.6-1.4 2.6-1.8 3.6-0.6 1.2-0.8 3.6-0.2 3.6 1.9"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.6"
                  stroke-linecap="round"
                />
                <path d="M8.5 10v6M11.5 10v6" stroke="currentColor" stroke-width="1.2" />
              </svg>
              Ежеквестик
            </RouterLink>
            <div v-if="auth.user" class="account">
              <SessionTimer />
              <PurseBadge :balance="auth.user.balance" />
              <span class="username">{{ auth.user.username }}</span>
              <NButton size="small" quaternary class="leave" @click="logout">Уйти</NButton>
            </div>
          </div>
          <nav v-if="auth.user" class="sign-nav">
            <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
              {{ item.label }}
            </RouterLink>
          </nav>
        </header>
        <main>
          <div :class="route.meta.guestOnly ? 'guest' : 'page'">
            <RouterView />
          </div>
        </main>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style scoped>
/* Шапка — деревянная вывеска над дверью таверны. */
.sign {
  position: sticky;
  top: 0;
  z-index: 10;
  color: var(--color-sign-text);
  background:
    repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.12) 0 1px, transparent 1px 7px),
    linear-gradient(180deg, #4a311b, var(--color-sign));
  border-bottom: 3px solid #1d130a;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
}

.sign-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  max-width: 960px;
  margin: 0 auto;
  padding: 10px 16px 6px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-sign-gold);
  font-family: var(--font-heading);
  font-size: 1.6rem;
  font-weight: 700;
  text-decoration: none;
  text-shadow: 0 1px 0 #000;
  white-space: nowrap;
}

.emblem {
  width: 26px;
  height: 26px;
}

.account {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.username {
  color: var(--color-sign-muted);
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.leave {
  color: var(--color-sign-muted);
}

.sign-nav {
  display: flex;
  gap: 2px;
  max-width: 960px;
  margin: 0 auto;
  padding: 0 10px;
  overflow-x: auto;
  scrollbar-width: none;
}

.sign-nav a {
  padding: 6px 10px 8px;
  color: var(--color-sign-muted);
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 700;
  text-decoration: none;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}

.sign-nav a:hover {
  color: var(--color-sign-text);
}

.sign-nav a.router-link-exact-active {
  color: var(--color-sign-gold);
  border-bottom-color: var(--color-sign-gold);
}

@media (max-width: 520px) {
  .username {
    display: none;
  }

  .logo {
    font-size: 1.35rem;
  }
}

main {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 12px 40px;
}

/* Страница книги, лежащей на столе. */
.page {
  padding: 20px 20px 28px;
  border: 1px solid var(--color-border);
  border-radius: 3px;
  background-color: var(--color-page);
  background-image: var(--paper-grain);
  box-shadow: var(--shadow-page);
}

@media (max-width: 520px) {
  main {
    padding: 12px 8px 32px;
  }

  .page {
    padding: 16px 14px 24px;
  }
}
</style>
