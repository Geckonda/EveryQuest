<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NDatePicker,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  useMessage,
} from 'naive-ui'
import type { Quest } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { useQuestsStore } from '@/stores/quests'
import { useRewardFields } from '@/composables/useRewardFields'
import PenaltyHint from './PenaltyHint.vue'

const props = defineProps<{ quest: Quest | null }>()
const show = defineModel<boolean>('show', { required: true })

const catalog = useCatalogStore()
const quests = useQuestsStore()
const message = useMessage()

const form = reactive({
  name: '',
  description: null as string | null,
  tierId: null as number | null,
  categoryId: null as number | null,
  reward: null as number | null,
  penalty: null as number | null,
  /** Срок как timestamp (мс) для NDatePicker. */
  due: null as number | null,
})
const error = ref<string | null>(null)
const saving = ref(false)

const { reset, setPenalty, resetPenalty, penaltyTouched } = useRewardFields(form)

const tierOptions = computed(() =>
  catalog.activeTiers.map((t) => ({ label: `${t.name} (+${t.default_reward})`, value: t.id })),
)
const categoryOptions = computed(() =>
  catalog.activeCategories.map((c) => ({ label: c.name, value: c.id })),
)

function endOfDay(daysFromToday: number): number {
  const d = new Date()
  d.setDate(d.getDate() + daysFromToday)
  d.setHours(23, 59, 0, 0)
  return d.getTime()
}

const shortcuts = {
  'Сегодня 23:59': () => endOfDay(0),
  'Завтра 23:59': () => endOfDay(1),
  'Через неделю': () => endOfDay(7),
}

function isPastDay(ts: number): boolean {
  return ts < new Date().setHours(0, 0, 0, 0)
}

watch(show, (opened) => {
  if (!opened) return
  error.value = null
  const q = props.quest
  const tier = catalog.activeTiers[0]
  Object.assign(form, {
    name: q?.name ?? '',
    description: q?.description ?? null,
    categoryId: q?.category_id ?? null,
    // Новый квест — по умолчанию до конца дня; у существующего срок как есть.
    due: q ? (q.due_at ? new Date(q.due_at).getTime() : null) : endOfDay(0),
  })
  if (q) reset(q.tier_id, q.reward, q.penalty)
  else reset(tier?.id ?? null, tier?.default_reward ?? null, null)
})

const isComplete = computed(
  () =>
    form.name.trim() !== '' &&
    form.tierId !== null &&
    form.reward !== null &&
    form.penalty !== null,
)

async function save() {
  const { tierId, reward, penalty } = form
  if (!isComplete.value || tierId === null || reward === null || penalty === null) return
  error.value = null
  saving.value = true
  const payload = {
    name: form.name.trim(),
    description: form.description?.trim() || null,
    tier_id: tierId,
    category_id: form.categoryId,
    reward,
    penalty,
    due_at: form.due === null ? null : new Date(form.due).toISOString(),
  }
  try {
    if (props.quest) await quests.update(props.quest.id, payload)
    else await quests.create(payload)
    message.success(props.quest ? 'Квест сохранён' : 'Квест создан')
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
    :title="quest ? 'Изменить квест' : 'Новый квест'"
    class="form-modal"
  >
    <NAlert v-if="!catalog.activeTiers.length" type="warning" class="error">
      Нет ни одного активного тира — верните тир из архива в настройках.
    </NAlert>
    <NForm @submit.prevent="save">
      <NFormItem label="Название">
        <NInput v-model:value="form.name" :maxlength="200" placeholder="Например, Пробежка 5 км" />
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
        <NFormItem label="Тир">
          <NSelect v-model:value="form.tierId" :options="tierOptions" />
        </NFormItem>
        <NFormItem label="Категория">
          <NSelect
            v-model:value="form.categoryId"
            :options="categoryOptions"
            clearable
            placeholder="Без категории"
          />
        </NFormItem>
      </div>
      <div class="row">
        <NFormItem label="Награда">
          <NInputNumber v-model:value="form.reward" :min="0" :precision="0" />
        </NFormItem>
        <NFormItem label="Штраф">
          <NInputNumber :value="form.penalty" :min="0" :precision="0" @update:value="setPenalty" />
          <template #feedback>
            <PenaltyHint :touched="penaltyTouched" @reset="resetPenalty" />
          </template>
        </NFormItem>
      </div>
      <NFormItem label="Срок">
        <NDatePicker
          v-model:value="form.due"
          type="datetime"
          format="dd.MM.yyyy HH:mm"
          clearable
          placeholder="Без срока"
          :shortcuts="shortcuts"
          :is-date-disabled="isPastDay"
          style="width: 100%"
        />
      </NFormItem>
      <p class="hint">
        Не выполните до срока — спишется штраф. Без срока квест висит, пока не выполните.
      </p>
      <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
      <NButton type="primary" attr-type="submit" block :loading="saving" :disabled="!isComplete">
        Сохранить
      </NButton>
    </NForm>
  </NModal>
</template>
