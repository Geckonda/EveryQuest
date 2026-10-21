<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import { errorMessage } from '@/api/errors'
import { useNow } from '@/composables/useNow'
import { useSessionsStore } from '@/stores/sessions'
import { countdown, formatTime } from '@/utils/format'

/** Идущие траты с полосками и кнопкой «Закончить раньше» — в шапке и на «Сегодня». */
withDefaults(defineProps<{ size?: 'small' | 'large' }>(), { size: 'small' })

const sessions = useSessionsStore()
const message = useMessage()

// Траты обычно короткие — пока хоть одна идёт, тикаем посекундно.
const now = useNow(() => sessions.active.length > 0)

const rows = computed(() =>
  sessions.active.map((s) => ({
    ...s,
    // Ждёт в очереди: отсчёт ещё не идёт.
    waiting: new Date(s.started_at) > now.value,
    timer: countdown(s.started_at, s.ends_at, now.value),
    minutes: Math.round((new Date(s.ends_at).getTime() - new Date(s.started_at).getTime()) / 60000),
  })),
)

const finishingId = ref<number | null>(null)

async function finish(id: number, name: string, waiting: boolean) {
  finishingId.value = id
  try {
    await sessions.finish(id)
    message.success(
      waiting ? `Убрали «${name}» из очереди` : `«${name}» — закончили раньше. Похвально!`,
    )
  } catch (e) {
    message.error(errorMessage(e))
    await sessions.load().catch(() => {})
  } finally {
    finishingId.value = null
  }
}
</script>

<template>
  <ul class="list" :class="size">
    <li v-for="row in rows" :key="row.id" :class="{ waiting: row.waiting }">
      <div class="row-head">
        <span class="row-name">{{ row.name }}</span>
        <span v-if="row.waiting" class="row-queue">
          в очереди · с {{ formatTime(row.started_at) }}, {{ row.minutes }} мин
        </span>
        <span v-else class="num row-left">{{ row.timer.left }}</span>
      </div>
      <div class="bar" :style="{ '--remaining': row.waiting ? 1 : row.timer.remaining }">
        <span />
      </div>
      <NButton
        :size="size === 'large' ? 'small' : 'tiny'"
        quaternary
        :loading="finishingId === row.id"
        @click="finish(row.id, row.name, row.waiting)"
      >
        {{ row.waiting ? 'Убрать из очереди' : 'Закончить раньше' }}
      </NButton>
    </li>
  </ul>
</template>

<style scoped>
.list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.list.small {
  min-width: 220px;
}

.list li + li {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-rule);
}

.row-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-weight: 700;
}

.large .row-head {
  font-family: var(--font-heading);
  font-size: 1.25rem;
}

.row-name {
  overflow-wrap: anywhere;
}

.row-left {
  color: var(--color-gold);
}

.row-queue {
  color: var(--color-muted);
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-style: italic;
  font-weight: 400;
  white-space: nowrap;
}

/* Ожидающая в очереди — бледнее, полоска ещё не тает. */
.waiting .bar span {
  background: var(--color-rule);
  opacity: 0.6;
}

.waiting .row-name {
  color: var(--color-muted);
}

.bar {
  height: 4px;
  margin: 6px 0 4px;
  border-radius: 2px;
  background: var(--color-rule);
}

.large .bar {
  height: 6px;
  border-radius: 3px;
}

.bar span {
  display: block;
  width: calc(var(--remaining) * 100%);
  height: 100%;
  border-radius: inherit;
  background: var(--color-gold);
  transition: width 1s linear;
}

@media (prefers-reduced-motion: reduce) {
  .bar span {
    transition: none;
  }
}
</style>
