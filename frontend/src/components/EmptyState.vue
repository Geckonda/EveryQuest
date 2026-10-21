<script setup lang="ts">
/**
 * Пустое состояние с рисунком в стиле таверны. Линии — приглушённым цветом текста,
 * акценты — золотом; подходит к обеим темам.
 */
export type EmptyArt =
  'board' | 'tavern' | 'archive' | 'chronicle' | 'recurring' | 'search' | 'rest'

withDefaults(defineProps<{ art: EmptyArt; text: string; compact?: boolean }>(), {
  compact: false,
})
</script>

<template>
  <div class="empty-state" :class="{ compact }">
    <svg class="art" viewBox="0 0 120 90" aria-hidden="true" focusable="false">
      <g
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <!-- Пустая доска объявлений: только гвоздик и место под квест. -->
        <template v-if="art === 'board'">
          <rect x="18" y="12" width="84" height="58" rx="3" />
          <rect x="26" y="20" width="68" height="42" rx="1" stroke-dasharray="4 5" opacity="0.45" />
          <path d="M30 70v12M90 70v12" />
          <circle cx="60" cy="12" r="3.5" class="gold-fill" />
        </template>

        <!-- Пустая кружка — меню таверны пустует. -->
        <template v-else-if="art === 'tavern'">
          <path d="M40 32h34v36a6 6 0 0 1-6 6H46a6 6 0 0 1-6-6z" />
          <path d="M74 40h7a8 8 0 0 1 0 16h-7" />
          <path d="M50 42v22M64 42v22" opacity="0.45" />
          <path d="M32 80h50" opacity="0.45" />
          <path d="M57 12c3.5 4.5 3.5 8 0 10.5-3.5-2.5-3.5-6 0-10.5z" class="gold-fill" />
        </template>

        <!-- Закрытый сундук — архив пока пуст. -->
        <template v-else-if="art === 'archive'">
          <path d="M30 40c0-12 8-18 30-18s30 6 30 18" />
          <rect x="30" y="40" width="60" height="32" rx="2" />
          <path d="M30 52h25M65 52h25" opacity="0.45" />
          <rect x="55" y="46" width="10" height="12" rx="1.5" class="gold-fill" />
          <path d="M24 78h72" opacity="0.45" />
        </template>

        <!-- Раскрытая чистая книга и перо — летопись ещё не начата. -->
        <template v-else-if="art === 'chronicle'">
          <path d="M60 30c-8-6-20-8-36-6v46c16-2 28 0 36 6 8-6 20-8 36-6V24c-16-2-28 0-36 6z" />
          <path d="M60 30v46" />
          <path d="M32 36c8-1 15 0 20 2M32 46c8-1 15 0 20 2" opacity="0.35" />
          <path d="M94 8c-9 4-16 13-19 24l2.5 1c4-9 10-15 18-19z" class="gold-fill" />
        </template>

        <!-- Песочные часы и стрелки по кругу — повторяющиеся. -->
        <template v-else-if="art === 'recurring'">
          <path d="M48 16h24M48 74h24" />
          <path d="M50 16c0 14 20 17 20 29s-20 15-20 29M70 16c0 14-20 17-20 29s20 15 20 29" />
          <path d="M53 70h14l-7-7z" class="gold-fill" />
          <path d="M32 50a29 29 0 0 1 10-28M88 40a29 29 0 0 1-10 28" />
          <path d="M37 21l5 1-1 5M83 69l-5-1 1-5" />
        </template>

        <!-- Лупа над свитком — поиск ничего не нашёл. -->
        <template v-else-if="art === 'search'">
          <path d="M28 18h40a6 6 0 0 1 6 6v8M74 66H34a6 6 0 0 1-6-6V18" />
          <path d="M36 30h26M36 40h18M36 50h12" opacity="0.4" />
          <circle cx="76" cy="54" r="13" />
          <path d="M85.5 63.5 98 76" class="gold-stroke" stroke-width="4" />
        </template>

        <!-- Свеча и звёзды — на сегодня дел нет, можно отдыхать. -->
        <template v-else>
          <path d="M53 42h14v30H53z" />
          <path d="M60 42v-4" />
          <path d="M44 74h32" />
          <path d="M60 18c5 6 5 11.5 0 16-5-4.5-5-10 0-16z" class="gold-fill" />
          <path d="M28 26v6M25 29h6M90 18v6M87 21h6M94 44v4M92 46h4" opacity="0.55" />
        </template>
      </g>
    </svg>
    <p class="text">{{ text }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 12px;
  color: var(--color-muted);
  text-align: center;
}

.empty-state.compact {
  padding: 12px;
}

.art {
  width: 120px;
  height: 90px;
  margin-bottom: 8px;
  opacity: 0.85;
}

.compact .art {
  width: 84px;
  height: 63px;
}

.gold-fill {
  fill: var(--color-gold);
  stroke: none;
}

.gold-stroke {
  stroke: var(--color-gold);
}

.text {
  max-width: 340px;
  margin: 0;
  font-style: italic;
}
</style>
