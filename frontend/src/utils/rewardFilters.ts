import type { Reward } from '@/api/types'

/** menu — порядок, в котором траты вписаны в меню. */
export type RewardSort = 'menu' | 'cheap' | 'expensive' | 'name'

export interface RewardFilters {
  q: string
  sort: RewardSort
  onlyAffordable: boolean
}

export const DEFAULT_REWARD_FILTERS: RewardFilters = { q: '', sort: 'menu', onlyAffordable: false }

const byName = (a: Reward, b: Reward) => a.name.localeCompare(b.name, 'ru')

/** Отбор и сортировка меню таверны. Архивные «по карману» не отсекаются — их всё равно не заказать. */
export function filterRewards(rewards: Reward[], f: RewardFilters, balance: number): Reward[] {
  const q = f.q.trim().toLocaleLowerCase('ru')
  const result = rewards.filter(
    (r) =>
      (!q ||
        r.name.toLocaleLowerCase('ru').includes(q) ||
        (r.description?.toLocaleLowerCase('ru').includes(q) ?? false)) &&
      (!f.onlyAffordable || r.is_archived || r.price <= balance),
  )
  const compare: Record<RewardSort, (a: Reward, b: Reward) => number> = {
    menu: (a, b) => a.id - b.id,
    cheap: (a, b) => a.price - b.price || byName(a, b),
    expensive: (a, b) => b.price - a.price || byName(a, b),
    name: byName,
  }
  return result.sort(compare[f.sort])
}
