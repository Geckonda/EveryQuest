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
  completed_at: null,
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
    const done = quest(1, null, { status: 'completed', completed_at: '2026-10-21T12:00:00Z' })
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
