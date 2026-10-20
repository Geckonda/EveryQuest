<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 16 })
</script>

<template>
  <svg
    class="coin"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    aria-hidden="true"
    focusable="false"
  >
    <defs>
      <radialGradient id="coin-face" cx="35%" cy="30%" r="75%">
        <stop offset="0" stop-color="#fff1b8" />
        <stop offset="0.45" stop-color="#e9b949" />
        <stop offset="1" stop-color="#a8701a" />
      </radialGradient>
    </defs>
    <circle cx="12" cy="12" r="11" fill="url(#coin-face)" stroke="#7a4f0e" stroke-width="1" />
    <circle cx="12" cy="12" r="7.5" fill="none" stroke="#8a5a12" stroke-width="0.8" opacity="0.7" />
    <!-- Корона на аверсе -->
    <path d="M7.8 14.6h8.4l-0.7-4.6-2 1.8L12 8.4l-1.5 3.4-2-1.8z" fill="#8a5a12" opacity="0.85" />
  </svg>
</template>

<style scoped>
.coin {
  display: inline-block;
  flex: none;
  vertical-align: -0.15em;
}
</style>
