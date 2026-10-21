import { onScopeDispose, readonly, ref, watch, type Ref } from 'vue'

const FAST_MS = 1_000
const SLOW_MS = 30_000

/** Одно «сейчас» на всё приложение — все карточки тикают синхронно. */
const now = ref(new Date())
let subscribers = 0
let fastSubscribers = 0
let timer: ReturnType<typeof setTimeout> | undefined

function schedule() {
  clearTimeout(timer)
  timer = undefined
  if (!subscribers || document.hidden) return
  const delay = fastSubscribers ? FAST_MS : SLOW_MS
  // Выравниваем по границе секунды — иначе «13:05» менялось бы не в такт настоящим часам.
  timer = setTimeout(tick, delay - (Date.now() % FAST_MS))
}

function tick() {
  now.value = new Date()
  schedule()
}

function onVisibilityChange() {
  // Свернули вкладку — не тикаем зря; вернулись — сразу актуальное время.
  if (document.hidden) schedule()
  else tick()
}

/**
 * Тикающее «сейчас». Пока хоть один подписчик просит fast (идёт посекундный отсчёт) —
 * раз в секунду, иначе раз в 30 секунд. В фоновой вкладке не тикает.
 *
 * fast получает текущее «сейчас» и пересчитывается на каждом тике и при смене своих
 * зависимостей: квест со сроком через два часа сам перейдёт на секунды за час до срока.
 */
export function useNow(fast?: (now: Date) => boolean): Readonly<Ref<Date>> {
  if (subscribers++ === 0) {
    document.addEventListener('visibilitychange', onVisibilityChange)
    tick()
  }

  let isFast = false
  const stop = fast
    ? watch(
        () => fast(now.value),
        (value) => {
          if (value === isFast) return
          isFast = value
          fastSubscribers += value ? 1 : -1
          tick()
        },
        { immediate: true },
      )
    : undefined

  onScopeDispose(() => {
    stop?.()
    if (isFast) fastSubscribers--
    if (--subscribers === 0) {
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
    schedule()
  })

  return readonly(now)
}
