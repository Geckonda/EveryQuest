<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  useMessage,
} from 'naive-ui'
import type { Reward, RewardPayload } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'

const props = defineProps<{ reward: Reward | null }>()
const show = defineModel<boolean>('show', { required: true })

const catalog = useCatalogStore()
const message = useMessage()

// price: null — поле очищено в форме; сохранять такое нельзя.
const form = reactive<Omit<RewardPayload, 'price'> & { price: number | null }>({
  name: '',
  description: null,
  price: 10,
  duration_minutes: null,
})
const error = ref<string | null>(null)
const saving = ref(false)

watch(show, (opened) => {
  if (!opened) return
  error.value = null
  const r = props.reward
  Object.assign(form, {
    name: r?.name ?? '',
    description: r?.description ?? null,
    price: r?.price ?? 10,
    duration_minutes: r?.duration_minutes ?? null,
  })
})

async function save() {
  if (form.price === null) return
  error.value = null
  saving.value = true
  try {
    await catalog.saveReward(props.reward?.id ?? null, {
      ...form,
      price: form.price,
      name: form.name.trim(),
      description: form.description?.trim() || null,
    })
    message.success(props.reward ? 'Трата сохранена' : 'Трата создана')
    show.value = false
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <NModal
    v-model:show="show"
    preset="card"
    :title="reward ? 'Изменить трату' : 'Новая трата'"
    class="form-modal"
  >
    <NForm @submit.prevent="save">
      <NFormItem label="Название">
        <NInput v-model:value="form.name" :maxlength="200" placeholder="Например, Серия сериала" />
      </NFormItem>
      <NFormItem label="Описание">
        <NInput
          v-model:value="form.description"
          type="textarea"
          :maxlength="2000"
          :autosize="{ minRows: 2, maxRows: 5 }"
          placeholder="Необязательно"
        />
      </NFormItem>
      <div class="row">
        <NFormItem label="Цена, монет">
          <NInputNumber v-model:value="form.price" :min="0" :precision="0" />
        </NFormItem>
        <NFormItem label="Длительность, мин">
          <NInputNumber
            v-model:value="form.duration_minutes"
            :min="1"
            :max="10080"
            :precision="0"
            clearable
            placeholder="Не задана"
          />
        </NFormItem>
      </div>
      <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
      <NButton
        type="primary"
        attr-type="submit"
        block
        :loading="saving"
        :disabled="!form.name.trim() || form.price === null"
      >
        Сохранить
      </NButton>
    </NForm>
  </NModal>
</template>
