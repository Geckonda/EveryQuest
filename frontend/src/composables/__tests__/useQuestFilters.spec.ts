import { describe, expect, it } from 'vitest'
import { DEFAULT_FILTERS } from '@/utils/questFilters'
import { fromQuery, toQuery } from '../useQuestFilters'

describe('фильтры в адресе', () => {
  it('без фильтров адрес пустой', () => {
    expect(toQuery(DEFAULT_FILTERS)).toEqual({})
    expect(fromQuery({})).toEqual(DEFAULT_FILTERS)
  })

  it('туда и обратно', () => {
    const filters = {
      q: 'бег',
      tiers: [1, 3],
      categories: [7],
      due: 'week' as const,
      onlyRecurring: true,
      sort: 'tier' as const,
    }
    const query = toQuery(filters)
    expect(query).toEqual({
      q: 'бег',
      tier: ['1', '3'],
      cat: ['7'],
      due: 'week',
      rec: '1',
      sort: 'tier',
    })
    expect(fromQuery(query as never)).toEqual(filters)
  })

  it('мусор в адресе игнорируется', () => {
    expect(
      fromQuery({ tier: ['x', '-1', '2'], due: 'yesterday', sort: 'random', rec: 'yes' }),
    ).toEqual({ ...DEFAULT_FILTERS, tiers: [2] })
  })

  it('одиночное значение вместо массива', () => {
    expect(fromQuery({ tier: '4' }).tiers).toEqual([4])
  })
})
