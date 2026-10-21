/** Монеты, летящие между кнопкой и кошельком. Чистый DOM — без компонентов и библиотек. */

const COIN_SIZE = 18

function reducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

export interface Point {
  x: number
  y: number
}

/**
 * Центр элемента на экране. Брать до запроса к API, если элемент после него исчезнет
 * (сданный квест уходит с доски): у отцепленного от DOM элемента координаты нулевые.
 */
export function pointOf(el: Element | null): Point | null {
  if (!el?.isConnected) return null
  const r = el.getBoundingClientRect()
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 }
}

const toPoint = (target: Element | Point | null) =>
  target instanceof Element ? pointOf(target) : target

/** Кошелёк в шапке помечен data-purse. */
export function purseElement(): Element | null {
  return document.querySelector('[data-purse]')
}

/**
 * Запускает count монет от from к to по дуге. Монеты вылетают с небольшим разбросом,
 * чтобы выглядело как горсть, а не одна точка.
 */
export function flyCoins(
  from: Element | Point | null,
  to: Element | Point | null,
  count = 6,
): void {
  const start = toPoint(from)
  const end = toPoint(to)
  if (!start || !end || reducedMotion() || typeof document.body.animate !== 'function') return

  for (let i = 0; i < count; i++) {
    const coin = document.createElement('span')
    coin.className = 'flying-coin'
    Object.assign(coin.style, {
      left: `${start.x - COIN_SIZE / 2}px`,
      top: `${start.y - COIN_SIZE / 2}px`,
      width: `${COIN_SIZE}px`,
      height: `${COIN_SIZE}px`,
    })
    document.body.append(coin)

    const dx = end.x - start.x
    const dy = end.y - start.y
    const spread = (Math.random() - 0.5) * 60
    // Вверх (к кошельку) — дуга над обеими точками; вниз (из кошелька) — лишь небольшой
    // подскок, иначе монеты улетели бы за верх экрана.
    const lift = dy < 0 ? dy - 60 - Math.random() * 40 : dy * 0.35 - 30 - Math.random() * 20
    coin
      .animate(
        [
          { transform: 'translate(0, 0) scale(0.6)', opacity: 0 },
          { transform: `translate(${spread}px, -20px) scale(1)`, opacity: 1, offset: 0.15 },
          {
            transform: `translate(${dx / 2 + spread}px, ${lift}px) scale(1.1) rotate(180deg)`,
            offset: 0.55,
          },
          { transform: `translate(${dx}px, ${dy}px) scale(0.7) rotate(360deg)`, opacity: 0.9 },
        ],
        { duration: 750 + Math.random() * 200, delay: i * 55, easing: 'ease-in', fill: 'both' },
      )
      .finished.catch(() => {})
      .finally(() => coin.remove())
  }
}
