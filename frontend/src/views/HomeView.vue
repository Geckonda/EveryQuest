<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NAlert, NCard, NSpin, NTag } from 'naive-ui'
import { api } from '@/api/client'
import type { Category, Tier } from '@/api/types'

const tiers = ref<Tier[]>([])
const categories = ref<Category[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    ;[tiers.value, categories.value] = await Promise.all([
      api.get<Tier[]>('/tiers'),
      api.get<Category[]>('/categories'),
    ])
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Не удалось загрузить данные'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <NSpin :show="loading">
    <NAlert v-if="error" type="error">{{ error }}</NAlert>
    <div v-else class="grid">
      <NCard title="Тиры" size="small">
        <ul class="list">
          <li v-for="tier in tiers" :key="tier.id">
            <NTag :color="{ color: tier.color ?? undefined, textColor: '#fff' }" size="small">
              {{ tier.name }}
            </NTag>
            <span class="reward">+{{ tier.default_reward }}</span>
            <span class="penalty">−{{ tier.default_penalty }}</span>
          </li>
        </ul>
      </NCard>
      <NCard title="Категории" size="small">
        <ul class="list">
          <li v-for="category in categories" :key="category.id">
            <span class="dot" :style="{ background: category.color ?? 'currentColor' }" />
            <div>
              <div>{{ category.name }}</div>
              <div v-if="category.description" class="muted">{{ category.description }}</div>
            </div>
          </li>
        </ul>
      </NCard>
    </div>
  </NSpin>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.list li {
  display: flex;
  align-items: center;
  gap: 10px;
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
}
</style>
