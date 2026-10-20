<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NDatePicker,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NTimePicker,
  useMessage,
} from 'naive-ui'
import type { Frequency, RecurringPayload, RecurringQuest } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { useRecurringStore } from '@/stores/recurring'
import { plural } from '@/utils/format'
import { WEEKDAYS, describeSchedule } from '@/utils/schedule'

const props = defineProps<{ template: RecurringQuest | null }>()
const show = defineModel<boolean>('show', { required: true })

const catalog = useCatalogStore()
const recurring = useRecurringStore()
const message = useMessage()

function todayIso(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const form = reactive({
  name: '',
  description: null as string | null,
  tierId: null as number | null,
  categoryId: null as number | null,
  reward: null as number | null,
  penalty: null as number | null,
  frequency: 'daily' as Frequency,
  interval: 1 as number | null,
  daysOfWeek: [] as number[],
  dayOfMonth: null as number | null,
  /** «HH:mm» — formatted-value пикера. */
  dueTime: '23:59' as string | null,
  startDate: todayIso() as string | null,
  endDate: null as string | null,
})
const error = ref<string | null>(null)
const saving = ref(false)

const tierOptions = computed(() =>
  catalog.activeTiers.map((t) => ({
    label: `${t.name} (+${t.default_reward} / −${t.default_penalty})`,
    value: t.id,
  })),
)
const categoryOptions = computed(() =>
  catalog.activeCategories.map((c) => ({ label: c.name, value: c.id })),
)
const dayOfMonthOptions = [
  ...Array.from({ length: 30 }, (_, i) => ({ label: `${i + 1}-е`, value: i + 1 })),
  { label: 'Последний день', value: 31 },
]

const intervalUnit = computed(() => {
  const n = form.interval ?? 1
  if (form.frequency === 'daily') return plural(n, 'день', 'дня', 'дней')
  if (form.frequency === 'weekly') return plural(n, 'неделю', 'недели', 'недель')
  return plural(n, 'месяц', 'месяца', 'месяцев')
})

let filling = false

watch(show, (opened) => {
  if (!opened) return
  error.value = null
  const t = props.template
  const tier = catalog.activeTiers[0]
  filling = true
  Object.assign(form, {
    name: t?.name ?? '',
    description: t?.description ?? null,
    tierId: t?.tier_id ?? tier?.id ?? null,
    categoryId: t?.category_id ?? null,
    reward: t?.reward ?? tier?.default_reward ?? null,
    penalty: t?.penalty ?? tier?.default_penalty ?? null,
    frequency: t?.frequency ?? 'daily',
    interval: t?.interval ?? 1,
    daysOfWeek: t?.days_of_week ?? [],
    dayOfMonth: t?.day_of_month ?? null,
    dueTime: t?.due_time.slice(0, 5) ?? '23:59',
    startDate: t?.start_date ?? todayIso(),
    endDate: t?.end_date ?? null,
  })
  filling = false
})

watch(
  () => form.tierId,
  (tierId) => {
    if (filling) return
    const tier = catalog.tiers.find((t) => t.id === tierId)
    if (tier) {
      form.reward = tier.default_reward
      form.penalty = tier.default_penalty
    }
  },
  // sync: иначе сработает после заполнения формы и затрёт награду редактируемого шаблона.
  { flush: 'sync' },
)

const payload = computed((): RecurringPayload | null => {
  const { tierId, reward, penalty, interval, dueTime, startDate } = form
  if (!form.name.trim() || tierId === null || reward === null || penalty === null) return null
  if (interval === null || dueTime === null || startDate === null) return null
  return {
    name: form.name.trim(),
    description: form.description?.trim() || null,
    tier_id: tierId,
    category_id: form.categoryId,
    reward,
    penalty,
    frequency: form.frequency,
    interval,
    // Поля чужой частоты сбрасываем — бэкенд не примет, например, дни недели у daily.
    days_of_week: form.frequency === 'weekly' && form.daysOfWeek.length ? form.daysOfWeek : null,
    day_of_month: form.frequency === 'monthly' ? form.dayOfMonth : null,
    due_time: dueTime,
    start_date: startDate,
    end_date: form.endDate,
  }
})

const preview = computed(() =>
  payload.value
    ? describeSchedule({ ...payload.value, due_time: `${payload.value.due_time}:00` })
    : '',
)

async function save() {
  if (!payload.value) return
  error.value = null
  saving.value = true
  try {
    await recurring.save(props.template?.id ?? null, payload.value)
    message.success(props.template ? 'Шаблон сохранён' : 'Повторяющийся квест создан')
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
    :title="template ? 'Изменить повторяющийся квест' : 'Новый повторяющийся квест'"
    class="form-modal"
  >
    <NForm @submit.prevent="save">
      <NFormItem label="Название">
        <NInput v-model:value="form.name" :maxlength="200" placeholder="Например, Зарядка" />
      </NFormItem>
      <NFormItem label="Описание">
        <NInput
          v-model:value="form.description"
          type="textarea"
          :maxlength="2000"
          :autosize="{ minRows: 1, maxRows: 4 }"
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
          <NInputNumber v-model:value="form.penalty" :min="0" :precision="0" />
        </NFormItem>
      </div>

      <NFormItem label="Повторять">
        <NRadioGroup v-model:value="form.frequency">
          <NRadioButton value="daily">Ежедневно</NRadioButton>
          <NRadioButton value="weekly">Еженедельно</NRadioButton>
          <NRadioButton value="monthly">Ежемесячно</NRadioButton>
        </NRadioGroup>
      </NFormItem>

      <div class="row">
        <NFormItem :label="`Каждые N (${intervalUnit})`">
          <NInputNumber v-model:value="form.interval" :min="1" :max="365" :precision="0" />
        </NFormItem>
        <NFormItem label="До какого времени">
          <NTimePicker
            v-model:formatted-value="form.dueTime"
            value-format="HH:mm"
            format="HH:mm"
            :actions="null"
          />
        </NFormItem>
      </div>

      <NFormItem
        v-if="form.frequency === 'weekly'"
        label="Дни недели"
        :feedback="
          form.daysOfWeek.length ? undefined : 'Не выбраны — раз в неделю, срок в воскресенье'
        "
      >
        <NCheckboxGroup v-model:value="form.daysOfWeek">
          <NCheckbox v-for="(day, i) in WEEKDAYS" :key="day" :value="i + 1" :label="day" />
        </NCheckboxGroup>
      </NFormItem>

      <NFormItem v-if="form.frequency === 'monthly'" label="Число месяца">
        <NSelect
          v-model:value="form.dayOfMonth"
          :options="dayOfMonthOptions"
          clearable
          placeholder="Без числа — срок в последний день"
        />
      </NFormItem>

      <div class="row">
        <NFormItem label="Начало">
          <NDatePicker
            v-model:formatted-value="form.startDate"
            type="date"
            value-format="yyyy-MM-dd"
            format="dd.MM.yyyy"
          />
        </NFormItem>
        <NFormItem label="Окончание">
          <NDatePicker
            v-model:formatted-value="form.endDate"
            type="date"
            value-format="yyyy-MM-dd"
            format="dd.MM.yyyy"
            clearable
            placeholder="Бессрочно"
          />
        </NFormItem>
      </div>

      <p v-if="preview" class="hint">
        {{ preview }}. Квест появляется в начале периода. Если срок сегодняшнего уже прошёл, первый
        появится в следующий раз.
      </p>
      <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
      <NButton type="primary" attr-type="submit" block :loading="saving" :disabled="!payload">
        Сохранить
      </NButton>
    </NForm>
  </NModal>
</template>
