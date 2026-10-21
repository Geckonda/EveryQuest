<script setup lang="ts">
import { NPopover } from 'naive-ui'

/**
 * Значок «?» рядом с названием раздела: по нажатию — коротко, что здесь можно делать.
 * По нажатию, а не по наведению: на телефоне наведения нет.
 */
defineProps<{ text: string; title?: string }>()
</script>

<template>
  <NPopover trigger="click" placement="bottom-start" :style="{ maxWidth: '300px' }">
    <template #trigger>
      <button type="button" class="hint-button" :aria-label="`Подсказка: ${title ?? text}`">
        ?
      </button>
    </template>
    <div class="hint">
      <div v-if="title" class="hint-title">{{ title }}</div>
      {{ text }}
    </div>
  </NPopover>
</template>

<style scoped>
.hint-button {
  display: inline-grid;
  place-items: center;
  width: 20px;
  height: 20px;
  margin-left: 6px;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-note);
  color: var(--color-muted);
  font-family: var(--font-body);
  font-size: 0.75rem;
  font-style: normal;
  font-weight: 700;
  line-height: 1;
  vertical-align: 0.25em;
  cursor: pointer;
}

.hint-button:hover,
.hint-button:focus-visible {
  border-color: var(--color-gold);
  color: var(--color-gold);
}

.hint {
  font-size: 0.875rem;
  line-height: 1.45;
}

.hint-title {
  margin-bottom: 4px;
  font-family: var(--font-heading);
  font-size: 1.05rem;
  font-weight: 700;
}
</style>
