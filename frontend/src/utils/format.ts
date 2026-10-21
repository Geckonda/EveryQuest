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

/** «1 золотой», «2 золотых», «5 золотых». */
export function coins(n: number): string {
  return `${n} ${plural(n, 'золотой', 'золотых', 'золотых')}`
}

const ROMAN = ['I', 'II', 'III', 'IV', 'V']

/** Уровень тира (1–5) римской цифрой: 3 → «III». */
export function romanLevel(level: number): string {
  return ROMAN[level - 1] ?? String(level)
}

/** Название тира стоит показывать текстом, только если оно не совпадает с цифрой на печати. */
export function tierLabel(tier: { name: string; level: number }): string | null {
  return tier.name.trim() === romanLevel(tier.level) ? null : tier.name
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

const MINUTE_MS = 60 * 1000
const HOUR_MS = 60 * MINUTE_MS

/** Насколько горит квест: от этого зависят цвет фитиля, свечение и дрожь карточки. */
export type Urgency = 'calm' | 'soon' | 'critical' | 'overdue'

export interface Countdown {
  /** «2 д 5 ч», «3 ч 14 мин», в последний час — «13:05» (минуты:секунды). */
  left: string
  urgency: Urgency
  /** Доля оставшегося времени от создания до срока, 0…1 — длина фитиля. */
  remaining: number
}

const pad2 = (n: number) => String(n).padStart(2, '0')

/** Сколько осталось до срока и насколько это срочно. */
export function countdown(createdAt: string, dueAt: string, now = new Date()): Countdown {
  const due = new Date(dueAt).getTime()
  const left = due - now.getTime()
  if (left <= 0) return { left: '0:00', urgency: 'overdue', remaining: 0 }

  // Квест могли создать «задним числом» относительно часов браузера — не даём доле выйти за 1.
  const total = Math.max(due - new Date(createdAt).getTime(), left)
  const remaining = left / total

  let text: string
  if (left < HOUR_MS) {
    const seconds = Math.floor(left / 1000)
    text = `${Math.floor(seconds / 60)}:${pad2(seconds % 60)}`
  } else if (left < DAY_MS) {
    const minutes = Math.floor(left / MINUTE_MS)
    text = `${Math.floor(minutes / 60)} ч ${minutes % 60} мин`
  } else {
    const hours = Math.floor(left / HOUR_MS)
    text = `${Math.floor(hours / 24)} д ${hours % 24} ч`
  }

  // «Скоро» — и по абсолютному времени, и по доле: недельный квест с 15% запаса тоже горит.
  const urgency: Urgency =
    left < 30 * MINUTE_MS ? 'critical' : left < 3 * HOUR_MS || remaining < 0.15 ? 'soon' : 'calm'
  return { left: text, urgency, remaining }
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}
