<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

/** Подпись под полем штрафа: откуда он взялся и как вернуть расчётный. */
defineProps<{ touched: boolean }>()
defineEmits<{ reset: [] }>()

const auth = useAuthStore()
const multiplier = computed(() => auth.user?.penalty_multiplier ?? 1)
</script>

<template>
  <span v-if="touched">
    Свой штраф ·
    <button type="button" class="link-button" @click="$emit('reset')">
      награда × {{ multiplier }}
    </button>
  </span>
  <span v-else>Награда × {{ multiplier }}</span>
</template>
