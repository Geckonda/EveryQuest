import { h, ref } from 'vue'
import { NButton, useDialog, useMessage } from 'naive-ui'
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

  async function undo(quest: Quest) {
    busyId.value = quest.id
    try {
      await quests.undo(quest.id)
      message.info(`Квест «${quest.name}» снова на доске`)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      busyId.value = null
    }
  }

  /** Сообщение с кнопкой «Отменить» — на случай промаха пальцем. */
  function withUndo(type: 'success' | 'warning', text: string, quest: Quest) {
    const toast = message[type](
      () =>
        h('span', { class: 'undo-message' }, [
          text,
          ' ',
          h(
            NButton,
            {
              text: true,
              type: 'primary',
              onClick: () => {
                toast.destroy()
                undo(quest)
              },
            },
            () => 'Отменить',
          ),
        ]),
      { duration: 10_000, closable: true },
    )
  }

  /** Сдача — с подтверждением: кнопка большая, задеть её пальцем легко. */
  function complete(quest: Quest, event: MouseEvent) {
    // Точка старта — до диалога и запроса: currentTarget есть только во время клика,
    // а после запроса карточка уйдёт с доски.
    const from = pointOf(event.currentTarget as Element | null)
    dialog.success({
      title: 'Сдать квест?',
      content: `«${quest.name}» уйдёт в архив, в кошель — награда: ${coins(quest.reward)}.`,
      positiveText: 'Сдать',
      negativeText: 'Отмена',
      onPositiveClick: async () => {
        busyId.value = quest.id
        try {
          await quests.complete(quest.id)
          flyCoins(from, purseElement())
          withUndo('success', `Квест «${quest.name}» сдан. Награда: ${coins(quest.reward)}.`, quest)
        } catch (e) {
          message.error(errorMessage(e))
          await quests.loadActive().catch(() => {})
        } finally {
          busyId.value = null
        }
      },
    })
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
          withUndo(
            'warning',
            quest.penalty
              ? `Квест «${quest.name}» провален. Штраф: ${coins(quest.penalty)}.`
              : `Квест «${quest.name}» провален.`,
            quest,
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

  return { busyId, complete, fail, archive, undo }
}
