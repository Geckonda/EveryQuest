import { describe, expect, it } from 'vitest'
import type { Reward } from '@/api/types'
import { DEFAULT_REWARD_FILTERS, filterRewards, type RewardFilters } from '../rewardFilters'

function reward(id: number, name: string, price: number, fields: Partial<Reward> = {}): Reward {
  return {
    id,
    name,
    description: null,
    price,
    duration_minutes: null,
    is_archived: false,
    created_at: '2026-10-21T00:00:00Z',
    ...fields,
  }
}

const menu = [
  reward(1, 'Сериал', 50, { description: 'Одна серия' }),
  reward(2, 'Кофе', 20),
  reward(3, 'Игры', 120),
  reward(4, 'Бар', 200, { is_archived: true }),
]

function ids(filters: Partial<RewardFilters>, balance = 100): number[] {
  return filterRewards(menu, { ...DEFAULT_REWARD_FILTERS, ...filters }, balance).map((r) => r.id)
}

describe('filterRewards', () => {
  it('по умолчанию — порядок меню', () => {
    expect(ids({})).toEqual([1, 2, 3, 4])
  })

  it('поиск по названию и описанию', () => {
    expect(ids({ q: 'СЕРИ' })).toEqual([1])
    expect(ids({ q: 'одна' })).toEqual([1])
  })

  it('сортировки', () => {
    expect(ids({ sort: 'cheap' })).toEqual([2, 1, 3, 4])
    expect(ids({ sort: 'expensive' })).toEqual([4, 3, 1, 2])
    expect(ids({ sort: 'name' })).toEqual([4, 3, 2, 1])
  })

  it('по карману: дороже баланса скрыто, архивные остаются', () => {
    expect(ids({ onlyAffordable: true }, 50)).toEqual([1, 2, 4])
    expect(ids({ onlyAffordable: true }, -10)).toEqual([4])
  })
})
