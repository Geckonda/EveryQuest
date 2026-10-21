import { ref } from 'vue'
import { useDialog, useMessage } from 'naive-ui'
import type { Quest } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useNow } from '@/composables/useNow'
import { useQuestsStore } from '@/stores/quests'
import { flyCoins, pointOf, purseElement } from '@/utils/coinFx'
import { coins } from '@/utils/format'

const HOUR_MS = 60 * 60 * 1000

/**
 * «Сейчас» для страниц с карточками квестов: посекундно — только пока
 * у какого-то активного квеста идёт последний час.
 */
export function useQuestNow() {
  const quests = useQuestsStore()
  return useNow((current) =>
    quests.active.some((q) => {
      if (!q.due_at) return false
      const left = new Date(q.due_at).getTime() - current.getTime()
      return left > 0 && left < HOUR_MS
    }),
  )
}

/** Сдать, провалить, снять с доски — одинаково на доске и на странице «Сегодня». */
export function useQuestActions() {
  const quests = useQuestsStore()
  const message = useMessage()
  const dialog = useDialog()

  /** Квест, по которому идёт запрос — его кнопки крутят индикатор. */
  const busyId = ref<number | null>(null)

  async function complete(quest: Quest, event: MouseEvent) {
    // Точка старта — до запроса: после него карточка уйдёт с доски.
    const from = pointOf(event.currentTarget as Element | null)
    busyId.value = quest.id
    try {
      await quests.complete(quest.id)
      flyCoins(from, purseElement())
      message.success(`Квест «${quest.name}» сдан. Награда: ${coins(quest.reward)}`)
    } catch (e) {
      message.error(errorMessage(e))
      await quests.loadActive().catch(() => {})
    } finally {
      busyId.value = null
    }
  }

  function fail(quest: Quest) {
    dialog.error({
      title: 'Признать квест проваленным?',
      content: quest.penalty
        ? `«${quest.name}» уйдёт в архив, гильдия взыщет штраф: ${coins(quest.penalty)}.`
        : `«${quest.name}» уйдёт в архив. Штрафа за него нет.`,
      positiveText: 'Провалить',
      negativeText: 'Отмена',
      onPositiveClick: async () => {
        busyId.value = quest.id
        try {
          await quests.fail(quest.id)
          message.warning(
            quest.penalty
              ? `Квест «${quest.name}» провален. Штраф: ${coins(quest.penalty)}`
              : `Квест «${quest.name}» провален`,
          )
        } catch (e) {
          message.error(errorMessage(e))
          await quests.loadActive().catch(() => {})
        } finally {
          busyId.value = null
        }
      },
    })
  }

  function archive(quest: Quest) {
    dialog.warning({
      title: 'Снять объявление с доски?',
      content: `«${quest.name}» исчезнет без награды и без штрафа.`,
      positiveText: 'Снять',
      negativeText: 'Отмена',
      onPositiveClick: async () => {
        try {
          await quests.update(quest.id, { status: 'archived' })
        } catch (e) {
          message.error(errorMessage(e))
        }
      },
    })
  }

  return { busyId, complete, fail, archive }
}
