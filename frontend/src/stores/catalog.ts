import { computed, ref, type Ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type {
  Category,
  CategoryPayload,
  PurchaseResult,
  Reward,
  RewardPayload,
  Tier,
  TierPayload,
} from '@/api/types'
import { useAuthStore } from './auth'
import { useSessionsStore } from './sessions'

type Comparator<T> = (a: T, b: T) => number

const byTier: Comparator<Tier> = (a, b) => a.level - b.level || a.id - b.id
const byId: Comparator<Category> = (a, b) => a.id - b.id
const byReward: Comparator<Reward> = (a, b) => a.price - b.price || a.id - b.id

function upsert<T extends { id: number }>(list: Ref<T[]>, item: T, compare: Comparator<T>) {
  list.value = [...list.value.filter((x) => x.id !== item.id), item].sort(compare)
}

/** Тиры, категории и траты пользователя — вместе с архивными; фильтруют страницы. */
export const useCatalogStore = defineStore('catalog', () => {
  const auth = useAuthStore()
  const sessions = useSessionsStore()

  const tiers = ref<Tier[]>([])
  const categories = ref<Category[]>([])
  const rewards = ref<Reward[]>([])
  // Для кого загружено: после смены пользователя данные нужно перечитать.
  const loadedFor = ref<number | null>(null)

  const activeTiers = computed(() => tiers.value.filter((t) => !t.is_archived))
  const activeCategories = computed(() => categories.value.filter((c) => !c.is_archived))
  const activeRewards = computed(() => rewards.value.filter((r) => !r.is_archived))

  async function load(force = false) {
    const userId = auth.user?.id ?? null
    if (!force && userId !== null && loadedFor.value === userId) return
    ;[tiers.value, categories.value, rewards.value] = await Promise.all([
      api.get<Tier[]>('/tiers?include_archived=true'),
      api.get<Category[]>('/categories?include_archived=true'),
      api.get<Reward[]>('/rewards?include_archived=true'),
    ])
    loadedFor.value = userId
  }

  async function saveTier(
    id: number | null,
    payload: Partial<TierPayload & Pick<Tier, 'is_archived'>>,
  ) {
    const tier =
      id === null
        ? await api.post<Tier>('/tiers', payload)
        : await api.patch<Tier>(`/tiers/${id}`, payload)
    upsert(tiers, tier, byTier)
    return tier
  }

  async function saveCategory(
    id: number | null,
    payload: Partial<CategoryPayload & Pick<Category, 'is_archived'>>,
  ) {
    const category =
      id === null
        ? await api.post<Category>('/categories', payload)
        : await api.patch<Category>(`/categories/${id}`, payload)
    upsert(categories, category, byId)
    return category
  }

  async function saveReward(
    id: number | null,
    payload: Partial<RewardPayload & Pick<Reward, 'is_archived'>>,
  ) {
    const reward =
      id === null
        ? await api.post<Reward>('/rewards', payload)
        : await api.patch<Reward>(`/rewards/${id}`, payload)
    upsert(rewards, reward, byReward)
    return reward
  }

  /** queue — трата со временем встаёт в очередь за идущими; false — стартует сразу. */
  async function purchase(rewardId: number, queue = true) {
    const result = await api.post<PurchaseResult>(`/rewards/${rewardId}/purchase?queue=${queue}`)
    auth.setBalance(result.balance, 'purchase')
    if (result.session) sessions.add(result.session)
    return result
  }

  return {
    tiers,
    categories,
    rewards,
    activeTiers,
    activeCategories,
    activeRewards,
    load,
    saveTier,
    saveCategory,
    saveReward,
    purchase,
  }
})
