<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { NAlert, NButton, NEmpty, NSpin, NTabPane, NTabs, useDialog, useMessage } from 'naive-ui'
import type { Quest } from '@/api/types'
import { errorMessage } from '@/api/errors'
import { coins } from '@/utils/format'
import { useCatalogStore } from '@/stores/catalog'
import { useQuestsStore } from '@/stores/quests'
import { useRecurringStore } from '@/stores/recurring'
import QuestCard from '@/components/QuestCard.vue'
import RecurringList from '@/components/RecurringList.vue'
import QuestFormModal from '@/components/QuestFormModal.vue'

const catalog = useCatalogStore()
const quests = useQuestsStore()
const recurring = useRecurringStore()
const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const loadError = ref<string | null>(null)
const historyLoaded = ref(false)
const historyLoading = ref(false)
const recurringLoading = ref(false)
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
  if (tab === 'recurring') {
    // Шаблоны перечитываем при каждом открытии: next_due_at зависит от текущего времени.
    recurringLoading.value = true
    try {
      await recurring.load()
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      recurringLoading.value = false
    }
    return
  }
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
    message.success(`Квест «${quest.name}» сдан. Награда: ${coins(quest.reward)}`)
  } catch (e) {
    message.error(errorMessage(e))
    await quests.loadActive().catch(() => {})
  } finally {
    busyId.value = null
  }
}

function archive(quest: Quest) {
  dialog.warning({
    title: 'Снять объявление с доски?',
    content: `«${quest.name}» исчезнет без награды и без штрафа.`,
    positiveText: 'Снять',
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
    <div>
      <h1 class="page-title">Доска квестов</h1>
      <p class="page-subtitle">Любишь кататься — люби и саночки возить</p>
    </div>
    <NButton type="primary" :disabled="loading || !!loadError" @click="open(null)">
      Повесить квест
    </NButton>
  </div>
  <div class="flourish">✦</div>

  <NAlert v-if="loadError" type="error">{{ loadError }}</NAlert>
  <NSpin v-else :show="loading">
    <NTabs type="line" animated @update:value="onTabChange">
      <NTabPane name="active" :tab="`Открытые (${quests.active.length})`">
        <NEmpty
          v-if="!quests.active.length"
          description="Доска пуста. Повесьте первый квест — и зарабатывайте золото на отдых"
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
      <NTabPane name="history" tab="Архив">
        <NSpin :show="historyLoading">
          <NEmpty
            v-if="historyLoaded && !quests.history.length"
            description="Пока ни одного закрытого квеста"
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
      <NTabPane name="recurring" tab="Повторяющиеся">
        <NSpin :show="recurringLoading">
          <RecurringList />
        </NSpin>
      </NTabPane>
    </NTabs>
  </NSpin>

  <QuestFormModal v-model:show="modal" :quest="edited" />
</template>

<style scoped>
.title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.empty {
  padding: 32px 0;
}
</style>
