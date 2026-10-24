import { describe, expect, it } from 'vitest'
import {
  amount,
  canUndo,
  coins,
  countdown,
  dueLabel,
  plural,
  romanLevel,
  signed,
  tierLabel,
} from '../format'

describe('romanLevel', () => {
  it.each([
    [1, 'I'],
    [4, 'IV'],
    [5, 'V'],
    [7, '7'],
  ])('%i → %s', (level, text) => {
    expect(romanLevel(level)).toBe(text)
  })
})

describe('tierLabel', () => {
  it('не дублирует цифру на печати', () => {
    expect(tierLabel({ name: 'III', level: 3 })).toBeNull()
  })

  it('показывает своё название', () => {
    expect(tierLabel({ name: 'Эпический', level: 5 })).toBe('Эпический')
    expect(tierLabel({ name: 'II', level: 3 })).toBe('II')
  })
})

describe('coins', () => {
  it.each([
    [1, '1 золотой'],
    [2, '2 золотых'],
    [5, '5 золотых'],
    [11, '11 золотых'],
    [21, '21 золотой'],
    [0, '0 золотых'],
  ])('%i → %s', (n, text) => {
    expect(coins(n)).toBe(text)
  })
})

describe('plural', () => {
  it.each([
    [1, 'день'],
    [2, 'дня'],
    [4, 'дня'],
    [5, 'дней'],
    [11, 'дней'],
    [12, 'дней'],
    [14, 'дней'],
    [21, 'день'],
    [22, 'дня'],
    [104, 'дня'],
    [111, 'дней'],
    [0, 'дней'],
    [-3, 'дня'],
  ])('%i → %s', (n, word) => {
    expect(plural(n, 'день', 'дня', 'дней')).toBe(word)
  })
})

describe('signed', () => {
  it('ставит знак', () => {
    expect(signed(50)).toBe('+50')
    expect(signed(-30)).toBe('−30')
    expect(signed(0)).toBe('0')
  })
})

describe('amount', () => {
  it('без плюса, минус — настоящий', () => {
    expect(amount(75)).toBe('75')
    expect(amount(-75)).toBe('−75')
    expect(amount(0)).toBe('0')
  })
})

describe('countdown', () => {
  const now = new Date('2026-10-21T12:00:00Z')
  const plus = (ms: number) => new Date(now.getTime() + ms).toISOString()
  const MIN = 60_000
  const HOUR = 60 * MIN
  const created = plus(-10 * 24 * HOUR) // создан 10 дней назад — доля почти не влияет

  it.each([
    [2 * 24 * HOUR + 5 * HOUR + 30 * MIN, '2 д 5 ч'],
    [3 * HOUR + 14 * MIN + 59_000, '3 ч 14 мин'],
    [13 * MIN + 5_000, '13:05'],
    [59 * MIN + 59_999, '59:59'],
    [4_000, '0:04'],
  ])('%i мс → %s', (left, text) => {
    expect(countdown(created, plus(left), now).left).toBe(text)
  })

  it('срочность по абсолютному времени', () => {
    expect(countdown(created, plus(29 * MIN), now).urgency).toBe('critical')
    expect(countdown(created, plus(2 * HOUR), now).urgency).toBe('soon')
    expect(countdown(plus(-HOUR), plus(5 * HOUR), now).urgency).toBe('calm')
  })

  it('срочность по доле оставшегося времени', () => {
    // Недельный квест, осталось 10% (≈17 ч) — уже горит.
    const week = 7 * 24 * HOUR
    const result = countdown(plus(-0.9 * week), plus(0.1 * week), now)
    expect(result.urgency).toBe('soon')
    expect(result.remaining).toBeCloseTo(0.1)
  })

  it('просрочен', () => {
    expect(countdown(created, plus(-1), now)).toEqual({
      left: '0:00',
      urgency: 'overdue',
      remaining: 0,
    })
  })

  it('создан «в будущем» по часам браузера — доля не больше 1', () => {
    expect(countdown(plus(HOUR), plus(5 * HOUR), now).remaining).toBe(1)
  })
})

describe('dueLabel', () => {
  const now = new Date(2026, 9, 21, 12, 0) // 21 октября, 12:00 по местному времени

  it('просроченный', () => {
    expect(dueLabel(new Date(2026, 9, 21, 11, 59).toISOString(), now)).toEqual({
      text: 'Срок истёк',
      overdue: true,
      soon: false,
    })
  })

  it('сегодня и скоро', () => {
    const label = dueLabel(new Date(2026, 9, 21, 14, 30).toISOString(), now)
    expect(label.text).toBe('сегодня до 14:30')
    expect(label.soon).toBe(true)
  })

  it('завтра', () => {
    const label = dueLabel(new Date(2026, 9, 22, 23, 59).toISOString(), now)
    expect(label.text).toBe('завтра до 23:59')
    expect(label.soon).toBe(false)
  })

  it('позже — с датой', () => {
    expect(dueLabel(new Date(2026, 9, 25, 9, 0).toISOString(), now).text).toMatch(/^до 25 окт/)
  })
})

describe('canUndo', () => {
  const now = new Date('2026-10-21T12:00:00Z')
  const ago = (min: number) => new Date(now.getTime() - min * 60_000).toISOString()
  const quest = (fields: Partial<Parameters<typeof canUndo>[0]>) => ({
    close_reason: 'completed',
    closed_at: ago(1),
    due_at: null,
    ...fields,
  })

  it('сдан или провален вручную только что — можно', () => {
    expect(canUndo(quest({}), now)).toBe(true)
    expect(canUndo(quest({ close_reason: 'abandoned', closed_at: ago(9.9) }), now)).toBe(true)
  })

  it('нельзя: окно прошло, срок прошёл, провал по сроку, снят', () => {
    expect(canUndo(quest({ closed_at: ago(10.1) }), now)).toBe(false)
    expect(canUndo(quest({ due_at: ago(0.5) }), now)).toBe(false)
    expect(canUndo(quest({ close_reason: 'expired' }), now)).toBe(false)
    expect(canUndo(quest({ close_reason: 'archived' }), now)).toBe(false)
    expect(canUndo(quest({ close_reason: null, closed_at: null }), now)).toBe(false)
  })
})
