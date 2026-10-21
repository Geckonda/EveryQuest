import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client'
import type { RewardSession } from '@/api/types'
import { useAuthStore } from './auth'

const ms = (iso: string) => new Date(iso).getTime()

/** Как на бэкенде: по началу, затем по концу. Идущие — раньше ожидающих в очереди. */
const byStart = (a: RewardSession, b: RewardSession) =>
  ms(a.started_at) - ms(b.started_at) || ms(a.ends_at) - ms(b.ends_at) || a.id - b.id

/** Идущие и ожидающие в очереди траты. */
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
    active.value = [...active.value.filter((s) => s.id !== session.id), session].sort(byStart)
  }

  /** Когда освободится очередь: конец последней незаконченной траты (null — свободна). */
  function queueEnd(now = new Date()): string | null {
    const last = active.value.reduce<string | null>(
      (max, s) => (max === null || ms(s.ends_at) > ms(max) ? s.ends_at : max),
      null,
    )
    return last !== null && ms(last) > now.getTime() ? last : null
  }

  /** Время вышло — убрать из списка без запроса: на сервере сеанс просто истёк. */
  function expire(id: number) {
    active.value = active.value.filter((s) => s.id !== id)
  }

  /** Закончить раньше срока или отменить ожидающую. Очередь сдвигается — перечитываем. */
  async function finish(id: number) {
    await api.post<RewardSession>(`/reward-sessions/${id}/finish`)
    expire(id)
    await load()
  }

  return { active, load, add, expire, finish, queueEnd }
})
