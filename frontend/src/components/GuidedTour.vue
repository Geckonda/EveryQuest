<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { NButton } from 'naive-ui'
import type { TourStep } from '@/composables/useTour'

/**
 * Тур с подсветкой: затемнение с «окном» вокруг элемента и карточка с пояснением.
 * Элемент ищется по data-tour; если таких несколько (меню в шапке и в нижней панели),
 * берётся видимый.
 */
const props = defineProps<{ steps: TourStep[] }>()
const open = defineModel<boolean>('open', { required: true })

const index = ref(0)
const rect = ref<DOMRect | null>(null)
const step = computed(() => props.steps[index.value]!)
const isLast = computed(() => index.value === props.steps.length - 1)

const PADDING = 6

function findTarget(name: string | undefined): HTMLElement | null {
  if (!name) return null
  const candidates = document.querySelectorAll<HTMLElement>(`[data-tour="${name}"]`)
  return [...candidates].find((el) => el.getClientRects().length > 0) ?? null
}

function measure() {
  const el = findTarget(step.value.target)
  rect.value = el ? el.getBoundingClientRect() : null
}

async function show() {
  await nextTick()
  findTarget(step.value.target)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  measure()
  // Плавная прокрутка двигает элемент — перемеряем, когда она закончится.
  setTimeout(measure, 350)
}

function go(delta: number) {
  index.value = Math.min(Math.max(index.value + delta, 0), props.steps.length - 1)
  show()
}

function close() {
  open.value = false
}

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
  else if (event.key === 'ArrowRight' || event.key === 'Enter') {
    if (isLast.value) close()
    else go(1)
  } else if (event.key === 'ArrowLeft') go(-1)
}

watch(
  open,
  (value) => {
    if (value) {
      index.value = 0
      window.addEventListener('resize', measure)
      window.addEventListener('scroll', measure, true)
      window.addEventListener('keydown', onKey)
      show()
    } else {
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', measure, true)
      window.removeEventListener('keydown', onKey)
    }
  },
  { immediate: true },
)

onUnmounted(() => (open.value = false))

const spotlight = computed(() => {
  const r = rect.value
  if (!r) return null
  return {
    top: `${r.top - PADDING}px`,
    left: `${r.left - PADDING}px`,
    width: `${r.width + PADDING * 2}px`,
    height: `${r.height + PADDING * 2}px`,
  }
})

/** Карточка — под элементом, если внизу хватает места, иначе над ним; без цели — по центру. */
const cardStyle = computed(() => {
  const r = rect.value
  const width = Math.min(340, window.innerWidth - 24)
  if (!r) {
    return { top: '50%', left: '50%', width: `${width}px`, transform: 'translate(-50%, -50%)' }
  }
  const left = Math.min(
    Math.max(r.left + r.width / 2 - width / 2, 12),
    window.innerWidth - width - 12,
  )
  const below = window.innerHeight - r.bottom > 220
  return below
    ? { top: `${r.bottom + PADDING + 12}px`, left: `${left}px`, width: `${width}px` }
    : {
        bottom: `${window.innerHeight - r.top + PADDING + 12}px`,
        left: `${left}px`,
        width: `${width}px`,
      }
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="tour" role="dialog" aria-modal="true" :aria-label="step.title">
      <!-- Клик мимо карточки не закрывает тур: легко промахнуться на телефоне. -->
      <div class="backdrop" :class="{ dim: !spotlight }" />
      <div v-if="spotlight" class="spotlight" :style="spotlight" />
      <div class="card" :style="cardStyle">
        <div class="progress num">{{ index + 1 }} / {{ steps.length }}</div>
        <h3 class="title">{{ step.title }}</h3>
        <p class="text">{{ step.text }}</p>
        <div class="actions">
          <NButton v-if="!isLast" quaternary size="small" @click="close">Пропустить</NButton>
          <span class="spacer" />
          <NButton v-if="index > 0" size="small" @click="go(-1)">Назад</NButton>
          <NButton v-if="!isLast" type="primary" size="small" @click="go(1)">Далее</NButton>
          <NButton v-else type="primary" size="small" @click="close">В путь!</NButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.tour {
  position: fixed;
  inset: 0;
  z-index: 4000;
}

.backdrop {
  position: absolute;
  inset: 0;
}

/* Без подсвеченного элемента затемняем весь экран сами. */
.backdrop.dim {
  background: rgba(20, 12, 5, 0.6);
}

/* «Окно» в затемнении — огромная тень вокруг рамки элемента. */
.spotlight {
  position: fixed;
  border: 2px solid var(--color-gold);
  border-radius: 8px;
  box-shadow:
    0 0 0 9999px rgba(20, 12, 5, 0.6),
    0 0 16px 4px rgba(231, 178, 79, 0.55);
  transition:
    top 0.3s ease,
    left 0.3s ease,
    width 0.3s ease,
    height 0.3s ease;
  pointer-events: none;
}

.card {
  position: fixed;
  max-width: calc(100vw - 24px);
  padding: 14px 16px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-page);
  background-image: var(--paper-grain);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
  color: var(--color-text);
}

.progress {
  color: var(--color-muted);
  font-size: 0.75rem;
}

.title {
  margin: 2px 0 6px;
  font-size: 1.35rem;
}

.text {
  margin: 0 0 12px;
  line-height: 1.45;
}

.actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.spacer {
  flex: 1;
}

@media (prefers-reduced-motion: reduce) {
  .spotlight {
    transition: none;
  }
}
</style>
