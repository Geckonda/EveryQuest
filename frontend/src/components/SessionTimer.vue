<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { NButton, NPopover, useMessage } from 'naive-ui'
import { errorMessage } from '@/api/errors'
import { useNow } from '@/composables/useNow'
import { useSessionsStore } from '@/stores/sessions'
import { countdown } from '@/utils/format'
import { playSound } from '@/utils/sound'

/** Идущие траты в шапке: ближайшая — на плашке, все — во всплывающем списке. */
const sessions = useSessionsStore()
const message = useMessage()

// Траты обычно короткие — пока хоть одна идёт, тикаем посекундно.
const now = useNow(() => sessions.active.length > 0)

const rows = computed(() =>
  sessions.active.map((s) => ({ ...s, timer: countdown(s.started_at, s.ends_at, now.value) })),
)
const nearest = computed(() => rows.value[0])

// Окончание ловим таймером на каждый сеанс, а не по тикам «сейчас»: тики в фоновой
// вкладке остановлены, а setTimeout браузер выполнит, пусть и с задержкой.
const timers = new Map<number, ReturnType<typeof setTimeout>>()

watch(
  () => sessions.active,
  (list) => {
    const ids = new Set(list.map((s) => s.id))
    for (const [id, timer] of timers) {
      if (!ids.has(id)) {
        clearTimeout(timer)
        timers.delete(id)
      }
    }
    for (const s of list) {
      if (timers.has(s.id)) continue
      const delay = Math.max(new Date(s.ends_at).getTime() - Date.now(), 0)
      timers.set(
        s.id,
        setTimeout(() => {
          timers.delete(s.id)
          sessions.expire(s.id)
          playSound('timeUp')
          message.info(`Время «${s.name}» вышло. Пора за квесты!`, { duration: 8000 })
        }, delay),
      )
    }
  },
  { immediate: true },
)

onUnmounted(() => timers.forEach(clearTimeout))

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
  <NPopover v-if="nearest" trigger="click" placement="bottom-end" :show-arrow="false">
    <template #trigger>
      <button
        type="button"
        class="session"
        :class="nearest.timer.urgency"
        :title="`Идёт: ${nearest.name}`"
      >
        <span class="hourglass" aria-hidden="true">⏳</span>
        <span class="name">{{ nearest.name }}</span>
        <span class="left num">{{ nearest.timer.left }}</span>
        <span v-if="rows.length > 1" class="more">+{{ rows.length - 1 }}</span>
      </button>
    </template>

    <ul class="list">
      <li v-for="row in rows" :key="row.id">
        <div class="row-head">
          <span class="row-name">{{ row.name }}</span>
          <span class="num row-left">{{ row.timer.left }}</span>
        </div>
        <div class="bar" :style="{ '--remaining': row.timer.remaining }"><span /></div>
        <NButton
          size="tiny"
          quaternary
          :loading="finishingId === row.id"
          @click="finish(row.id, row.name)"
        >
          Закончить раньше
        </NButton>
      </li>
    </ul>
  </NPopover>
</template>

<style scoped>
.session {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  max-width: 220px;
  padding: 2px 10px;
  border: 1px solid rgba(231, 178, 79, 0.45);
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.25);
  color: var(--color-sign-text);
  font: inherit;
  font-size: 0.95rem;
  cursor: pointer;
}

.session:hover {
  border-color: var(--color-sign-gold);
}

/* Меньше 30 минут — время тает: мягкое мигание песочных часов. */
.session.critical .hourglass {
  animation: pulse 1s ease-in-out infinite alternate;
}

.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.left {
  color: var(--color-sign-gold);
  font-weight: 700;
}

.more {
  color: var(--color-sign-muted);
  font-size: 0.8rem;
}

.list {
  min-width: 220px;
  margin: 0;
  padding: 0;
  list-style: none;
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

.bar span {
  display: block;
  width: calc(var(--remaining) * 100%);
  height: 100%;
  border-radius: inherit;
  background: var(--color-gold);
  transition: width 1s linear;
}

@keyframes pulse {
  to {
    opacity: 0.4;
  }
}

/* На телефоне в шапке тесно: остаются часы и время, плашка не сжимается. */
@media (max-width: 520px) {
  .session {
    flex: none;
    gap: 3px;
    padding: 2px 8px 2px 6px;
  }

  .name,
  .more {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .session.critical .hourglass {
    animation: none;
  }

  .bar span {
    transition: none;
  }
}
</style>
