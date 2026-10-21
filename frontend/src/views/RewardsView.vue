<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { NAlert, NButton, NCheckbox, NInput, NSelect, NSpin, useDialog, useMessage } from 'naive-ui'
import type { Reward } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useAuthStore } from '@/stores/auth'
import { useCatalogStore } from '@/stores/catalog'
import { useSessionsStore } from '@/stores/sessions'
import { useArchiveToggle } from '@/composables/useArchiveToggle'
import { coins, formatTime } from '@/utils/format'
import { DEFAULT_REWARD_FILTERS, filterRewards } from '@/utils/rewardFilters'
import { flyCoins, purseElement } from '@/utils/coinFx'
import CatalogSection from '@/components/CatalogSection.vue'
import CoinIcon from '@/components/CoinIcon.vue'
import RewardFormModal from '@/components/RewardFormModal.vue'

const auth = useAuthStore()
const catalog = useCatalogStore()
const sessions = useSessionsStore()
const toggleArchive = useArchiveToggle()
const dialog = useDialog()
const message = useMessage()

const balance = computed(() => auth.user?.balance ?? 0)
const buyingId = ref<number | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const modal = ref(false)
const edited = ref<Reward | null>(null)

const filters = reactive({ ...DEFAULT_REWARD_FILTERS })
const visible = computed(() => filterRewards(catalog.rewards, filters, balance.value))
const filtering = computed(() => filters.q.trim() !== '' || filters.onlyAffordable)
const sortOptions = [
  { label: 'Как в меню', value: 'menu' },
  { label: 'Сначала дешёвые', value: 'cheap' },
  { label: 'Сначала дорогие', value: 'expensive' },
  { label: 'По названию', value: 'name' },
]

onMounted(async () => {
  try {
    await catalog.load()
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})

function open(reward: Reward | null) {
  edited.value = reward
  modal.value = true
}

function buy(reward: Reward, event: MouseEvent) {
  // Запоминаем кнопку до диалога: к ней из кошелька полетят монеты.
  const button = event.currentTarget as Element | null
  const afford = `«${reward.name}» за ${coins(reward.price)}. В кошеле останется ${coins(balance.value - reward.price)}.`

  async function order(queue: boolean) {
    buyingId.value = reward.id
    try {
      const { session } = await catalog.purchase(reward.id, queue)
      flyCoins(purseElement(), button)
      message.success(
        session && new Date(session.started_at) > new Date()
          ? `«${reward.name}» в очереди — начнётся в ${formatTime(session.started_at)}`
          : `«${reward.name}» — ваше. Славного отдыха, путник!`,
      )
    } catch (e) {
      message.error(errorMessage(e))
      await auth.fetchMe().catch(() => {})
    } finally {
      buyingId.value = null
    }
  }

  // У траты со временем, пока идёт другая, — выбор: в очередь или параллельно.
  const busyUntil = reward.duration_minutes ? sessions.queueEnd() : null
  if (busyUntil) {
    dialog.info({
      title: 'Заказать?',
      content: `${afford} Сейчас уже идёт отдых — до ${formatTime(busyUntil)}. Начать «${reward.name}» после него или прямо сейчас, параллельно?`,
      positiveText: `После, в ${formatTime(busyUntil)}`,
      negativeText: 'Сейчас, параллельно',
      // Цвет кнопки — основной темы, а не синий «информационный».
      positiveButtonProps: { type: 'primary' },
      onPositiveClick: () => order(true),
      onNegativeClick: () => order(false),
    })
    return
  }

  dialog.info({
    title: 'Заказать?',
    content: afford,
    positiveText: 'Заказать',
    negativeText: 'Отмена',
    positiveButtonProps: { type: 'primary' },
    onPositiveClick: () => order(true),
  })
}
</script>

<template>
  <h1 class="page-title">Таверна</h1>
  <p class="page-subtitle">Отдых и развлечения за честно заработанное золото</p>
  <div class="flourish">✦</div>
  <NAlert v-if="loadError" type="error">{{ loadError }}</NAlert>
  <NSpin v-else :show="loading">
    <CatalogSection
      :items="visible"
      add-label="Добавить в меню"
      :empty-text="
        filtering
          ? 'Ничего не нашлось — попробуйте другой запрос'
          : 'Меню пустует. Впишите то, ради чего стоит браться за квесты'
      "
      @add="open(null)"
      @edit="open"
      @toggle-archive="
        (reward) =>
          toggleArchive(reward, (is_archived) => catalog.saveReward(reward.id, { is_archived }))
      "
    >
      <template v-if="catalog.rewards.length" #toolbar>
        <div class="tools">
          <NInput
            v-model:value="filters.q"
            clearable
            size="small"
            placeholder="Поиск по меню"
            class="search"
          />
          <NSelect v-model:value="filters.sort" :options="sortOptions" size="small" class="sort" />
          <NCheckbox v-model:checked="filters.onlyAffordable">По карману</NCheckbox>
        </div>
      </template>
      <template #item="{ item: reward }">
        <!-- Строка меню: название ········ цена -->
        <div class="line">
          <span class="name">{{ reward.name }}</span>
          <span class="leader" aria-hidden="true" />
          <span class="price num"><CoinIcon :size="15" /> {{ reward.price }}</span>
        </div>
        <div v-if="reward.description || reward.duration_minutes" class="muted">
          {{ reward.description }}
          <span v-if="reward.duration_minutes">
            {{ reward.description ? '·' : '' }} {{ reward.duration_minutes }} мин
          </span>
        </div>
      </template>
      <template #actions="{ item: reward }">
        <NButton
          size="small"
          type="primary"
          secondary
          :disabled="balance < reward.price"
          :title="balance < reward.price ? `Не хватает ${reward.price - balance}` : undefined"
          :loading="buyingId === reward.id"
          @click="buy(reward, $event)"
        >
          Заказать
        </NButton>
      </template>
    </CatalogSection>
  </NSpin>

  <RewardFormModal v-model:show="modal" :reward="edited" />
</template>

<style scoped>
.tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin-bottom: 4px;
}

.search {
  flex: 1 1 200px;
}

.sort {
  width: 170px;
}

/* Длинное название не влезает — точки и цена переносятся на следующую строку. */
.line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px;
}

.name {
  font-family: var(--font-heading);
  font-size: 1.25rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

/* Точки от названия до цены, как в меню. */
.leader {
  flex: 1;
  min-width: 16px;
  border-bottom: 2px dotted var(--color-border);
  transform: translateY(-4px);
}

.price {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-gold);
  font-weight: 700;
  white-space: nowrap;
}

.muted {
  color: var(--color-muted);
  font-size: 0.875rem;
  font-style: italic;
  overflow-wrap: anywhere;
}
</style>
