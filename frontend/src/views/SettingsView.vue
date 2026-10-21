<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NAlert, NSpin, NTabPane, NTabs } from 'naive-ui'
import type { Category, Tier } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { useArchiveToggle } from '@/composables/useArchiveToggle'
import { tierLabel } from '@/utils/format'
import CatalogSection from '@/components/CatalogSection.vue'
import CoinIcon from '@/components/CoinIcon.vue'
import TierSeal from '@/components/TierSeal.vue'
import TierFormModal from '@/components/TierFormModal.vue'
import CategoryFormModal from '@/components/CategoryFormModal.vue'
import ProfileSection from '@/components/ProfileSection.vue'
import AppIcon from '@/components/AppIcon.vue'
import HelpHint from '@/components/HelpHint.vue'

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
  <h1 class="page-title">
    Настройки
    <HelpHint
      text="Тиры — уровни важности квестов и их награда. Категории — сферы жизни для фильтров. В профиле — часовой пояс, множитель штрафа, тема, звук и устройства."
    />
  </h1>
  <p class="page-subtitle">Устав гильдии: тиры квестов и их награды, категории дел, профиль</p>
  <div class="flourish"><AppIcon name="sparkle" :size="14" /></div>
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
              <TierSeal :tier="tier" />
              <span v-if="tierLabel(tier)" class="tier-name">{{ tierLabel(tier) }}</span>
              <span class="reward num"><CoinIcon :size="14" /> +{{ tier.default_reward }}</span>
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

      <NTabPane name="profile" tab="Профиль">
        <ProfileSection />
      </NTabPane>
    </NTabs>
  </NSpin>

  <TierFormModal v-model:show="tierModal" :tier="editedTier" />
  <CategoryFormModal v-model:show="categoryModal" :category="editedCategory" />
</template>

<style scoped>
.line {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.text {
  min-width: 0;
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 700;
}

.tier-name {
  min-width: 0;
  overflow: hidden;
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reward {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-gold);
  font-weight: 700;
}

.dot {
  flex: none;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.muted {
  color: var(--color-muted);
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-style: italic;
  font-weight: 400;
  overflow-wrap: anywhere;
}
</style>
