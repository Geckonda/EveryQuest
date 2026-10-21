import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { Quest, User } from '@/api/types'
import { useAuthStore } from '../auth'
import { useQuestsStore } from '../quests'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const quest = (id: number, due_at: string | null, extra: Partial<Quest> = {}): Quest => ({
  id,
  name: `Q${id}`,
  description: null,
  tier_id: 1,
  category_id: null,
  recurring_quest_id: null,
  period_date: null,
  reward: 10,
  penalty: 5,
  status: 'active',
  created_at: '2026-10-21T00:00:00Z',
  due_at,
  closed_at: null,
  close_reason: null,
  penalty_applied: false,
  ...extra,
})

describe('quests store', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.unstubAllGlobals())

  it('новый квест встаёт в список по сроку, без срока — в конец', async () => {
    const created = quest(3, '2026-10-22T10:00:00Z')
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(json(created)))
    const quests = useQuestsStore()
    quests.active = [quest(1, '2026-10-21T10:00:00Z'), quest(2, null)]

    await quests.create({
      name: 'Q3',
      description: null,
      tier_id: 1,
      category_id: null,
      reward: 10,
      penalty: 5,
      due_at: created.due_at,
    })

    expect(quests.active.map((q) => q.id)).toEqual([1, 3, 2])
  })

  it('выполнение переносит квест в историю и обновляет баланс', async () => {
    const done = quest(1, null, {
      status: 'completed',
      closed_at: '2026-10-21T12:00:00Z',
      close_reason: 'completed',
    })
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(json({ quest: done, balance: 110 })),
    )
    const auth = useAuthStore()
    auth.user = { id: 1, balance: 100 } as User
    const quests = useQuestsStore()
    quests.active = [quest(1, null), quest(2, null)]

    await quests.complete(1)

    expect(quests.active.map((q) => q.id)).toEqual([2])
    expect(quests.history[0]?.status).toBe('completed')
    expect(auth.user?.balance).toBe(110)
  })

  it('провал списывает штраф и переносит квест в историю', async () => {
    const failed = quest(1, null, {
      status: 'failed',
      closed_at: '2026-10-21T12:00:00Z',
      close_reason: 'abandoned',
      penalty_applied: true,
    })
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(json({ quest: failed, balance: -5 }))
    vi.stubGlobal('fetch', fetchMock)
    const auth = useAuthStore()
    auth.user = { id: 1, balance: 0 } as User
    const quests = useQuestsStore()
    quests.active = [quest(1, null)]

    await quests.fail(1)

    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/quests\/1\/fail$/)
    expect(quests.active).toEqual([])
    expect(quests.history[0]?.close_reason).toBe('abandoned')
    expect(auth.user?.balance).toBe(-5)
  })

  it('архив грузится страницами без повторов', async () => {
    const closed = (id: number) =>
      quest(id, null, { status: 'completed', close_reason: 'completed' })
    const firstPage = Array.from({ length: 50 }, (_, i) => closed(100 - i))
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(firstPage))
      // Пока листали, закрыли ещё квест — offset сдвинулся, квест 51 пришёл повторно.
      .mockResolvedValueOnce(json([closed(51), closed(50)]))
    vi.stubGlobal('fetch', fetchMock)
    const quests = useQuestsStore()

    await quests.loadHistory()
    expect(quests.historyHasMore).toBe(true)
    const url = String(fetchMock.mock.calls[0]?.[0])
    expect(url).toContain('status=completed&status=failed&status=archived')
    expect(url).toContain('offset=0')

    await quests.loadHistory(true)
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('offset=50')
    expect(quests.history).toHaveLength(51)
    expect(quests.history[50]?.id).toBe(50)
    expect(quests.historyHasMore).toBe(false)
  })

  it('при смене пользователя списки очищаются', async () => {
    const auth = useAuthStore()
    auth.user = { id: 1 } as User
    const quests = useQuestsStore()
    quests.active = [quest(1, null)]

    auth.user = { id: 2 } as User
    await Promise.resolve()

    expect(quests.active).toEqual([])
  })
})
