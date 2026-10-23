import { describe, expect, it } from 'vitest'
import type { Quest } from '@/api/types'
import { questComparator } from '../questFilters'
import { boardSize, dayKey, todayBoard } from '../today'

function quest(id: number, due_at: string | null, tier_id = 1, recurring = false): Quest {
  return {
    id,
    name: `Квест ${id}`,
    description: null,
    tier_id,
    category_id: null,
    recurring_quest_id: recurring ? 1 : null,
    period_date: null,
    reward: 10,
    penalty: 10,
    status: 'active',
    created_at: '2026-10-20T00:00:00Z',
    due_at,
    closed_at: null,
    close_reason: null,
    penalty_applied: false,
  }
}

const levels: Record<number, number> = { 1: 1, 2: 3, 3: 5 }
const tierLevel = (id: number) => levels[id] ?? 0
const byTier = questComparator('tier', tierLevel)

describe('dayKey', () => {
  it('дата в заданном поясе', () => {
    // 21:30 UTC — в Токио уже следующий день.
    expect(dayKey('2026-10-21T21:30:00Z', 'UTC')).toBe('2026-10-21')
    expect(dayKey('2026-10-21T21:30:00Z', 'Asia/Tokyo')).toBe('2026-10-22')
  })
})

describe('todayBoard', () => {
  const now = new Date('2026-10-21T10:00:00Z') // Саратов (UTC+4): 14:00, 21 октября
  const tz = 'Europe/Saratov'

  it('раскладывает по группам', () => {
    const board = todayBoard(
      [
        quest(1, '2026-10-21T09:00:00Z'), // просрочен
        quest(2, '2026-10-21T19:00:00Z', 1), // сегодня 23:00 по Саратову
        quest(3, '2026-10-21T12:00:00Z', 3), // сегодня 16:00, важный
        quest(4, '2026-10-21T20:30:00Z'), // 00:30 22-го по Саратову — уже завтра
        quest(5, null, 1),
        quest(6, null, 3),
        quest(7, '2026-10-21T11:00:00Z', 1), // сегодня 15:00
      ],
      now,
      tz,
      byTier,
    )

    expect(board.overdue.map((q) => q.id)).toEqual([1])
    expect(board.today.once.map((q) => q.id)).toEqual([3, 7, 2])
    expect(board.today.recurring).toEqual([])
    expect(board.noDue.map((q) => q.id)).toEqual([6, 5])
    expect(board.todayCount).toBe(4)
    expect(boardSize(board)).toBe(6)
  })

  it('разовые отдельно от повторяющихся, внутри — выбранная сортировка', () => {
    const quests = [
      quest(1, '2026-10-21T12:00:00Z', 3, true), // повторяющийся, важный
      quest(2, '2026-10-21T19:00:00Z', 1), // разовый, неважный
      quest(3, '2026-10-21T11:00:00Z', 1, true),
      quest(4, '2026-10-21T13:00:00Z', 2),
    ]
    const board = todayBoard(quests, now, tz, byTier)
    expect(board.today.once.map((q) => q.id)).toEqual([4, 2])
    expect(board.today.recurring.map((q) => q.id)).toEqual([1, 3])

    const byDue = todayBoard(quests, now, tz, questComparator('due', tierLevel))
    expect(byDue.today.once.map((q) => q.id)).toEqual([4, 2])
    expect(byDue.today.recurring.map((q) => q.id)).toEqual([3, 1])
  })

  it('в просроченных и без срока разовые тоже первыми', () => {
    const quests = [
      quest(1, '2026-10-21T08:00:00Z', 3, true),
      quest(2, '2026-10-21T09:00:00Z', 1),
      quest(3, null, 3, true),
      quest(4, null, 1),
    ]
    const board = todayBoard(quests, now, tz, byTier)
    expect(board.overdue.map((q) => q.id)).toEqual([2, 1])
    expect(board.noDue.map((q) => q.id)).toEqual([4, 3])
  })

  it('день — по поясу профиля, а не по UTC', () => {
    // 21:30 UTC 21-го: в UTC ещё сегодня, в Токио — уже завтра.
    const late = [quest(1, '2026-10-21T21:30:00Z')]
    expect(todayBoard(late, now, 'UTC', byTier).todayCount).toBe(1)
    expect(todayBoard(late, now, 'Asia/Tokyo', byTier).todayCount).toBe(0)
  })
})
