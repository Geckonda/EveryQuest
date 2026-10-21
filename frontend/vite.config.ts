import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      // xfwd — передать бэкенду настоящий IP (X-Forwarded-For): по нему лимит попыток входа.
      '/api': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8000', xfwd: true },
    },
    // В Docker на Windows события файловой системы не доходят до контейнера.
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true' },
  },
})
