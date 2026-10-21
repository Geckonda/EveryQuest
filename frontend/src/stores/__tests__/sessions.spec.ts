import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { RewardSession, User } from '@/api/types'
import { useAuthStore } from '../auth'
import { useCatalogStore } from '../catalog'
import { useSessionsStore } from '../sessions'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const session = (id: number, ends_at: string): RewardSession => ({
  id,
  reward_id: 1,
  name: `Трата ${id}`,
  started_at: '2026-10-21T12:00:00Z',
  ends_at,
  finished_at: null,
})

describe('sessions store', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.unstubAllGlobals())

  it('покупка траты с длительностью добавляет сеанс по времени окончания', async () => {
    const later = session(1, '2026-10-21T13:00:00Z')
    const sooner = session(2, '2026-10-21T12:20:00Z')
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(json({ transaction: {}, balance: 80, session: sooner })),
    )
    useAuthStore().user = { id: 1, balance: 100 } as User
    const sessions = useSessionsStore()
    sessions.add(later)

    await useCatalogStore().purchase(5)

    expect(sessions.active.map((s) => s.id)).toEqual([2, 1])
  })

  it('покупка без длительности сеанс не добавляет', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(json({ transaction: {}, balance: 80, session: null })),
    )
    useAuthStore().user = { id: 1, balance: 100 } as User

    await useCatalogStore().purchase(5)

    expect(useSessionsStore().active).toEqual([])
  })

  it('закончить раньше — запрос и перечитывание сдвинутой очереди', async () => {
    const shifted = { ...session(2, '2026-10-21T12:40:00Z'), started_at: '2026-10-21T12:10:00Z' }
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(session(1, '2026-10-21T12:15:00Z')))
      .mockResolvedValueOnce(json([shifted]))
    vi.stubGlobal('fetch', fetchMock)
    const sessions = useSessionsStore()
    sessions.add(session(1, '2026-10-21T12:15:00Z'))

    await sessions.finish(1)

    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/reward-sessions\/1\/finish$/)
    expect(String(fetchMock.mock.calls[1]?.[0])).toMatch(/\/reward-sessions\/active$/)
    expect(sessions.active).toEqual([shifted])
  })

  it('покупка передаёт выбор: в очередь или параллельно', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      // Новый Response на каждый вызов: тело ответа читается только один раз.
      .mockImplementation(async () => json({ transaction: {}, balance: 80, session: null }))
    vi.stubGlobal('fetch', fetchMock)
    useAuthStore().user = { id: 1, balance: 100 } as User

    await useCatalogStore().purchase(5)
    await useCatalogStore().purchase(5, false)

    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/rewards\/5\/purchase\?queue=true$/)
    expect(String(fetchMock.mock.calls[1]?.[0])).toMatch(/queue=false$/)
  })

  it('конец очереди — самое позднее окончание, пустая или истёкшая — null', () => {
    const sessions = useSessionsStore()
    const now = new Date('2026-10-21T12:05:00Z')
    expect(sessions.queueEnd(now)).toBeNull()

    sessions.add(session(1, '2026-10-21T12:45:00Z'))
    sessions.add({ ...session(2, '2026-10-21T12:20:00.500Z'), started_at: '2026-10-21T12:05:00Z' })
    expect(sessions.queueEnd(now)).toBe('2026-10-21T12:45:00Z')
    // Сортировка по началу: первая начавшаяся — первая.
    expect(sessions.active.map((s) => s.id)).toEqual([1, 2])

    expect(sessions.queueEnd(new Date('2026-10-21T13:00:00Z'))).toBeNull()
  })
})
