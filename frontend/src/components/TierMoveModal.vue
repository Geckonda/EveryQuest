<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NAlert, NButton, NModal, NSelect, useMessage } from 'naive-ui'
import type { Tier, TierInUse } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { plural } from '@/utils/format'

/** Удаление тира, у которого есть квесты: куда их перенести. */
const props = defineProps<{ tier: Tier | null; usage: TierInUse | null }>()
const show = defineModel<boolean>('show', { required: true })

const catalog = useCatalogStore()
const message = useMessage()

const target = ref<number | null>(null)
const saving = ref(false)
const error = ref<string | null>(null)

const options = computed(() =>
  catalog.activeTiers
    .filter((t) => t.id !== props.tier?.id)
    .map((t) => ({ label: `${t.name} (+${t.default_reward})`, value: t.id })),
)

const summary = computed(() => {
  const u = props.usage
  if (!u) return ''
  const parts = []
  if (u.quests) parts.push(`${u.quests} ${plural(u.quests, 'квест', 'квеста', 'квестов')}`)
  if (u.recurring_quests) {
    parts.push(
      `${u.recurring_quests} ${plural(u.recurring_quests, 'повторяющийся', 'повторяющихся', 'повторяющихся')}`,
    )
  }
  return parts.join(' и ')
})

watch(show, (opened) => {
  if (!opened) return
  error.value = null
  target.value = options.value[0]?.value ?? null
})

async function confirm() {
  if (!props.tier || target.value === null) return
  saving.value = true
  error.value = null
  try {
    await catalog.removeTier(props.tier.id, target.value)
    message.success(`Тир «${props.tier.name}» удалён, квесты перенесены`)
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
    :title="tier ? `Удалить тир «${tier.name}»` : 'Удалить тир'"
    class="form-modal"
  >
    <p class="text">
      У этого тира {{ summary }} — в том числе закрытые, в архиве. Без тира квест не живёт, поэтому
      их нужно перенести. Награды и штрафы у квестов не изменятся — поменяется только печать.
    </p>
    <NSelect v-model:value="target" :options="options" placeholder="Куда перенести" />
    <NAlert v-if="error" type="error" class="error">{{ error }}</NAlert>
    <NButton
      type="error"
      block
      class="confirm"
      :loading="saving"
      :disabled="target === null"
      @click="confirm"
    >
      Перенести и удалить
    </NButton>
  </NModal>
</template>

<style scoped>
.text {
  margin: 0 0 12px;
}

.error {
  margin-top: 12px;
}

.confirm {
  margin-top: 16px;
}
</style>
