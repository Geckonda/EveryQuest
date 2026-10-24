/** Время «ЧЧ:ММ» или «ЧЧ:ММ:СС» в заданный день от сегодня, по часам устройства. */
export function atTime(time: string, daysFromToday: number, now = new Date()): number {
  const [h = 23, m = 59] = time.split(':').map(Number)
  const d = new Date(now)
  d.setDate(d.getDate() + daysFromToday)
  d.setHours(h, m, 0, 0)
  return d.getTime()
}

/**
 * Срок нового квеста: сегодня во время из профиля, а если оно уже прошло — завтра.
 * Иначе квест в 20:00 с «концом дня» в 18:00 сразу оказался бы просроченным.
 */
export function defaultDue(time: string, now = new Date()): number {
  const today = atTime(time, 0, now)
  return today > now.getTime() ? today : atTime(time, 1, now)
}
