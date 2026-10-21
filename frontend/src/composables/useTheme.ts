import { computed, ref, watch, watchEffect } from 'vue'

/** system — как в настройках устройства. */
export type ThemePreference = 'system' | 'light' | 'dark'

// Тот же ключ читает скрипт в index.html — до загрузки приложения, чтобы тема не мигала.
const STORAGE_KEY = 'eq.theme'

function readPreference(): ThemePreference {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : 'system'
  } catch {
    return 'system'
  }
}

const media =
  typeof window !== 'undefined' ? window.matchMedia?.('(prefers-color-scheme: dark)') : undefined

/** Выбор пользователя — настройка устройства, как и звук: на рабочем ноутбуке может быть своя. */
const preference = ref<ThemePreference>(readPreference())
const systemDark = ref(media?.matches ?? false)
media?.addEventListener('change', (event) => (systemDark.value = event.matches))

const isDark = computed(() =>
  preference.value === 'system' ? systemDark.value : preference.value === 'dark',
)

watch(preference, (value) => {
  try {
    if (value === 'system') localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, value)
  } catch {
    /* приватный режим — выбор живёт до перезагрузки */
  }
})

// CSS-переменные тёмной темы висят на :root[data-theme='dark'].
watchEffect(() => {
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = isDark.value ? 'dark' : 'light'
  }
})

export function useTheme() {
  return { preference, isDark }
}
