<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { NAlert, NButton, NCard, NForm, NFormItem, NInput } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { errorMessage } from '@/api/errors'
import { useTour } from '@/composables/useTour'

const MIN_PASSWORD = 8

const auth = useAuthStore()
const router = useRouter()
const { start: startTour } = useTour()

const email = ref('')
const username = ref('')
const password = ref('')
const passwordRepeat = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

const passwordTooShort = computed(
  () => password.value.length > 0 && password.value.length < MIN_PASSWORD,
)
const passwordsDiffer = computed(
  () => passwordRepeat.value.length > 0 && password.value !== passwordRepeat.value,
)
const canSubmit = computed(
  () =>
    email.value.trim() &&
    username.value.trim() &&
    password.value.length >= MIN_PASSWORD &&
    password.value === passwordRepeat.value,
)

async function submit() {
  if (!canSubmit.value) return
  error.value = null
  loading.value = true
  try {
    await auth.register({
      email: email.value.trim(),
      username: username.value.trim(),
      password: password.value,
      timezone,
    })
    await router.replace('/')
    // Новичку — обзор возможностей, один раз сразу после регистрации.
    startTour()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <NCard class="auth-card" title="Вступить в гильдию">
      <p class="auth-intro">Впишите имя в книгу гильдии — и доска квестов откроется для вас.</p>
      <NForm @submit.prevent="submit">
        <NFormItem label="Email">
          <NInput
            v-model:value="email"
            :input-props="{ type: 'email', autocomplete: 'email' }"
            placeholder="you@example.com"
          />
        </NFormItem>
        <NFormItem label="Имя в гильдии">
          <NInput
            v-model:value="username"
            :maxlength="64"
            :input-props="{ autocomplete: 'nickname' }"
          />
        </NFormItem>
        <NFormItem
          label="Пароль"
          :validation-status="passwordTooShort ? 'error' : undefined"
          :feedback="passwordTooShort ? `Минимум ${MIN_PASSWORD} символов` : undefined"
        >
          <NInput
            v-model:value="password"
            type="password"
            show-password-on="click"
            :input-props="{ autocomplete: 'new-password' }"
          />
        </NFormItem>
        <NFormItem
          label="Пароль ещё раз"
          :validation-status="passwordsDiffer ? 'error' : undefined"
          :feedback="passwordsDiffer ? 'Пароли не совпадают' : undefined"
        >
          <NInput
            v-model:value="passwordRepeat"
            type="password"
            show-password-on="click"
            :input-props="{ autocomplete: 'new-password' }"
          />
        </NFormItem>
        <p class="hint">Часовой пояс: {{ timezone }}</p>
        <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
        <NButton type="primary" attr-type="submit" block :loading="loading" :disabled="!canSubmit">
          Вступить
        </NButton>
      </NForm>
      <p class="switch">Уже в гильдии? <RouterLink to="/login">Войти</RouterLink></p>
    </NCard>
  </div>
</template>

<style scoped>
.auth-page {
  max-width: 400px;
  margin: 32px auto;
}

.hint {
  margin: 0 0 16px;
  color: var(--color-muted);
  font-size: 0.875rem;
}

.error {
  margin-bottom: 16px;
}

.switch {
  margin: 16px 0 0;
  text-align: center;
}
</style>
