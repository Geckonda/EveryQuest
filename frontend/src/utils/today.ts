import type { Quest } from '@/api/types'
import { isRecurring } from './questFilters'

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
  /** Срок сегодня: разовые отдельно от повторяющихся. */
  today: { once: Quest[]; recurring: Quest[] }
  /** Побочные — без срока. */
  noDue: Quest[]
  /** Сколько квестов со сроком сегодня (включая просроченные). */
  todayCount: number
}

/**
 * Раскладка активных квестов для страницы «Сегодня». «Сегодня» — по часовому поясу
 * из профиля, как у повторяющихся квестов: иначе в поездке день «съезжал» бы.
 *
 * Разовые идут первыми: их повесили руками ради конкретного дела, а повторяющиеся —
 * рутина, которая появится снова. Внутри — порядок `compare`.
 */
export function todayBoard(
  quests: Quest[],
  now: Date,
  timeZone: string,
  compare: (a: Quest, b: Quest) => number,
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

  const onceFirst = (a: Quest, b: Quest) =>
    Number(isRecurring(a)) - Number(isRecurring(b)) || compare(a, b)
  dueToday.sort(compare)

  return {
    overdue: overdue.sort(onceFirst),
    today: {
      once: dueToday.filter((q) => !isRecurring(q)),
      recurring: dueToday.filter(isRecurring),
    },
    noDue: noDue.sort(onceFirst),
    todayCount: overdue.length + dueToday.length,
  }
}

/** Сколько квестов видно на странице «Сегодня». */
export function boardSize(board: TodayBoard): number {
  return (
    board.overdue.length +
    board.today.once.length +
    board.today.recurring.length +
    board.noDue.length
  )
}

/**
 * Что ещё на кону сегодня: награды и штрафы квестов со сроком до конца дня, который
 * ещё не вышел. Просроченные не считаются — сдать их уже нельзя, а штраф попадёт
 * в «Штрафы», когда гильдия его взыщет. Побочные без срока — не сегодняшние.
 */
export function todayStakes(board: TodayBoard): { reward: number; penalty: number } {
  const quests = [...board.today.once, ...board.today.recurring]
  return {
    reward: quests.reduce((sum, q) => sum + q.reward, 0),
    penalty: quests.reduce((sum, q) => sum + q.penalty, 0),
  }
}
