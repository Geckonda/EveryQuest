<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { useAuthStore, type CoinReason } from '@/stores/auth'
import { signed } from '@/utils/format'
import { playSound, type SoundKind } from '@/utils/sound'
import CoinIcon from './CoinIcon.vue'

/** Кошелёк в шапке: баланс докручивается, изменение всплывает, звенят монеты. */
const props = defineProps<{ balance: number }>()

const auth = useAuthStore()

const shown = ref(props.balance)
const flash = ref<'gain' | 'loss' | null>(null)
const floats = ref<{ id: number; delta: number }[]>([])

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

let frame = 0
watch(
  () => props.balance,
  (to) => {
    cancelAnimationFrame(frame)
    const from = shown.value
    if (reducedMotion() || Math.abs(to - from) < 2) {
      shown.value = to
      return
    }
    const start = performance.now()
    const duration = 650
    const step = (t: number) => {
      const k = Math.min((t - start) / duration, 1)
      const eased = 1 - (1 - k) ** 3
      shown.value = Math.round(from + (to - from) * eased)
      if (k < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
  },
)

function soundFor(reason: CoinReason, delta: number): SoundKind {
  if (reason === 'reward' || reason === 'purchase' || reason === 'penalty') return reason
  return delta > 0 ? 'reward' : 'penalty'
}

let flashTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => auth.coinEvent,
  (event) => {
    if (!event) return
    playSound(soundFor(event.reason, event.delta))

    flash.value = null
    // Перезапуск CSS-анимации: снять класс и вернуть на следующем кадре.
    requestAnimationFrame(() => (flash.value = event.delta > 0 ? 'gain' : 'loss'))
    clearTimeout(flashTimer)
    flashTimer = setTimeout(() => (flash.value = null), 900)

    floats.value = [...floats.value, { id: event.id, delta: event.delta }]
    setTimeout(() => (floats.value = floats.value.filter((f) => f.id !== event.id)), 1400)
  },
)

onUnmounted(() => {
  cancelAnimationFrame(frame)
  clearTimeout(flashTimer)
})
</script>

<template>
  <span
    class="purse num"
    :class="[flash, { negative: balance < 0 }]"
    :title="balance < 0 ? 'Долг перед гильдией' : 'Кошель'"
    data-purse
    data-tour="purse"
  >
    <CoinIcon :size="18" />
    {{ shown }}
    <span
      v-for="f in floats"
      :key="f.id"
      class="float"
      :class="f.delta > 0 ? 'up' : 'down'"
      aria-hidden="true"
    >
      {{ signed(f.delta) }}
    </span>
  </span>
</template>

<style scoped>
.purse {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px 2px 6px;
  border: 1px solid rgba(231, 178, 79, 0.45);
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.25);
  color: var(--color-sign-gold);
  font-size: 1.05rem;
  font-weight: 700;
  white-space: nowrap;
}

.purse.negative {
  color: #ff9c86;
  border-color: rgba(255, 120, 100, 0.5);
}

/* Начисление: золотой блеск. */
.purse.gain {
  animation: gain 0.9s ease-out;
}

/* Списание: кошель вздрагивает и краснеет. */
.purse.loss {
  animation: loss 0.9s ease-out;
}

@keyframes gain {
  30% {
    transform: scale(1.12);
    box-shadow: 0 0 16px 4px rgba(255, 210, 110, 0.65);
    border-color: #ffd36e;
  }
}

@keyframes loss {
  10%,
  30% {
    transform: translateX(-3px);
  }
  20%,
  40% {
    transform: translateX(3px);
  }
  25% {
    box-shadow: 0 0 14px 3px rgba(255, 100, 80, 0.6);
    border-color: #ff7a64;
    color: #ffb3a3;
  }
  50% {
    transform: none;
  }
}

/* «+50» / «−30» всплывает от кошелька и тает. */
.float {
  position: absolute;
  top: 100%;
  right: 6px;
  font-size: 1rem;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
  pointer-events: none;
  animation: float 1.4s ease-out forwards;
}

.float.up {
  color: #ffd36e;
}

.float.down {
  color: #ff8f7a;
}

@keyframes float {
  from {
    transform: translateY(-6px);
    opacity: 0;
  }
  15% {
    opacity: 1;
  }
  to {
    transform: translateY(22px);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .purse.gain,
  .purse.loss,
  .float {
    animation: none;
  }
}
</style>
