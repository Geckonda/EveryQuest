import { h } from 'vue'
import { useDialog, useMessage } from 'naive-ui'
import { archiveConflictOf, errorMessage } from '@/api/errors'
import type { ArchiveBlocker, ArchiveConflict } from '@/api/types'

function blockerList(title: string, items: ArchiveBlocker[]) {
  if (!items.length) return null
  return [
    h('p', { style: 'margin: 12px 0 4px; font-weight: 600' }, title),
    h(
      'ul',
      { style: 'margin: 0; padding-left: 20px' },
      items.map((q) => h('li', { key: q.id }, q.name)),
    ),
  ]
}

function renderConflict(conflict: ArchiveConflict) {
  return h('div', [
    h('p', { style: 'margin: 0' }, conflict.message),
    blockerList('Активные квесты:', conflict.quests),
    blockerList('Повторяющиеся квесты:', conflict.recurring_quests),
  ])
}

/**
 * Архивирует или возвращает объект справочника с уведомлением.
 * При 409 показывает, какие квесты мешают архивации.
 */
export function useArchiveToggle() {
  const message = useMessage()
  const dialog = useDialog()

  return async function toggle(
    item: { name: string; is_archived: boolean },
    save: (isArchived: boolean) => Promise<unknown>,
  ) {
    const archiving = !item.is_archived
    try {
      await save(archiving)
      message.success(archiving ? `«${item.name}» в архиве` : `«${item.name}» возвращён`)
    } catch (error) {
      const conflict = archiveConflictOf(error)
      if (conflict) {
        dialog.warning({
          title: `Нельзя архивировать «${item.name}»`,
          content: () => renderConflict(conflict),
          positiveText: 'Понятно',
        })
      } else {
        message.error(errorMessage(error))
      }
    }
  }
}
