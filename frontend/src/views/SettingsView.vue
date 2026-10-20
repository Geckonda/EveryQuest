<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NAlert, NSpin, NTabPane, NTabs, NTag } from 'naive-ui'
import type { Category, Tier } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { useArchiveToggle } from '@/composables/useArchiveToggle'
import CatalogSection from '@/components/CatalogSection.vue'
import TierFormModal from '@/components/TierFormModal.vue'
import CategoryFormModal from '@/components/CategoryFormModal.vue'

const catalog = useCatalogStore()
const toggleArchive = useArchiveToggle()

const loading = ref(true)
const loadError = ref<string | null>(null)

const tierModal = ref(false)
const editedTier = ref<Tier | null>(null)
const categoryModal = ref(false)
const editedCategory = ref<Category | null>(null)

onMounted(async () => {
  try {
    await catalog.load()
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})

function openTier(tier: Tier | null) {
  editedTier.value = tier
  tierModal.value = true
}

function openCategory(category: Category | null) {
  editedCategory.value = category
  categoryModal.value = true
}
</script>

<template>
  <h1>Настройки</h1>
  <NAlert v-if="loadError" type="error">{{ loadError }}</NAlert>
  <NSpin v-else :show="loading">
    <NTabs type="line" animated>
      <NTabPane name="tiers" tab="Тиры">
        <CatalogSection
          :items="catalog.tiers"
          add-label="Добавить тир"
          empty-text="Тиров нет"
          @add="openTier(null)"
          @edit="openTier"
          @toggle-archive="
            (tier) =>
              toggleArchive(tier, (is_archived) => catalog.saveTier(tier.id, { is_archived }))
          "
        >
          <template #item="{ item: tier }">
            <div class="line">
              <NTag :color="{ color: tier.color ?? undefined, textColor: '#fff' }" size="small">
                {{ tier.name }}
              </NTag>
              <span class="reward">+{{ tier.default_reward }}</span>
              <span class="penalty">−{{ tier.default_penalty }}</span>
            </div>
          </template>
        </CatalogSection>
      </NTabPane>

      <NTabPane name="categories" tab="Категории">
        <CatalogSection
          :items="catalog.categories"
          add-label="Добавить категорию"
          empty-text="Категорий нет"
          @add="openCategory(null)"
          @edit="openCategory"
          @toggle-archive="
            (category) =>
              toggleArchive(category, (is_archived) =>
                catalog.saveCategory(category.id, { is_archived }),
              )
          "
        >
          <template #item="{ item: category }">
            <div class="line">
              <span class="dot" :style="{ background: category.color ?? 'currentColor' }" />
              <div class="text">
                <div>{{ category.name }}</div>
                <div v-if="category.description" class="muted">{{ category.description }}</div>
              </div>
            </div>
          </template>
        </CatalogSection>
      </NTabPane>
    </NTabs>
  </NSpin>

  <TierFormModal v-model:show="tierModal" :tier="editedTier" />
  <CategoryFormModal v-model:show="categoryModal" :category="editedCategory" />
</template>

<style scoped>
h1 {
  margin: 0 0 12px;
  font-size: 1.5rem;
}

.line {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.text {
  min-width: 0;
}

.reward {
  color: var(--color-ok);
  font-variant-numeric: tabular-nums;
}

.penalty {
  color: var(--color-error);
  font-variant-numeric: tabular-nums;
}

.dot {
  flex: none;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.muted {
  color: var(--color-muted);
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
</style>
