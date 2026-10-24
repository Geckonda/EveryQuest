import type { ForecastQuest, Quest } from '@/api/types'
import { isRecurring } from './questFilters'
import { dayKey } from './today'

/**
 * Даты календаря — строки «YYYY-MM-DD» (местные даты пользователя). Арифметика — в UTC,
 * чтобы переход на летнее время в браузере не сдвигал дни.
 */

function fromKey(key: string): Date {
  const [y, m, d] = key.split('-').map(Number) as [number, number, number]
  return new Date(Date.UTC(y, m - 1, d))
}

function toKey(date: Date): string {
  return date.toISOString().slice(0, 10)
}

export function addDays(key: string, days: number): string {
  const date = fromKey(key)
  date.setUTCDate(date.getUTCDate() + days)
  return toKey(date)
}

export function addMonths(month: string, months: number): string {
  const date = fromKey(`${month}-01`)
  date.setUTCMonth(date.getUTCMonth() + months)
  return toKey(date).slice(0, 7)
}

export interface CalendarDay {
  key: string
  day: number
  /** День соседнего месяца — бледный. */
  outside: boolean
}

/** Сетка месяца «YYYY-MM»: 6 недель с понедельника — высота календаря не прыгает. */
export function monthGrid(month: string): CalendarDay[] {
  const first = fromKey(`${month}-01`)
  const weekday = (first.getUTCDay() + 6) % 7 // пн = 0
  const start = addDays(`${month}-01`, -weekday)
  return Array.from({ length: 42 }, (_, i) => {
    const key = addDays(start, i)
    return { key, day: Number(key.slice(8)), outside: key.slice(0, 7) !== month }
  })
}

export interface DayItems {
  quests: Quest[]
  forecast: ForecastQuest[]
}

/**
 * Квесты и прогноз по дням срока в поясе пользователя.
 * Внутри дня разовые идут первыми, повторяющиеся — за ними: в ячейке помещается
 * всего несколько отметок, и рутина не должна вытеснять за «+N» особые дела.
 */
export function groupByDay(
  quests: Quest[],
  forecast: ForecastQuest[],
  timeZone: string,
): Map<string, DayItems> {
  const days = new Map<string, DayItems>()
  const slot = (iso: string) => {
    const key = dayKey(iso, timeZone)
    let items = days.get(key)
    if (!items) days.set(key, (items = { quests: [], forecast: [] }))
    return items
  }
  for (const quest of quests) if (quest.due_at) slot(quest.due_at).quests.push(quest)
  for (const item of forecast) slot(item.due_at).forecast.push(item)
  // sort устойчивый: внутри группы остаётся порядок с сервера.
  for (const items of days.values()) {
    items.quests.sort((a, b) => Number(isRecurring(a)) - Number(isRecurring(b)))
  }
  return days
}
