/**
 * Execution State Composable (feat-007)
 *
 * Manages persistent execution state for workflow jobs:
 * - Fetch per-node outputs (state viewer)
 * - Fetch shared context
 * - Resume failed jobs from checkpoint
 * - Track state loading status
 */

export interface NodeState {
  output: any
  status: 'completed' | 'failed' | 'running' | 'pending'
  error: string | null
  duration_ms: number | null
  saved_at: string | null
}

export interface ExecutionStateData {
  state_id: string
  job_id: string
  workflow_id: string | null
  status: 'running' | 'completed' | 'failed' | 'cancelled' | 'resuming' | 'cleaned'
  node_states: Record<string, NodeState>
  context: Record<string, any>
  checkpoint_node: string | null
  resume_from: string | null
  retention_hours: number
  created_at: string
  updated_at: string
}

export interface ResumeResponse {
  original_job_id: string
  new_job_id: string
  status: string
  resume_from_node: string
  completed_nodes: string[]
  poll_url: string
  message: string
}

export function useExecutionState() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  // State
  const executionState = useState<ExecutionStateData | null>('exec-state-data', () => null)
  const isLoading = useState<boolean>('exec-state-loading', () => false)
  const stateError = useState<string | null>('exec-state-error', () => null)
  const stateViewerOpen = useState<boolean>('exec-state-viewer-open', () => false)

  /**
   * Fetch execution state for a job
   */
  const fetchState = async (jobId: string): Promise<ExecutionStateData | null> => {
    isLoading.value = true
    stateError.value = null

    try {
      const state = await $fetch<ExecutionStateData>(
        `${apiBaseUrl}/api/v1/jobs/${jobId}/state`
      )
      executionState.value = state
      return state
    } catch (error: any) {
      if (error?.statusCode === 404) {
        stateError.value = 'No execution state found for this job'
      } else {
        stateError.value = error?.message || 'Failed to fetch execution state'
      }
      executionState.value = null
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch all node outputs for a job
   */
  const fetchNodeOutputs = async (jobId: string): Promise<Record<string, any>> => {
    try {
      const response = await $fetch<{ job_id: string; node_outputs: Record<string, any> }>(
        `${apiBaseUrl}/api/v1/jobs/${jobId}/state/nodes`
      )
      return response.node_outputs
    } catch {
      return {}
    }
  }

  /**
   * Fetch a specific node's output
   */
  const fetchNodeOutput = async (jobId: string, nodeId: string): Promise<NodeState | null> => {
    try {
      const response = await $fetch<NodeState & { job_id: string; node_id: string }>(
        `${apiBaseUrl}/api/v1/jobs/${jobId}/state/nodes/${nodeId}`
      )
      return response
    } catch {
      return null
    }
  }

  /**
   * Fetch shared execution context
   */
  const fetchContext = async (jobId: string): Promise<Record<string, any>> => {
    try {
      const response = await $fetch<{ job_id: string; context: Record<string, any> }>(
        `${apiBaseUrl}/api/v1/jobs/${jobId}/state/context`
      )
      return response.context
    } catch {
      return {}
    }
  }

  /**
   * Resume a failed job from checkpoint
   */
  const resumeJob = async (
    jobId: string,
    file: File,
    nodeId?: string
  ): Promise<ResumeResponse | null> => {
    isLoading.value = true
    stateError.value = null

    try {
      const formData = new FormData()
      formData.append('file', file)
      if (nodeId) {
        formData.append('node_id', nodeId)
      }

      const response = await $fetch<ResumeResponse>(
        `${apiBaseUrl}/api/v1/jobs/${jobId}/resume`,
        { method: 'POST', body: formData }
      )
      return response
    } catch (error: any) {
      stateError.value = error?.data?.detail || error?.message || 'Failed to resume job'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Check if a job can be resumed
   */
  const canResume = computed(() => {
    if (!executionState.value) return false
    return (
      executionState.value.status === 'failed' &&
      executionState.value.checkpoint_node !== null
    )
  })

  /**
   * Get the list of completed node IDs
   */
  const completedNodeIds = computed(() => {
    if (!executionState.value) return []
    return Object.entries(executionState.value.node_states)
      .filter(([_, data]) => data.status === 'completed')
      .map(([nodeId]) => nodeId)
  })

  /**
   * Get the failed node ID (if any)
   */
  const failedNodeId = computed(() => {
    if (!executionState.value) return null
    const failed = Object.entries(executionState.value.node_states)
      .find(([_, data]) => data.status === 'failed')
    return failed ? failed[0] : null
  })

  /**
   * Open the state viewer panel
   */
  const openStateViewer = (jobId?: string) => {
    stateViewerOpen.value = true
    if (jobId) {
      fetchState(jobId)
    }
  }

  /**
   * Close the state viewer panel
   */
  const closeStateViewer = () => {
    stateViewerOpen.value = false
  }

  return {
    // State
    executionState: readonly(executionState),
    isLoading: readonly(isLoading),
    stateError: readonly(stateError),
    stateViewerOpen,
    canResume,
    completedNodeIds,
    failedNodeId,

    // Actions
    fetchState,
    fetchNodeOutputs,
    fetchNodeOutput,
    fetchContext,
    resumeJob,
    openStateViewer,
    closeStateViewer,
  }
}
