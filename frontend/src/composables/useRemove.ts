import { useDialog, useMessage } from 'naive-ui'
import { errorMessage } from '@/api/errors'

export interface RemoveOptions {
  /** «Удалить тир «Лишний»?» */
  title: string
  /** Что станет с тем, что на него ссылается. */
  content: string
  action: () => Promise<unknown>
  /** Сообщение после удаления. */
  done: string
  /** Ошибка, которую обработает вызывающий (например, «тир используется»); true — обработана. */
  onError?: (error: unknown) => boolean
}

/** Удаление насовсем с подтверждением и понятным объяснением последствий. */
export function useRemove() {
  const dialog = useDialog()
  const message = useMessage()

  return function remove(options: RemoveOptions) {
    dialog.warning({
      title: options.title,
      content: options.content,
      positiveText: 'Удалить',
      negativeText: 'Отмена',
      positiveButtonProps: { type: 'error' },
      onPositiveClick: async () => {
        try {
          await options.action()
          message.success(options.done)
        } catch (error) {
          if (!options.onError?.(error)) message.error(errorMessage(error))
        }
      },
    })
  }
}
