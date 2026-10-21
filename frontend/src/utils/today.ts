import type { Quest } from '@/api/types'
import { byDue } from './questFilters'

const keyFormats = new Map<string, Intl.DateTimeFormat>()

/** Дата «YYYY-MM-DD» в заданном часовом поясе — чтобы сравнивать дни, а не моменты. */
export function dayKey(date: Date | string, timeZone: string): string {
  let format = keyFormats.get(timeZone)
  if (!format) {
    // en-CA форматирует дату как ISO: 2026-10-21.
    format = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
    keyFormats.set(timeZone, format)
  }
  return format.format(typeof date === 'string' ? new Date(date) : date)
}

export interface TodayBoard {
  /** Срок вышел, а штраф ещё не списан. */
  overdue: Quest[]
  /** Срок сегодня: важные сверху, внутри тира — по сроку. */
  today: Quest[]
  /** Побочные — без срока. */
  noDue: Quest[]
  /** Сколько квестов со сроком сегодня (включая просроченные). */
  todayCount: number
}

/**
 * Раскладка активных квестов для страницы «Сегодня». «Сегодня» — по часовому поясу
 * из профиля, как у повторяющихся квестов: иначе в поездке день «съезжал» бы.
 */
export function todayBoard(
  quests: Quest[],
  now: Date,
  timeZone: string,
  tierLevel: (tierId: number) => number,
): TodayBoard {
  const todayKey = dayKey(now, timeZone)
  const overdue: Quest[] = []
  const dueToday: Quest[] = []
  const noDue: Quest[] = []

  for (const quest of quests) {
    if (quest.due_at === null) noDue.push(quest)
    else if (new Date(quest.due_at) <= now) overdue.push(quest)
    else if (dayKey(quest.due_at, timeZone) === todayKey) dueToday.push(quest)
  }

  const byImportance = (a: Quest, b: Quest) =>
    tierLevel(b.tier_id) - tierLevel(a.tier_id) || byDue(a, b)

  return {
    overdue: overdue.sort(byDue),
    today: dueToday.sort(byImportance),
    noDue: noDue.sort(byImportance),
    todayCount: overdue.length + dueToday.length,
  }
}
