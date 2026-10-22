import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import type { Quest } from '@/api/types'
import QuestCard from '../QuestCard.vue'

const now = new Date('2026-10-21T14:00:00Z')

function quest(fields: Partial<Quest>): Quest {
  return {
    id: 1,
    name: 'Пробежка',
    description: null,
    tier_id: 1,
    category_id: null,
    recurring_quest_id: null,
    period_date: null,
    reward: 10,
    penalty: 10,
    status: 'active',
    created_at: '2026-10-21T11:00:00Z',
    // Срок был час назад.
    due_at: '2026-10-21T13:00:00Z',
    closed_at: null,
    close_reason: null,
    penalty_applied: false,
    ...fields,
  }
}

const mountCard = (q: Quest) =>
  mount(QuestCard, { props: { quest: q, tier: undefined, category: undefined, now } })

describe('QuestCard', () => {
  it('сданный до срока квест не помечается просроченным, даже когда срок уже прошёл', () => {
    // Сдан за 30 минут до срока, смотрим через час после срока.
    const card = mountCard(
      quest({ status: 'completed', close_reason: 'completed', closed_at: '2026-10-21T12:30:00Z' }),
    )

    expect(card.find('article').classes()).not.toContain('overdue')
    expect(card.text()).not.toContain('Гильдия взыщет штраф')
    expect(card.text()).toContain('Сдан')
  })

  it('открытый квест с прошедшим сроком — просрочен', () => {
    const card = mountCard(quest({}))

    expect(card.find('article').classes()).toContain('overdue')
    expect(card.text()).toContain('Гильдия взыщет штраф')
  })
})
