<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NAlert, NButton, NSpin, useDialog, useMessage } from 'naive-ui'
import type { Reward } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useAuthStore } from '@/stores/auth'
import { useCatalogStore } from '@/stores/catalog'
import { useArchiveToggle } from '@/composables/useArchiveToggle'
import { coins } from '@/utils/format'
import CatalogSection from '@/components/CatalogSection.vue'
import CoinIcon from '@/components/CoinIcon.vue'
import RewardFormModal from '@/components/RewardFormModal.vue'

const auth = useAuthStore()
const catalog = useCatalogStore()
const toggleArchive = useArchiveToggle()
const dialog = useDialog()
const message = useMessage()

const balance = computed(() => auth.user?.balance ?? 0)
const buyingId = ref<number | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const modal = ref(false)
const edited = ref<Reward | null>(null)

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

function buy(reward: Reward) {
  dialog.info({
    title: 'Заказать?',
    content: `«${reward.name}» за ${coins(reward.price)}. В кошеле останется ${coins(balance.value - reward.price)}.`,
    positiveText: 'Заказать',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      buyingId.value = reward.id
      try {
        await catalog.purchase(reward.id)
        message.success(`«${reward.name}» — ваше. Славного отдыха, путник!`)
      } catch (e) {
        message.error(errorMessage(e))
        await auth.fetchMe().catch(() => {})
      } finally {
        buyingId.value = null
      }
    },
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
      :items="catalog.rewards"
      add-label="Добавить в меню"
      empty-text="Меню пустует. Впишите то, ради чего стоит браться за квесты"
      @add="open(null)"
      @edit="open"
      @toggle-archive="
        (reward) =>
          toggleArchive(reward, (is_archived) => catalog.saveReward(reward.id, { is_archived }))
      "
    >
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
          @click="buy(reward)"
        >
          Заказать
        </NButton>
      </template>
    </CatalogSection>
  </NSpin>

  <RewardFormModal v-model:show="modal" :reward="edited" />
</template>

<style scoped>
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
