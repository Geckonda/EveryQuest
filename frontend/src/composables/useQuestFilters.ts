import { reactive, watch } from 'vue'
import { useRoute, useRouter, type LocationQuery, type LocationQueryRaw } from 'vue-router'
import {
  DEFAULT_FILTERS,
  type DueFilter,
  type QuestFilters,
  type QuestSort,
} from '@/utils/questFilters'

const DUE: DueFilter[] = ['all', 'overdue', 'today', 'week', 'none']
const SORT: QuestSort[] = ['due', 'tier', 'reward']

/** Значение параметра; отсутствующий ключ — undefined. */
type QueryValue = LocationQuery[string] | undefined

function list(value: QueryValue): string[] {
  if (value === undefined || value === null) return []
  return (Array.isArray(value) ? value : [value]).filter((v): v is string => v !== null)
}

function ids(value: QueryValue): number[] {
  return list(value)
    .map(Number)
    .filter((n) => Number.isInteger(n) && n > 0)
}

function oneOf<T extends string>(value: QueryValue, allowed: T[], fallback: T): T {
  const [first] = list(value)
  return allowed.includes(first as T) ? (first as T) : fallback
}

export function fromQuery(query: LocationQuery): QuestFilters {
  return {
    q: list(query.q)[0] ?? '',
    tiers: ids(query.tier),
    categories: ids(query.cat),
    due: oneOf(query.due, DUE, DEFAULT_FILTERS.due),
    onlyRecurring: list(query.rec)[0] === '1',
    sort: oneOf(query.sort, SORT, DEFAULT_FILTERS.sort),
  }
}

/** Значения по умолчанию в адрес не пишем — ссылка на доску без фильтров остаётся чистой. */
export function toQuery(f: QuestFilters): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  if (f.q.trim()) query.q = f.q.trim()
  if (f.tiers.length) query.tier = f.tiers.map(String)
  if (f.categories.length) query.cat = f.categories.map(String)
  if (f.due !== DEFAULT_FILTERS.due) query.due = f.due
  if (f.onlyRecurring) query.rec = '1'
  if (f.sort !== DEFAULT_FILTERS.sort) query.sort = f.sort
  return query
}

/** Фильтры доски, синхронизированные с query-параметрами: переживают перезагрузку и «назад». */
export function useQuestFilters() {
  const route = useRoute()
  const router = useRouter()
  const filters = reactive<QuestFilters>(fromQuery(route.query))

  watch(
    filters,
    (f) => {
      // replace, а не push: каждая буква поиска не должна попадать в историю браузера.
      router.replace({ query: toQuery(f) }).catch(() => {})
    },
    { deep: true },
  )

  function reset() {
    Object.assign(filters, { ...DEFAULT_FILTERS, sort: filters.sort })
  }

  return { filters, reset }
}
