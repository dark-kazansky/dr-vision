<template>
  <div class="jobs-view">
    <!-- Header / stats -->
    <div class="jobs-header">
      <div class="jobs-title-block">
        <h2 class="jobs-title">Jobs</h2>
        <p class="jobs-subtitle">
          Workflow runs, status and history
          <span class="jobs-source-tag" :class="useBackend ? 'tag-backend' : 'tag-local'">
            {{ useBackend ? 'backend' : 'local' }}
          </span>
        </p>
      </div>
      <div class="jobs-actions">
        <button class="jobs-btn jobs-btn-ghost" @click="autoRefresh = !autoRefresh" :title="autoRefresh ? 'Pause auto-refresh' : 'Resume auto-refresh'">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {{ autoRefresh ? 'Live' : 'Paused' }}
        </button>
        <button class="jobs-btn jobs-btn-ghost" @click="onClearCompleted" :disabled="stats.completed + stats.failed === 0">
          Clear finished
        </button>
        <button class="jobs-btn jobs-btn-danger" @click="onClearAll" :disabled="rows.length === 0">
          Clear all
        </button>
      </div>
    </div>

    <!-- Stat tiles -->
    <div class="jobs-stats">
      <button
        v-for="tile in tiles"
        :key="tile.key"
        class="stat-tile"
        :class="{ active: filter === tile.key, [`tile-${tile.tone}`]: true }"
        @click="filter = tile.key"
      >
        <span class="stat-tile-value">{{ tile.value }}</span>
        <span class="stat-tile-label">{{ tile.label }}</span>
      </button>
    </div>

    <!-- Search -->
    <div class="jobs-toolbar">
      <input
        v-model="searchTerm"
        type="search"
        class="jobs-search"
        placeholder="Search workflow name or file…"
      />
    </div>

    <!-- Table -->
    <div class="jobs-table-wrap">
      <table class="jobs-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Workflow</th>
            <th>Files</th>
            <th>Started</th>
            <th>Duration</th>
            <th>Progress</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredRows.length === 0">
            <td colspan="7" class="jobs-empty">No runs match the current filter.</td>
          </tr>
          <tr
            v-for="row in filteredRows"
            :key="row.id"
            class="jobs-row"
            :class="{ active: selectedId === row.id }"
            @click="selectedId = row.id"
          >
            <td>
              <span class="status-badge" :class="`status-${row.status}`">
                <span class="status-dot" />
                {{ row.status }}
              </span>
            </td>
            <td>
              <div class="cell-primary">{{ row.workflowName }}</div>
              <div class="cell-secondary">{{ row.id }}</div>
            </td>
            <td>
              <div class="cell-primary">{{ row.inputFiles.length }} file<template v-if="row.inputFiles.length !== 1">s</template></div>
              <div class="cell-secondary">{{ formatFiles(row.inputFiles) }}</div>
            </td>
            <td>{{ row.startedAt ? formatTime(row.startedAt) : '—' }}</td>
            <td>{{ formatDuration(row) }}</td>
            <td>
              <div class="progress-bar" :title="`${row.completedNodes}/${row.totalNodes} nodes`">
                <div
                  class="progress-fill"
                  :class="`progress-${row.status}`"
                  :style="{ width: `${row.progress}%` }"
                />
              </div>
              <div class="cell-secondary">{{ row.completedNodes }}/{{ row.totalNodes }} nodes</div>
            </td>
            <td>
              <button class="row-action" @click.stop="onDeleteRun(row.id)" title="Delete run">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Detail drawer -->
    <div v-if="selected" class="job-drawer" :class="{ open: !!selected }">
      <div class="drawer-header">
        <div>
          <div class="drawer-title">{{ selected.workflowName }}</div>
          <div class="drawer-subtitle">
            <span class="status-badge" :class="`status-${selected.status}`">
              <span class="status-dot" />
              {{ selected.status }}
            </span>
            <span class="drawer-id">{{ selected.id }}</span>
          </div>
        </div>
        <button class="drawer-close" @click="selectedId = null">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Cancel running run (backend only) -->
      <div v-if="useBackend && (selected.status === 'running' || selected.status === 'queued')" class="drawer-actions">
        <button class="jobs-btn jobs-btn-danger" @click="onCancelRun">
          Cancel run
        </button>
      </div>

      <div class="drawer-meta">
        <div class="meta-pair">
          <span class="meta-label">Created</span>
          <span class="meta-value">{{ formatTime(selected.createdAt) }}</span>
        </div>
        <div class="meta-pair">
          <span class="meta-label">Started</span>
          <span class="meta-value">{{ selected.startedAt ? formatTime(selected.startedAt) : '—' }}</span>
        </div>
        <div class="meta-pair">
          <span class="meta-label">Finished</span>
          <span class="meta-value">{{ selected.finishedAt ? formatTime(selected.finishedAt) : '—' }}</span>
        </div>
        <div class="meta-pair">
          <span class="meta-label">Duration</span>
          <span class="meta-value">{{ formatDuration(rowFor(selected)) }}</span>
        </div>
        <div class="meta-pair full">
          <span class="meta-label">Files</span>
          <span class="meta-value">{{ selected.inputFiles.join(', ') || '—' }}</span>
        </div>
        <div v-if="selected.error" class="meta-pair full meta-error">
          <span class="meta-label">Error</span>
          <span class="meta-value">{{ selected.error }}</span>
        </div>
      </div>

      <!-- Nodes list -->
      <div class="drawer-section">
        <div class="drawer-section-title">Nodes</div>
        <div class="node-list">
          <div
            v-for="n in selected.nodes"
            :key="n.nodeId"
            class="node-row"
            :class="`node-${n.status}`"
          >
            <div class="node-row-main">
              <span class="status-badge small" :class="`status-${mapNodeStatus(n.status)}`">
                <span class="status-dot" />
                {{ n.status }}
              </span>
              <div class="node-row-text">
                <div class="node-row-label">{{ n.nodeLabel }}</div>
                <div class="node-row-type">{{ n.nodeType }}</div>
              </div>
            </div>
            <div class="node-row-meta">
              <span v-if="n.startedAt && n.finishedAt">
                {{ formatMs(n.finishedAt - n.startedAt) }}
              </span>
              <span v-else-if="n.startedAt">running…</span>
              <span v-else>—</span>
            </div>
            <div v-if="n.error" class="node-row-error">{{ n.error }}</div>
            <div v-else-if="n.outputSummary" class="node-row-output">{{ n.outputSummary }}</div>
          </div>
        </div>
      </div>

      <!-- Logs -->
      <div class="drawer-section">
        <div class="drawer-section-title">Logs ({{ selected.logs.length }})</div>
        <div class="log-list">
          <div
            v-for="(l, i) in selected.logs"
            :key="i"
            class="log-line"
            :class="`log-${l.level}`"
          >
            <span class="log-ts">{{ formatTime(l.ts, true) }}</span>
            <span class="log-level">{{ l.level }}</span>
            <span class="log-msg">{{ l.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { JobRecord, JobStatus, NodeStatus } from '../composables/useJobs'

type FilterKey = 'all' | JobStatus

const { jobs, stats, list, remove, clearCompleted, clearAll } = useJobs()
const api = useWorkflowApi()

const filter = ref<FilterKey>('all')
const searchTerm = ref('')
const selectedId = ref<string | null>(null)
const autoRefresh = ref(true)
const useBackend = ref(false)

// Backend-backed state. Populated when /workflows is reachable.
const backendRuns = ref<JobRecord[]>([])
const backendStats = ref({ total: 0, running: 0, queued: 0, completed: 0, failed: 0 })
const backendDetail = ref<JobRecord | null>(null)

const refreshFromBackend = async () => {
  try {
    const res = await api.listRuns({ limit: 100 })
    // Map backend summaries to the JobRecord shape used by the rest of the view.
    backendRuns.value = res.runs.map((r) => ({
      id: r.id,
      workflowId: r.workflowId,
      workflowName: r.workflowName,
      status: r.status,
      createdAt: r.createdAt,
      startedAt: r.startedAt ?? undefined,
      finishedAt: r.finishedAt ?? undefined,
      inputFiles: r.inputFiles,
      // The list endpoint does not include nodes/logs; backendDetail holds them.
      nodes: Array.from({ length: r.totalNodes }, (_, i) => ({
        nodeId: `${r.id}-node-${i}`,
        nodeLabel: '',
        nodeType: '',
        status: i < r.completedNodes ? 'completed' : 'pending',
      })),
      logs: [],
      error: r.error ?? undefined,
    }))
    let running = 0, queued = 0, completed = 0, failed = 0
    for (const r of res.runs) {
      if (r.status === 'running') running++
      else if (r.status === 'queued') queued++
      else if (r.status === 'completed') completed++
      else if (r.status === 'failed') failed++
    }
    backendStats.value = { total: res.total, running, queued, completed, failed }
  } catch (err) {
    console.warn('Failed to load backend runs', err)
  }
}

const refreshDetail = async () => {
  if (!useBackend.value || !selectedId.value) return
  try {
    const detail = await api.getRun(selectedId.value)
    backendDetail.value = {
      id: detail.id,
      workflowId: detail.workflowId,
      workflowName: detail.workflowName,
      status: detail.status,
      createdAt: detail.createdAt,
      startedAt: detail.startedAt ?? undefined,
      finishedAt: detail.finishedAt ?? undefined,
      inputFiles: detail.inputFiles,
      nodes: detail.nodes.map((n) => ({
        nodeId: n.nodeId,
        nodeLabel: n.nodeLabel,
        nodeType: n.nodeType,
        status: n.status,
        startedAt: n.startedAt ?? undefined,
        finishedAt: n.finishedAt ?? undefined,
        error: n.error ?? undefined,
        outputSummary: n.outputSummary ?? undefined,
      })),
      logs: detail.logs,
      error: detail.error ?? undefined,
    }
  } catch (err) {
    console.warn('Failed to load run detail', err)
  }
}

// useState in jobs auto-updates; this just nudges the computed when localStorage
// is mutated by another tab.
let pollHandle: ReturnType<typeof setInterval> | null = null
onMounted(async () => {
  useBackend.value = await api.checkAvailable()
  if (useBackend.value) await refreshFromBackend()

  pollHandle = setInterval(async () => {
    if (!autoRefresh.value) return
    if (useBackend.value) {
      await refreshFromBackend()
      await refreshDetail()
    } else {
      // Force a recompute by touching the reactive ref length.
      void jobs.value.length
    }
  }, 1500)
})
onBeforeUnmount(() => {
  if (pollHandle) clearInterval(pollHandle)
})

watch(selectedId, async () => {
  if (useBackend.value && selectedId.value) await refreshDetail()
  else backendDetail.value = null
})

const tiles = computed(() => {
  const s = useBackend.value ? backendStats.value : stats.value
  return [
    { key: 'all' as FilterKey, label: 'Total', value: s.total, tone: 'neutral' },
    { key: 'running' as FilterKey, label: 'Running', value: s.running, tone: 'running' },
    { key: 'queued' as FilterKey, label: 'Queued', value: s.queued, tone: 'queued' },
    { key: 'completed' as FilterKey, label: 'Completed', value: s.completed, tone: 'completed' },
    { key: 'failed' as FilterKey, label: 'Failed', value: s.failed, tone: 'failed' },
  ]
})

interface DisplayRow extends JobRecord {
  totalNodes: number
  completedNodes: number
  progress: number
}

const rows = computed<DisplayRow[]>(() => {
  const source = useBackend.value
    ? [...backendRuns.value].sort((a, b) => b.createdAt - a.createdAt)
    : list()
  return source.map((j) => {
    const total = j.nodes.length
    const completed = j.nodes.filter((n) => n.status === 'completed' || n.status === 'skipped').length
    const failed = j.nodes.filter((n) => n.status === 'failed').length
    const progress = total === 0 ? 0 : Math.round(((completed + failed) / total) * 100)
    return { ...j, totalNodes: total, completedNodes: completed, progress }
  })
})

const filteredRows = computed<DisplayRow[]>(() => {
  const term = searchTerm.value.trim().toLowerCase()
  return rows.value.filter((row) => {
    if (filter.value !== 'all' && row.status !== filter.value) return false
    if (!term) return true
    const haystack = [
      row.workflowName,
      row.id,
      ...row.inputFiles,
    ].join(' ').toLowerCase()
    return haystack.includes(term)
  })
})

const selected = computed<JobRecord | undefined>(() => {
  if (useBackend.value) return backendDetail.value || undefined
  return selectedId.value ? rows.value.find((r) => r.id === selectedId.value) : undefined
})

const rowFor = (j: JobRecord): DisplayRow | undefined => rows.value.find((r) => r.id === j.id)

const mapNodeStatus = (s: NodeStatus): JobStatus => {
  if (s === 'running') return 'running'
  if (s === 'completed') return 'completed'
  if (s === 'failed') return 'failed'
  if (s === 'skipped') return 'cancelled'
  return 'queued'
}

const formatTime = (ts: number, withMs = false): string => {
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  const base = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  return withMs ? `${base}.${String(d.getMilliseconds()).padStart(3, '0')}` : base
}

const formatMs = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  const m = Math.floor(ms / 60_000)
  const s = Math.floor((ms % 60_000) / 1000)
  return `${m}m ${s}s`
}

const formatDuration = (row?: DisplayRow | JobRecord): string => {
  if (!row) return '—'
  if (!row.startedAt) return '—'
  const end = row.finishedAt ?? Date.now()
  return formatMs(end - row.startedAt)
}

const formatFiles = (files: string[]): string => {
  if (!files.length) return '—'
  if (files.length <= 2) return files.join(', ')
  return `${files.slice(0, 2).join(', ')} +${files.length - 2}`
}

const onDeleteRun = async (id: string) => {
  if (!confirm('Delete this run from history?')) return
  if (useBackend.value) {
    try {
      await api.deleteRun(id)
      await refreshFromBackend()
    } catch (err) {
      console.error('Failed to delete run', err)
    }
  } else {
    remove(id)
  }
  if (selectedId.value === id) selectedId.value = null
}

const onClearCompleted = async () => {
  if (!confirm('Clear all completed and failed runs?')) return
  if (useBackend.value) {
    try {
      await api.clearFinishedRuns()
      await refreshFromBackend()
    } catch (err) {
      console.error('Failed to clear runs', err)
    }
  } else {
    clearCompleted()
  }
}

const onClearAll = () => {
  if (!confirm('Clear ALL runs including running ones from history?')) return
  if (useBackend.value) {
    // Backend has no bulk delete; do it best-effort by clearing finished only.
    api.clearFinishedRuns().then(() => refreshFromBackend()).catch((err) =>
      console.error('Failed to clear runs', err),
    )
  } else {
    clearAll()
  }
  selectedId.value = null
}

const onCancelRun = async () => {
  if (!useBackend.value || !selected.value) return
  if (!confirm('Cancel this run?')) return
  try {
    await api.cancelRun(selected.value.id)
    await refreshDetail()
    await refreshFromBackend()
  } catch (err: any) {
    console.error('Failed to cancel run', err)
  }
}
</script>

<style scoped>
.jobs-view {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  gap: 16px;
  overflow: hidden;
}

.jobs-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.jobs-title {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.jobs-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin: 4px 0 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.jobs-source-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.tag-backend { color: #047857; background: #d1fae5; border: 1px solid #a7f3d0; }
.tag-local   { color: #92400e; background: #fef3c7; border: 1px solid #fde68a; }

.drawer-actions {
  padding: 10px 16px;
  border-bottom: 1px solid #f3f4f6;
  background: #fff7ed;
}

.jobs-actions {
  display: flex;
  gap: 8px;
}

.jobs-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  transition: all 0.15s;
}
.jobs-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}
.jobs-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.jobs-btn-danger {
  color: #b91c1c;
  border-color: #fecaca;
}
.jobs-btn-danger:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #fca5a5;
}

.jobs-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.stat-tile {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 14px 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
}
.stat-tile:hover { border-color: #9ca3af; }
.stat-tile.active { border-color: #ff8c5a; box-shadow: 0 0 0 1px #ff8c5a; }
.stat-tile-value {
  font-size: 22px;
  font-weight: 600;
  color: #111827;
  line-height: 1;
}
.stat-tile-label {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.tile-running .stat-tile-value { color: #1d4ed8; }
.tile-queued .stat-tile-value { color: #92400e; }
.tile-completed .stat-tile-value { color: #047857; }
.tile-failed .stat-tile-value { color: #b91c1c; }

.jobs-toolbar {
  display: flex;
  gap: 8px;
}
.jobs-search {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
}
.jobs-search:focus {
  outline: none;
  border-color: #ff8c5a;
  box-shadow: 0 0 0 2px rgba(255, 140, 90, 0.2);
}

.jobs-table-wrap {
  flex: 1;
  overflow: auto;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.jobs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.jobs-table thead th {
  text-align: left;
  padding: 10px 14px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
  position: sticky;
  top: 0;
  z-index: 1;
}
.jobs-table tbody td {
  padding: 10px 14px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: top;
}
.jobs-row {
  cursor: pointer;
  transition: background 0.1s;
}
.jobs-row:hover { background: #f9fafb; }
.jobs-row.active { background: #fff4ec; }
.jobs-empty {
  text-align: center;
  color: #9ca3af;
  padding: 32px !important;
}
.cell-primary {
  color: #111827;
  font-weight: 500;
}
.cell-secondary {
  color: #9ca3af;
  font-size: 11px;
  margin-top: 2px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
  border: 1px solid transparent;
}
.status-badge.small { padding: 1px 6px; font-size: 10px; }
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.status-running   { color: #1d4ed8; background: #dbeafe; border-color: #bfdbfe; }
.status-queued    { color: #92400e; background: #fef3c7; border-color: #fde68a; }
.status-completed { color: #047857; background: #d1fae5; border-color: #a7f3d0; }
.status-failed    { color: #b91c1c; background: #fee2e2; border-color: #fecaca; }
.status-cancelled { color: #4b5563; background: #f3f4f6; border-color: #e5e7eb; }

.progress-bar {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #f3f4f6;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  transition: width 0.3s;
}
.progress-running   { background: #3b82f6; }
.progress-queued    { background: #f59e0b; }
.progress-completed { background: #10b981; }
.progress-failed    { background: #ef4444; }
.progress-cancelled { background: #9ca3af; }

.row-action {
  border: none;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}
.row-action:hover { color: #b91c1c; background: #fef2f2; }

/* Drawer */
.job-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 480px;
  background: white;
  border-left: 1px solid #e5e7eb;
  box-shadow: -8px 0 24px -8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transform: translateX(100%);
  transition: transform 0.2s ease-out;
}
.job-drawer.open { transform: translateX(0); }
.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}
.drawer-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}
.drawer-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.drawer-id {
  font-size: 11px;
  color: #9ca3af;
  font-family: ui-monospace, SFMono-Regular, monospace;
}
.drawer-close {
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}
.drawer-close:hover { background: #f3f4f6; }

.drawer-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
  padding: 14px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 12px;
}
.meta-pair { display: flex; flex-direction: column; gap: 2px; }
.meta-pair.full { grid-column: 1 / -1; }
.meta-label { color: #6b7280; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }
.meta-value { color: #111827; word-break: break-word; }
.meta-error .meta-value { color: #b91c1c; }

.drawer-section {
  padding: 14px 16px;
  border-bottom: 1px solid #f3f4f6;
}
.drawer-section:last-child { border-bottom: none; flex: 1; overflow: auto; }
.drawer-section-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  margin-bottom: 10px;
}

.node-list { display: flex; flex-direction: column; gap: 8px; }
.node-row {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px 12px;
  background: white;
}
.node-row.node-running { border-color: #bfdbfe; background: #eff6ff; }
.node-row.node-failed { border-color: #fecaca; background: #fef2f2; }
.node-row.node-completed { border-color: #a7f3d0; background: #f0fdf4; }
.node-row-main { display: flex; align-items: center; gap: 10px; }
.node-row-text { flex: 1; min-width: 0; }
.node-row-label { font-size: 13px; font-weight: 500; color: #111827; }
.node-row-type { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.03em; }
.node-row-meta { font-size: 11px; color: #6b7280; margin-top: 4px; }
.node-row-error { font-size: 12px; color: #b91c1c; margin-top: 6px; word-break: break-word; }
.node-row-output { font-size: 11px; color: #4b5563; margin-top: 6px; font-family: ui-monospace, SFMono-Regular, monospace; word-break: break-word; }

.log-list {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 11px;
  background: #0b1220;
  color: #e5e7eb;
  border-radius: 8px;
  padding: 10px 12px;
  max-height: 280px;
  overflow: auto;
}
.log-line { display: grid; grid-template-columns: 80px 60px 1fr; gap: 8px; padding: 2px 0; }
.log-ts { color: #9ca3af; }
.log-level { text-transform: uppercase; }
.log-info  .log-level { color: #60a5fa; }
.log-warn  .log-level { color: #fbbf24; }
.log-error .log-level { color: #f87171; }
.log-msg { white-space: pre-wrap; word-break: break-word; }
</style>
