<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NSpin } from 'naive-ui'
import { api } from '@/api/client'
import type { CalendarData, ForecastQuest, Quest } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useQuestActions, useQuestNow } from '@/composables/useQuestActions'
import { useAuthStore } from '@/stores/auth'
import { useCatalogStore } from '@/stores/catalog'
import { useQuestsStore } from '@/stores/quests'
import { addMonths, groupByDay, monthGrid, type DayItems } from '@/utils/calendar'
import { dueLabel } from '@/utils/format'
import { dayKey } from '@/utils/today'
import CoinIcon from '@/components/CoinIcon.vue'
import QuestCard from '@/components/QuestCard.vue'
import QuestFormModal from '@/components/QuestFormModal.vue'
import TierSeal from '@/components/TierSeal.vue'
import AppIcon from '@/components/AppIcon.vue'
import HelpHint from '@/components/HelpHint.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const catalog = useCatalogStore()
const quests = useQuestsStore()
const { busyId, complete, fail, archive } = useQuestActions()
const now = useQuestNow()

const timezone = computed(() => auth.user?.timezone ?? 'UTC')
const todayKey = computed(() => dayKey(now.value, timezone.value))

// Месяц — в адресе: календарь на ноябре переживает перезагрузку.
const month = computed(() => {
  const value = route.query.month
  return typeof value === 'string' && /^\d{4}-\d{2}$/.test(value)
    ? value
    : todayKey.value.slice(0, 7)
})
const selected = ref(todayKey.value)

function goMonth(offset: number) {
  const next = addMonths(month.value, offset)
  router.replace({ query: { ...route.query, month: next } }).catch(() => {})
  // Выбранный день переносим в новый месяц: сегодня, если он там, иначе первое число.
  selected.value = todayKey.value.startsWith(next) ? todayKey.value : `${next}-01`
}

function goToday() {
  router.replace({ query: { ...route.query, month: undefined } }).catch(() => {})
  selected.value = todayKey.value
}

const grid = computed(() => monthGrid(month.value))
const loading = ref(false)
const loadError = ref<string | null>(null)
const data = ref<CalendarData>({ quests: [], forecast: [] })

async function load() {
  loading.value = true
  try {
    const cells = grid.value
    const [first, last] = [cells[0]!.key, cells[cells.length - 1]!.key]
    data.value = await api.get<CalendarData>(`/calendar?start=${first}&end=${last}`)
    loadError.value = null
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

catalog.load().catch(() => {})
watch(month, load, { immediate: true })
// Квест сдали, провалили или изменили прямо отсюда — перечитываем месяц.
watch(() => quests.active, load)

const days = computed(() => groupByDay(data.value.quests, data.value.forecast, timezone.value))
const EMPTY: DayItems = { quests: [], forecast: [] }
const selectedItems = computed(() => days.value.get(selected.value) ?? EMPTY)

const tierOf = (id: number) => catalog.tiers.find((t) => t.id === id)
const categoryOf = (quest: Quest) => catalog.categories.find((c) => c.id === quest.category_id)

const MAX_MARKS = 4

/** Отметки в ячейке: цвет тира у открытых, статус — у закрытых, кольцо — у прогноза. */
function marks(items: DayItems) {
  const all = [
    ...items.quests.map((q) => ({
      key: `q${q.id}`,
      kind: q.status,
      color: tierOf(q.tier_id)?.color ?? undefined,
    })),
    ...items.forecast.map((f) => ({
      key: `f${f.recurring_quest_id}-${f.period_date}`,
      kind: 'forecast',
      color: tierOf(f.tier_id)?.color ?? undefined,
    })),
  ]
  return { shown: all.slice(0, MAX_MARKS), more: Math.max(all.length - MAX_MARKS, 0) }
}

const monthTitle = computed(() =>
  new Intl.DateTimeFormat('ru', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(
    new Date(`${month.value}-01T00:00:00Z`),
  ),
)
const selectedTitle = computed(() =>
  new Intl.DateTimeFormat('ru', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: 'UTC',
  }).format(new Date(`${selected.value}T00:00:00Z`)),
)
const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

const modal = ref(false)
const edited = ref<Quest | null>(null)
function open(quest: Quest) {
  edited.value = quest
  modal.value = true
}

const forecastLabel = (item: ForecastQuest) => dueLabel(item.due_at, now.value).text
</script>

<template>
  <h1 class="page-title">
    Календарь
    <HelpHint
      text="Точки — квесты по сроку: цвет тира у открытых, зелёная — сдан, красная — провален. Кольцо — повторяющийся квест, который ещё появится. Нажмите на день, чтобы увидеть список."
    />
  </h1>
  <p class="page-subtitle">Сроки квестов и что появится по расписанию</p>
  <div class="flourish"><AppIcon name="sparkle" :size="14" /></div>

  <div class="month-bar">
    <NButton quaternary size="small" aria-label="Предыдущий месяц" @click="goMonth(-1)">
      ‹
    </NButton>
    <h2 class="month-title">{{ monthTitle }}</h2>
    <NButton quaternary size="small" aria-label="Следующий месяц" @click="goMonth(1)"> › </NButton>
    <NButton size="small" class="today-btn" @click="goToday">Сегодня</NButton>
  </div>

  <NAlert v-if="loadError" type="error">{{ loadError }}</NAlert>
  <NSpin v-else :show="loading">
    <div class="grid" role="grid">
      <div v-for="name in WEEKDAYS" :key="name" class="weekday">{{ name }}</div>
      <button
        v-for="cell in grid"
        :key="cell.key"
        type="button"
        class="cell"
        :class="{
          outside: cell.outside,
          today: cell.key === todayKey,
          selected: cell.key === selected,
          past: cell.key < todayKey,
        }"
        @click="selected = cell.key"
      >
        <span class="day num">{{ cell.day }}</span>
        <span v-if="days.get(cell.key)" class="marks">
          <span
            v-for="mark in marks(days.get(cell.key)!).shown"
            :key="mark.key"
            class="mark"
            :class="mark.kind"
            :style="{ '--tier': mark.color }"
          />
          <span v-if="marks(days.get(cell.key)!).more" class="more num">
            +{{ marks(days.get(cell.key)!).more }}
          </span>
        </span>
      </button>
    </div>

    <ul class="legend">
      <li><span class="mark active" /> открыт</li>
      <li><span class="mark completed" /> сдан</li>
      <li><span class="mark failed" /> провален</li>
      <li><span class="mark forecast" /> появится по расписанию</li>
    </ul>

    <section class="day-panel">
      <h3 class="day-title">{{ selectedTitle }}</h3>
      <p v-if="!selectedItems.quests.length && !selectedItems.forecast.length" class="empty">
        В этот день сроков нет.
      </p>
      <QuestCard
        v-for="quest in selectedItems.quests"
        :key="quest.id"
        :quest="quest"
        :tier="tierOf(quest.tier_id)"
        :category="categoryOf(quest)"
        :now="now"
        :busy="busyId === quest.id"
        @complete="complete(quest, $event)"
        @fail="fail(quest)"
        @edit="open(quest)"
        @archive="archive(quest)"
      />
      <ul v-if="selectedItems.forecast.length" class="forecast">
        <li
          v-for="item in selectedItems.forecast"
          :key="`${item.recurring_quest_id}-${item.period_date}`"
        >
          <TierSeal v-if="tierOf(item.tier_id)" :tier="tierOf(item.tier_id)!" :size="26" />
          <span class="forecast-name"
            ><AppIcon name="repeat" :size="16" class="repeat" /> {{ item.name }}</span
          >
          <span class="forecast-reward num"><CoinIcon :size="14" /> +{{ item.reward }}</span>
          <span class="forecast-when">появится · {{ forecastLabel(item) }}</span>
        </li>
      </ul>
    </section>
  </NSpin>

  <QuestFormModal v-model:show="modal" :quest="edited" />
</template>

<style scoped>
.month-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
}

.month-title {
  min-width: 170px;
  margin: 0;
  font-size: 1.4rem;
  text-align: center;
}

.month-title::first-letter {
  text-transform: uppercase;
}

.today-btn {
  margin-left: auto;
}

.grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 3px;
}

.weekday {
  padding: 2px 0 4px;
  color: var(--color-muted);
  font-size: 0.8125rem;
  text-align: center;
}

.cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-height: 72px;
  padding: 4px 6px;
  border: 1px solid var(--color-rule);
  border-radius: 3px;
  background-color: var(--color-note);
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.cell:hover {
  border-color: var(--color-gold);
}

.cell.outside {
  opacity: 0.45;
}

.cell.past .day {
  color: var(--color-muted);
}

.cell.today {
  border-color: var(--color-gold);
  box-shadow: inset 0 0 0 1px var(--color-gold);
}

.cell.today .day {
  color: var(--color-gold);
  font-weight: 700;
}

.cell.selected {
  background-color: color-mix(in srgb, var(--color-gold), var(--color-note) 82%);
}

.day {
  font-size: 0.95rem;
}

.marks {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 3px;
}

.mark {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.mark.active {
  background: var(--tier, var(--color-gold));
}

.mark.completed {
  background: var(--color-ok);
}

.mark.failed {
  background: var(--color-error);
}

.mark.archived {
  background: var(--color-muted);
  opacity: 0.6;
}

.mark.forecast {
  border: 2px solid var(--tier, var(--color-gold));
  background: transparent;
}

.more {
  color: var(--color-muted);
  font-size: 0.75rem;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  margin: 8px 0 0;
  padding: 0;
  color: var(--color-muted);
  font-size: 0.8125rem;
  list-style: none;
}

.legend li {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend .mark.active {
  background: var(--color-gold);
}

.legend .mark.forecast {
  border-color: var(--color-gold);
}

.day-panel {
  margin-top: 20px;
}

.day-title {
  margin: 0 0 10px;
  font-size: 1.3rem;
}

.day-title::first-letter {
  text-transform: uppercase;
}

.empty {
  margin: 0;
  color: var(--color-muted);
  font-style: italic;
}

.forecast {
  margin: 0;
  padding: 0;
  list-style: none;
}

.forecast li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px dashed var(--color-border);
  border-radius: 2px;
  opacity: 0.85;
}

.repeat {
  color: var(--color-muted);
}

.forecast-name {
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.forecast-reward {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-gold);
  font-weight: 700;
}

.forecast-when {
  color: var(--color-muted);
  font-size: 0.875rem;
  font-style: italic;
}

/* На телефоне ячейки маленькие: только число и отметки. */
@media (max-width: 560px) {
  .grid {
    gap: 2px;
  }

  .cell {
    align-items: center;
    min-height: 48px;
    padding: 3px 2px;
  }

  .mark {
    width: 6px;
    height: 6px;
  }

  .mark.forecast {
    border-width: 1.5px;
  }

  .marks {
    justify-content: center;
    gap: 2px;
  }

  .month-title {
    min-width: 0;
    font-size: 1.2rem;
  }
}
</style>
