import { describe, expect, it } from 'vitest'
import type { Quest } from '@/api/types'
import {
  DEFAULT_FILTERS,
  activeFilterCount,
  filterQuests,
  type QuestFilters,
} from '../questFilters'

const now = new Date(2026, 9, 21, 12, 0) // среда, 21 октября, 12:00 по местному времени

function quest(id: number, fields: Partial<Quest> = {}): Quest {
  return {
    id,
    name: `Квест ${id}`,
    description: null,
    tier_id: 1,
    category_id: null,
    recurring_quest_id: null,
    period_date: null,
    reward: 10,
    penalty: 10,
    status: 'active',
    created_at: '2026-10-20T00:00:00Z',
    due_at: null,
    closed_at: null,
    close_reason: null,
    penalty_applied: false,
    ...fields,
  }
}

const at = (day: number, hour: number) => new Date(2026, 9, day, hour, 0).toISOString()
const levels: Record<number, number> = { 1: 1, 2: 3, 3: 5 }
const ctx = { now, tierLevel: (id: number) => levels[id] ?? 0 }

function ids(quests: Quest[], filters: Partial<QuestFilters>): number[] {
  return filterQuests(quests, { ...DEFAULT_FILTERS, ...filters }, ctx).map((q) => q.id)
}

describe('filterQuests', () => {
  const overdue = quest(1, { due_at: at(21, 11) })
  const today = quest(2, { due_at: at(21, 23) })
  const sunday = quest(3, { due_at: at(27, 23) }) // через 6 дней — ещё «неделя»
  const nextWeek = quest(4, { due_at: at(28, 0) })
  const noDue = quest(5)
  const all = [noDue, nextWeek, sunday, today, overdue]

  it('по умолчанию — все, по сроку, без срока в конце', () => {
    expect(ids(all, {})).toEqual([1, 2, 3, 4, 5])
  })

  it.each([
    ['overdue', [1]],
    ['today', [1, 2]],
    ['week', [1, 2, 3]],
    ['none', [5]],
  ] as const)('срок %s', (due, expected) => {
    expect(ids(all, { due })).toEqual(expected)
  })

  it('поиск по названию и описанию без учёта регистра', () => {
    const quests = [
      quest(1, { name: 'Пробежка 5 км' }),
      quest(2, { name: 'Уборка', description: 'Пропылесосить и ПРОБЕЖАТЬСЯ тряпкой' }),
      quest(3, { name: 'Чтение' }),
    ]
    expect(ids(quests, { q: '  пробеж ' })).toEqual([1, 2])
  })

  it('тиры, категории, разовые и повторяющиеся', () => {
    const quests = [
      quest(1, { tier_id: 1, category_id: 10 }),
      quest(2, { tier_id: 2, category_id: 20, recurring_quest_id: 7 }),
      quest(3, { tier_id: 3 }),
    ]
    expect(ids(quests, { tiers: [2, 3] })).toEqual([2, 3])
    expect(ids(quests, { categories: [10] })).toEqual([1])
    expect(ids(quests, { kind: 'recurring' })).toEqual([2])
    expect(ids(quests, { kind: 'once' })).toEqual([1, 3])
  })

  it('сортировка по важности тира, внутри — по сроку', () => {
    const quests = [
      quest(1, { tier_id: 1, due_at: at(21, 13) }),
      quest(2, { tier_id: 3 }),
      quest(3, { tier_id: 3, due_at: at(22, 9) }),
      quest(4, { tier_id: 2, due_at: at(21, 14) }),
    ]
    expect(ids(quests, { sort: 'tier' })).toEqual([3, 2, 4, 1])
  })

  it('сортировка по награде', () => {
    const quests = [quest(1, { reward: 5 }), quest(2, { reward: 50 }), quest(3, { reward: 20 })]
    expect(ids(quests, { sort: 'reward' })).toEqual([2, 3, 1])
  })

  it('не меняет исходный массив', () => {
    const quests = [quest(2, { reward: 1 }), quest(1, { reward: 2 })]
    filterQuests(quests, { ...DEFAULT_FILTERS, sort: 'reward' }, ctx)
    expect(quests.map((q) => q.id)).toEqual([2, 1])
  })
})

describe('activeFilterCount', () => {
  it('считает условия отбора, но не поиск и сортировку', () => {
    expect(activeFilterCount(DEFAULT_FILTERS)).toBe(0)
    expect(activeFilterCount({ ...DEFAULT_FILTERS, q: 'x', sort: 'tier' })).toBe(0)
    expect(
      activeFilterCount({
        ...DEFAULT_FILTERS,
        tiers: [1],
        categories: [2],
        due: 'none',
        kind: 'once',
      }),
    ).toBe(4)
  })
})
