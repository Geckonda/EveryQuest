/** Русское склонение после числа: plural(2, 'день', 'дня', 'дней') → 'дня'. */
export function plural(n: number, one: string, few: string, many: string): string {
  const abs = Math.abs(n)
  const lastTwo = abs % 100
  const last = abs % 10
  if (lastTwo >= 11 && lastTwo <= 14) return many
  if (last === 1) return one
  if (last >= 2 && last <= 4) return few
  return many
}

/** «1 монета», «2 монеты», «5 монет». */
export function coins(n: number): string {
  return `${n} ${plural(n, 'монета', 'монеты', 'монет')}`
}

/** Сумма со знаком: «+50», «−30» (типографский минус). */
export function signed(n: number): string {
  return n > 0 ? `+${n}` : n < 0 ? `−${Math.abs(n)}` : '0'
}

const timeFormat = new Intl.DateTimeFormat('ru', { hour: '2-digit', minute: '2-digit' })
const dateFormat = new Intl.DateTimeFormat('ru', { day: 'numeric', month: 'short' })
const dateTimeFormat = new Intl.DateTimeFormat('ru', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
}

const DAY_MS = 24 * 60 * 60 * 1000

export interface DueLabel {
  text: string
  overdue: boolean
  /** Осталось меньше трёх часов. */
  soon: boolean
}

/** Подпись срока квеста относительно now (в часовом поясе браузера). */
export function dueLabel(dueAt: string, now = new Date()): DueLabel {
  const due = new Date(dueAt)
  const left = due.getTime() - now.getTime()
  if (left <= 0) return { text: 'Срок истёк', overdue: true, soon: false }

  const days = Math.round((startOfDay(due) - startOfDay(now)) / DAY_MS)
  const time = timeFormat.format(due)
  let text: string
  if (days === 0) text = `сегодня до ${time}`
  else if (days === 1) text = `завтра до ${time}`
  else text = `до ${dateFormat.format(due)}, ${time}`
  return { text, overdue: false, soon: left < 3 * 60 * 60 * 1000 }
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}
