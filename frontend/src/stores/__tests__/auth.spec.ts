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

  it('login держит access-токен в памяти, а не в localStorage', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(200, { access_token: 'a', token_type: 'bearer' }))
      .mockResolvedValueOnce(json(200, { id: 1, username: 'Hero', balance: 0 }))
    vi.stubGlobal('fetch', fetchMock)
    const auth = useAuthStore()

    await auth.login('hero@example.com', 'secret-pass')

    expect(auth.accessToken).toBe('a')
    expect(auth.user?.username).toBe('Hero')
    expect(localStorage.length).toBe(0)
    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/auth\/login$/)
  })

  it('restore: по cookie получает токен и профиль', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(200, { access_token: 'fresh', token_type: 'bearer' }))
      .mockResolvedValueOnce(json(200, { id: 1, username: 'Hero', balance: 5 }))
    vi.stubGlobal('fetch', fetchMock)
    const auth = useAuthStore()

    expect(await auth.restore()).toBe(true)

    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/auth\/refresh$/)
    expect(auth.user?.balance).toBe(5)
    expect(auth.restoreAttempted).toBe(true)
  })

  it('restore без cookie — гость, попытка отмечена', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(json(401, { detail: 'Сессия истекла' })),
    )
    const auth = useAuthStore()

    expect(await auth.restore()).toBe(false)
    expect(auth.user).toBeNull()
    expect(auth.restoreAttempted).toBe(true)
  })

  it('logout просит сервер отозвать сессию и забывает токен', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)
    const auth = useAuthStore()
    auth.accessToken = 'a'
    auth.user = { id: 1 } as User

    await auth.logout()

    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/auth\/logout$/)
    expect(auth.accessToken).toBeNull()
    expect(auth.user).toBeNull()
  })

  it('параллельные refresh делают один запрос', async () => {
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
    const auth = useAuthStore()
    auth.accessToken = 'a'

    await auth.fetchMe()
    expect(auth.coinEvent).toBeNull()

    await auth.fetchMe()
    expect(auth.coinEvent).toMatchObject({ delta: -5, reason: 'sync' })

    await auth.fetchMe()
    expect(auth.coinEvent).toMatchObject({ delta: -5 })
  })
})
