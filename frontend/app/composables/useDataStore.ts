/**
 * useDataStore Composable
 *
 * Manages the Data Store — persistent storage of processing results
 * from Parse, Classify, Extract, Split, and Workflow actions.
 *
 * Each entry is tagged with the action type for filtering.
 */

export interface DataStoreEntry {
  id: string
  filename: string
  action_tag: 'Parse' | 'Classify' | 'Extract' | 'Split' | 'WF'
  result_data: any
  model_used: string | null
  created_at: string
}

export function useDataStore() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  const entries = useState<DataStoreEntry[]>('data-store-entries', () => [])
  const isLoading = useState<boolean>('data-store-loading', () => false)

  /**
   * Load all entries from backend
   */
  const loadEntries = async () => {
    isLoading.value = true
    try {
      const response = await $fetch<{ entries: DataStoreEntry[]; total: number }>(
        `${apiBaseUrl}/api/v1/data-store`
      )
      entries.value = response.entries || []
    } catch (error) {
      console.error('Failed to load data store entries:', error)
      entries.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Save a new entry to the data store
   */
  const saveEntry = async (params: {
    filename: string
    action_tag: 'Parse' | 'Classify' | 'Extract' | 'Split' | 'WF'
    result_data: any
    model_used?: string
  }) => {
    try {
      const response = await $fetch<DataStoreEntry>(`${apiBaseUrl}/api/v1/data-store`, {
        method: 'POST',
        body: params,
      })
      // Add to local state
      entries.value = [response, ...entries.value]
      return response
    } catch (error) {
      console.error('Failed to save data store entry:', error)
      return null
    }
  }

  /**
   * Delete an entry
   */
  const deleteEntry = async (id: string) => {
    try {
      await $fetch(`${apiBaseUrl}/api/v1/data-store/${id}`, { method: 'DELETE' })
      entries.value = entries.value.filter(e => e.id !== id)
    } catch (error) {
      console.error('Failed to delete data store entry:', error)
    }
  }

  /**
   * Get entries filtered by tag
   */
  const getByTag = (tag: string) => {
    return computed(() => entries.value.filter(e => e.action_tag === tag))
  }

  return {
    entries,
    isLoading,
    loadEntries,
    saveEntry,
    deleteEntry,
    getByTag,
  }
}
