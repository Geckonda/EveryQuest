<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { NAlert, NButton, NCard, NForm, NFormItem, NInput } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { errorMessage } from '@/api/errors'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

async function submit() {
  error.value = null
  loading.value = true
  try {
    await auth.login(email.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <NCard class="auth-card" title="Вход в таверну">
      <p class="auth-intro">Скрипит дверь, пахнет элем и свежим хлебом. Назовитесь, путник.</p>
      <NForm @submit.prevent="submit">
        <NFormItem label="Email">
          <NInput
            v-model:value="email"
            :input-props="{ type: 'email', autocomplete: 'email' }"
            placeholder="you@example.com"
          />
        </NFormItem>
        <NFormItem label="Пароль">
          <NInput
            v-model:value="password"
            type="password"
            show-password-on="click"
            :input-props="{ autocomplete: 'current-password' }"
          />
        </NFormItem>
        <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
        <NButton
          type="primary"
          attr-type="submit"
          block
          :loading="loading"
          :disabled="!email || !password"
        >
          Войти
        </NButton>
      </NForm>
      <p class="switch">
        Впервые здесь? <RouterLink to="/register">Вступить в гильдию</RouterLink>
      </p>
    </NCard>
  </div>
</template>

<style scoped>
.auth-page {
  max-width: 400px;
  margin: 32px auto;
}

.error {
  margin-bottom: 16px;
}

.switch {
  margin: 16px 0 0;
  text-align: center;
}
</style>
