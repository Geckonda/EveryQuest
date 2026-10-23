import { reactive, watch } from 'vue'
import { useRoute, useRouter, type LocationQuery, type LocationQueryRaw } from 'vue-router'
import {
  DEFAULT_FILTERS,
  type DueFilter,
  type QuestFilters,
  type QuestKind,
  type QuestSort,
} from '@/utils/questFilters'

const DUE: DueFilter[] = ['all', 'overdue', 'today', 'week', 'none']
const SORT: QuestSort[] = ['due', 'tier', 'reward']
const KIND: QuestKind[] = ['all', 'once', 'recurring']

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

export function fromQuery(
  query: LocationQuery,
  defaults: QuestFilters = DEFAULT_FILTERS,
): QuestFilters {
  // rec=1 — старые ссылки, до фильтра «разовые / повторяющиеся».
  const legacyKind = list(query.rec)[0] === '1' ? 'recurring' : defaults.kind
  return {
    q: list(query.q)[0] ?? '',
    tiers: ids(query.tier),
    categories: ids(query.cat),
    due: oneOf(query.due, DUE, defaults.due),
    kind: oneOf(query.kind, KIND, legacyKind),
    sort: oneOf(query.sort, SORT, defaults.sort),
  }
}

/** Значения по умолчанию в адрес не пишем — ссылка на доску без фильтров остаётся чистой. */
export function toQuery(
  f: QuestFilters,
  defaults: QuestFilters = DEFAULT_FILTERS,
): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  if (f.q.trim()) query.q = f.q.trim()
  if (f.tiers.length) query.tier = f.tiers.map(String)
  if (f.categories.length) query.cat = f.categories.map(String)
  if (f.due !== defaults.due) query.due = f.due
  if (f.kind !== defaults.kind) query.kind = f.kind
  if (f.sort !== defaults.sort) query.sort = f.sort
  return query
}

/**
 * Фильтры доски, синхронизированные с query-параметрами: переживают перезагрузку и «назад».
 * `defaults` — свои значения по умолчанию для страницы (на «Сегодня» — по важности).
 */
export function useQuestFilters(defaults: Partial<QuestFilters> = {}) {
  const route = useRoute()
  const router = useRouter()
  const base: QuestFilters = { ...DEFAULT_FILTERS, ...defaults }
  const filters = reactive<QuestFilters>(fromQuery(route.query, base))

  watch(
    filters,
    (f) => {
      // replace, а не push: каждая буква поиска не должна попадать в историю браузера.
      router.replace({ query: toQuery(f, base) }).catch(() => {})
    },
    { deep: true },
  )

  function reset() {
    Object.assign(filters, { ...base, sort: filters.sort })
  }

  return { filters, reset }
}
