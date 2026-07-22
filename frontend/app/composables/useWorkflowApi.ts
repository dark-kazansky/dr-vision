/**
 * Workflow API Composable
 *
 * Thin client around the backend `/workflows` and `/workflow-runs` routes.
 * Used by the Jobs tab and the Save/Load dialogs when the backend is
 * reachable. When `apiBaseUrl` cannot be reached, callers should fall
 * back to the local stores (`useWorkflowStore`, `useJobs`).
 */

import type { WorkflowNode } from './useJourney'

export interface BackendWorkflowSummary {
  id: string
  name: string
  description?: string | null
  createdAt: number
  updatedAt: number
  nodeCount: number
}

export interface BackendWorkflow extends BackendWorkflowSummary {
  nodes: WorkflowNode[]
}

export interface BackendRunSummary {
  id: string
  workflowId: string | null
  workflowName: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  createdAt: number
  startedAt: number | null
  finishedAt: number | null
  inputFiles: string[]
  totalNodes: number
  completedNodes: number
  failedNodes: number
  error: string | null
}

export interface BackendRunNode {
  nodeId: string
  nodeLabel: string
  nodeType: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  startedAt: number | null
  finishedAt: number | null
  error: string | null
  outputSummary: string | null
}

export interface BackendRunDetail extends BackendRunSummary {
  nodes: BackendRunNode[]
  logs: { ts: number; level: 'info' | 'warn' | 'error'; message: string; nodeId?: string }[]
  cancelRequested: boolean
}

export function useWorkflowApi() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  // ----- Workflows -----
  const listWorkflows = async (): Promise<BackendWorkflowSummary[]> => {
    const res = await $fetch<{ workflows: BackendWorkflowSummary[] }>(`${apiBaseUrl}/workflows`)
    return res.workflows
  }

  const getWorkflow = async (id: string): Promise<BackendWorkflow> => {
    return await $fetch<BackendWorkflow>(`${apiBaseUrl}/workflows/${id}`)
  }

  const createWorkflow = async (payload: {
    name: string
    description?: string
    nodes: WorkflowNode[]
  }): Promise<BackendWorkflow> => {
    return await $fetch<BackendWorkflow>(`${apiBaseUrl}/workflows`, {
      method: 'POST',
      body: payload,
    })
  }

  const updateWorkflow = async (
    id: string,
    payload: { name?: string; description?: string; nodes?: WorkflowNode[] },
  ): Promise<BackendWorkflow> => {
    return await $fetch<BackendWorkflow>(`${apiBaseUrl}/workflows/${id}`, {
      method: 'PUT',
      body: payload,
    })
  }

  const deleteWorkflow = async (id: string): Promise<void> => {
    await $fetch(`${apiBaseUrl}/workflows/${id}`, { method: 'DELETE' })
  }

  const runSavedWorkflow = async (
    id: string,
    files: File[],
  ): Promise<{ run: BackendRunDetail; result: any }> => {
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    return await $fetch<{ run: BackendRunDetail; result: any }>(
      `${apiBaseUrl}/workflows/${id}/run`,
      { method: 'POST', body: fd },
    )
  }

  const runAdhocWorkflow = async (params: {
    nodes: WorkflowNode[]
    files: File[]
    workflowName?: string
  }): Promise<{ run: BackendRunDetail; result: any }> => {
    const fd = new FormData()
    for (const f of params.files) fd.append('files', f)
    fd.append('nodes', JSON.stringify(params.nodes))
    if (params.workflowName) fd.append('workflow_name', params.workflowName)
    return await $fetch<{ run: BackendRunDetail; result: any }>(
      `${apiBaseUrl}/workflows/run`,
      { method: 'POST', body: fd },
    )
  }

  // ----- Runs -----
  const listRuns = async (
    params: { status?: string; limit?: number; offset?: number } = {},
  ): Promise<{ total: number; limit: number; offset: number; runs: BackendRunSummary[] }> => {
    const query = new URLSearchParams()
    if (params.status) query.set('status', params.status)
    if (params.limit !== undefined) query.set('limit', String(params.limit))
    if (params.offset !== undefined) query.set('offset', String(params.offset))
    const qs = query.toString()
    return await $fetch(`${apiBaseUrl}/workflow-runs${qs ? `?${qs}` : ''}`)
  }

  const getRun = async (id: string): Promise<BackendRunDetail> => {
    return await $fetch<BackendRunDetail>(`${apiBaseUrl}/workflow-runs/${id}`)
  }

  const cancelRun = async (id: string): Promise<void> => {
    await $fetch(`${apiBaseUrl}/workflow-runs/${id}/cancel`, { method: 'POST' })
  }

  const deleteRun = async (id: string): Promise<void> => {
    await $fetch(`${apiBaseUrl}/workflow-runs/${id}`, { method: 'DELETE' })
  }

  const clearFinishedRuns = async (): Promise<number> => {
    const res = await $fetch<{ removed: number }>(`${apiBaseUrl}/workflow-runs/clear-finished`, {
      method: 'POST',
    })
    return res.removed
  }

  /**
   * Probe the backend once. Cached for the lifetime of the page so the UI
   * can decide whether to talk to the API or fall back to localStorage.
   */
  const isAvailable = useState<boolean | null>('workflow-api-available', () => null)
  const checkAvailable = async (): Promise<boolean> => {
    if (isAvailable.value !== null) return isAvailable.value
    try {
      await $fetch(`${apiBaseUrl}/workflows`, { method: 'GET' })
      isAvailable.value = true
    } catch {
      isAvailable.value = false
    }
    return isAvailable.value
  }

  return {
    isAvailable,
    checkAvailable,
    // workflows
    listWorkflows,
    getWorkflow,
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    runSavedWorkflow,
    runAdhocWorkflow,
    // runs
    listRuns,
    getRun,
    cancelRun,
    deleteRun,
    clearFinishedRuns,
  }
}
