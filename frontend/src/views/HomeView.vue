<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { NAlert, NButton, NEmpty, NSpin, NTabPane, NTabs, useDialog, useMessage } from 'naive-ui'
import type { Quest } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { useCatalogStore } from '@/stores/catalog'
import { useQuestsStore } from '@/stores/quests'
import QuestCard from '@/components/QuestCard.vue'
import QuestFormModal from '@/components/QuestFormModal.vue'

const catalog = useCatalogStore()
const quests = useQuestsStore()
const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const loadError = ref<string | null>(null)
const historyLoaded = ref(false)
const historyLoading = ref(false)
const busyId = ref<number | null>(null)

const modal = ref(false)
const edited = ref<Quest | null>(null)

// Тикающее «сейчас»: просроченные квесты помечаются без перезагрузки страницы.
const now = ref(new Date())
let timer: ReturnType<typeof setInterval> | undefined

onMounted(async () => {
  timer = setInterval(() => (now.value = new Date()), 30_000)
  try {
    await Promise.all([catalog.load(), quests.loadActive()])
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})

onUnmounted(() => clearInterval(timer))

async function onTabChange(tab: string) {
  if (tab !== 'history' || historyLoaded.value) return
  historyLoading.value = true
  try {
    await quests.loadHistory()
    historyLoaded.value = true
  } catch (e) {
    message.error(errorMessage(e))
  } finally {
    historyLoading.value = false
  }
}

function open(quest: Quest | null) {
  edited.value = quest
  modal.value = true
}

async function complete(quest: Quest) {
  busyId.value = quest.id
  try {
    await quests.complete(quest.id)
    message.success(`+${quest.reward} — «${quest.name}» выполнен`)
  } catch (e) {
    message.error(errorMessage(e))
    await quests.loadActive().catch(() => {})
  } finally {
    busyId.value = null
  }
}

function archive(quest: Quest) {
  dialog.warning({
    title: 'Убрать квест?',
    content: `«${quest.name}» исчезнет из списка без награды и без штрафа.`,
    positiveText: 'Убрать',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await quests.update(quest.id, { status: 'archived' })
      } catch (e) {
        message.error(errorMessage(e))
      }
    },
  })
}

const tierOf = (quest: Quest) => catalog.tiers.find((t) => t.id === quest.tier_id)
const categoryOf = (quest: Quest) => catalog.categories.find((c) => c.id === quest.category_id)
</script>

<template>
  <div class="title-row">
    <h1>Квесты</h1>
    <NButton type="primary" :disabled="loading || !!loadError" @click="open(null)">
      Новый квест
    </NButton>
  </div>

  <NAlert v-if="loadError" type="error">{{ loadError }}</NAlert>
  <NSpin v-else :show="loading">
    <NTabs type="line" animated @update:value="onTabChange">
      <NTabPane name="active" :tab="`Активные (${quests.active.length})`">
        <NEmpty
          v-if="!quests.active.length"
          description="Активных квестов нет. Добавьте первый — и зарабатывайте монеты"
          class="empty"
        />
        <QuestCard
          v-for="quest in quests.active"
          :key="quest.id"
          :quest="quest"
          :tier="tierOf(quest)"
          :category="categoryOf(quest)"
          :now="now"
          :busy="busyId === quest.id"
          @complete="complete(quest)"
          @edit="open(quest)"
          @archive="archive(quest)"
        />
      </NTabPane>
      <NTabPane name="history" tab="История">
        <NSpin :show="historyLoading">
          <NEmpty
            v-if="historyLoaded && !quests.history.length"
            description="Пока пусто"
            class="empty"
          />
          <QuestCard
            v-for="quest in quests.history"
            :key="quest.id"
            :quest="quest"
            :tier="tierOf(quest)"
            :category="categoryOf(quest)"
            :now="now"
          />
        </NSpin>
      </NTabPane>
    </NTabs>
  </NSpin>

  <QuestFormModal v-model:show="modal" :quest="edited" />
</template>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

h1 {
  margin: 0;
  font-size: 1.5rem;
}

.empty {
  padding: 32px 0;
}
</style>
