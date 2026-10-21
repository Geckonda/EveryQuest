<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { NAlert, NButton, NCollapse, NCollapseItem, NSpin } from 'naive-ui'
import { api } from '@/api/client'
import type { DaySummary, Quest } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useQuestActions, useQuestNow } from '@/composables/useQuestActions'
import { useAuthStore } from '@/stores/auth'
import { useCatalogStore } from '@/stores/catalog'
import { useQuestsStore } from '@/stores/quests'
import { useSessionsStore } from '@/stores/sessions'
import { signed } from '@/utils/format'
import { todayBoard } from '@/utils/today'
import CoinIcon from '@/components/CoinIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import QuestCard from '@/components/QuestCard.vue'
import QuestFormModal from '@/components/QuestFormModal.vue'
import SessionList from '@/components/SessionList.vue'
import AppIcon from '@/components/AppIcon.vue'

const auth = useAuthStore()
const catalog = useCatalogStore()
const quests = useQuestsStore()
const sessions = useSessionsStore()
const { busyId, complete, fail, archive } = useQuestActions()
const now = useQuestNow()

const loading = ref(true)
const loadError = ref<string | null>(null)
const summary = ref<DaySummary | null>(null)

const modal = ref(false)
const edited = ref<Quest | null>(null)

function open(quest: Quest | null) {
  edited.value = quest
  modal.value = true
}

async function loadSummary() {
  summary.value = await api.get<DaySummary>('/transactions/today')
}

onMounted(async () => {
  try {
    await Promise.all([catalog.load(), quests.loadActive(), loadSummary()])
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})

// Монеты пришли или ушли — итог дня устарел.
watch(
  () => auth.coinEvent?.id,
  () => loadSummary().catch(() => {}),
)

const timezone = computed(() => auth.user?.timezone ?? 'UTC')
const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone

const tierOf = (id: number) => catalog.tiers.find((t) => t.id === id)
const categoryOf = (quest: Quest) => catalog.categories.find((c) => c.id === quest.category_id)

const board = computed(() =>
  todayBoard(quests.active, now.value, timezone.value, (id) => tierOf(id)?.level ?? 0),
)

const dateTitle = computed(() =>
  new Intl.DateTimeFormat('ru', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: timezone.value,
  }).format(now.value),
)

const stats = computed(() => {
  const s = summary.value
  if (!s) return []
  return [
    { label: 'Заработано', value: s.earned, kind: 'gain', show: true },
    { label: 'Потрачено', value: -s.spent, kind: 'spend', show: true },
    { label: 'Штрафы', value: -s.penalties, kind: 'loss', show: s.penalties > 0 },
    { label: 'Поправки', value: s.manual, kind: 'manual', show: s.manual !== 0 },
  ].filter((stat) => stat.show)
})
</script>

<template>
  <div class="title-row">
    <div>
      <h1 class="page-title">Сегодня</h1>
      <p class="page-subtitle date">{{ dateTitle }}</p>
    </div>
    <NButton type="primary" :disabled="loading || !!loadError" @click="open(null)">
      Повесить квест
    </NButton>
  </div>
  <div class="flourish"><AppIcon name="sparkle" :size="14" /></div>

  <NAlert v-if="loadError" type="error">{{ loadError }}</NAlert>
  <NSpin v-else :show="loading">
    <p v-if="browserTimezone && browserTimezone !== timezone" class="tz-note">
      День считается по поясу профиля ({{ timezone }}), а устройство сейчас в {{ browserTimezone }}.
      <RouterLink to="/settings">Поменять в профиле</RouterLink>
    </p>

    <!-- Итог дня -->
    <div v-if="summary" class="stats">
      <div v-for="stat in stats" :key="stat.label" class="stat" :class="stat.kind">
        <span class="stat-label">{{ stat.label }}</span>
        <span class="stat-value num">{{ signed(stat.value) }}</span>
      </div>
      <div class="stat purse">
        <span class="stat-label">В кошеле</span>
        <span class="stat-value num"><CoinIcon :size="16" /> {{ auth.user?.balance ?? 0 }}</span>
      </div>
    </div>

    <section v-if="sessions.active.length" class="block session-block">
      <h2 class="block-title">Идёт сейчас</h2>
      <SessionList size="large" />
    </section>

    <section v-if="board.overdue.length" class="block">
      <h2 class="block-title late">Срок вышел</h2>
      <QuestCard
        v-for="quest in board.overdue"
        :key="quest.id"
        :quest="quest"
        :tier="tierOf(quest.tier_id)"
        :category="categoryOf(quest)"
        :now="now"
      />
    </section>

    <section class="block">
      <h2 class="block-title">
        На сегодня
        <span v-if="board.today.length" class="count">({{ board.today.length }})</span>
      </h2>
      <EmptyState
        v-if="!board.today.length"
        art="rest"
        :text="
          board.noDue.length
            ? 'На сегодня квестов со сроком нет — можно взяться за побочный ниже.'
            : 'На сегодня квестов со сроком нет. Отдыхайте — или повесьте новый.'
        "
        compact
      >
        <RouterLink to="/quests" class="board-link">Вся доска</RouterLink>
      </EmptyState>
      <QuestCard
        v-for="quest in board.today"
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
    </section>

    <NCollapse v-if="board.noDue.length" class="block">
      <NCollapseItem name="side" :title="`Без срока (${board.noDue.length})`">
        <QuestCard
          v-for="quest in board.noDue"
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
      </NCollapseItem>
    </NCollapse>
  </NSpin>

  <QuestFormModal v-model:show="modal" :quest="edited" />
</template>

<style scoped>
.title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.date::first-letter {
  text-transform: uppercase;
}

.tz-note {
  margin: 0 0 12px;
  color: var(--color-muted);
  font-size: 0.875rem;
  font-style: italic;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 3px;
  background-color: var(--color-note);
  background-image: var(--paper-grain);
}

.stat-label {
  color: var(--color-muted);
  font-size: 0.8125rem;
}

.stat-value {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 1.35rem;
  font-weight: 700;
}

.gain .stat-value,
.purse .stat-value {
  color: var(--color-gold);
}

.loss .stat-value {
  color: var(--color-error);
}

.block {
  margin-top: 20px;
}

.block-title {
  margin: 0 0 10px;
  font-size: 1.4rem;
}

.block-title.late {
  color: var(--color-error);
}

.count {
  color: var(--color-muted);
  font-size: 1rem;
}

.session-block {
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: 3px;
  background-color: var(--color-note);
  background-image: var(--paper-grain);
  box-shadow: var(--shadow-note);
}

.board-link {
  margin-top: 6px;
  color: var(--color-gold);
}
</style>
