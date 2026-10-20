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
    title: 'Купить?',
    content: `«${reward.name}» за ${coins(reward.price)}. Останется ${coins(balance.value - reward.price)}.`,
    positiveText: 'Купить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      buyingId.value = reward.id
      try {
        await catalog.purchase(reward.id)
        message.success(`Куплено: «${reward.name}». Приятного отдыха!`)
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
  <h1>Траты</h1>
  <p class="intro">Развлечения, которые оплачиваются монетами за квесты.</p>
  <NAlert v-if="loadError" type="error">{{ loadError }}</NAlert>
  <NSpin v-else :show="loading">
    <CatalogSection
      :items="catalog.rewards"
      add-label="Добавить трату"
      empty-text="Трат пока нет — добавьте то, ради чего стоит выполнять квесты"
      @add="open(null)"
      @edit="open"
      @toggle-archive="
        (reward) =>
          toggleArchive(reward, (is_archived) => catalog.saveReward(reward.id, { is_archived }))
      "
    >
      <template #item="{ item: reward }">
        <div class="line">
          <div class="text">
            <div>{{ reward.name }}</div>
            <div v-if="reward.description" class="muted">{{ reward.description }}</div>
          </div>
          <div class="meta">
            <span class="price">{{ coins(reward.price) }}</span>
            <span v-if="reward.duration_minutes" class="muted"
              >{{ reward.duration_minutes }} мин</span
            >
          </div>
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
          Купить
        </NButton>
      </template>
    </CatalogSection>
  </NSpin>

  <RewardFormModal v-model:show="modal" :reward="edited" />
</template>

<style scoped>
h1 {
  margin: 0;
  font-size: 1.5rem;
}

.intro {
  margin: 4px 0 16px;
  color: var(--color-muted);
}

.line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.text {
  min-width: 0;
}

.meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex: none;
}

.price {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.muted {
  color: var(--color-muted);
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
</style>
