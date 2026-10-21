<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NAlert, NButton, NSelect, NSpin } from 'naive-ui'
import { api } from '@/api/client'
import type { Transaction, TransactionPage, TransactionType } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { formatDateTime, signed } from '@/utils/format'
import ManualTransactionModal from '@/components/ManualTransactionModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import AppIcon from '@/components/AppIcon.vue'
import HelpHint from '@/components/HelpHint.vue'

const PAGE_SIZE = 50

const TYPE_LABEL: Record<TransactionType, string> = {
  quest_reward: 'Награда за квест',
  penalty: 'Штраф гильдии',
  purchase: 'Заказ в таверне',
  manual: 'Поправка казначея',
  reversal: 'Отмена квеста',
}

const typeOptions = [
  { label: 'Все записи', value: 'all' },
  ...Object.entries(TYPE_LABEL).map(([value, label]) => ({ label, value })),
]

const items = ref<Transaction[]>([])
const total = ref(0)
const filter = ref<TransactionType | 'all'>('all')
const loading = ref(false)
const error = ref<string | null>(null)
const manualModal = ref(false)

async function load(reset: boolean) {
  loading.value = true
  error.value = null
  const params = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String(reset ? 0 : items.value.length),
  })
  if (filter.value !== 'all') params.set('type', filter.value)
  try {
    const page = await api.get<TransactionPage>(`/transactions?${params}`)
    items.value = reset ? page.items : [...items.value, ...page.items]
    total.value = page.total
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => load(true))
</script>

<template>
  <div class="title-row">
    <div>
      <h1 class="page-title">
        Летопись
        <HelpHint
          text="Все движения золота: награды, штрафы, заказы и отмены. Ошиблись — «Поправка» добавит или спишет вручную, с комментарием."
        />
      </h1>
      <p class="page-subtitle">Каждый золотой на счету</p>
    </div>
    <NButton size="small" @click="manualModal = true">Поправка</NButton>
  </div>
  <div class="flourish"><AppIcon name="sparkle" :size="14" /></div>

  <NSelect
    v-model:value="filter"
    :options="typeOptions"
    class="filter"
    @update:value="load(true)"
  />

  <NAlert v-if="error" type="error">{{ error }}</NAlert>
  <NSpin v-else :show="loading && !items.length">
    <EmptyState
      v-if="!loading && !items.length"
      art="chronicle"
      text="Страницы летописи пока чисты"
    />
    <ul class="list">
      <li v-for="t in items" :key="t.id">
        <div class="text">
          <div class="title">{{ t.title ?? TYPE_LABEL[t.type] }}</div>
          <div class="muted">
            <span v-if="t.title">{{ TYPE_LABEL[t.type] }} · </span
            >{{ formatDateTime(t.created_at) }}
          </div>
          <div v-if="t.note" class="note">{{ t.note }}</div>
        </div>
        <div class="amounts num">
          <span class="amount" :class="t.amount > 0 ? 'plus' : 'minus'">{{
            signed(t.amount)
          }}</span>
          <span class="muted">в кошеле {{ t.balance_after }}</span>
        </div>
      </li>
    </ul>
    <NButton
      v-if="items.length < total"
      block
      quaternary
      :loading="loading"
      class="more"
      @click="load(false)"
    >
      Показать ещё ({{ total - items.length }})
    </NButton>
  </NSpin>

  <ManualTransactionModal v-model:show="manualModal" @saved="load(true)" />
</template>

<style scoped>
.title-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.filter {
  max-width: 240px;
  margin-bottom: 8px;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--color-rule);
}

.text {
  min-width: 0;
}

.title {
  font-family: var(--font-heading);
  font-size: 1.15rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.note {
  margin-top: 2px;
  font-size: 0.875rem;
  font-style: italic;
  overflow-wrap: anywhere;
}

.amounts {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex: none;
}

.amount {
  font-size: 1.1rem;
  font-weight: 700;
}

.amount.plus {
  color: var(--color-ok);
}

.amount.minus {
  color: var(--color-error);
}

.muted {
  color: var(--color-muted);
  font-size: 0.875rem;
}

.more {
  margin-top: 8px;
}
</style>
