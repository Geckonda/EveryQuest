import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { RecurringPayload, RecurringQuest } from '@/api/types'
import { useAuthStore } from './auth'
import { useQuestsStore } from './quests'

type RecurringChanges = Partial<
  RecurringPayload & Pick<RecurringQuest, 'is_active' | 'is_archived'>
>

/** Шаблоны повторяющихся квестов — вместе с архивными; фильтрует страница. */
export const useRecurringStore = defineStore('recurring', () => {
  const auth = useAuthStore()
  const quests = useQuestsStore()

  const templates = ref<RecurringQuest[]>([])

  watch(
    () => auth.user?.id,
    () => (templates.value = []),
  )

  async function load() {
    templates.value = await api.get<RecurringQuest[]>('/recurring-quests?include_archived=true')
  }

  async function save(id: number | null, payload: RecurringChanges) {
    const template =
      id === null
        ? await api.post<RecurringQuest>('/recurring-quests', payload)
        : await api.patch<RecurringQuest>(`/recurring-quests/${id}`, payload)
    templates.value = [...templates.value.filter((t) => t.id !== template.id), template].sort(
      (a, b) => a.id - b.id,
    )
    // Создание, снятие с паузы или смена расписания могли сразу породить экземпляр.
    await quests.loadActive()
    return template
  }

  return { templates, load, save }
})
