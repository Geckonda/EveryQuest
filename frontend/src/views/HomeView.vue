<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { NCard } from 'naive-ui'
</script>

<template>
  <h1>Квесты</h1>
  <!-- Временная заглушка: список квестов появится на этапе 4. -->
  <NCard size="small">
    <p class="text">
      Здесь будут ваши квесты. А пока настройте под себя
      <RouterLink to="/settings">тиры и категории</RouterLink> и добавьте
      <RouterLink to="/rewards">траты</RouterLink>, ради которых стоит их выполнять.
    </p>
  </NCard>
</template>

<style scoped>
h1 {
  margin: 0 0 12px;
  font-size: 1.5rem;
}

.text {
  margin: 0;
}
</style>
