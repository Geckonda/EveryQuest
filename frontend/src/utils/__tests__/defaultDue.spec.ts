import { describe, expect, it } from 'vitest'
import { atTime, defaultDue } from '../defaultDue'

const now = new Date(2026, 9, 24, 15, 0) // 24 октября, 15:00 по часам устройства

describe('defaultDue', () => {
  it('время из профиля сегодня, если ещё не прошло', () => {
    expect(new Date(defaultDue('18:30', now))).toEqual(new Date(2026, 9, 24, 18, 30))
  })

  it('прошло — завтра в то же время', () => {
    expect(new Date(defaultDue('09:00:00', now))).toEqual(new Date(2026, 9, 25, 9, 0))
    // Ровно сейчас — тоже уже поздно.
    expect(new Date(defaultDue('15:00', now))).toEqual(new Date(2026, 9, 25, 15, 0))
  })

  it('через границу месяца', () => {
    expect(new Date(atTime('23:59', 8, now))).toEqual(new Date(2026, 10, 1, 23, 59))
  })
})
