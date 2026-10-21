<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  NButton,
  NConfigProvider,
  NDialogProvider,
  NMessageProvider,
  darkTheme,
  dateRuRU,
  ruRU,
} from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { darkOverrides, lightOverrides } from '@/theme'
import { useTheme } from '@/composables/useTheme'
import AppIcon, { type IconName } from '@/components/AppIcon.vue'
import PurseBadge from '@/components/PurseBadge.vue'
import SessionTimer from '@/components/SessionTimer.vue'
import { useSessionsStore } from '@/stores/sessions'

const auth = useAuthStore()
const sessions = useSessionsStore()
const route = useRoute()
const router = useRouter()
const { isDark } = useTheme()
const theme = computed(() => (isDark.value ? darkTheme : null))
const overrides = computed(() => (isDark.value ? darkOverrides : lightOverrides))

// Телефон — та же граница, что у панели вкладок в стилях ниже.
const phoneQuery = window.matchMedia('(max-width: 640px)')
const isPhone = ref(phoneQuery.matches)
phoneQuery.addEventListener('change', (event) => (isPhone.value = event.matches))

// Сообщения на телефоне — над панелью вкладок, а не под ней.
const messagesStyle = computed(() =>
  isPhone.value && auth.user
    ? { bottom: 'calc(var(--tab-bar-height) + 8px + env(safe-area-inset-bottom))' }
    : undefined,
)

const navItems: { to: string; label: string; icon: IconName }[] = [
  { to: '/', label: 'Сегодня', icon: 'today' },
  { to: '/quests', label: 'Квесты', icon: 'quests' },
  { to: '/calendar', label: 'Календарь', icon: 'calendar' },
  { to: '/rewards', label: 'Таверна', icon: 'tavern' },
  { to: '/history', label: 'Летопись', icon: 'chronicle' },
  { to: '/settings', label: 'Настройки', icon: 'settings' },
]

async function logout() {
  await auth.logout()
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
    <NMessageProvider placement="bottom" :container-style="messagesStyle">
      <NDialogProvider>
        <header class="sign">
          <div class="sign-row">
            <RouterLink to="/" class="logo">
              <AppIcon name="tavern" :size="26" />
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
        <main :class="{ 'with-tabs': auth.user }">
          <div :class="route.meta.guestOnly ? 'guest' : 'page'">
            <RouterView />
          </div>
        </main>
        <!-- На телефоне меню — панель вкладок внизу, под большим пальцем. -->
        <nav v-if="auth.user" class="tab-bar" aria-label="Разделы">
          <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="tab">
            <AppIcon :name="item.icon" :size="22" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
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

/* Панель вкладок — та же деревянная вывеска, только внизу. */
.tab-bar {
  display: none;
}

@media (max-width: 640px) {
  .sign-nav {
    display: none;
  }

  .sign-row {
    padding-bottom: 10px;
  }

  /* Место под панель, чтобы она не закрывала конец страницы. */
  main.with-tabs {
    padding-bottom: calc(var(--tab-bar-height) + 24px + env(safe-area-inset-bottom));
  }

  .tab-bar {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 10;
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    height: calc(var(--tab-bar-height) + env(safe-area-inset-bottom));
    padding-bottom: env(safe-area-inset-bottom);
    background:
      repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.12) 0 1px, transparent 1px 7px),
      linear-gradient(0deg, #4a311b, var(--color-sign));
    border-top: 3px solid #1d130a;
    box-shadow: 0 -3px 10px rgba(0, 0, 0, 0.35);
  }

  .tab {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    min-width: 0;
    color: var(--color-sign-muted);
    font-size: 0.6875rem;
    font-weight: 700;
    text-decoration: none;
    -webkit-tap-highlight-color: transparent;
  }

  .tab span {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tab.router-link-exact-active {
    color: var(--color-sign-gold);
  }

  .tab.router-link-exact-active .icon {
    filter: drop-shadow(0 0 4px rgba(231, 178, 79, 0.6));
  }
}
</style>
