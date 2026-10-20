import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { setAuthHandler } from './api/client'
import { useAuthStore } from './stores/auth'

const app = createApp(App)

app.use(createPinia())

const auth = useAuthStore()
setAuthHandler({
  getAccessToken: () => auth.accessToken,
  refresh: auth.refresh,
  onUnauthorized: () => {
    auth.logout()
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  },
})

app.use(router)

app.mount('#app')
