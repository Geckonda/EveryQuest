<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSwitch,
  useDialog,
  useMessage,
} from 'naive-ui'
import { useRouter } from 'vue-router'
import { errorMessage } from '@/api/errors'
import { useAuthStore } from '@/stores/auth'
import { penaltyFor } from '@/utils/penalty'
import { playSound, soundEnabled } from '@/utils/sound'
import { useTheme } from '@/composables/useTheme'
import DeviceList from './DeviceList.vue'
import { useTour } from '@/composables/useTour'
import HelpHint from './HelpHint.vue'

const auth = useAuthStore()
const router = useRouter()
const dialog = useDialog()
const leavingAll = ref(false)
const { preference } = useTheme()
const message = useMessage()

const form = reactive({
  username: '',
  timezone: 'UTC',
  multiplier: 1 as number | null,
})
const error = ref<string | null>(null)
const saving = ref(false)

watch(
  () => auth.user,
  (user) => {
    if (!user) return
    Object.assign(form, {
      username: user.username,
      timezone: user.timezone,
      multiplier: user.penalty_multiplier,
    })
  },
  { immediate: true },
)

const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone
const timezoneOptions = Intl.supportedValuesOf('timeZone').map((tz) => ({ label: tz, value: tz }))

const example = computed(() => (form.multiplier === null ? null : penaltyFor(50, form.multiplier)))

const isComplete = computed(() => form.username.trim() !== '' && form.multiplier !== null)

const tour = useTour()

/** Обзор показывает разделы на главной — туда и переходим. */
async function replayTour() {
  await router.push('/')
  tour.start()
}

function confirmLogoutAll() {
  dialog.warning({
    title: 'Выйти на всех устройствах?',
    content: 'Все сессии будут закрыты сразу — на телефоне, ноутбуке и здесь.',
    positiveText: 'Выйти везде',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      leavingAll.value = true
      try {
        await auth.logoutAll()
        router.push({ name: 'login' })
      } catch (e) {
        message.error(errorMessage(e))
      } finally {
        leavingAll.value = false
      }
    },
  })
}

async function save() {
  if (!isComplete.value || form.multiplier === null) return
  error.value = null
  saving.value = true
  try {
    await auth.updateMe({
      username: form.username.trim(),
      timezone: form.timezone,
      penalty_multiplier: form.multiplier,
    })
    message.success('Профиль сохранён')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <NForm class="profile" @submit.prevent="save">
    <NFormItem label="Имя">
      <NInput v-model:value="form.username" :maxlength="64" />
    </NFormItem>
    <NFormItem label="Часовой пояс">
      <NSelect v-model:value="form.timezone" :options="timezoneOptions" filterable />
      <template v-if="browserTimezone && browserTimezone !== form.timezone" #feedback>
        На устройстве {{ browserTimezone }} ·
        <button type="button" class="link-button" @click="form.timezone = browserTimezone">
          подставить
        </button>
      </template>
    </NFormItem>
    <NFormItem>
      <template #label
        >Множитель штрафа
        <HelpHint
          text="Штраф нового квеста = награда × множитель. 0 — без штрафов, 2 — штраф вдвое больше награды. В форме квеста его всегда можно поменять."
      /></template>
      <NInputNumber
        v-model:value="form.multiplier"
        :min="0"
        :max="10"
        :step="0.25"
        :precision="2"
      />
      <template #feedback>
        <template v-if="example !== null">За квест на 50 — штраф {{ example }}</template>
      </template>
    </NFormItem>
    <p class="hint">
      Штраф нового квеста = награда × множитель; в форме квеста его можно поменять. По часовому
      поясу появляются повторяющиеся квесты.
    </p>
    <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
    <NButton type="primary" attr-type="submit" :loading="saving" :disabled="!isComplete">
      Сохранить
    </NButton>

    <h3 class="device-title">На этом устройстве</h3>
    <div class="device-row">
      <span class="device-label">Тема</span>
      <NRadioGroup v-model:value="preference" size="small">
        <NRadioButton value="light">Пергамент</NRadioButton>
        <NRadioButton value="dark">Свечи</NRadioButton>
        <NRadioButton value="system">Как в системе</NRadioButton>
      </NRadioGroup>
    </div>
    <div class="device-row">
      <label class="switch">
        <NSwitch v-model:value="soundEnabled" />
        Звон монет
      </label>
      <NButton size="small" quaternary :disabled="!soundEnabled" @click="playSound('reward')">
        Послушать
      </NButton>
    </div>
    <div class="device-row">
      <NButton size="small" secondary @click="replayTour">Показать обзор возможностей</NButton>
    </div>

    <h3 class="device-title">Безопасность</h3>
    <DeviceList />
    <p class="hint">
      Потеряли телефон или входили с чужого компьютера — выйдите везде. Войти заново придётся и
      здесь.
    </p>
    <NButton secondary type="error" :loading="leavingAll" @click="confirmLogoutAll">
      Выйти на всех устройствах
    </NButton>
  </NForm>
</template>

<style scoped>
.profile {
  max-width: 480px;
}

.hint {
  margin: 0 0 16px;
  color: var(--color-muted);
  font-size: 0.875rem;
  font-style: italic;
}

.error {
  margin-bottom: 16px;
}

.device-title {
  margin: 28px 0 8px;
  font-size: 1.15rem;
}

.device-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.device-row + .device-row {
  margin-top: 12px;
}

.device-label {
  min-width: 48px;
}

.switch {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
</style>
