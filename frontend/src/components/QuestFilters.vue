<script setup lang="ts">
import { computed, ref } from 'vue'
import { NBadge, NButton, NCheckbox, NCollapseTransition, NInput, NSelect } from 'naive-ui'
import { useCatalogStore } from '@/stores/catalog'
import { activeFilterCount, type QuestFilters } from '@/utils/questFilters'

const filters = defineModel<QuestFilters>('filters', { required: true })
defineProps<{ shown: number; total: number }>()
defineEmits<{ reset: [] }>()

const catalog = useCatalogStore()

const count = computed(() => activeFilterCount(filters.value))
// Открыли доску по ссылке с фильтрами — сразу показываем, какие заданы.
const expanded = ref(count.value > 0)
const filtering = computed(() => count.value > 0 || filters.value.q.trim() !== '')

// Архивные тиры и категории тоже: у старых квестов они могут остаться.
const tierOptions = computed(() =>
  [...catalog.tiers].sort((a, b) => b.level - a.level).map((t) => ({ label: t.name, value: t.id })),
)
const categoryOptions = computed(() =>
  catalog.categories.map((c) => ({ label: c.name, value: c.id })),
)
const dueOptions = [
  { label: 'Любой срок', value: 'all' },
  { label: 'Срок вышел', value: 'overdue' },
  { label: 'До конца дня', value: 'today' },
  { label: 'На этой неделе', value: 'week' },
  { label: 'Без срока', value: 'none' },
]
const sortOptions = [
  { label: 'По сроку', value: 'due' },
  { label: 'По важности', value: 'tier' },
  { label: 'По награде', value: 'reward' },
]
</script>

<template>
  <div class="filters">
    <div class="bar">
      <NInput
        v-model:value="filters.q"
        clearable
        placeholder="Поиск по доске"
        class="search"
        size="small"
      />
      <NSelect v-model:value="filters.sort" :options="sortOptions" size="small" class="sort" />
      <NBadge :value="count" :show="count > 0">
        <NButton
          size="small"
          :type="expanded ? 'primary' : 'default'"
          secondary
          @click="expanded = !expanded"
        >
          Фильтры
        </NButton>
      </NBadge>
    </div>

    <NCollapseTransition :show="expanded">
      <div class="panel">
        <NSelect
          v-model:value="filters.tiers"
          :options="tierOptions"
          multiple
          clearable
          size="small"
          placeholder="Все тиры"
          max-tag-count="responsive"
        />
        <NSelect
          v-model:value="filters.categories"
          :options="categoryOptions"
          multiple
          clearable
          size="small"
          placeholder="Все категории"
          max-tag-count="responsive"
        />
        <NSelect v-model:value="filters.due" :options="dueOptions" size="small" />
        <NCheckbox v-model:checked="filters.onlyRecurring">Только повторяющиеся</NCheckbox>
      </div>
    </NCollapseTransition>

    <p v-if="filtering" class="summary">
      Найдено {{ shown }} из {{ total }} ·
      <button type="button" class="link-button" @click="$emit('reset')">сбросить</button>
    </p>
  </div>
</template>

<style scoped>
.filters {
  margin: 4px 0 12px;
}

.bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.search {
  flex: 1 1 200px;
}

.sort {
  width: 150px;
}

.panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  align-items: center;
  gap: 8px 12px;
  padding-top: 10px;
}

.summary {
  margin: 8px 0 0;
  color: var(--color-muted);
  font-size: 0.875rem;
  font-style: italic;
}
</style>
