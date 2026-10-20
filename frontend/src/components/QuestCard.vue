<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NTag } from 'naive-ui'
import type { Category, Quest, Tier } from '@/api/types'
import { dueLabel, formatDateTime } from '@/utils/format'

const props = defineProps<{
  quest: Quest
  tier: Tier | undefined
  category: Category | undefined
  /** Текущее время — тикает в родителе, чтобы срок обновлялся без перезагрузки. */
  now: Date
  busy?: boolean
}>()

defineEmits<{ complete: []; edit: []; archive: [] }>()

const isActive = computed(() => props.quest.status === 'active')
const due = computed(() => (props.quest.due_at ? dueLabel(props.quest.due_at, props.now) : null))

const STATUS_LABEL = {
  completed: 'Выполнен',
  failed: 'Провален',
  archived: 'Убран',
} as const
const STATUS_TYPE = { completed: 'success', failed: 'error', archived: 'default' } as const
</script>

<template>
  <article class="quest" :class="{ overdue: due?.overdue }">
    <div class="head">
      <h3 class="name">{{ quest.name }}</h3>
      <NTag
        v-if="tier"
        :color="{ color: tier.color ?? undefined, textColor: '#fff' }"
        size="small"
        :bordered="false"
      >
        {{ tier.name }}
      </NTag>
    </div>

    <p v-if="quest.description" class="description">{{ quest.description }}</p>

    <div class="meta">
      <span v-if="category" class="category">
        <span class="dot" :style="{ background: category.color ?? 'currentColor' }" />
        {{ category.name }}
      </span>
      <span class="reward">+{{ quest.reward }}</span>
      <span class="penalty">−{{ quest.penalty }}</span>
      <template v-if="isActive">
        <span v-if="due" class="due" :class="{ late: due.overdue, soon: due.soon }">
          {{ due.text }}
        </span>
        <span v-else class="due">без срока</span>
      </template>
      <template v-else>
        <NTag size="small" :type="STATUS_TYPE[quest.status as keyof typeof STATUS_TYPE]">
          {{ STATUS_LABEL[quest.status as keyof typeof STATUS_LABEL] }}
        </NTag>
        <span v-if="quest.completed_at" class="due">{{ formatDateTime(quest.completed_at) }}</span>
        <span v-else-if="quest.due_at" class="due">срок {{ formatDateTime(quest.due_at) }}</span>
      </template>
    </div>

    <div v-if="isActive" class="actions">
      <NButton
        type="primary"
        size="small"
        :disabled="due?.overdue"
        :loading="busy"
        @click="$emit('complete')"
      >
        Выполнено
      </NButton>
      <NButton size="small" quaternary :disabled="due?.overdue" @click="$emit('edit')">
        Изменить
      </NButton>
      <NButton size="small" quaternary :disabled="due?.overdue" @click="$emit('archive')">
        Убрать
      </NButton>
    </div>
    <p v-if="due?.overdue" class="overdue-note">Штраф спишется автоматически в ближайшие минуты.</p>
  </article>
</template>

<style scoped>
.quest {
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.name {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.description {
  margin: 4px 0 0;
  color: var(--color-muted);
  font-size: 0.875rem;
  overflow-wrap: anywhere;
  white-space: pre-line;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
  margin-top: 6px;
  font-size: 0.875rem;
}

.category {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.reward {
  color: var(--color-ok);
  font-variant-numeric: tabular-nums;
}

.penalty {
  color: var(--color-error);
  font-variant-numeric: tabular-nums;
}

.due {
  color: var(--color-muted);
}

.due.soon {
  color: var(--color-warning);
  font-weight: 600;
}

.due.late {
  color: var(--color-error);
  font-weight: 600;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.overdue-note {
  margin: 6px 0 0;
  color: var(--color-muted);
  font-size: 0.8125rem;
}
</style>
