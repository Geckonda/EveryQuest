<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, useMessage } from 'naive-ui'
import { errorMessage } from '@/api/errors'
import { useNow } from '@/composables/useNow'
import { useSessionsStore } from '@/stores/sessions'
import { countdown } from '@/utils/format'

/** Идущие траты с полосками и кнопкой «Закончить раньше» — в шапке и на «Сегодня». */
withDefaults(defineProps<{ size?: 'small' | 'large' }>(), { size: 'small' })

const sessions = useSessionsStore()
const message = useMessage()

// Траты обычно короткие — пока хоть одна идёт, тикаем посекундно.
const now = useNow(() => sessions.active.length > 0)

const rows = computed(() =>
  sessions.active.map((s) => ({ ...s, timer: countdown(s.started_at, s.ends_at, now.value) })),
)

const finishingId = ref<number | null>(null)

async function finish(id: number, name: string) {
  finishingId.value = id
  try {
    await sessions.finish(id)
    message.success(`«${name}» — закончили раньше. Похвально!`)
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
    <li v-for="row in rows" :key="row.id">
      <div class="row-head">
        <span class="row-name">{{ row.name }}</span>
        <span class="num row-left">{{ row.timer.left }}</span>
      </div>
      <div class="bar" :style="{ '--remaining': row.timer.remaining }"><span /></div>
      <NButton
        :size="size === 'large' ? 'small' : 'tiny'"
        quaternary
        :loading="finishingId === row.id"
        @click="finish(row.id, row.name)"
      >
        Закончить раньше
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
