<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'
import { NPopover, useMessage } from 'naive-ui'
import { useNow } from '@/composables/useNow'
import { useSessionsStore } from '@/stores/sessions'
import type { RewardSession } from '@/api/types'
import { countdown, formatTime } from '@/utils/format'
import { playSound } from '@/utils/sound'
import SessionList from './SessionList.vue'

/** Идущие траты в шапке: ближайшая — на плашке, все — во всплывающем списке. */
const sessions = useSessionsStore()
const message = useMessage()

// Траты обычно короткие — пока хоть одна идёт, тикаем посекундно.
const now = useNow(() => sessions.active.length > 0)

const rows = computed(() =>
  sessions.active.map((s) => ({
    ...s,
    waiting: new Date(s.started_at) > now.value,
    timer: countdown(s.started_at, s.ends_at, now.value),
  })),
)
// На плашке — идущая трата; если все ждут в очереди — ближайшая из них.
const nearest = computed(() => rows.value.find((r) => !r.waiting) ?? rows.value[0])

// Окончание ловим таймером на каждый сеанс, а не по тикам «сейчас»: тики в фоновой
// вкладке остановлены, а setTimeout браузер выполнит, пусть и с задержкой.
// Ключ — id и время окончания: очередь сдвинулась — таймер переставляется.
const timers = new Map<string, ReturnType<typeof setTimeout>>()
const timerKey = (s: RewardSession) => `${s.id}@${s.ends_at}`

function onTimeUp(session: RewardSession) {
  sessions.expire(session.id)
  playSound('timeUp')
  // Следующая в очереди начинается ровно сейчас — скажем, что дальше.
  const end = new Date(session.ends_at).getTime()
  const next = sessions.active.find((s) => Math.abs(new Date(s.started_at).getTime() - end) < 2000)
  message.info(
    next
      ? `Время «${session.name}» вышло. Дальше — «${next.name}».`
      : `Время «${session.name}» вышло. Пора за квесты!`,
    { duration: 8000 },
  )
}

watch(
  () => sessions.active,
  (list) => {
    const keys = new Set(list.map(timerKey))
    for (const [key, timer] of timers) {
      if (!keys.has(key)) {
        clearTimeout(timer)
        timers.delete(key)
      }
    }
    for (const s of list) {
      const key = timerKey(s)
      if (timers.has(key)) continue
      const delay = Math.max(new Date(s.ends_at).getTime() - Date.now(), 0)
      timers.set(
        key,
        setTimeout(() => {
          timers.delete(key)
          onTimeUp(s)
        }, delay),
      )
    }
  },
  { immediate: true },
)

onUnmounted(() => timers.forEach(clearTimeout))
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
        <span v-if="nearest.waiting" class="left num">с {{ formatTime(nearest.started_at) }}</span>
        <span v-else class="left num">{{ nearest.timer.left }}</span>
        <span v-if="rows.length > 1" class="more">+{{ rows.length - 1 }}</span>
      </button>
    </template>

    <SessionList />
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
}
</style>
