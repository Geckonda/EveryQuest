<script setup lang="ts">
/**
 * Линейные иконки приложения: одна толщина линии, без библиотеки.
 * Рисуются цветом текста (currentColor) — подходят к обеим темам и вывеске.
 */
export type IconName =
  | 'today'
  | 'quests'
  | 'calendar'
  | 'tavern'
  | 'chronicle'
  | 'settings'
  | 'hourglass'
  | 'repeat'
  | 'sparkle'

withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 20 })

/** Контуры 24×24; fill: true — залитая фигура вместо линии. */
const ICONS: Record<IconName, { d: string; fill?: boolean }> = {
  // Свеча: «сегодня» — то, что горит прямо сейчас.
  today: {
    d: 'M9 10h6v10a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1zM12 10V8M12 3c1.6 1.7 1.6 3.3 0 5-1.6-1.7-1.6-3.3 0-5zM7 21h10',
  },
  // Свиток с объявлениями.
  quests: {
    d: 'M7 4h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2zM7 4a2 2 0 0 0-2 2v2h2M10 9h6M10 12.5h6M10 16h3.5',
  },
  calendar: {
    d: 'M5 6h14a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zM4 10.5h16M8.5 3.5v4M15.5 3.5v4M8 14h2M14 14h2M8 17h2',
  },
  // Кружка эля, как в эмблеме.
  tavern: {
    d: 'M5 7h10v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2zM15 10h2.5a2.5 2.5 0 0 1 0 5H15M4.5 7.5c0-2 1.6-3 3-2.5.6-1.4 2.6-1.8 3.6-.6 1.2-.8 3.6-.2 3.6 1.9M8.5 11v5M11.5 11v5',
  },
  // Летопись — раскрытая книга.
  chronicle: {
    d: 'M12 6.5C10.5 5 8 4.5 4 5v13c4-.5 6.5 0 8 1.5 1.5-1.5 4-2 8-1.5V5c-4-.5-6.5 0-8 1.5zM12 6.5v13',
  },
  settings: {
    d: 'M4 7h9M17 7h3M4 17h3M11 17h9M15 5v4M9 15v4',
  },
  hourglass: {
    d: 'M6.5 3h11M6.5 21h11M8 3c0 4.5 8 5.5 8 9s-8 4.5-8 9M16 3c0 4.5-8 5.5-8 9s8 4.5 8 9M10 18.5h4',
  },
  repeat: {
    d: 'M16.5 3.5 19.5 6.5 16.5 9.5M4.5 11.5V10a3.5 3.5 0 0 1 3.5-3.5h11.5M7.5 20.5 4.5 17.5 7.5 14.5M19.5 12.5V14a3.5 3.5 0 0 1-3.5 3.5H4.5',
  },
  // Четырёхлучевая звёздочка — украшение под заголовком.
  sparkle: {
    d: 'M12 3c.6 4.6 2.4 6.4 7 7-4.6.6-6.4 2.4-7 7-.6-4.6-2.4-6.4-7-7 4.6-.6 6.4-2.4 7-7z',
    fill: true,
  },
}
</script>

<template>
  <svg
    class="icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    aria-hidden="true"
    focusable="false"
  >
    <path
      :d="ICONS[name].d"
      :fill="ICONS[name].fill ? 'currentColor' : 'none'"
      :stroke="ICONS[name].fill ? 'none' : 'currentColor'"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>

<style scoped>
.icon {
  display: inline-block;
  flex: none;
  vertical-align: -0.2em;
}
</style>
