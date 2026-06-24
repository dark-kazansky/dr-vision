/**
 * useBatchProcess Composable
 *
 * Manages multi-file batch processing:
 * - Submit multiple files (or zip) for parallel processing
 * - Track per-file progress via SSE
 * - List/get/cancel batches
 * - Retrieve aggregated results
 */

// --- Types ---

export interface BatchFileResult {
  file_id: string
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'skipped' | 'cancelled'
  result?: any
  error?: string | null
  duration_ms?: number | null
}

export interface BatchJob {
  batch_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'partial'
  total: number
  completed: number
  failed: number
  pending: number
  progress: number
  max_concurrency: number
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  files?: BatchFileResult[]
}

export interface BatchSubmitOptions {
  workflow?: { steps: Array<{ type: string; tier?: string; config?: Record<string, any> }> }
  maxConcurrency?: number
}

// --- Composable ---

export function useBatchProcess() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  const baseUrl = `${apiBaseUrl}/api/v1/batch`

  // State
  const batches = useState<BatchJob[]>('batch-list', () => [])
  const currentBatch = useState<BatchJob | null>('batch-current', () => null)
  const isSubmitting = useState<boolean>('batch-submitting', () => false)
  const error = useState<string | null>('batch-error', () => null)

  // SSE
  let eventSource: EventSource | null = null

  // --- Helpers ---

  function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('auth_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  // --- Actions ---

  /**
   * Submit files for batch processing.
   */
  async function submitBatch(
    files: File[],
    options: BatchSubmitOptions = {},
  ): Promise<string | null> {
    isSubmitting.value = true
    error.value = null

    try {
      const formData = new FormData()

      for (const file of files) {
        formData.append('files', file)
      }

      const workflow = options.workflow || { steps: [{ type: 'parse', tier: 'Normal' }] }
      formData.append('workflow', JSON.stringify(workflow))
      formData.append('max_concurrency', String(options.maxConcurrency || 3))

      const response = await fetch(`${baseUrl}/process`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
      })

      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || `HTTP ${response.status}`)
      }

      const result = await response.json()
      await listBatches()
      return result.batch_id
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      isSubmitting.value = false
    }
  }

  /**
   * List recent batch jobs.
   */
  async function listBatches(limit = 50): Promise<void> {
    error.value = null
    try {
      const response = await fetch(`${baseUrl}?limit=${limit}`, {
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      batches.value = data.batches || []
    } catch (e: any) {
      error.value = e.message
    }
  }

  /**
   * Get batch status with per-file progress.
   */
  async function getBatch(batchId: string): Promise<BatchJob | null> {
    error.value = null
    try {
      const response = await fetch(`${baseUrl}/${batchId}`, {
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      currentBatch.value = data
      return data
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  /**
   * Cancel a running batch.
   */
  async function cancelBatch(batchId: string): Promise<boolean> {
    try {
      const response = await fetch(`${baseUrl}/${batchId}/cancel`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      await getBatch(batchId)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  /**
   * Get aggregated results for a completed batch.
   */
  async function getBatchResults(batchId: string): Promise<BatchFileResult[]> {
    try {
      const response = await fetch(`${baseUrl}/${batchId}/results`, {
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      return data.results || []
    } catch (e: any) {
      error.value = e.message
      return []
    }
  }

  /**
   * Subscribe to SSE events for a batch.
   */
  function subscribeToBatch(
    batchId: string,
    onEvent: (eventType: string, data: Record<string, any>) => void,
    onEnd?: (reason: string) => void,
  ): () => void {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }

    const token = localStorage.getItem('auth_token')
    const url = `${baseUrl}/${batchId}/stream${token ? `?token=${token}` : ''}`
    eventSource = new EventSource(url)

    const eventTypes = [
      'connected',
      'batch_started',
      'file_started',
      'file_completed',
      'file_failed',
      'batch_completed',
      'batch_cancelled',
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

          // Auto-refresh current batch on file events
          if (['file_completed', 'file_failed', 'batch_completed'].includes(type)) {
            getBatch(batchId)
          }
        } catch {
          // Ignore parse errors
        }
      })
    }

    eventSource.onerror = () => {
      eventSource?.close()
      eventSource = null
    }

    return () => {
      eventSource?.close()
      eventSource = null
    }
  }

  /**
   * Close SSE connection.
   */
  function disconnect(): void {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  // Lifecycle
  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    batches,
    currentBatch,
    isSubmitting,
    error,

    // Actions
    submitBatch,
    listBatches,
    getBatch,
    cancelBatch,
    getBatchResults,
    subscribeToBatch,
    disconnect,
  }
}
