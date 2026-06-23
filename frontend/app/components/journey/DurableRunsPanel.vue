<script setup lang="ts">
/**
 * DurableRunsPanel — Shows durable workflow engine runs with real-time progress.
 *
 * Displays active and recent runs from the durable engine,
 * with per-activity progress, status badges, and SSE live updates.
 */
import { useDurableWorkflow } from '~/composables/useDurableWorkflow'
import type { DurableRun } from '~/composables/useDurableWorkflow'

const {
  runs,
  isLoading,
  error,
  engineHealth,
  listRuns,
  cancelRun,
  getHealth,
  subscribeToRun,
  disconnect,
} = useDurableWorkflow()

// Active SSE subscriptions
const liveUpdates = ref<Record<string, Record<string, any>>>({})
const cleanupFns = ref<Record<string, () => void>>({})

// Filter
const statusFilter = ref<string>('')

const filteredRuns = computed(() => {
  if (!statusFilter.value) return runs.value
  return runs.value.filter(r => r.status === statusFilter.value)
})

// Status styling
const statusConfig: Record<string, { label: string; class: string }> = {
  pending: { label: 'Pending', class: 'badge-pending' },
  running: { label: 'Running', class: 'badge-running' },
  waiting_activity: { label: 'Processing', class: 'badge-running' },
  waiting_timer: { label: 'Waiting', class: 'badge-waiting' },
  completed: { label: 'Completed', class: 'badge-completed' },
  failed: { label: 'Failed', class: 'badge-failed' },
  cancelled: { label: 'Cancelled', class: 'badge-cancelled' },
  timed_out: { label: 'Timed Out', class: 'badge-failed' },
}

function getStatusBadge(status: string) {
  return statusConfig[status] || { label: status, class: 'badge-pending' }
}

function formatDuration(run: DurableRun): string {
  if (!run.started_at) return '-'
  const start = new Date(run.started_at).getTime()
  const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now()
  const ms = end - start
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// Subscribe to active runs for live updates
function subscribeActive() {
  // Clean up existing
  Object.values(cleanupFns.value).forEach(fn => fn())
  cleanupFns.value = {}

  const activeRuns = runs.value.filter(r =>
    ['running', 'waiting_activity', 'pending'].includes(r.status)
  )

  for (const run of activeRuns) {
    const cleanup = subscribeToRun(
      run.run_id,
      (eventType, data) => {
        // Update live state
        liveUpdates.value[run.run_id] = {
          ...liveUpdates.value[run.run_id],
          lastEvent: eventType,
          lastData: data,
          updatedAt: new Date().toISOString(),
        }
      },
      () => {
        // On stream end — refresh list
        listRuns()
      },
    )
    cleanupFns.value[run.run_id] = cleanup
  }
}

// Cancel handler
async function handleCancel(runId: string) {
  if (!confirm('Cancel this workflow run?')) return
  await cancelRun(runId)
}

// Activity count from run data
function getActivitySummary(run: DurableRun): string {
  const states = run.activity_states
  if (!states) return ''
  const total = Object.keys(states).length
  const completed = Object.values(states).filter((s: any) => s.status === 'completed').length
  if (total === 0) return ''
  return `${completed}/${total}`
}

// Lifecycle
onMounted(async () => {
  await Promise.all([listRuns(), getHealth()])
  subscribeActive()
})

// Re-subscribe when runs change
watch(runs, () => {
  subscribeActive()
}, { deep: true })

onUnmounted(() => {
  Object.values(cleanupFns.value).forEach(fn => fn())
  disconnect()
})
</script>

<template>
  <div class="durable-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="panel-title-row">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <span class="panel-title">Durable Workflows</span>
        <span v-if="engineHealth" class="engine-badge" :class="engineHealth.engine_status === 'running' ? 'badge-running' : 'badge-failed'">
          {{ engineHealth.engine_status }}
        </span>
      </div>

      <!-- Filter -->
      <div class="panel-controls">
        <select v-model="statusFilter" class="status-filter">
          <option value="">All</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <button class="btn-refresh" @click="listRuns()" title="Refresh">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="engineHealth" class="stats-row">
      <div class="stat-item">
        <span class="stat-value">{{ engineHealth.active_runs }}</span>
        <span class="stat-label">Active</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ engineHealth.pending_tasks }}</span>
        <span class="stat-label">Queued</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ engineHealth.processing_tasks }}</span>
        <span class="stat-label">Processing</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading && runs.length === 0" class="loading-state">
      <div class="load-spinner" />
      <span>Loading runs...</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <span>{{ error }}</span>
    </div>

    <!-- Empty -->
    <div v-else-if="filteredRuns.length === 0" class="empty-state">
      <p>No workflow runs{{ statusFilter ? ` with status "${statusFilter}"` : '' }}</p>
    </div>

    <!-- Runs list -->
    <div v-else class="runs-list">
      <div
        v-for="run in filteredRuns"
        :key="run.run_id"
        class="run-card"
      >
        <div class="run-header">
          <span class="run-name">{{ run.workflow_name || 'Untitled' }}</span>
          <span class="run-badge" :class="getStatusBadge(run.status).class">
            {{ getStatusBadge(run.status).label }}
          </span>
        </div>

        <div class="run-meta">
          <span class="run-time">{{ formatTime(run.created_at) }}</span>
          <span v-if="run.started_at" class="run-duration">{{ formatDuration(run) }}</span>
          <span v-if="getActivitySummary(run)" class="run-progress">
            {{ getActivitySummary(run) }} activities
          </span>
        </div>

        <!-- Activity progress bar -->
        <div v-if="run.activity_states && Object.keys(run.activity_states).length > 0" class="activity-bar">
          <div
            v-for="(state, actId) in run.activity_states"
            :key="actId"
            class="activity-dot"
            :class="`dot-${(state as any).status}`"
            :title="`${(state as any).label || actId}: ${(state as any).status}`"
          />
        </div>

        <!-- Live update indicator -->
        <div v-if="liveUpdates[run.run_id]" class="live-indicator">
          <span class="live-dot" />
          <span class="live-text">{{ liveUpdates[run.run_id]?.lastEvent }}</span>
        </div>

        <!-- Actions -->
        <div v-if="['running', 'waiting_activity', 'pending'].includes(run.status)" class="run-actions">
          <button class="btn-cancel" @click.stop="handleCancel(run.run_id)">
            Cancel
          </button>
        </div>

        <!-- Error message -->
        <div v-if="run.error" class="run-error">
          {{ run.error }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.durable-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: #fafbfc;
  border-radius: 12px;
  border: 1px solid #e8ecf0;
  font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Header */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.panel-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-filter {
  font-size: 12px;
  padding: 4px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #475569;
  cursor: pointer;
}

.btn-refresh {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-refresh:hover {
  border-color: #ff6f3c;
  color: #ff6f3c;
}

/* Engine badge */
.engine-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  text-transform: uppercase;
}

/* Stats */
.stats-row {
  display: flex;
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}

.stat-label {
  font-size: 10px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Loading / Error / Empty */
.loading-state, .error-state, .empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: #64748b;
  font-size: 13px;
}

.error-state { color: #ef4444; }

.load-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e2e8f0;
  border-top-color: #ff6f3c;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Runs list */
.runs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.run-card {
  padding: 12px;
  background: white;
  border: 1px solid #e8ecf0;
  border-radius: 8px;
  transition: border-color 0.15s;
}

.run-card:hover {
  border-color: #ff6f3c40;
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.run-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

/* Status badges */
.run-badge, .engine-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.badge-pending { background: #f1f5f9; color: #64748b; }
.badge-running { background: #dbeafe; color: #2563eb; }
.badge-waiting { background: #fef3c7; color: #d97706; }
.badge-completed { background: #dcfce7; color: #16a34a; }
.badge-failed { background: #fee2e2; color: #dc2626; }
.badge-cancelled { background: #f1f5f9; color: #94a3b8; }

/* Meta */
.run-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.run-duration {
  font-weight: 500;
  color: #64748b;
}

/* Activity progress bar */
.activity-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
}

.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-pending { background: #e2e8f0; }
.dot-scheduled { background: #e2e8f0; border: 1px solid #94a3b8; }
.dot-running { background: #3b82f6; animation: pulse 1s infinite; }
.dot-completed { background: #22c55e; }
.dot-failed { background: #ef4444; }
.dot-skipped { background: #cbd5e1; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Live indicator */
.live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: #64748b;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  animation: pulse 1.5s infinite;
}

.live-text {
  font-family: monospace;
  font-size: 10px;
}

/* Actions */
.run-actions {
  margin-top: 8px;
}

.btn-cancel {
  font-size: 11px;
  padding: 3px 10px;
  border: 1px solid #fecaca;
  border-radius: 4px;
  background: #fff5f5;
  color: #dc2626;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s;
}

.btn-cancel:hover {
  background: #fee2e2;
  border-color: #f87171;
}

/* Error */
.run-error {
  margin-top: 6px;
  font-size: 11px;
  color: #dc2626;
  background: #fef2f2;
  padding: 4px 8px;
  border-radius: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
