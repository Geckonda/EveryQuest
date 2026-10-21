/**
 * «Chrome · Windows» из User-Agent — чтобы в списке устройств было понятно, что есть что.
 * Без библиотеки: нужно узнать лишь самые распространённые браузеры и системы.
 */

// Порядок важен: Edge и Opera притворяются Chrome, Chrome — Safari.
const BROWSERS: [RegExp, string][] = [
  [/YaBrowser\//, 'Яндекс Браузер'],
  [/Edg(e|A|iOS)?\//, 'Edge'],
  [/OPR\/|Opera/, 'Opera'],
  [/Firefox\/|FxiOS\//, 'Firefox'],
  [/Chrome\/|CriOS\//, 'Chrome'],
  [/Safari\//, 'Safari'],
]

const SYSTEMS: [RegExp, string][] = [
  [/Windows/, 'Windows'],
  [/iPhone/, 'iPhone'],
  [/iPad/, 'iPad'],
  [/Android/, 'Android'],
  [/Mac OS X|Macintosh/, 'macOS'],
  [/Linux/, 'Linux'],
]

const find = (ua: string, table: [RegExp, string][]) => table.find(([re]) => re.test(ua))?.[1]

export function describeDevice(userAgent: string | null): string {
  if (!userAgent) return 'Неизвестное устройство'
  const parts = [find(userAgent, BROWSERS), find(userAgent, SYSTEMS)].filter(Boolean)
  return parts.length ? parts.join(' · ') : 'Неизвестное устройство'
}
