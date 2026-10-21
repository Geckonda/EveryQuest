import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { RewardSession } from '@/api/types'
import { useAuthStore } from './auth'

const byEnd = (a: RewardSession, b: RewardSession) =>
  a.ends_at < b.ends_at ? -1 : a.ends_at > b.ends_at ? 1 : a.id - b.id

/** Идущие траты — сначала те, что кончатся раньше. */
export const useSessionsStore = defineStore('sessions', () => {
  const auth = useAuthStore()
  const active = ref<RewardSession[]>([])

  watch(
    () => auth.user?.id,
    () => (active.value = []),
  )

  async function load() {
    active.value = await api.get<RewardSession[]>('/reward-sessions/active')
  }

  function add(session: RewardSession) {
    active.value = [...active.value.filter((s) => s.id !== session.id), session].sort(byEnd)
  }

  /** Время вышло — убрать из списка без запроса: на сервере сеанс просто истёк. */
  function expire(id: number) {
    active.value = active.value.filter((s) => s.id !== id)
  }

  /** Закончить раньше срока. */
  async function finish(id: number) {
    await api.post<RewardSession>(`/reward-sessions/${id}/finish`)
    expire(id)
  }

  return { active, load, add, expire, finish }
})
