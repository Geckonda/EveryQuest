import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { User } from '@/api/types'
import { useAuthStore } from '../auth'

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })
  afterEach(() => vi.unstubAllGlobals())

  it('login сохраняет токены и загружает профиль', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(json(200, { access_token: 'a', refresh_token: 'r' }))
        .mockResolvedValueOnce(json(200, { id: 1, username: 'Hero', balance: 0 })),
    )
    const auth = useAuthStore()

    await auth.login('hero@example.com', 'secret-pass')

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.user?.username).toBe('Hero')
    expect(localStorage.getItem('eq.refreshToken')).toBe('r')
  })

  it('logout очищает токены', () => {
    localStorage.setItem('eq.refreshToken', 'r')
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(true)

    auth.logout()

    expect(auth.isAuthenticated).toBe(false)
    expect(localStorage.getItem('eq.refreshToken')).toBeNull()
  })

  it('параллельные refresh делают один запрос', async () => {
    localStorage.setItem('eq.refreshToken', 'r')
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(json(200, { access_token: 'fresh' }))
    vi.stubGlobal('fetch', fetchMock)
    const auth = useAuthStore()

    const results = await Promise.all([auth.refresh(), auth.refresh(), auth.refresh()])

    expect(results).toEqual([true, true, true])
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(auth.accessToken).toBe('fresh')
  })

  it('изменение баланса объявляется с суммой и причиной', () => {
    const auth = useAuthStore()
    auth.user = { id: 1, balance: 100 } as User

    auth.setBalance(70, 'purchase')
    expect(auth.coinEvent).toMatchObject({ delta: -30, reason: 'purchase' })
    const first = auth.coinEvent?.id

    auth.setBalance(40, 'purchase')
    expect(auth.coinEvent?.id).not.toBe(first) // одинаковые покупки подряд — разные события

    auth.setBalance(40, 'reward')
    expect(auth.coinEvent).toMatchObject({ delta: -30 }) // без изменения — без события
  })

  it('fetchMe объявляет изменение баланса, но не первую загрузку и не чужой профиль', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(200, { id: 1, balance: 50 }))
      .mockResolvedValueOnce(json(200, { id: 1, balance: 45 }))
      .mockResolvedValueOnce(json(200, { id: 2, balance: 999 }))
    vi.stubGlobal('fetch', fetchMock)
    localStorage.setItem('eq.accessToken', 'a')
    const auth = useAuthStore()

    await auth.fetchMe()
    expect(auth.coinEvent).toBeNull()

    await auth.fetchMe()
    expect(auth.coinEvent).toMatchObject({ delta: -5, reason: 'sync' })

    await auth.fetchMe()
    expect(auth.coinEvent).toMatchObject({ delta: -5 })
  })
})
