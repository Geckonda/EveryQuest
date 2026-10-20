<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NRadioButton,
  NRadioGroup,
  useMessage,
} from 'naive-ui'
import { api } from '@/api/client'
import type { BalanceChange } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useAuthStore } from '@/stores/auth'
import { coins } from '@/utils/format'

const show = defineModel<boolean>('show', { required: true })
const emit = defineEmits<{ saved: [] }>()

const auth = useAuthStore()
const message = useMessage()

const direction = ref<'add' | 'subtract'>('add')
const amount = ref<number | null>(null)
const note = ref('')
const error = ref<string | null>(null)
const saving = ref(false)

const signedAmount = computed(() =>
  amount.value ? (direction.value === 'add' ? amount.value : -amount.value) : 0,
)

watch(show, (opened) => {
  if (!opened) return
  direction.value = 'add'
  amount.value = null
  note.value = ''
  error.value = null
})

async function save() {
  if (!signedAmount.value) return
  error.value = null
  saving.value = true
  try {
    const result = await api.post<BalanceChange>('/transactions/manual', {
      amount: signedAmount.value,
      note: note.value.trim() || null,
    })
    auth.setBalance(result.balance)
    message.success(`Баланс: ${coins(result.balance)}`)
    emit('saved')
    show.value = false
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <NModal v-model:show="show" preset="card" title="Ручная корректировка" class="form-modal">
    <p class="hint">
      Для исправления ошибок: например, квест отмечен выполненным по ошибке. В минус вручную уйти
      нельзя.
    </p>
    <NForm @submit.prevent="save">
      <NFormItem label="Действие">
        <NRadioGroup v-model:value="direction">
          <NRadioButton value="add">Начислить</NRadioButton>
          <NRadioButton value="subtract">Списать</NRadioButton>
        </NRadioGroup>
      </NFormItem>
      <NFormItem label="Сумма">
        <NInputNumber v-model:value="amount" :min="1" :max="1000000" :precision="0" />
      </NFormItem>
      <NFormItem label="Комментарий">
        <NInput v-model:value="note" :maxlength="2000" placeholder="Почему меняем баланс" />
      </NFormItem>
      <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
      <NButton type="primary" attr-type="submit" block :loading="saving" :disabled="!signedAmount">
        Сохранить
      </NButton>
    </NForm>
  </NModal>
</template>
