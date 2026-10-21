import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    // PWA: установка на телефон (иконка, полный экран) и мгновенный запуск — оболочка
    // приложения кэшируется. Данные API не кэшируются никогда: они всегда с сервера.
    VitePWA({
      // prompt — новая версия ждёт согласия пользователя (плашка «Обновить»), а не
      // подменяет приложение посреди заполнения формы.
      registerType: 'prompt',
      includeAssets: ['favicon.svg', 'icons/favicon-32.png', 'icons/apple-touch-icon.png'],
      manifest: {
        name: 'Ежеквестик',
        short_name: 'Ежеквестик',
        description: 'Квесты за золото, отдых — за заработанное',
        lang: 'ru',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait',
        // Цвет вывески: полоса состояния и заставка при запуске.
        theme_color: '#2b1d10',
        background_color: '#2b1d10',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: '/icons/icon-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // Оболочка: скрипты, стили, шрифты, иконки. Шрифты — только woff2 (его понимают все
        // современные браузеры) и без греческого и вьетнамского: из 2,2 МБ остаётся 1,6.
        // Пропущенное браузер при надобности возьмёт из сети.
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        globIgnores: ['**/*-{greek,greek-ext,vietnamese}-*'],
        // Переходы по адресам приложения (/quests, /calendar…) — на index.html из кэша,
        // но не /api: запросы к серверу всегда идут в сеть.
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
      },
    }),
  ],
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
