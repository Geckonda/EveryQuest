import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { Quest, QuestClosed, QuestPage, QuestPayload } from '@/api/types'
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

  /** Курсор следующей страницы архива; null — дальше пусто. */
  let historyCursor: string | null = null

  /**
   * Архив страницами по курсору, свежезакрытые сверху. more — следующая страница.
   * Курсор, а не сдвиг: квесты, закрытые пока листали, не сдвигают страницы.
   */
  async function loadHistory(more = false) {
    const params = new URLSearchParams({ limit: String(HISTORY_PAGE) })
    if (more && historyCursor) params.set('cursor', historyCursor)
    const page = await api.get<QuestPage>(`/quests/archive?${params}`)
    // Закрытые здесь же (сдал, провалил) уже добавлены в начало локально — не повторяем.
    const known = new Set(more ? history.value.map((q) => q.id) : [])
    history.value = [...(more ? history.value : []), ...page.items.filter((q) => !known.has(q.id))]
    historyCursor = page.next_cursor
    historyHasMore.value = page.next_cursor !== null
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

  /** Передумал: квест возвращается на доску, награда списывается или штраф возвращается. */
  async function undo(id: number) {
    const result = await api.post<QuestClosed>(`/quests/${id}/undo`)
    history.value = history.value.filter((q) => q.id !== id)
    active.value = [...active.value.filter((q) => q.id !== id), result.quest].sort(byDue)
    auth.setBalance(result.balance, 'manual')
    return result.quest
  }

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
    undo,
  }
})
