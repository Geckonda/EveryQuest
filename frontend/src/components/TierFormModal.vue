<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NColorPicker,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  useMessage,
} from 'naive-ui'
import type { Tier, TierPayload } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { COLOR_SWATCHES, DEFAULT_COLOR } from './colors'

const props = defineProps<{ tier: Tier | null }>()
const show = defineModel<boolean>('show', { required: true })

const catalog = useCatalogStore()
const message = useMessage()

type NumberField = 'level' | 'default_reward'
// Числа null — поле очищено в форме; сохранять такое нельзя.
const form = reactive<Omit<TierPayload, NumberField> & Record<NumberField, number | null>>({
  name: '',
  level: 1,
  default_reward: 10,
  color: DEFAULT_COLOR,
})
const error = ref<string | null>(null)
const saving = ref(false)

watch(show, (opened) => {
  if (!opened) return
  error.value = null
  const t = props.tier
  Object.assign(form, {
    name: t?.name ?? '',
    level: t?.level ?? 1,
    default_reward: t?.default_reward ?? 10,
    color: t?.color ?? DEFAULT_COLOR,
  })
})

const isComplete = computed(
  () => form.name.trim() !== '' && form.level !== null && form.default_reward !== null,
)

async function save() {
  const { level, default_reward } = form
  if (level === null || default_reward === null) return
  error.value = null
  saving.value = true
  try {
    await catalog.saveTier(props.tier?.id ?? null, {
      name: form.name.trim(),
      level,
      default_reward,
      color: form.color,
    })
    message.success(props.tier ? 'Тир сохранён' : 'Тир создан')
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
    :title="tier ? 'Изменить тир' : 'Новый тир'"
    class="form-modal"
  >
    <NForm @submit.prevent="save">
      <NFormItem label="Название">
        <NInput v-model:value="form.name" :maxlength="64" placeholder="Например, III" />
      </NFormItem>
      <NFormItem label="Уровень (1–5, для сортировки)">
        <NInputNumber v-model:value="form.level" :min="1" :max="5" :precision="0" />
      </NFormItem>
      <NFormItem label="Награда" feedback="Штраф = награда × множитель из профиля">
        <NInputNumber v-model:value="form.default_reward" :min="0" :precision="0" />
      </NFormItem>
      <NFormItem label="Цвет">
        <NColorPicker
          v-model:value="form.color"
          :modes="['hex']"
          :show-alpha="false"
          :swatches="COLOR_SWATCHES"
        />
      </NFormItem>
      <p v-if="tier" class="hint">
        Новая награда применится к новым квестам. Уже созданные не изменятся.
      </p>
      <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
      <NButton type="primary" attr-type="submit" block :loading="saving" :disabled="!isComplete">
        Сохранить
      </NButton>
    </NForm>
  </NModal>
</template>
