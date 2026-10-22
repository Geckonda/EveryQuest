<script setup lang="ts">
import { computed } from 'vue'
import { NButton } from 'naive-ui'
import type { Category, Quest, Tier } from '@/api/types'
import { canUndo, countdown, dueLabel, formatDateTime, tierLabel } from '@/utils/format'
import CoinIcon from './CoinIcon.vue'
import TierSeal from './TierSeal.vue'
import AppIcon from './AppIcon.vue'

const props = defineProps<{
  quest: Quest
  tier: Tier | undefined
  category: Category | undefined
  /** Текущее время — тикает в родителе, чтобы срок обновлялся без перезагрузки. */
  now: Date
  busy?: boolean
}>()

/** complete передаёт событие клика — от кнопки полетят монеты. */
defineEmits<{ complete: [event: MouseEvent]; fail: []; edit: []; archive: []; undo: [] }>()

const isActive = computed(() => props.quest.status === 'active')
// Срок и просрочка — только у открытого квеста. Закрытый (сдан, провален, снят) свою судьбу
// уже получил: иначе сданный вовремя квест с прошедшим сроком краснел бы с «гильдия взыщет штраф».
const due = computed(() =>
  isActive.value && props.quest.due_at ? dueLabel(props.quest.due_at, props.now) : null,
)
/** Живой отсчёт — только у открытого квеста со сроком. */
const timer = computed(() =>
  isActive.value && props.quest.due_at
    ? countdown(props.quest.created_at, props.quest.due_at, props.now)
    : null,
)

/** Штамп на закрытом объявлении. */
const STAMP = {
  completed: 'Сдан',
  failed: 'Провален',
  archived: 'Снят',
} as const
/** Только что закрыт — ещё можно передумать (10 минут). */
const undoable = computed(() => canUndo(props.quest, props.now))
const stamp = computed(() => (props.quest.status === 'active' ? null : STAMP[props.quest.status]))

/** Подпись под датой закрытия: почему провален. */
const FAIL_NOTE = { expired: 'срок вышел', abandoned: 'не справился' } as const
const failNote = computed(() =>
  props.quest.close_reason === 'expired' || props.quest.close_reason === 'abandoned'
    ? FAIL_NOTE[props.quest.close_reason]
    : null,
)
</script>

<template>
  <article
    class="notice"
    :class="[quest.status, { overdue: due?.overdue }, timer && `urgency-${timer.urgency}`]"
  >
    <TierSeal v-if="tier" :tier="tier" class="seal" />

    <div class="body">
      <h3 class="name">
        <span v-if="quest.recurring_quest_id" class="recurring" title="Повторяющийся квест">
          <AppIcon name="repeat" :size="18" />
        </span>
        {{ quest.name }}
      </h3>
      <p v-if="quest.description" class="description">{{ quest.description }}</p>

      <div class="meta">
        <span class="reward num" title="Награда"> <CoinIcon :size="15" />+{{ quest.reward }} </span>
        <span v-if="quest.penalty" class="penalty num" title="Штраф за провал">
          штраф {{ quest.penalty }}
        </span>
        <span v-if="tier && tierLabel(tier)" class="tier">{{ tierLabel(tier) }}</span>
        <span v-if="category" class="category">
          <span class="dot" :style="{ background: category.color ?? 'currentColor' }" />
          {{ category.name }}
        </span>
      </div>

      <div class="when">
        <template v-if="isActive">
          <template v-if="due">
            <span class="due" :class="{ late: due.overdue, soon: due.soon }">
              <AppIcon name="hourglass" :size="14" /> {{ due.text }}
            </span>
            <span v-if="timer && !due.overdue" class="left num"> · осталось {{ timer.left }}</span>
          </template>
          <span v-else>без срока</span>
        </template>
        <template v-else>
          <span v-if="quest.closed_at">{{ formatDateTime(quest.closed_at) }}</span>
          <span v-if="failNote">{{ quest.closed_at ? ' · ' : '' }}{{ failNote }}</span>
          <span v-if="quest.status === 'failed' && quest.penalty" class="late num">
            · −{{ quest.penalty }}
          </span>
        </template>
      </div>

      <!-- Фитиль: догорает от создания квеста до срока. -->
      <div
        v-if="timer && !due?.overdue"
        class="fuse"
        :style="{ '--remaining': timer.remaining }"
        aria-hidden="true"
      >
        <span class="burn" />
      </div>

      <div v-if="isActive" class="actions">
        <NButton
          type="primary"
          size="small"
          :disabled="due?.overdue"
          :loading="busy"
          @click="$emit('complete', $event)"
        >
          Сдать квест
        </NButton>
        <NButton size="small" quaternary :disabled="due?.overdue" @click="$emit('edit')">
          Изменить
        </NButton>
        <NButton size="small" quaternary :disabled="due?.overdue" @click="$emit('archive')">
          Снять с доски
        </NButton>
        <NButton
          size="small"
          quaternary
          type="error"
          :disabled="due?.overdue || busy"
          @click="$emit('fail')"
        >
          Провалить
        </NButton>
      </div>
      <div v-if="undoable" class="actions">
        <NButton size="small" secondary :loading="busy" @click="$emit('undo')">Отменить</NButton>
      </div>
      <p v-if="due?.overdue" class="overdue-note">
        Срок вышел. Гильдия взыщет штраф в ближайшие минуты.
      </p>
    </div>

    <span v-if="stamp" class="stamp">{{ stamp }}</span>
  </article>
</template>

<style scoped>
/* Объявление, приколотое к доске гильдии. */
.notice {
  position: relative;
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  padding: 14px 14px 12px;
  border: 1px solid var(--color-border);
  border-radius: 2px;
  background-color: var(--color-note);
  background-image: var(--paper-grain);
  box-shadow: var(--shadow-note);
}

/* Гвоздик сверху. */
.notice::before {
  content: '';
  position: absolute;
  top: -5px;
  left: 50%;
  width: 10px;
  height: 10px;
  margin-left: -5px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #d8d0c0, #6b6255 70%);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}

.notice.overdue {
  border-color: var(--color-error);
}

.notice:not(.active) .body {
  opacity: 0.72;
}

.seal {
  margin-top: 2px;
}

.body {
  flex: 1;
  min-width: 0;
}

.name {
  margin: 0;
  font-size: 1.3rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.notice:not(.active) .name {
  padding-right: 96px; /* место под штамп */
}

.recurring {
  color: var(--color-muted);
  font-weight: 600;
}

.description {
  margin: 4px 0 0;
  color: var(--color-muted);
  font-style: italic;
  overflow-wrap: anywhere;
  white-space: pre-line;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 14px;
  margin-top: 8px;
}

.reward {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-gold);
  font-weight: 700;
  font-size: 1.05rem;
}

.penalty {
  color: var(--color-error);
  font-size: 0.875rem;
}

.tier {
  max-width: 100%;
  overflow: hidden;
  font-size: 0.875rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.875rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.when {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 0.875rem;
}

.when .soon {
  color: var(--color-warning);
  font-weight: 700;
}

.when .late {
  color: var(--color-error);
  font-weight: 700;
}

.when .left {
  font-weight: 700;
}

.urgency-critical .when .left {
  color: var(--color-error);
}

.fuse {
  position: relative;
  height: 4px;
  margin-top: 8px;
  border-radius: 2px;
  background: var(--color-rule);
}

.burn {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: calc(var(--remaining) * 100%);
  border-radius: inherit;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--color-gold), #000 30%),
    var(--color-gold)
  );
  transition: width 1s linear;
}

/* Искра на конце фитиля. */
.burn::after {
  content: '';
  position: absolute;
  top: 50%;
  right: -5px;
  width: 10px;
  height: 10px;
  margin-top: -5px;
  border-radius: 50%;
  background: radial-gradient(circle, #fff6c8 0 20%, #f2a530 45%, transparent 70%);
  animation: spark 0.5s ease-in-out infinite alternate;
}

.urgency-soon .burn {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--color-warning), #000 25%),
    var(--color-warning)
  );
}

.urgency-critical .burn {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--color-error), #000 25%),
    var(--color-error)
  );
}

/* Горит: мягкое янтарное свечение. */
.notice.urgency-soon {
  border-color: color-mix(in srgb, var(--color-warning), transparent 30%);
  animation: glow-soon 2.4s ease-in-out infinite;
}

/* Вот-вот сгорит: красное пульсирующее свечение и короткая дрожь раз в несколько секунд. */
.notice.urgency-critical {
  border-color: var(--color-error);
  animation:
    glow-critical 1.2s ease-in-out infinite,
    shake 4s ease-in-out infinite;
}

@keyframes spark {
  from {
    transform: scale(0.8);
    opacity: 0.7;
  }
  to {
    transform: scale(1.25);
    opacity: 1;
  }
}

@keyframes glow-soon {
  50% {
    box-shadow:
      var(--shadow-note),
      0 0 14px 2px color-mix(in srgb, var(--color-warning), transparent 55%);
  }
}

@keyframes glow-critical {
  50% {
    box-shadow:
      var(--shadow-note),
      0 0 18px 4px color-mix(in srgb, var(--color-error), transparent 45%);
  }
}

@keyframes shake {
  0%,
  88%,
  100% {
    transform: none;
  }
  90% {
    transform: translateX(-3px) rotate(-0.6deg);
  }
  92% {
    transform: translateX(3px) rotate(0.6deg);
  }
  94% {
    transform: translateX(-2px) rotate(-0.3deg);
  }
  96% {
    transform: translateX(2px);
  }
}

/* Без анимаций — остаются цвет рамки и фитиля. */
@media (prefers-reduced-motion: reduce) {
  .notice.urgency-soon,
  .notice.urgency-critical,
  .burn::after {
    animation: none;
  }

  .burn {
    transition: none;
  }
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 10px;
}

.overdue-note {
  margin: 6px 0 0;
  color: var(--color-muted);
  font-size: 0.8125rem;
  font-style: italic;
}

/* Чернильный штамп на закрытом объявлении. */
.stamp {
  position: absolute;
  top: 12px;
  right: 14px;
  padding: 2px 10px;
  border: 2px solid currentColor;
  border-radius: 4px;
  font-family: var(--font-heading);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  transform: rotate(-8deg);
  opacity: 0.85;
  pointer-events: none;
}

.completed .stamp {
  color: var(--color-ok);
}

.failed .stamp {
  color: var(--color-error);
}

.archived .stamp {
  color: var(--color-muted);
}
</style>
