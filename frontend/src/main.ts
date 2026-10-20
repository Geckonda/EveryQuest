// Шрифты локально, а не с Google Fonts: будут работать и офлайн в PWA.
import '@fontsource/alegreya/400.css'
import '@fontsource/alegreya/400-italic.css'
import '@fontsource/alegreya/700.css'
import '@fontsource/cormorant-garamond/600.css'
import '@fontsource/cormorant-garamond/700.css'
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
