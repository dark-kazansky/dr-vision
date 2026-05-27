/**
 * Composable for managing workflow list — fetch, pagination, search, delete.
 */
import { useNotification } from '~/composables/useNotification'

const PAGE_SIZE = 16

export function useWorkflowList() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  const { error: notifyError } = useNotification()

  // State
  const workflows = ref<any[]>([])
  const allWorkflowsCache = ref<any[]>([])
  const searchQuery = ref('')
  const isLoading = ref(true)
  const isLoadingMore = ref(false)
  const workflowTotal = ref(0)

  // Computed
  const hasMoreWorkflows = computed(() => workflows.value.length < workflowTotal.value)

  const filteredWorkflows = computed(() => {
    if (!searchQuery.value.trim()) return workflows.value
    const q = searchQuery.value.toLowerCase()
    return workflows.value.filter(w =>
      w.name?.toLowerCase().includes(q) ||
      w.description?.toLowerCase().includes(q)
    )
  })

  // Fetch workflows from API
  const fetchWorkflows = async () => {
    isLoading.value = true
    try {
      const response = await $fetch<{ workflows: any[]; total: number }>(
        `${apiBaseUrl}/api/v1/workflows?limit=100&offset=0`
      )
      allWorkflowsCache.value = response.workflows || []
    } catch (error) {
      console.error('Failed to fetch workflows:', error)
      allWorkflowsCache.value = []
    }
    workflowTotal.value = allWorkflowsCache.value.length
    workflows.value = allWorkflowsCache.value.slice(0, PAGE_SIZE)
    isLoading.value = false
  }

  // Load more (infinite scroll)
  const loadMoreWorkflows = () => {
    if (workflows.value.length >= workflowTotal.value) return
    isLoadingMore.value = true
    const next = allWorkflowsCache.value.slice(
      workflows.value.length,
      workflows.value.length + PAGE_SIZE
    )
    workflows.value = [...workflows.value, ...next]
    isLoadingMore.value = false
  }

  // Delete workflow
  const deleteWorkflow = async (workflowId: string) => {
    try {
      await $fetch(`${apiBaseUrl}/api/v1/workflows/${workflowId}`, {
        method: 'DELETE',
      })
      workflows.value = workflows.value.filter(w => w.workflow_id !== workflowId)
      allWorkflowsCache.value = allWorkflowsCache.value.filter(w => w.workflow_id !== workflowId)
      workflowTotal.value = allWorkflowsCache.value.length
    } catch (error) {
      console.error('Failed to delete workflow:', error)
      notifyError('Failed to delete workflow')
    }
  }

  return {
    workflows,
    searchQuery,
    isLoading,
    isLoadingMore,
    hasMoreWorkflows,
    filteredWorkflows,
    fetchWorkflows,
    loadMoreWorkflows,
    deleteWorkflow,
  }
}
