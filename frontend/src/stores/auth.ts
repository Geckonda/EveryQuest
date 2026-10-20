import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { API_PREFIX, api } from '@/api/client'
import type { RegisterPayload, TokenPair, User } from '@/api/types'

const ACCESS_KEY = 'eq.accessToken'
const REFRESH_KEY = 'eq.refreshToken'

// localStorage может быть недоступен (приватный режим) — тогда сессия живёт до перезагрузки.
const storage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set(key: string, value: string | null): void {
    try {
      if (value === null) localStorage.removeItem(key)
      else localStorage.setItem(key, value)
    } catch {
      /* ignore */
    }
  },
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(storage.get(ACCESS_KEY))
  const refreshToken = ref(storage.get(REFRESH_KEY))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => refreshToken.value !== null)

  function setAccessToken(token: string | null) {
    accessToken.value = token
    storage.set(ACCESS_KEY, token)
  }

  function setTokens(pair: TokenPair | null) {
    setAccessToken(pair?.access_token ?? null)
    refreshToken.value = pair?.refresh_token ?? null
    storage.set(REFRESH_KEY, refreshToken.value)
  }

  // Несколько запросов могут получить 401 одновременно — обновляем токен один раз.
  let refreshing: Promise<boolean> | null = null

  function refresh(): Promise<boolean> {
    if (!refreshToken.value) return Promise.resolve(false)
    refreshing ??= (async () => {
      try {
        // Напрямую через fetch: api.post при 401 сам вызвал бы refresh.
        const response = await fetch(`${API_PREFIX}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken.value }),
        })
        if (!response.ok) return false
        setAccessToken((await response.json()).access_token)
        return true
      } catch {
        return false
      } finally {
        refreshing = null
      }
    })()
    return refreshing
  }

  async function login(email: string, password: string) {
    setTokens(await api.post<TokenPair>('/auth/login', { email, password }))
    await fetchMe()
  }

  async function register(payload: RegisterPayload) {
    setTokens(await api.post<TokenPair>('/auth/register', payload))
    await fetchMe()
  }

  async function fetchMe() {
    user.value = await api.get<User>('/me')
  }

  function logout() {
    setTokens(null)
    user.value = null
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    refresh,
    login,
    register,
    fetchMe,
    logout,
  }
})
