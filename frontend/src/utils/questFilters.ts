import type { Quest } from '@/api/types'

export type DueFilter = 'all' | 'overdue' | 'today' | 'week' | 'none'
export type QuestSort = 'due' | 'tier' | 'reward'

export interface QuestFilters {
  /** Поиск по названию и описанию, без учёта регистра. */
  q: string
  /** Пусто — любые. */
  tiers: number[]
  categories: number[]
  due: DueFilter
  onlyRecurring: boolean
  sort: QuestSort
}

export const DEFAULT_FILTERS: QuestFilters = {
  q: '',
  tiers: [],
  categories: [],
  due: 'all',
  onlyRecurring: false,
  sort: 'due',
}

/** Сколько условий отбора задано (поиск и сортировка не считаются) — для бейджа на кнопке. */
export function activeFilterCount(f: QuestFilters): number {
  return (
    Number(f.tiers.length > 0) +
    Number(f.categories.length > 0) +
    Number(f.due !== 'all') +
    Number(f.onlyRecurring)
  )
}

function endOfDay(now: Date, plusDays: number): number {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() + plusDays + 1).getTime()
}

function matchesDue(quest: Quest, due: DueFilter, now: Date): boolean {
  if (due === 'all') return true
  if (quest.due_at === null) return due === 'none'
  const at = new Date(quest.due_at).getTime()
  switch (due) {
    case 'overdue':
      return at <= now.getTime()
    case 'today':
      return at < endOfDay(now, 0)
    case 'week':
      return at < endOfDay(now, 6)
    case 'none':
      return false
  }
}

/** Срок по возрастанию, без срока — в конце (как на бэкенде). */
export function byDue(a: Quest, b: Quest): number {
  if (a.due_at === b.due_at) return a.id - b.id
  if (a.due_at === null) return 1
  if (b.due_at === null) return -1
  return a.due_at < b.due_at ? -1 : 1
}

/**
 * Отбор и сортировка активных квестов доски. Время — в часовом поясе браузера,
 * как и подпись срока на карточке.
 *
 * «Сегодня» и «неделя» включают просроченные: они тоже горят.
 */
export function filterQuests(
  quests: Quest[],
  f: QuestFilters,
  ctx: { now: Date; tierLevel: (tierId: number) => number },
): Quest[] {
  const q = f.q.trim().toLocaleLowerCase('ru')
  const result = quests.filter(
    (quest) =>
      (!q ||
        quest.name.toLocaleLowerCase('ru').includes(q) ||
        (quest.description?.toLocaleLowerCase('ru').includes(q) ?? false)) &&
      (!f.tiers.length || f.tiers.includes(quest.tier_id)) &&
      (!f.categories.length ||
        (quest.category_id !== null && f.categories.includes(quest.category_id))) &&
      (!f.onlyRecurring || quest.recurring_quest_id !== null) &&
      matchesDue(quest, f.due, ctx.now),
  )

  const compare: Record<QuestSort, (a: Quest, b: Quest) => number> = {
    due: byDue,
    // Важные сверху, внутри уровня — по сроку.
    tier: (a, b) => ctx.tierLevel(b.tier_id) - ctx.tierLevel(a.tier_id) || byDue(a, b),
    reward: (a, b) => b.reward - a.reward || byDue(a, b),
  }
  return result.sort(compare[f.sort])
}
