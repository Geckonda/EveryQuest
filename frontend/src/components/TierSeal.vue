<script setup lang="ts">
import type { Tier } from '@/api/types'
import { romanLevel } from '@/utils/format'

/**
 * Тир в виде сургучной печати цвета тира.
 *
 * На печати — уровень римской цифрой: название тира может быть любой длины
 * и в круг не влезет. Название — в подсказке и рядом в тексте.
 */
withDefaults(defineProps<{ tier: Pick<Tier, 'name' | 'level' | 'color'>; size?: number }>(), {
  size: 34,
})
</script>

<template>
  <span
    class="seal"
    :style="{ '--seal': tier.color ?? '#8e2f1c', width: `${size}px`, height: `${size}px` }"
    :title="`Тир ${tier.name}`"
  >
    <span class="name">{{ romanLevel(tier.level) }}</span>
  </span>
</template>

<style scoped>
.seal {
  display: inline-grid;
  place-items: center;
  flex: none;
  /* Неровный край сургуча — радиусы чуть разные. */
  border-radius: 48% 52% 50% 46% / 50% 46% 54% 50%;
  background:
    radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.35), transparent 45%),
    radial-gradient(circle at 50% 50%, var(--seal) 55%, color-mix(in srgb, var(--seal), #000 35%));
  box-shadow:
    inset 0 0 0 2px color-mix(in srgb, var(--seal), #000 25%),
    inset 0 0 0 4px color-mix(in srgb, var(--seal), #fff 15%),
    0 1px 3px rgba(0, 0, 0, 0.35);
}

.name {
  max-width: 80%;
  overflow: hidden;
  color: #fff8e6;
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 0.95em;
  line-height: 1;
  white-space: nowrap;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.45);
}
</style>
