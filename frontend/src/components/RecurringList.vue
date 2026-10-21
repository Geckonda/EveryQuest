<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import type { RecurringQuest } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { useRecurringStore } from '@/stores/recurring'
import { useArchiveToggle } from '@/composables/useArchiveToggle'
import { dueLabel } from '@/utils/format'
import { describeSchedule } from '@/utils/schedule'
import CatalogSection from './CatalogSection.vue'
import CoinIcon from './CoinIcon.vue'
import TierSeal from './TierSeal.vue'
import RecurringFormModal from './RecurringFormModal.vue'
import AppIcon from './AppIcon.vue'

const catalog = useCatalogStore()
const recurring = useRecurringStore()
const message = useMessage()
const toggleArchive = useArchiveToggle()

const modal = ref(false)
const edited = ref<RecurringQuest | null>(null)
const busyId = ref<number | null>(null)

function open(template: RecurringQuest | null) {
  edited.value = template
  modal.value = true
}

async function togglePause(template: RecurringQuest) {
  busyId.value = template.id
  try {
    await recurring.save(template.id, { is_active: !template.is_active })
    message.success(
      template.is_active ? `«${template.name}» на паузе` : `«${template.name}» снова в деле`,
    )
  } catch (e) {
    message.error(errorMessage(e))
  } finally {
    busyId.value = null
  }
}

const tierOf = (t: RecurringQuest) => catalog.tiers.find((tier) => tier.id === t.tier_id)
</script>

<template>
  <CatalogSection
    :items="recurring.templates"
    add-label="Новый повторяющийся"
    empty-text="Повторяющихся квестов нет. Зарядка каждый день? Уборка по субботам?"
    empty-art="recurring"
    @add="open(null)"
    @edit="open"
    @toggle-archive="
      (t) => toggleArchive(t, (is_archived) => recurring.save(t.id, { is_archived }))
    "
  >
    <template #item="{ item: t }">
      <div class="head">
        <TierSeal v-if="tierOf(t)" :tier="tierOf(t)!" :size="28" />
        <span class="name"><AppIcon name="repeat" :size="18" class="repeat" /> {{ t.name }}</span>
        <NTag v-if="!t.is_active && !t.is_archived" size="small">на паузе</NTag>
      </div>
      <div class="meta">
        <span class="schedule">{{ describeSchedule(t) }}</span>
        <span class="reward num"><CoinIcon :size="14" /> +{{ t.reward }}</span>
        <span v-if="t.penalty" class="penalty num">штраф {{ t.penalty }}</span>
      </div>
      <div v-if="t.next_due_at" class="muted">Следующий: {{ dueLabel(t.next_due_at).text }}</div>
      <div v-else-if="t.is_active && !t.is_archived" class="muted">Расписание закончилось</div>
    </template>
    <template #actions="{ item: t }">
      <NButton size="small" quaternary :loading="busyId === t.id" @click="togglePause(t)">
        {{ t.is_active ? 'Пауза' : 'Возобновить' }}
      </NButton>
    </template>
  </CatalogSection>

  <RecurringFormModal v-model:show="modal" :template="edited" />
</template>

<style scoped>
.head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.repeat {
  color: var(--color-muted);
}

.name {
  font-family: var(--font-heading);
  font-size: 1.2rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 14px;
  margin-top: 4px;
}

.schedule {
  font-style: italic;
}

.reward {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-gold);
  font-weight: 700;
}

.penalty {
  color: var(--color-error);
  font-size: 0.875rem;
}

.muted {
  color: var(--color-muted);
  font-size: 0.875rem;
}
</style>
