/**
 * useDurableWorkflow Composable
 *
 * Manages durable workflow operations:
 * - Start a workflow run
 * - List/get/cancel runs
 * - Subscribe to real-time SSE events
 * - Track activity progress
 */

// --- Types ---

export interface DurableActivity {
  activity_id: string
  activity_type: string
  label: string
  status: string
  attempt: number
  output?: any
  error?: string | null
  started_at?: string | null
  completed_at?: string | null
  duration_ms?: number | null
}

export interface DurableRun {
  run_id: string
  workflow_id: string
  workflow_name: string
  status: string
  input_data: Record<string, any>
  output_data: Record<string, any>
  error?: string | null
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  activity_states?: Record<string, DurableActivity>
  activity_results?: Record<string, any>
}

export interface DurableEvent {
  event_id?: number
  workflow_run_id: string
  sequence_num: number
  event_type: string
  timestamp: string
  payload: Record<string, any>
}

export interface WorkflowStartRequest {
  workflow_id?: string
  name: string
  activities: Array<{
    activity_id?: string
    activity_type: string
    label?: string
    config?: Record<string, any>
    timeout_seconds?: number
    depends_on?: string[]
  }>
  input_data?: Record<string, any>
  timeout_seconds?: number
  metadata?: Record<string, any>
}

export interface EngineHealth {
  engine_status: string
  active_runs: number
  stale_runs: number
  pending_tasks: number
  processing_tasks: number
  queue_stats?: Record<string, number>
}

// --- Composable ---

export function useDurableWorkflow() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  const baseUrl = `${apiBaseUrl}/api/v1/durable`

  // State
  const runs = useState<DurableRun[]>('durable-runs', () => [])
  const currentRun = useState<DurableRun | null>('durable-current-run', () => null)
  const currentEvents = useState<DurableEvent[]>('durable-current-events', () => [])
  const isLoading = useState<boolean>('durable-loading', () => false)
  const error = useState<string | null>('durable-error', () => null)
  const engineHealth = useState<EngineHealth | null>('durable-health', () => null)

  // SSE connection
  let eventSource: EventSource | null = null

  // --- Helpers ---

  function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('auth_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(options.headers as Record<string, string> || {}),
    }

    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // --- Actions ---

  /**
   * Start a new durable workflow run.
   */
  async function startWorkflow(request: WorkflowStartRequest): Promise<string> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apiFetch<{ run_id: string }>('/workflows', {
        method: 'POST',
        body: JSON.stringify(request),
      })
      // Refresh runs list
      await listRuns()
      return result.run_id
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      isLoading.value = false
    }
  }

  /**
   * List workflow runs with optional status filter.
   */
  async function listRuns(status?: string, limit = 50): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      if (status) params.set('status', status)
      params.set('limit', String(limit))

      const result = await apiFetch<{ runs: DurableRun[] }>(`/runs?${params}`)
      runs.value = result.runs
    } catch (e: any) {
      error.value = e.message
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get full state of a specific run (replayed from events).
   */
  async function getRun(runId: string): Promise<DurableRun | null> {
    isLoading.value = true
    error.value = null

    try {
      const result = await apiFetch<DurableRun>(`/runs/${runId}`)
      currentRun.value = result
      return result
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get event history for a run.
   */
  async function getRunEvents(runId: string): Promise<DurableEvent[]> {
    try {
      const result = await apiFetch<{ events: DurableEvent[] }>(`/runs/${runId}/events`)
      currentEvents.value = result.events
      return result.events
    } catch (e: any) {
      error.value = e.message
      return []
    }
  }

  /**
   * Cancel a running workflow.
   */
  async function cancelRun(runId: string, reason = 'Cancelled by user'): Promise<boolean> {
    try {
      await apiFetch(`/runs/${runId}/cancel`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
      // Refresh
      await getRun(runId)
      await listRuns()
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  /**
   * Get engine health and stats.
   */
  async function getHealth(): Promise<EngineHealth | null> {
    try {
      const result = await apiFetch<EngineHealth>('/health')
      engineHealth.value = result
      return result
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  /**
   * Subscribe to real-time SSE events for a run.
   * Calls onEvent for each event received.
   * Returns a cleanup function to close the connection.
   */
  function subscribeToRun(
    runId: string,
    onEvent: (eventType: string, data: Record<string, any>) => void,
    onEnd?: (reason: string) => void,
    onError?: (err: string) => void,
  ): () => void {
    // Close existing connection
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    const token = localStorage.getItem('auth_token')
    const url = `${baseUrl}/runs/${runId}/stream${token ? `?token=${token}` : ''}`

    eventSource = new EventSource(url)

    // Listen for specific event types
    const eventTypes = [
      'connected',
      'workflow_started',
      'activity_scheduled',
      'activity_started',
      'activity_completed',
      'activity_failed',
      'activity_retrying',
      'workflow_completed',
      'workflow_failed',
      'workflow_cancelled',
      'workflow_timed_out',
      'timer_scheduled',
      'timer_fired',
      'stream_end',
    ]

    for (const type of eventTypes) {
      eventSource.addEventListener(type, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)

          if (type === 'stream_end') {
            onEnd?.(data.reason || 'completed')
            eventSource?.close()
            eventSource = null
            return
          }

          onEvent(type, data)
        } catch {
          // Ignore parse errors
        }
      })
    }

    eventSource.onerror = () => {
      onError?.('SSE connection error')
      eventSource?.close()
      eventSource = null
    }

    // Return cleanup function
    return () => {
      eventSource?.close()
      eventSource = null
    }
  }

  /**
   * Close any active SSE connection.
   */
  function disconnect(): void {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  // --- Lifecycle ---
  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    runs,
    currentRun,
    currentEvents,
    isLoading,
    error,
    engineHealth,

    // Actions
    startWorkflow,
    listRuns,
    getRun,
    getRunEvents,
    cancelRun,
    getHealth,
    subscribeToRun,
    disconnect,
  }
}
