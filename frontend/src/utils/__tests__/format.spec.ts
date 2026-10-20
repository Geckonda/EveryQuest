import { describe, expect, it } from 'vitest'
import { coins, dueLabel, signed } from '../format'

describe('coins', () => {
  it.each([
    [1, '1 монета'],
    [2, '2 монеты'],
    [5, '5 монет'],
    [11, '11 монет'],
    [12, '12 монет'],
    [21, '21 монета'],
    [104, '104 монеты'],
    [0, '0 монет'],
    [-3, '-3 монеты'],
  ])('%i → %s', (n, text) => {
    expect(coins(n)).toBe(text)
  })
})

describe('signed', () => {
  it('ставит знак', () => {
    expect(signed(50)).toBe('+50')
    expect(signed(-30)).toBe('−30')
    expect(signed(0)).toBe('0')
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
