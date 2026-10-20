import type { RecurringQuest } from '@/api/types'
import { plural } from './format'

export const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'] as const

type Schedule = Pick<
  RecurringQuest,
  'frequency' | 'interval' | 'days_of_week' | 'day_of_month' | 'due_time'
>

function sameDays(days: number[], expected: number[]): boolean {
  return days.length === expected.length && expected.every((d) => days.includes(d))
}

function weekdays(days: number[]): string {
  if (sameDays(days, [1, 2, 3, 4, 5])) return 'по будням'
  if (sameDays(days, [6, 7])) return 'по выходным'
  if (days.length === 7) return 'каждый день'
  return [...days]
    .sort((a, b) => a - b)
    .map((d) => WEEKDAYS[d - 1])
    .join(', ')
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Расписание человеческим языком: «По будням до 09:00», «Каждый месяц, 15-го до 23:59». */
export function describeSchedule(s: Schedule): string {
  const time = s.due_time.slice(0, 5)
  const n = s.interval

  if (s.frequency === 'daily') {
    return n === 1
      ? `Каждый день до ${time}`
      : `Раз в ${n} ${plural(n, 'день', 'дня', 'дней')} до ${time}`
  }

  if (s.frequency === 'weekly') {
    const every = n === 1 ? '' : `раз в ${n} ${plural(n, 'неделю', 'недели', 'недель')}, `
    if (s.days_of_week?.length) return capitalize(`${every}${weekdays(s.days_of_week)} до ${time}`)
    return capitalize(`${every || 'раз в неделю, '}до вс ${time}`)
  }

  const every = n === 1 ? 'каждый месяц' : `раз в ${n} ${plural(n, 'месяц', 'месяца', 'месяцев')}`
  if (s.day_of_month === 31) return capitalize(`${every}, в последний день до ${time}`)
  if (s.day_of_month) return capitalize(`${every}, ${s.day_of_month}-го до ${time}`)
  return capitalize(`${every}, до последнего дня ${time}`)
}
