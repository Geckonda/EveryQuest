import { afterEach, describe, expect, it, vi, type Mock } from 'vitest'
import { ApiError, api, setAuthHandler, type AuthHandler } from '../client'

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

function mockFetch(...responses: Response[]): Mock<typeof fetch> {
  const fetchMock = vi.fn<typeof fetch>()
  for (const response of responses) fetchMock.mockResolvedValueOnce(response)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function authHeader(fetchMock: Mock<typeof fetch>, call: number): string | undefined {
  const headers = fetchMock.mock.calls[call]?.[1]?.headers as Record<string, string> | undefined
  return headers?.Authorization
}

function makeHandler(overrides: Partial<AuthHandler> = {}) {
  let token = 'old'
  return {
    getAccessToken: () => token,
    refresh: vi.fn<AuthHandler['refresh']>(async () => {
      token = 'new'
      return true
    }),
    onUnauthorized: vi.fn<AuthHandler['onUnauthorized']>(),
    ...overrides,
  }
}

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setAuthHandler(null)
  })

  it('подставляет Bearer-токен', async () => {
    const fetchMock = mockFetch(json(200, { ok: true }))
    setAuthHandler(makeHandler())

    await api.get('/me')

    expect(authHeader(fetchMock, 0)).toBe('Bearer old')
  })

  it('при 401 обновляет токен и повторяет запрос', async () => {
    const fetchMock = mockFetch(json(401, { detail: 'expired' }), json(200, { id: 1 }))
    const handler = makeHandler()
    setAuthHandler(handler)

    await expect(api.get('/me')).resolves.toEqual({ id: 1 })
    expect(handler.refresh).toHaveBeenCalledOnce()
    expect(authHeader(fetchMock, 1)).toBe('Bearer new')
    expect(handler.onUnauthorized).not.toHaveBeenCalled()
  })

  it('если refresh не удался — разлогинивает и бросает ApiError', async () => {
    mockFetch(json(401, { detail: 'Требуется вход' }))
    const handler = makeHandler({ refresh: vi.fn<AuthHandler['refresh']>(async () => false) })
    setAuthHandler(handler)

    await expect(api.get('/me')).rejects.toMatchObject({ status: 401, message: 'Требуется вход' })
    expect(handler.onUnauthorized).toHaveBeenCalledOnce()
  })

  it('без токена 401 не вызывает refresh (например, неверный пароль)', async () => {
    mockFetch(json(401, { detail: 'Неверный пароль' }))
    const handler = makeHandler({ getAccessToken: () => null })
    setAuthHandler(handler)

    await expect(api.post('/auth/login', {})).rejects.toBeInstanceOf(ApiError)
    expect(handler.refresh).not.toHaveBeenCalled()
  })

  it('берёт текст ошибки валидации 422', async () => {
    mockFetch(json(422, { detail: [{ msg: 'Неизвестный часовой пояс' }] }))
    await expect(api.post('/auth/register', {})).rejects.toThrow('Неизвестный часовой пояс')
  })
})
