<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NAlert, NSpin } from 'naive-ui'
import type { Reward } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { useArchiveToggle } from '@/composables/useArchiveToggle'
import CatalogSection from '@/components/CatalogSection.vue'
import RewardFormModal from '@/components/RewardFormModal.vue'

const catalog = useCatalogStore()
const toggleArchive = useArchiveToggle()

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
            <span class="price">{{ reward.price }} монет</span>
            <span v-if="reward.duration_minutes" class="muted"
              >{{ reward.duration_minutes }} мин</span
            >
          </div>
        </div>
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
