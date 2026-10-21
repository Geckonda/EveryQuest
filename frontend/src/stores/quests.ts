import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { Quest, QuestClosed, QuestPayload } from '@/api/types'
import { byDue } from '@/utils/questFilters'
import { useAuthStore } from './auth'

const HISTORY_PAGE = 50

export const useQuestsStore = defineStore('quests', () => {
  const auth = useAuthStore()

  const active = ref<Quest[]>([])
  const history = ref<Quest[]>([])
  /** Есть ли в архиве ещё не загруженные квесты. */
  const historyHasMore = ref(false)

  // Другой пользователь — чужие квесты не должны мелькнуть до загрузки своих.
  watch(
    () => auth.user?.id,
    () => {
      active.value = []
      history.value = []
      historyHasMore.value = false
    },
  )

  async function loadActive() {
    active.value = await api.get<Quest[]>('/quests?status=active')
  }

  /** Архив страницами, свежезакрытые сверху. more — дозагрузить следующую страницу. */
  async function loadHistory(more = false) {
    const params = new URLSearchParams([
      ['status', 'completed'],
      ['status', 'failed'],
      ['status', 'archived'],
      ['limit', String(HISTORY_PAGE)],
      ['offset', String(more ? history.value.length : 0)],
    ])
    const page = await api.get<Quest[]>(`/quests?${params}`)
    // Квесты, закрытые после загрузки первой страницы, сдвигают offset — убираем повторы.
    const known = new Set(more ? history.value.map((q) => q.id) : [])
    history.value = [...(more ? history.value : []), ...page.filter((q) => !known.has(q.id))]
    historyHasMore.value = page.length === HISTORY_PAGE
  }

  async function create(payload: QuestPayload) {
    const quest = await api.post<Quest>('/quests', payload)
    active.value = [...active.value, quest].sort(byDue)
    return quest
  }

  async function update(id: number, payload: Partial<QuestPayload> | { status: 'archived' }) {
    const quest = await api.patch<Quest>(`/quests/${id}`, payload)
    active.value = active.value.filter((q) => q.id !== id)
    if (quest.status === 'active') active.value = [...active.value, quest].sort(byDue)
    else history.value = [quest, ...history.value]
    return quest
  }

  /** Сдать или провалить: квест уходит в архив, баланс — из ответа. */
  async function close(id: number, action: 'complete' | 'fail') {
    const result = await api.post<QuestClosed>(`/quests/${id}/${action}`)
    active.value = active.value.filter((q) => q.id !== id)
    history.value = [result.quest, ...history.value]
    auth.setBalance(result.balance, action === 'complete' ? 'reward' : 'penalty')
    return result.quest
  }

  const complete = (id: number) => close(id, 'complete')
  const fail = (id: number) => close(id, 'fail')

  return {
    active,
    history,
    historyHasMore,
    loadActive,
    loadHistory,
    create,
    update,
    complete,
    fail,
  }
})
