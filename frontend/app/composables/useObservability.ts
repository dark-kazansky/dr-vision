/**
 * Observability Composable — feat-010
 *
 * Fetches metrics, timeline, error analytics, audit log,
 * and dashboard summary from the observability API.
 */

export interface NodeTimeline {
  node_id: string
  node_type: string
  node_label: string
  status: string
  duration_ms: number | null
  error: string | null
  saved_at: string | null
}

export interface ExecutionTimeline {
  job_id: string
  workflow_id: string | null
  workflow_name: string | null
  status: string
  total_duration_ms: number | null
  started_at: string | null
  completed_at: string | null
  nodes: NodeTimeline[]
}

export interface NodeTypeMetric {
  node_type: string
  execution_count: number
  success_count: number
  failure_count: number
  failure_rate: number
  avg_duration_ms: number | null
  min_duration_ms: number | null
  max_duration_ms: number | null
}

export interface PerformanceMetrics {
  period_days: number
  workflow_id: string | null
  summary: {
    total_jobs: number
    completed_jobs: number
    failed_jobs: number
    cancelled_jobs: number
    success_rate: number
    avg_duration_ms: number | null
    min_duration_ms: number | null
    max_duration_ms: number | null
  }
  node_types: NodeTypeMetric[]
}

export interface ErrorEntry {
  node_type: string
  node_label: string
  error_message: string
  occurrence_count: number
  last_occurred: string | null
}

export interface FailureRate {
  node_type: string
  successes: number
  failures: number
  total: number
  failure_rate: number
}

export interface ErrorAnalytics {
  period_days: number
  top_errors: ErrorEntry[]
  failure_rates: FailureRate[]
}

export interface AuditEntry {
  job_id: string
  workflow_id: string | null
  workflow_name: string | null
  status: string
  filename: string | null
  file_count: number
  progress: number
  error: string | null
  duration_ms: number | null
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  cancelled_at: string | null
}

export interface AuditLog {
  entries: AuditEntry[]
  total: number
  limit: number
  offset: number
}

export interface WorkflowHealth {
  workflow_id: string
  workflow_name: string | null
  total_jobs: number
  completed: number
  failed: number
  running: number
  queued: number
  success_rate: number
  health: 'healthy' | 'warning' | 'critical'
  last_run: string | null
  avg_duration_ms: number | null
}

export interface DashboardSummary {
  period_days: number
  system: {
    total_jobs: number
    completed: number
    failed: number
    running: number
    queued: number
    unique_workflows: number
    success_rate: number
    health: 'healthy' | 'warning' | 'critical'
  }
  workflows: WorkflowHealth[]
}

export function useObservability() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  // State
  const dashboard = useState<DashboardSummary | null>('obs-dashboard', () => null)
  const metrics = useState<PerformanceMetrics | null>('obs-metrics', () => null)
  const errors = useState<ErrorAnalytics | null>('obs-errors', () => null)
  const auditLog = useState<AuditLog | null>('obs-audit', () => null)
  const timeline = useState<ExecutionTimeline | null>('obs-timeline', () => null)
  const isLoading = useState<boolean>('obs-loading', () => false)
  const error = useState<string | null>('obs-error', () => null)

  /**
   * Fetch dashboard summary
   */
  const fetchDashboard = async (days: number = 7): Promise<void> => {
    isLoading.value = true
    error.value = null
    try {
      const result = await $fetch<DashboardSummary>(
        `${apiBaseUrl}/api/v1/observability/dashboard`,
        { params: { days } }
      )
      dashboard.value = result
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch dashboard'
      console.error('Failed to fetch dashboard:', e)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch performance metrics
   */
  const fetchMetrics = async (options?: {
    workflowId?: string
    days?: number
  }): Promise<void> => {
    isLoading.value = true
    error.value = null
    try {
      const params: Record<string, any> = { days: options?.days || 7 }
      if (options?.workflowId) params.workflow_id = options.workflowId

      const result = await $fetch<PerformanceMetrics>(
        `${apiBaseUrl}/api/v1/observability/metrics`,
        { params }
      )
      metrics.value = result
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch metrics'
      console.error('Failed to fetch metrics:', e)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch error analytics
   */
  const fetchErrors = async (options?: {
    workflowId?: string
    days?: number
    limit?: number
  }): Promise<void> => {
    isLoading.value = true
    error.value = null
    try {
      const params: Record<string, any> = {
        days: options?.days || 7,
        limit: options?.limit || 20,
      }
      if (options?.workflowId) params.workflow_id = options.workflowId

      const result = await $fetch<ErrorAnalytics>(
        `${apiBaseUrl}/api/v1/observability/errors`,
        { params }
      )
      errors.value = result
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch errors'
      console.error('Failed to fetch errors:', e)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch audit log
   */
  const fetchAuditLog = async (options?: {
    workflowId?: string
    days?: number
    limit?: number
    offset?: number
  }): Promise<void> => {
    isLoading.value = true
    error.value = null
    try {
      const params: Record<string, any> = {
        days: options?.days || 7,
        limit: options?.limit || 50,
        offset: options?.offset || 0,
      }
      if (options?.workflowId) params.workflow_id = options.workflowId

      const result = await $fetch<AuditLog>(
        `${apiBaseUrl}/api/v1/observability/audit`,
        { params }
      )
      auditLog.value = result
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch audit log'
      console.error('Failed to fetch audit log:', e)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch execution timeline for a specific job
   */
  const fetchTimeline = async (jobId: string): Promise<void> => {
    isLoading.value = true
    error.value = null
    try {
      const result = await $fetch<ExecutionTimeline>(
        `${apiBaseUrl}/api/v1/observability/timeline/${jobId}`
      )
      timeline.value = result
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch timeline'
      console.error('Failed to fetch timeline:', e)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Format duration in ms to human-readable
   */
  const formatDuration = (ms: number | null | undefined): string => {
    if (ms == null) return '—'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  /**
   * Get health color class
   */
  const healthColor = (health: string): string => {
    switch (health) {
      case 'healthy': return 'text-emerald-600'
      case 'warning': return 'text-amber-600'
      case 'critical': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  /**
   * Get health bg class
   */
  const healthBg = (health: string): string => {
    switch (health) {
      case 'healthy': return 'bg-emerald-50 border-emerald-200'
      case 'warning': return 'bg-amber-50 border-amber-200'
      case 'critical': return 'bg-red-50 border-red-200'
      default: return 'bg-gray-50 border-gray-200'
    }
  }

  return {
    // State
    dashboard: readonly(dashboard),
    metrics: readonly(metrics),
    errors: readonly(errors),
    auditLog: readonly(auditLog),
    timeline: readonly(timeline),
    isLoading: readonly(isLoading),
    error: readonly(error),

    // Actions
    fetchDashboard,
    fetchMetrics,
    fetchErrors,
    fetchAuditLog,
    fetchTimeline,

    // Utilities
    formatDuration,
    healthColor,
    healthBg,
  }
}
