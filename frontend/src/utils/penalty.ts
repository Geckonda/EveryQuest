const MAX_COINS = 1_000_000

/**
 * Штраф по умолчанию: награда × множитель, половина вверх — как `economy.default_penalty`.
 *
 * Множитель переводится в сотые, чтобы не ловить ошибки float: 25 × 1.5 должно дать ровно 37.5.
 */
export function penaltyFor(reward: number, multiplier: number): number {
  const hundredths = Math.round(multiplier * 100)
  return Math.min(Math.round((reward * hundredths) / 100), MAX_COINS)
}
