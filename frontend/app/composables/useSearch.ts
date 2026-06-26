/**
 * Composable for full-text document search (feat-070).
 *
 * Calls the backend GET /api/v1/search endpoint which performs PostgreSQL
 * tsvector full-text search over stored OCR document content. Returns ranked
 * hits with highlight snippets (control-char delimited, see renderSnippet).
 */
import { useNotification } from '~/composables/useNotification'

export interface SearchHit {
  id: string
  filename: string
  model_id: string | null
  provider: string | null
  tier: string | null
  created_at: string
  rank: number
  snippet: string
}

interface SearchResponse {
  success: boolean
  items: SearchHit[]
  total: number
  limit: number
  offset: number
  query: string
}

export function useSearch() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  const { error: notifyError } = useNotification()

  const query = ref('')
  const results = ref<SearchHit[]>([])
  const total = ref(0)
  const isLoading = ref(false)
  const hasSearched = ref(false)
  const errorMessage = ref<string | null>(null)

  // Optional date-range filters (ISO 8601 strings).
  const dateFrom = ref('')
  const dateTo = ref('')

  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  const performSearch = async () => {
    const q = query.value.trim()
    if (!q) {
      results.value = []
      total.value = 0
      hasSearched.value = false
      errorMessage.value = null
      return
    }

    isLoading.value = true
    errorMessage.value = null
    hasSearched.value = true

    try {
      const params: Record<string, string | number> = { q, limit: 50, offset: 0 }
      if (dateFrom.value) params.date_from = dateFrom.value
      if (dateTo.value) params.date_to = dateTo.value

      const response = await $fetch<SearchResponse>(`${apiBaseUrl}/api/v1/search`, {
        params,
      })
      results.value = response.items || []
      total.value = response.total || 0
    } catch (e: any) {
      errorMessage.value = e?.data?.detail || e?.message || 'Search failed'
      results.value = []
      total.value = 0
    } finally {
      isLoading.value = false
    }
  }

  /** Debounced trigger for input typing. */
  const onInput = () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => performSearch(), 300)
  }

  const clear = () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    query.value = ''
    results.value = []
    total.value = 0
    hasSearched.value = false
    errorMessage.value = null
  }

  /** Apply date filters then re-run the current query. */
  const applyFilters = async () => {
    await performSearch()
  }

  return {
    query,
    results,
    total,
    isLoading,
    hasSearched,
    errorMessage,
    dateFrom,
    dateTo,
    performSearch,
    onInput,
    clear,
    applyFilters,
    notifyError,
  }
}
