<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NColorPicker,
  NForm,
  NFormItem,
  NInput,
  NModal,
  useMessage,
} from 'naive-ui'
import type { Category, CategoryPayload } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { COLOR_SWATCHES, DEFAULT_COLOR } from './colors'

const props = defineProps<{ category: Category | null }>()
const show = defineModel<boolean>('show', { required: true })

const catalog = useCatalogStore()
const message = useMessage()

const form = reactive<CategoryPayload>({ name: '', description: null, color: DEFAULT_COLOR })
const error = ref<string | null>(null)
const saving = ref(false)

watch(show, (opened) => {
  if (!opened) return
  error.value = null
  const c = props.category
  Object.assign(form, {
    name: c?.name ?? '',
    description: c?.description ?? null,
    color: c?.color ?? DEFAULT_COLOR,
  })
})

async function save() {
  error.value = null
  saving.value = true
  try {
    await catalog.saveCategory(props.category?.id ?? null, {
      ...form,
      name: form.name.trim(),
      description: form.description?.trim() || null,
    })
    message.success(props.category ? 'Категория сохранена' : 'Категория создана')
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
    :title="category ? 'Изменить категорию' : 'Новая категория'"
    class="form-modal"
  >
    <NForm @submit.prevent="save">
      <NFormItem label="Название">
        <NInput v-model:value="form.name" :maxlength="64" placeholder="Например, Спорт" />
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
      <NFormItem label="Цвет">
        <NColorPicker
          v-model:value="form.color"
          :modes="['hex']"
          :show-alpha="false"
          :swatches="COLOR_SWATCHES"
        />
      </NFormItem>
      <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
      <NButton
        type="primary"
        attr-type="submit"
        block
        :loading="saving"
        :disabled="!form.name.trim()"
      >
        Сохранить
      </NButton>
    </NForm>
  </NModal>
</template>
