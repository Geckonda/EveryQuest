import { ref } from 'vue'

/** Событие beforeinstallprompt (Chrome, Edge, Яндекс; в стандартных типах DOM его нет). */
interface InstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const standaloneQuery =
  typeof window !== 'undefined' ? window.matchMedia?.('(display-mode: standalone)') : undefined

/** Уже открыто как установленное приложение (с иконки, без адресной строки). */
const isStandalone = ref(
  (standaloneQuery?.matches ?? false) ||
    // Safari на iPhone — своё нестандартное свойство.
    (typeof navigator !== 'undefined' &&
      (navigator as Navigator & { standalone?: boolean }).standalone === true),
)

/** iPhone и iPad: установить можно только вручную, через «Поделиться → На экран „Домой“». */
const isIos = typeof navigator !== 'undefined' && /iPhone|iPad|iPod/.test(navigator.userAgent)

let deferred: InstallPromptEvent | null = null
/** Браузер готов показать своё окно установки. */
const canInstall = ref(false)

// Событие приходит один раз и рано — слушаем с загрузки модуля, а не с открытия профиля.
if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault() // своё окно браузер покажет по кнопке, а не сам по себе
    deferred = event as InstallPromptEvent
    canInstall.value = true
  })
  window.addEventListener('appinstalled', () => {
    deferred = null
    canInstall.value = false
    isStandalone.value = true
  })
}

/** Установка приложения на телефон или компьютер. */
export function useInstall() {
  async function install(): Promise<boolean> {
    if (!deferred) return false
    await deferred.prompt()
    const { outcome } = await deferred.userChoice
    // Повторно этим же событием окно не показать.
    deferred = null
    canInstall.value = false
    return outcome === 'accepted'
  }

  return { canInstall, isStandalone, isIos, install }
}
