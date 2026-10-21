import { ref } from 'vue'
import { defineStore } from 'pinia'
import { API_PREFIX, api } from '@/api/client'
import type { AccessToken, RegisterPayload, User, UserPayload } from '@/api/types'

// До перехода на httpOnly-cookie токены лежали в localStorage — подчищаем следы.
try {
  localStorage.removeItem('eq.accessToken')
  localStorage.removeItem('eq.refreshToken')
} catch {
  /* приватный режим */
}

/** Почему изменился баланс: от этого зависят звук и анимация кошелька. */
export type CoinReason = 'reward' | 'purchase' | 'penalty' | 'manual' | 'sync'

export interface CoinEvent {
  /** Растёт с каждым событием — чтобы два одинаковых изменения подряд различались. */
  id: number
  delta: number
  reason: CoinReason
}

/**
 * Вход. Refresh-токен — в httpOnly-cookie, скрипт его не видит; access-токен (15 минут)
 * живёт только в памяти. После перезагрузки страницы сессия восстанавливается по cookie.
 */
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<User | null>(null)
  /** Последнее изменение баланса; null — ещё не было. */
  const coinEvent = ref<CoinEvent | null>(null)
  let coinEventId = 0

  function announce(delta: number, reason: CoinReason) {
    if (delta !== 0) coinEvent.value = { id: ++coinEventId, delta, reason }
  }

  // Несколько запросов могут получить 401 одновременно — обновляем токен один раз.
  let refreshing: Promise<boolean> | null = null

  /** Новый access-токен по cookie. Cookie при этом тоже меняется (ротация на сервере). */
  function refresh(): Promise<boolean> {
    refreshing ??= (async () => {
      try {
        // Напрямую через fetch: api.post при 401 сам вызвал бы refresh.
        const response = await fetch(`${API_PREFIX}/auth/refresh`, { method: 'POST' })
        if (!response.ok) return false
        accessToken.value = ((await response.json()) as AccessToken).access_token
        return true
      } catch {
        return false
      } finally {
        refreshing = null
      }
    })()
    return refreshing
  }

  /** Пробовали ли уже восстановить сессию после загрузки страницы. */
  const restoreAttempted = ref(false)
  let restoring: Promise<boolean> | null = null

  /** Восстановить вход после перезагрузки: cookie → access-токен → профиль. */
  function restore(): Promise<boolean> {
    restoring ??= (async () => {
      try {
        if (!accessToken.value && !(await refresh())) return false
        await fetchMe()
        return true
      } catch {
        return false
      } finally {
        restoreAttempted.value = true
        restoring = null
      }
    })()
    return restoring
  }

  async function login(email: string, password: string) {
    accessToken.value = (
      await api.post<AccessToken>('/auth/login', { email, password })
    ).access_token
    await fetchMe()
  }

  async function register(payload: RegisterPayload) {
    accessToken.value = (await api.post<AccessToken>('/auth/register', payload)).access_token
    await fetchMe()
  }

  async function fetchMe() {
    const before = user.value
    const fresh = await api.get<User>('/me')
    // Баланс поменялся «сам» — штраф планировщика или операция на другом устройстве.
    if (before && before.id === fresh.id) announce(fresh.balance - before.balance, 'sync')
    user.value = fresh
  }

  async function updateMe(payload: Partial<UserPayload>) {
    user.value = await api.patch<User>('/me', payload)
  }

  function forget() {
    accessToken.value = null
    user.value = null
  }

  /** Выйти на этом устройстве: сервер отзывает сессию и удаляет cookie. */
  async function logout() {
    // Напрямую через fetch: при истёкшем access-токене api.post ушёл бы в refresh.
    await fetch(`${API_PREFIX}/auth/logout`, { method: 'POST' }).catch(() => {})
    forget()
  }

  /** Выйти на всех устройствах — в том числе на этом. */
  async function logoutAll() {
    await api.post('/auth/logout-all')
    forget()
  }

  /** Баланс из ответа операции с монетами — без лишнего запроса /me. */
  function setBalance(balance: number, reason: CoinReason = 'sync') {
    if (!user.value) return
    announce(balance - user.value.balance, reason)
    user.value = { ...user.value, balance }
  }

  return {
    accessToken,
    user,
    coinEvent,
    restoreAttempted,
    refresh,
    restore,
    login,
    register,
    fetchMe,
    updateMe,
    logout,
    logoutAll,
    setBalance,
  }
})
