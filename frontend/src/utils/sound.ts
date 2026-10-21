import { ref, watch } from 'vue'

/** reward — награда, purchase — заказ в таверне, penalty — штраф. */
export type SoundKind = 'reward' | 'purchase' | 'penalty'

const STORAGE_KEY = 'eq.sound'

function readEnabled(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== 'off'
  } catch {
    return true
  }
}

/** Звук монет — настройка устройства, а не профиля: на работе можно выключить только там. */
export const soundEnabled = ref(readEnabled())

watch(soundEnabled, (on) => {
  try {
    localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off')
  } catch {
    /* приватный режим — настройка живёт до перезагрузки */
  }
})

let context: AudioContext | null = null

/**
 * AudioContext создаётся и «размораживается» только после жеста пользователя —
 * иначе браузер его заблокирует. Звуки идут в ответ на клики, так что к ним он уже готов.
 */
function audio(): AudioContext | null {
  if (typeof AudioContext === 'undefined') return null
  context ??= new AudioContext()
  if (context.state === 'suspended') context.resume().catch(() => {})
  return context
}

if (typeof window !== 'undefined') {
  window.addEventListener('pointerdown', () => audio(), { once: true, capture: true })
}

/** Затухающий тон: монетный «дзынь» — высокий синус с быстрым спадом. */
function tone(
  ctx: AudioContext,
  out: AudioNode,
  freq: number,
  start: number,
  duration: number,
  { type = 'sine' as OscillatorType, volume = 1, slideTo = freq } = {},
) {
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, start)
  if (slideTo !== freq) osc.frequency.exponentialRampToValueAtTime(slideTo, start + duration)
  gain.gain.setValueAtTime(0.0001, start)
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.005)
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration)
  osc.connect(gain).connect(out)
  osc.start(start)
  osc.stop(start + duration + 0.02)
}

/** Металлический звон: основной тон и негармонический обертон, как у настоящей монеты. */
function clink(ctx: AudioContext, out: AudioNode, freq: number, start: number, volume = 1) {
  tone(ctx, out, freq, start, 0.22, { volume })
  tone(ctx, out, freq * 2.76, start, 0.12, { volume: volume * 0.35 })
}

export function playSound(kind: SoundKind): void {
  if (!soundEnabled.value) return
  const ctx = audio()
  if (!ctx || ctx.state !== 'running') return

  const master = ctx.createGain()
  master.gain.value = 0.18
  master.connect(ctx.destination)
  const t = ctx.currentTime + 0.01

  switch (kind) {
    case 'reward':
      // Две монеты вверх по тону — «заработал».
      clink(ctx, master, 1319, t)
      clink(ctx, master, 1760, t + 0.09)
      break
    case 'purchase':
      // Горсть монет высыпается на стойку.
      ;[2093, 1661, 1865, 1480].forEach((freq, i) => clink(ctx, master, freq, t + i * 0.06, 0.8))
      break
    case 'penalty':
      // Глухой удар и тон вниз — «взыскано».
      tone(ctx, master, 196, t, 0.45, { type: 'triangle', volume: 0.9, slideTo: 98 })
      tone(ctx, master, 784, t, 0.12, { volume: 0.25, slideTo: 392 })
      break
  }
}
