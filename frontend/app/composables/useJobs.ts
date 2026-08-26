/**
 * Jobs / Run History Composable
 *
 * Tracks workflow run history with per-node status, timing and logs so
 * the Jobs tab can present an Airflow-style dashboard.
 *
 * Persistence: localStorage (capped to MAX_RUNS most recent). The API
 * surface mirrors what a future backend `/workflows/runs` endpoint will
 * expose, so swapping to server-backed runs only requires changing this
 * composable's internals.
 */

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type NodeStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'

export interface JobLogEntry {
  ts: number
  level: 'info' | 'warn' | 'error'
  message: string
  nodeId?: string
}

export interface JobNodeRecord {
  nodeId: string
  nodeLabel: string
  nodeType: string
  status: NodeStatus
  startedAt?: number
  finishedAt?: number
  error?: string
  /** Compact preview of the node's output, suitable for table cells. */
  outputSummary?: string
}

export interface JobRecord {
  id: string
  /** Optional saved-workflow id; null for ad-hoc runs. */
  workflowId: string | null
  workflowName: string
  status: JobStatus
  createdAt: number
  startedAt?: number
  finishedAt?: number
  /** Filenames included in the run (best-effort, no file contents). */
  inputFiles: string[]
  nodes: JobNodeRecord[]
  logs: JobLogEntry[]
  error?: string
}

const STORAGE_KEY = 'dr-vision.jobs.v1'
const MAX_RUNS = 200
const MAX_LOGS_PER_RUN = 500

function readAll(): JobRecord[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch (err) {
    console.warn('Failed to parse job history', err)
    return []
  }
}

function writeAll(items: JobRecord[]): void {
  if (typeof window === 'undefined') return
  try {
    // Trim to bounded history before writing.
    const trimmed = items.slice(-MAX_RUNS)
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
  } catch (err) {
    console.error('Failed to persist jobs', err)
  }
}

function genId(): string {
  return `run-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function summarise(value: unknown): string | undefined {
  if (value === null || value === undefined) return undefined
  if (typeof value === 'string') {
    return value.length > 200 ? `${value.slice(0, 200)}…` : value
  }
  try {
    const json = JSON.stringify(value)
    return json.length > 200 ? `${json.slice(0, 200)}…` : json
  } catch {
    return undefined
  }
}

export function useJobs() {
  const jobs = useState<JobRecord[]>('jobs-store', () => readAll())
  const activeJobId = useState<string | null>('jobs-active-id', () => null)

  const persist = () => writeAll(jobs.value)

  const list = (filter?: { status?: JobStatus }): JobRecord[] => {
    const base = [...jobs.value].sort((a, b) => b.createdAt - a.createdAt)
    if (!filter?.status) return base
    return base.filter((j) => j.status === filter.status)
  }

  const get = (id: string): JobRecord | undefined => {
    return jobs.value.find((j) => j.id === id)
  }

  const create = (params: {
    workflowName: string
    workflowId?: string | null
    inputFiles: string[]
    nodes: Array<{ id: string; label: string; type: string }>
  }): JobRecord => {
    const now = Date.now()
    const record: JobRecord = {
      id: genId(),
      workflowId: params.workflowId ?? null,
      workflowName: params.workflowName,
      status: 'queued',
      createdAt: now,
      inputFiles: params.inputFiles,
      nodes: params.nodes.map((n) => ({
        nodeId: n.id,
        nodeLabel: n.label,
        nodeType: n.type,
        status: 'pending',
      })),
      logs: [
        {
          ts: now,
          level: 'info',
          message: `Run created with ${params.nodes.length} node(s) and ${params.inputFiles.length} file(s)`,
        },
      ],
    }
    jobs.value = [...jobs.value, record]
    activeJobId.value = record.id
    persist()
    return record
  }

  const start = (id: string) => {
    const job = jobs.value.find((j) => j.id === id)
    if (!job) return
    job.status = 'running'
    job.startedAt = Date.now()
    job.logs.push({ ts: job.startedAt, level: 'info', message: 'Run started' })
    persist()
  }

  const updateNode = (
    runId: string,
    nodeId: string,
    patch: Partial<JobNodeRecord> & { output?: unknown }
  ) => {
    const job = jobs.value.find((j) => j.id === runId)
    if (!job) return
    const node = job.nodes.find((n) => n.nodeId === nodeId)
    if (!node) return

    const { output, ...rest } = patch
    Object.assign(node, rest)
    if (output !== undefined && node.outputSummary === undefined) {
      node.outputSummary = summarise(output)
    }
    persist()
  }

  const log = (
    runId: string,
    message: string,
    level: JobLogEntry['level'] = 'info',
    nodeId?: string
  ) => {
    const job = jobs.value.find((j) => j.id === runId)
    if (!job) return
    job.logs.push({ ts: Date.now(), level, message, nodeId })
    if (job.logs.length > MAX_LOGS_PER_RUN) {
      job.logs.splice(0, job.logs.length - MAX_LOGS_PER_RUN)
    }
    persist()
  }

  const finish = (runId: string, status: 'completed' | 'failed' | 'cancelled', error?: string) => {
    const job = jobs.value.find((j) => j.id === runId)
    if (!job) return
    job.status = status
    job.finishedAt = Date.now()
    if (error) job.error = error
    job.logs.push({
      ts: job.finishedAt,
      level: status === 'completed' ? 'info' : 'error',
      message: status === 'completed' ? 'Run completed' : `Run ${status}${error ? `: ${error}` : ''}`,
    })
    if (activeJobId.value === runId) activeJobId.value = null
    persist()
  }

  const remove = (id: string): boolean => {
    const next = jobs.value.filter((j) => j.id !== id)
    if (next.length === jobs.value.length) return false
    jobs.value = next
    persist()
    return true
  }

  const clearCompleted = (): number => {
    const before = jobs.value.length
    jobs.value = jobs.value.filter((j) => j.status === 'running' || j.status === 'queued')
    persist()
    return before - jobs.value.length
  }

  const clearAll = (): void => {
    jobs.value = []
    activeJobId.value = null
    persist()
  }

  /** Stats for header tiles. */
  const stats = computed(() => {
    let running = 0
    let completed = 0
    let failed = 0
    let queued = 0
    for (const j of jobs.value) {
      if (j.status === 'running') running++
      else if (j.status === 'completed') completed++
      else if (j.status === 'failed') failed++
      else if (j.status === 'queued') queued++
    }
    return { total: jobs.value.length, running, completed, failed, queued }
  })

  return {
    jobs,
    activeJobId,
    stats,
    list,
    get,
    create,
    start,
    updateNode,
    log,
    finish,
    remove,
    clearCompleted,
    clearAll,
  }
}
