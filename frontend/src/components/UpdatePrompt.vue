<script setup lang="ts">
import { NButton } from 'naive-ui'
import { useRegisterSW } from 'virtual:pwa-register/vue'

/**
 * Плашка «Доступна новая версия». Сервис-воркер держит в кэше старую оболочку приложения;
 * новая подключится только по согласию — не посреди заполнения формы.
 */
const HOUR_MS = 60 * 60 * 1000

const { needRefresh, updateServiceWorker } = useRegisterSW({
  // Приложение может неделями висеть открытым на телефоне — проверяем обновление раз в час.
  onRegisteredSW(_url, registration) {
    if (registration) setInterval(() => registration.update().catch(() => {}), HOUR_MS)
  },
})
</script>

<template>
  <Transition name="slide">
    <div v-if="needRefresh" class="update" role="status">
      <span class="text">Доступна новая версия Ежеквестика</span>
      <NButton size="small" quaternary class="later" @click="needRefresh = false">Позже</NButton>
      <NButton size="small" type="primary" @click="updateServiceWorker(true)">Обновить</NButton>
    </div>
  </Transition>
</template>

<style scoped>
.update {
  position: fixed;
  left: 50%;
  bottom: 16px;
  z-index: 3500;
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(440px, calc(100vw - 24px));
  padding: 10px 12px 10px 16px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-page);
  background-image: var(--paper-grain);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  transform: translateX(-50%);
}

.text {
  flex: 1;
  font-weight: 700;
}

/* Над нижней панелью вкладок. */
@media (max-width: 640px) {
  .update {
    bottom: calc(var(--tab-bar-height) + 10px + env(safe-area-inset-bottom));
  }
}

.slide-enter-active,
.slide-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translate(-50%, 12px);
}
</style>
