/**
 * Job Manager Composable
 * 
 * Manages job submission, progress tracking via SSE, cancellation,
 * and job history for the workflow builder.
 */

export interface JobNode {
  node_id: string
  node_type: string
  node_label: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'retrying'
  retry_count: number
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface Job {
  job_id: string
  workflow_id: string | null
  workflow_name: string | null
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  nodes: JobNode[]
  filename: string | null
  file_count: number
  max_retries: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  cancelled_at: string | null
  error: string | null
  results: any[] | null
}

export interface JobEvent {
  event: string
  job_id: string
  timestamp: string
  node_id?: string
  node_type?: string
  node_label?: string
  progress?: number
  error?: string
  attempt?: number
  max_retries?: number
}

export function useJobManager() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  // State
  const currentJob = useState<Job | null>('job-manager-current', () => null)
  const jobHistory = useState<Job[]>('job-manager-history', () => [])
  const isSubmitting = useState<boolean>('job-manager-submitting', () => false)
  const jobPanelOpen = useState<boolean>('job-manager-panel-open', () => false)
  const sseEvents = useState<JobEvent[]>('job-manager-events', () => [])

  let eventSource: EventSource | null = null

  /**
   * Submit a workflow execution job
   */
  const submitJob = async (
    file: File,
    steps: Array<{ id?: string; type: string; label?: string; tier?: string; config?: any }>,
    options?: {
      workflowId?: string
      workflowName?: string
      maxRetries?: number
    }
  ): Promise<Job | null> => {
    isSubmitting.value = true
    sseEvents.value = []

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('workflow', JSON.stringify({ steps }))

      if (options?.workflowId) {
        formData.append('workflow_id', options.workflowId)
      }
      if (options?.workflowName) {
        formData.append('workflow_name', options.workflowName)
      }
      if (options?.maxRetries !== undefined) {
        formData.append('max_retries', String(options.maxRetries))
      }

      const response = await $fetch<{ job_id: string; status: string; poll_url: string }>(
        `${apiBaseUrl}/api/v1/jobs`,
        { method: 'POST', body: formData }
      )

      // Fetch full job details
      const job = await fetchJob(response.job_id)
      if (job) {
        currentJob.value = job
        jobPanelOpen.value = true
        // Start SSE stream
        connectSSE(job.job_id)
      }

      return job
    } catch (error: any) {
      console.error('Failed to submit job:', error)
      throw error
    } finally {
      isSubmitting.value = false
    }
  }

  /**
   * Fetch a single job by ID
   */
  const fetchJob = async (jobId: string): Promise<Job | null> => {
    try {
      const job = await $fetch<Job>(`${apiBaseUrl}/api/v1/jobs/${jobId}`)
      return job
    } catch (error) {
      console.error('Failed to fetch job:', error)
      return null
    }
  }

  /**
   * Fetch job history with optional filters
   */
  const fetchJobHistory = async (filters?: {
    status?: string
    workflowId?: string
    limit?: number
    offset?: number
  }): Promise<void> => {
    try {
      const params = new URLSearchParams()
      if (filters?.status) params.set('status', filters.status)
      if (filters?.workflowId) params.set('workflow_id', filters.workflowId)
      if (filters?.limit) params.set('limit', String(filters.limit))
      if (filters?.offset) params.set('offset', String(filters.offset))

      const queryString = params.toString()
      const url = `${apiBaseUrl}/api/v1/jobs${queryString ? `?${queryString}` : ''}`

      const response = await $fetch<{ jobs: Job[]; total: number }>(url)
      jobHistory.value = response.jobs
    } catch (error) {
      console.error('Failed to fetch job history:', error)
    }
  }

  /**
   * Cancel a running or queued job
   */
  const cancelJob = async (jobId?: string): Promise<boolean> => {
    const id = jobId || currentJob.value?.job_id
    if (!id) return false

    try {
      await $fetch(`${apiBaseUrl}/api/v1/jobs/${id}/cancel`, { method: 'POST' })

      // Update local state
      if (currentJob.value?.job_id === id) {
        currentJob.value = {
          ...currentJob.value,
          status: 'cancelled',
        }
      }

      return true
    } catch (error) {
      console.error('Failed to cancel job:', error)
      return false
    }
  }

  /**
   * Connect to SSE stream for real-time progress
   */
  const connectSSE = (jobId: string) => {
    // Close existing connection
    disconnectSSE()

    const url = `${apiBaseUrl}/api/v1/jobs/${jobId}/stream`
    eventSource = new EventSource(url)

    // Handle initial connection
    eventSource.addEventListener('connected', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      // Update current job with initial state
      if (currentJob.value && currentJob.value.job_id === jobId) {
        currentJob.value = {
          ...currentJob.value,
          status: (data as any).status || currentJob.value.status,
          progress: (data as any).progress ?? currentJob.value.progress,
        }
      }
    })

    // Node events
    eventSource.addEventListener('node_started', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      updateNodeInCurrentJob(data.node_id!, 'running')
    })

    eventSource.addEventListener('node_completed', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      updateNodeInCurrentJob(data.node_id!, 'completed')
    })

    eventSource.addEventListener('node_failed', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      updateNodeInCurrentJob(data.node_id!, 'failed', data.error)
    })

    eventSource.addEventListener('node_retrying', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      updateNodeInCurrentJob(data.node_id!, 'retrying')
    })

    eventSource.addEventListener('node_skipped', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      updateNodeInCurrentJob(data.node_id!, 'skipped')
    })

    // Job progress
    eventSource.addEventListener('job_progress', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      if (currentJob.value) {
        currentJob.value = {
          ...currentJob.value,
          progress: data.progress ?? currentJob.value.progress,
        }
      }
    })

    // Job started
    eventSource.addEventListener('job_started', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      if (currentJob.value) {
        currentJob.value = { ...currentJob.value, status: 'running' }
      }
    })

    // Terminal events
    eventSource.addEventListener('job_completed', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      if (currentJob.value) {
        currentJob.value = { ...currentJob.value, status: 'completed', progress: 1.0 }
      }
      disconnectSSE()
      // Refresh full job data for results
      refreshCurrentJob()
    })

    eventSource.addEventListener('job_failed', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      if (currentJob.value) {
        currentJob.value = { ...currentJob.value, status: 'failed', error: data.error || null }
      }
      disconnectSSE()
    })

    eventSource.addEventListener('job_cancelled', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobEvent
      sseEvents.value.push(data)
      if (currentJob.value) {
        currentJob.value = { ...currentJob.value, status: 'cancelled' }
      }
      disconnectSSE()
    })

    // Error handling
    eventSource.onerror = () => {
      console.warn('SSE connection error, will retry...')
      // EventSource auto-reconnects, but if job is done we close
      if (currentJob.value && ['completed', 'failed', 'cancelled'].includes(currentJob.value.status)) {
        disconnectSSE()
      }
    }
  }

  /**
   * Disconnect SSE stream
   */
  const disconnectSSE = () => {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  /**
   * Update a node's status in the current job
   */
  const updateNodeInCurrentJob = (
    nodeId: string,
    status: JobNode['status'],
    error?: string
  ) => {
    if (!currentJob.value) return

    const updatedNodes = currentJob.value.nodes.map(n => {
      if (n.node_id === nodeId) {
        return { ...n, status, error: error || n.error }
      }
      return n
    })

    currentJob.value = { ...currentJob.value, nodes: updatedNodes }
  }

  /**
   * Refresh current job data from server
   */
  const refreshCurrentJob = async () => {
    if (!currentJob.value) return
    const job = await fetchJob(currentJob.value.job_id)
    if (job) {
      currentJob.value = job
    }
  }

  /**
   * Select a job from history to view
   */
  const selectJob = (job: Job) => {
    currentJob.value = job
    jobPanelOpen.value = true
    sseEvents.value = []

    // If job is still active, connect SSE
    if (job.status === 'queued' || job.status === 'running') {
      connectSSE(job.job_id)
    }
  }

  /**
   * Close the job panel
   */
  const closePanel = () => {
    jobPanelOpen.value = false
    disconnectSSE()
  }

  /**
   * Check if a job is in a terminal state
   */
  const isTerminal = computed(() => {
    if (!currentJob.value) return true
    return ['completed', 'failed', 'cancelled'].includes(currentJob.value.status)
  })

  /**
   * Check if current job is running
   */
  const isRunning = computed(() => {
    return currentJob.value?.status === 'running' || currentJob.value?.status === 'queued'
  })

  // Cleanup on unmount
  onUnmounted(() => {
    disconnectSSE()
  })

  return {
    // State
    currentJob,
    jobHistory,
    isSubmitting: readonly(isSubmitting),
    jobPanelOpen,
    sseEvents: readonly(sseEvents),
    isTerminal,
    isRunning,

    // Actions
    submitJob,
    fetchJob,
    fetchJobHistory,
    cancelJob,
    selectJob,
    closePanel,
    connectSSE,
    disconnectSSE,
  }
}
