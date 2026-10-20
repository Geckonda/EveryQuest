import { describe, expect, it } from 'vitest'
import { describeSchedule } from '../schedule'

type Schedule = Parameters<typeof describeSchedule>[0]

const base: Omit<Schedule, 'frequency'> = {
  interval: 1,
  days_of_week: null,
  day_of_month: null,
  due_time: '23:59:00',
}

const cases: [Partial<Schedule> & Pick<Schedule, 'frequency'>, string][] = [
  [{ frequency: 'daily' }, 'Каждый день до 23:59'],
  [{ frequency: 'daily', interval: 2 }, 'Раз в 2 дня до 23:59'],
  [{ frequency: 'daily', interval: 5, due_time: '09:00:00' }, 'Раз в 5 дней до 09:00'],
  [{ frequency: 'weekly' }, 'Раз в неделю, до вс 23:59'],
  [{ frequency: 'weekly', interval: 2 }, 'Раз в 2 недели, до вс 23:59'],
  [{ frequency: 'weekly', days_of_week: [5, 1, 3] }, 'Пн, Ср, Пт до 23:59'],
  [{ frequency: 'weekly', days_of_week: [1, 2, 3, 4, 5] }, 'По будням до 23:59'],
  [{ frequency: 'weekly', days_of_week: [6, 7] }, 'По выходным до 23:59'],
  [{ frequency: 'weekly', days_of_week: [1], interval: 2 }, 'Раз в 2 недели, Пн до 23:59'],
  [{ frequency: 'monthly' }, 'Каждый месяц, до последнего дня 23:59'],
  [{ frequency: 'monthly', day_of_month: 15 }, 'Каждый месяц, 15-го до 23:59'],
  [{ frequency: 'monthly', day_of_month: 31 }, 'Каждый месяц, в последний день до 23:59'],
  [{ frequency: 'monthly', interval: 3, day_of_month: 1 }, 'Раз в 3 месяца, 1-го до 23:59'],
]

describe('describeSchedule', () => {
  it.each(cases)('%o → %s', (schedule, text) => {
    expect(describeSchedule({ ...base, ...schedule })).toBe(text)
  })
})
