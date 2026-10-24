import { describe, expect, it } from 'vitest'
import type { ForecastQuest, Quest } from '@/api/types'
import { addDays, addMonths, groupByDay, monthGrid } from '../calendar'

describe('даты', () => {
  it('сдвиг дней и месяцев через границы', () => {
    expect(addDays('2026-10-31', 1)).toBe('2026-11-01')
    expect(addDays('2026-03-01', -1)).toBe('2026-02-28')
    expect(addMonths('2026-12', 1)).toBe('2027-01')
    expect(addMonths('2026-01', -1)).toBe('2025-12')
  })

  it('переход на летнее время не сдвигает дни', () => {
    // В Европе часы переводят в последнее воскресенье октября.
    expect(addDays('2026-10-24', 2)).toBe('2026-10-26')
  })
})

describe('monthGrid', () => {
  it('6 недель с понедельника, соседние дни помечены', () => {
    const grid = monthGrid('2026-10') // 1 октября 2026 — четверг
    expect(grid).toHaveLength(42)
    expect(grid[0]).toEqual({ key: '2026-09-28', day: 28, outside: true })
    expect(grid[3]).toEqual({ key: '2026-10-01', day: 1, outside: false })
    expect(grid[41]?.key).toBe('2026-11-08')
  })

  it('месяц с понедельника начинается без хвоста', () => {
    expect(monthGrid('2026-06')[0]?.key).toBe('2026-06-01')
  })
})

describe('groupByDay', () => {
  const quest = (id: number, due_at: string | null) => ({ id, due_at }) as Quest
  const forecast = (id: number, due_at: string) =>
    ({ recurring_quest_id: id, due_at }) as ForecastQuest

  it('раскладывает по местной дате срока, без срока — пропускает', () => {
    const days = groupByDay(
      [quest(1, '2026-10-21T19:59:00Z'), quest(2, '2026-10-21T20:30:00Z'), quest(3, null)],
      [forecast(7, '2026-10-22T05:00:00Z')],
      'Europe/Saratov', // UTC+4
    )
    expect(days.get('2026-10-21')?.quests.map((q) => q.id)).toEqual([1])
    expect(days.get('2026-10-22')?.quests.map((q) => q.id)).toEqual([2])
    expect(days.get('2026-10-22')?.forecast.map((f) => f.recurring_quest_id)).toEqual([7])
    expect(days.size).toBe(2)
  })

  it('внутри дня разовые первыми, порядок внутри групп сохраняется', () => {
    const at = (id: number, recurring: boolean) =>
      ({ id, due_at: '2026-10-21T10:00:00Z', recurring_quest_id: recurring ? 9 : null }) as Quest
    const days = groupByDay([at(1, true), at(2, false), at(3, true), at(4, false)], [], 'UTC')
    expect(days.get('2026-10-21')?.quests.map((q) => q.id)).toEqual([2, 4, 1, 3])
  })
})
