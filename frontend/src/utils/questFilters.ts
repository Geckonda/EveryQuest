import type { Quest } from '@/api/types'

export type DueFilter = 'all' | 'overdue' | 'today' | 'week' | 'none'
export type QuestSort = 'due' | 'tier' | 'reward'
/** Разовые — повешены вручную, повторяющиеся — созданы по расписанию. */
export type QuestKind = 'all' | 'once' | 'recurring'

export interface QuestFilters {
  /** Поиск по названию и описанию, без учёта регистра. */
  q: string
  /** Пусто — любые. */
  tiers: number[]
  categories: number[]
  due: DueFilter
  kind: QuestKind
  sort: QuestSort
}

export const DEFAULT_FILTERS: QuestFilters = {
  q: '',
  tiers: [],
  categories: [],
  due: 'all',
  kind: 'all',
  sort: 'due',
}

/** Сколько условий отбора задано (поиск и сортировка не считаются) — для бейджа на кнопке. */
export function activeFilterCount(f: QuestFilters): number {
  return (
    Number(f.tiers.length > 0) +
    Number(f.categories.length > 0) +
    Number(f.due !== 'all') +
    Number(f.kind !== 'all')
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

export const isRecurring = (quest: Quest) => quest.recurring_quest_id !== null

/** Порядок квестов для выбранной сортировки; при равенстве — по сроку. */
export function questComparator(
  sort: QuestSort,
  tierLevel: (tierId: number) => number,
): (a: Quest, b: Quest) => number {
  switch (sort) {
    case 'due':
      return byDue
    // Важные сверху, внутри уровня — по сроку.
    case 'tier':
      return (a, b) => tierLevel(b.tier_id) - tierLevel(a.tier_id) || byDue(a, b)
    case 'reward':
      return (a, b) => b.reward - a.reward || byDue(a, b)
  }
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
      (f.kind === 'all' || (f.kind === 'recurring') === isRecurring(quest)) &&
      matchesDue(quest, f.due, ctx.now),
  )
  return result.sort(questComparator(f.sort, ctx.tierLevel))
}
