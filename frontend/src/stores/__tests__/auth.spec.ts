import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
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
})
