import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { Quest, QuestClosed, QuestPayload } from '@/api/types'
import { useAuthStore } from './auth'

/** Активные квесты сортируются как на бэкенде: по сроку, без срока — в конце. */
function byDue(a: Quest, b: Quest): number {
  if (a.due_at === b.due_at) return a.id - b.id
  if (a.due_at === null) return 1
  if (b.due_at === null) return -1
  return a.due_at < b.due_at ? -1 : 1
}

export const useQuestsStore = defineStore('quests', () => {
  const auth = useAuthStore()

  const active = ref<Quest[]>([])
  const history = ref<Quest[]>([])

  // Другой пользователь — чужие квесты не должны мелькнуть до загрузки своих.
  watch(
    () => auth.user?.id,
    () => {
      active.value = []
      history.value = []
    },
  )

  async function loadActive() {
    active.value = await api.get<Quest[]>('/quests?status=active')
  }

  async function loadHistory() {
    const all = await api.get<Quest[]>('/quests?limit=200')
    history.value = all.filter((q) => q.status !== 'active')
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
    auth.setBalance(result.balance)
    return result.quest
  }

  const complete = (id: number) => close(id, 'complete')
  const fail = (id: number) => close(id, 'fail')

  return { active, history, loadActive, loadHistory, create, update, complete, fail }
})
