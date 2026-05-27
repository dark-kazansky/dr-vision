/**
 * useLocale Composable
 * 
 * Manages language state (vi/en) with localStorage persistence.
 * Default: Vietnamese (vi)
 */

export type Locale = 'vi' | 'en'

const STORAGE_KEY = 'drvision-locale'

export function useLocale() {
  const locale = useState<Locale>('app-locale', () => {
    if (import.meta.client) {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved === 'en' || saved === 'vi') return saved
    }
    return 'en'
  })

  const setLocale = (newLocale: Locale) => {
    locale.value = newLocale
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, newLocale)
    }
  }

  const toggleLocale = () => {
    setLocale(locale.value === 'vi' ? 'en' : 'vi')
  }

  const isVi = computed(() => locale.value === 'vi')
  const isEn = computed(() => locale.value === 'en')

  return {
    locale,
    setLocale,
    toggleLocale,
    isVi,
    isEn,
  }
}
