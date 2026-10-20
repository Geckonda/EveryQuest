<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
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

const auth = useAuthStore()
const router = useRouter()
const osTheme = useOsTheme()
const theme = computed(() => (osTheme.value === 'dark' ? darkTheme : null))

const navItems = [
  { to: '/', label: 'Квесты' },
  { to: '/rewards', label: 'Траты' },
  { to: '/settings', label: 'Настройки' },
]

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <NConfigProvider :theme="theme" :locale="ruRU" :date-locale="dateRuRU">
    <NMessageProvider>
      <NDialogProvider>
        <header class="app-header">
          <span class="logo">Ежеквестик</span>
          <div v-if="auth.user" class="account">
            <span class="balance" :class="{ negative: auth.user.balance < 0 }">
              {{ auth.user.balance }} монет
            </span>
            <span class="username">{{ auth.user.username }}</span>
            <NButton size="small" quaternary @click="logout">Выйти</NButton>
          </div>
        </header>
        <nav v-if="auth.user" class="app-nav">
          <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
            {{ item.label }}
          </RouterLink>
        </nav>
        <main>
          <RouterView />
        </main>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}

.logo {
  font-weight: 700;
  font-size: 1.25rem;
}

.account {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.balance {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.balance.negative {
  color: var(--color-error);
}

.username {
  color: var(--color-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-nav {
  display: flex;
  gap: 4px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border);
  overflow-x: auto;
}

.app-nav a {
  padding: 10px 12px;
  color: var(--color-muted);
  text-decoration: none;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}

.app-nav a.router-link-exact-active {
  color: var(--color-text);
  border-bottom-color: var(--color-accent);
}

@media (max-width: 480px) {
  .username {
    display: none;
  }
}

main {
  max-width: 960px;
  margin: 0 auto;
  padding: 16px;
}
</style>
