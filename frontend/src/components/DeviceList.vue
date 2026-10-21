<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NSpin, NTag, useMessage } from 'naive-ui'
import { api } from '@/api/client'
import type { AuthSession } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useAuthStore } from '@/stores/auth'
import { describeDevice } from '@/utils/device'
import { formatDateTime } from '@/utils/format'

/** Устройства, где выполнен вход, — с выходом на любом из них. */
const auth = useAuthStore()
const router = useRouter()
const message = useMessage()

const devices = ref<AuthSession[]>([])
const loading = ref(true)
const revokingId = ref<number | null>(null)

async function load() {
  try {
    devices.value = await api.get<AuthSession[]>('/auth/sessions')
  } catch (e) {
    message.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function revoke(device: AuthSession) {
  revokingId.value = device.id
  try {
    await api.post(`/auth/sessions/${device.id}/revoke`)
    if (device.current) {
      // Вышли на этом же устройстве — сессии больше нет.
      await auth.logout()
      router.push({ name: 'login' })
      return
    }
    devices.value = devices.value.filter((d) => d.id !== device.id)
    message.success(`Вышли на устройстве «${describeDevice(device.user_agent)}»`)
  } catch (e) {
    message.error(errorMessage(e))
  } finally {
    revokingId.value = null
  }
}
</script>

<template>
  <NSpin :show="loading">
    <ul class="devices">
      <li v-for="device in devices" :key="device.id">
        <div class="info">
          <div class="name">
            {{ describeDevice(device.user_agent) }}
            <NTag v-if="device.current" size="small" type="success" round>это устройство</NTag>
          </div>
          <div class="meta">
            вход {{ formatDateTime(device.created_at) }} · активность
            {{ formatDateTime(device.last_used_at) }}
          </div>
        </div>
        <NButton
          size="small"
          quaternary
          :loading="revokingId === device.id"
          @click="revoke(device)"
        >
          Выйти
        </NButton>
      </li>
    </ul>
  </NSpin>
</template>

<style scoped>
.devices {
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
}

.devices li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--color-rule);
}

.info {
  min-width: 0;
}

.name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-weight: 700;
}

.meta {
  color: var(--color-muted);
  font-size: 0.8125rem;
}
</style>
