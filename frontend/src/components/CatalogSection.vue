<script setup lang="ts" generic="T extends { id: number; is_archived: boolean }">
import { computed, ref } from 'vue'
import { NButton, NEmpty, NSwitch } from 'naive-ui'

const props = defineProps<{
  items: T[]
  addLabel: string
  emptyText: string
}>()

defineEmits<{
  add: []
  edit: [item: T]
  toggleArchive: [item: T]
}>()

defineSlots<{
  item(props: { item: T }): unknown
  /** Дополнительные кнопки для неархивного элемента (например, «Купить»). */
  actions?(props: { item: T }): unknown
  /** Поиск, сортировка — под кнопкой «Добавить». */
  toolbar?(): unknown
}>()

const showArchived = ref(false)
const archivedCount = computed(() => props.items.filter((i) => i.is_archived).length)
const visible = computed(() =>
  showArchived.value ? props.items : props.items.filter((i) => !i.is_archived),
)
</script>

<template>
  <section>
    <div class="toolbar">
      <NButton type="primary" size="small" @click="$emit('add')">{{ addLabel }}</NButton>
      <label v-if="archivedCount" class="archive-switch">
        <NSwitch v-model:value="showArchived" size="small" />
        Архив ({{ archivedCount }})
      </label>
    </div>
    <slot name="toolbar" />

    <NEmpty v-if="!visible.length" :description="emptyText" class="empty" />
    <ul v-else class="list">
      <li v-for="item in visible" :key="item.id" :class="{ archived: item.is_archived }">
        <div class="content">
          <slot name="item" :item="item" />
        </div>
        <div class="actions">
          <slot v-if="!item.is_archived" name="actions" :item="item" />
          <NButton v-if="!item.is_archived" size="small" quaternary @click="$emit('edit', item)">
            Изменить
          </NButton>
          <NButton size="small" quaternary @click="$emit('toggleArchive', item)">
            {{ item.is_archived ? 'Вернуть' : 'В архив' }}
          </NButton>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.archive-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-muted);
  font-size: 0.875rem;
  cursor: pointer;
}

.empty {
  padding: 32px 0;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px dashed var(--color-rule);
}

.list li.archived .content {
  opacity: 0.5;
}

.content {
  min-width: 0;
  flex: 1;
}

.actions {
  display: flex;
  flex: none;
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* На телефоне кнопки уходят под содержимое, иначе сжимают его в узкую колонку. */
@media (max-width: 560px) {
  .list li {
    flex-wrap: wrap;
    gap: 6px;
  }

  .content {
    flex-basis: 100%;
  }

  .actions {
    flex: 1 1 100%;
    justify-content: flex-start;
  }

  .toolbar {
    flex-wrap: wrap;
  }
}
</style>
