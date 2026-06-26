<script setup lang="ts">
/**
 * Job Panel — Modal popup showing job list + execution state details.
 *
 * Layout:
 * - Left: List of all executed jobs (with status badges)
 * - Right: Selected job details (progress, node outputs/state)
 *
 * feat-007: Integrates execution state viewer directly into job details.
 */
import { useJobManager } from '~/composables/workflow/useJobManager'
import { useExecutionState } from '~/composables/workflow/useExecutionState'
import type { Job, JobNode } from '~/composables/workflow/useJobManager'

const {
  currentJob,
  jobHistory,
  jobPanelOpen,
  isSubmitting,
  isTerminal,
  isRunning,
  cancelJob,
  closePanel,
  fetchJobHistory,
  selectJob,
  connectSSE,
} = useJobManager()

const {
  executionState,
  isLoading: isStateLoading,
  stateError,
  canResume,
  completedNodeIds,
  failedNodeId,
  fetchState,
  resumeJob,
} = useExecutionState()

// Detail view tab
const detailTab = ref<'progress' | 'state' | 'context'>('progress')
const expandedNodes = ref<Set<string>>(new Set())
const showResumeDialog = ref(false)
const resumeFile = ref<File | null>(null)

// Fetch history when panel opens
watch(jobPanelOpen, (open) => {
  if (open) {
    fetchJobHistory()
  }
})

// Fetch execution state when selecting a job
watch(currentJob, (job) => {
  if (job) {
    fetchState(job.job_id)
  }
})

const statusColor = (status: string): string => {
  switch (status) {
    case 'queued': return '#6b7280'
    case 'running': return '#3b82f6'
    case 'completed': return '#10b981'
    case 'failed': return '#ef4444'
    case 'cancelled': return '#f59e0b'
    case 'retrying': return '#f97316'
    case 'skipped': return '#9ca3af'
    case 'pending': return '#d1d5db'
    default: return '#6b7280'
  }
}

const statusIcon = (status: string): string => {
  switch (status) {
    case 'pending': return '○'
    case 'running': return '◉'
    case 'completed': return '✓'
    case 'failed': return '✗'
    case 'cancelled': return '⊘'
    case 'retrying': return '↻'
    case 'skipped': return '–'
    case 'queued': return '◷'
    default: return '○'
  }
}

const formatDuration = (job: Job): string => {
  if (!job.started_at) return '—'
  const start = new Date(job.started_at).getTime()
  const end = job.completed_at ? new Date(job.completed_at).getTime() : Date.now()
  const seconds = Math.round((end - start) / 1000)
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

const formatTime = (iso: string | null): string => {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString()
}

const formatDate = (iso: string | null): string => {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`
}

const formatMs = (ms: number | null): string => {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

const formatOutput = (output: any): string => {
  if (output === null || output === undefined) return 'null'
  if (typeof output === 'string') return output
  return JSON.stringify(output, null, 2)
}

const toggleNodeExpand = (nodeId: string) => {
  if (expandedNodes.value.has(nodeId)) {
    expandedNodes.value.delete(nodeId)
  } else {
    expandedNodes.value.add(nodeId)
  }
}

const onCancel = async () => {
  if (confirm('Cancel this job? The current node will finish before stopping.')) {
    await cancelJob()
  }
}

const onSelectJob = (job: Job) => {
  selectJob(job)
  detailTab.value = 'progress'
  expandedNodes.value.clear()
}

const handleResumeFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    resumeFile.value = input.files[0] ?? null
  }
}

const handleResume = async () => {
  if (!resumeFile.value || !currentJob.value) return
  const result = await resumeJob(
    currentJob.value.job_id,
    resumeFile.value,
    failedNodeId.value || undefined,
  )
  if (result) {
    showResumeDialog.value = false
    resumeFile.value = null
    connectSSE(result.new_job_id)
    fetchJobHistory()
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="jobPanelOpen" class="job-modal-overlay" @click.self="closePanel">
        <div class="job-modal">
          <!-- Modal Header -->
          <div class="modal-header">
            <h3>Jobs</h3>
            <button class="close-btn" @click="closePanel">
              <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- Left: Job List -->
            <div class="job-list-panel">
              <div class="list-header">
                <span>Execution History</span>
                <button class="refresh-btn" @click="() => fetchJobHistory()" title="Refresh">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
              </div>

              <div v-if="jobHistory.length === 0" class="empty-list">
                No jobs executed yet.
              </div>

              <div v-else class="job-list">
                <div
                  v-for="job in jobHistory"
                  :key="job.job_id"
                  class="job-list-item"
                  :class="{ active: currentJob?.job_id === job.job_id }"
                  @click="onSelectJob(job)"
                >
                  <span class="item-status" :style="{ color: statusColor(job.status) }">
                    {{ statusIcon(job.status) }}
                  </span>
                  <div class="item-info">
                    <span class="item-name">{{ job.workflow_name || 'Unnamed' }}</span>
                    <span class="item-meta">{{ job.filename }} · {{ formatTime(job.created_at) }}</span>
                  </div>
                  <span
                    class="item-badge"
                    :style="{ background: statusColor(job.status) + '15', color: statusColor(job.status) }"
                  >
                    {{ job.status }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Right: Job Detail -->
            <div class="job-detail-panel">
              <div v-if="!currentJob" class="empty-detail">
                <svg width="40" height="40" fill="none" stroke="currentColor" viewBox="0 0 24 24" opacity="0.3">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p>Select a job to view details</p>
              </div>

              <template v-else>
                <!-- Detail Header -->
                <div class="detail-header">
                  <div class="detail-title">
                    <h4>{{ currentJob.workflow_name || 'Unnamed Job' }}</h4>
                    <span
                      class="detail-badge"
                      :style="{ background: statusColor(currentJob.status) + '15', color: statusColor(currentJob.status) }"
                    >
                      {{ currentJob.status }}
                    </span>
                  </div>
                  <div class="detail-meta">
                    <span>{{ currentJob.filename }}</span>
                    <span>{{ formatDuration(currentJob) }}</span>
                    <span>{{ formatDate(currentJob.created_at) }}</span>
                  </div>
                  <div class="detail-actions">
                    <button v-if="isRunning" class="cancel-btn" @click="onCancel">Cancel</button>
                    <button v-if="canResume" class="resume-btn" @click="showResumeDialog = true">
                      Resume
                    </button>
                  </div>
                </div>

                <!-- Detail Tabs -->
                <div class="detail-tabs">
                  <button
                    :class="['dtab', { active: detailTab === 'progress' }]"
                    @click="detailTab = 'progress'"
                  >
                    Progress
                  </button>
                  <button
                    :class="['dtab', { active: detailTab === 'state' }]"
                    @click="detailTab = 'state'"
                  >
                    Node Outputs
                    <span v-if="executionState" class="dtab-count">
                      {{ Object.keys(executionState.node_states).length }}
                    </span>
                  </button>
                  <button
                    :class="['dtab', { active: detailTab === 'context' }]"
                    @click="detailTab = 'context'"
                  >
                    Context
                  </button>
                </div>

                <!-- Progress Tab -->
                <div v-if="detailTab === 'progress'" class="detail-content">
                  <!-- Progress bar -->
                  <div class="progress-bar-container">
                    <div
                      class="progress-bar-fill"
                      :style="{ width: `${currentJob.progress * 100}%`, background: statusColor(currentJob.status) }"
                    />
                    <span class="progress-label">{{ Math.round(currentJob.progress * 100) }}%</span>
                  </div>

                  <!-- Node timeline -->
                  <div class="node-timeline">
                    <div
                      v-for="node in currentJob.nodes"
                      :key="node.node_id"
                      class="node-item"
                      :class="node.status"
                    >
                      <span class="node-icon" :style="{ color: statusColor(node.status) }">
                        {{ statusIcon(node.status) }}
                      </span>
                      <span class="node-label">{{ node.node_label }}</span>
                      <span v-if="node.retry_count > 0" class="retry-badge">↻{{ node.retry_count }}</span>
                      <span v-if="node.error" class="node-error" :title="node.error">
                        {{ node.error.slice(0, 50) }}{{ node.error.length > 50 ? '...' : '' }}
                      </span>
                    </div>
                  </div>

                  <!-- Error -->
                  <div v-if="currentJob.error" class="job-error">
                    <strong>Error:</strong> {{ currentJob.error }}
                  </div>
                </div>

                <!-- State (Node Outputs) Tab -->
                <div v-if="detailTab === 'state'" class="detail-content">
                  <div v-if="isStateLoading" class="loading-state">Loading state...</div>
                  <div v-else-if="stateError" class="error-state">{{ stateError }}</div>
                  <div v-else-if="!executionState || Object.keys(executionState.node_states).length === 0" class="empty-detail">
                    <p>No node outputs recorded yet.</p>
                  </div>
                  <div v-else class="node-states-list">
                    <div
                      v-for="(nodeData, nodeId) in executionState.node_states"
                      :key="nodeId"
                      class="state-item"
                      :class="nodeData.status"
                    >
                      <div class="state-item-header" @click="toggleNodeExpand(nodeId as string)">
                        <span class="state-dot" :class="nodeData.status" />
                        <span class="state-node-id">{{ nodeId }}</span>
                        <span class="state-status-label">{{ nodeData.status }}</span>
                        <span v-if="nodeData.duration_ms" class="state-duration">{{ formatMs(nodeData.duration_ms) }}</span>
                        <svg
                          width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                          class="expand-icon"
                          :class="{ expanded: expandedNodes.has(nodeId as string) }"
                        >
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                      <div v-if="nodeData.error" class="state-error">{{ nodeData.error }}</div>
                      <Transition name="expand">
                        <div v-if="expandedNodes.has(nodeId as string)" class="state-output">
                          <pre>{{ formatOutput(nodeData.output) }}</pre>
                        </div>
                      </Transition>
                    </div>
                  </div>
                </div>

                <!-- Context Tab -->
                <div v-if="detailTab === 'context'" class="detail-content">
                  <div v-if="!executionState || Object.keys(executionState.context).length === 0" class="empty-detail">
                    <p>No shared context data.</p>
                  </div>
                  <div v-else class="context-list">
                    <div v-for="(value, key) in executionState.context" :key="key" class="context-item">
                      <span class="context-key">{{ key }}</span>
                      <span class="context-value">{{ typeof value === 'string' ? value : JSON.stringify(value) }}</span>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Resume Dialog -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="showResumeDialog" class="resume-overlay" @click.self="showResumeDialog = false">
        <div class="resume-dialog">
          <h4>Resume Job</h4>
          <p>Job failed at node <strong>{{ failedNodeId }}</strong>. Upload the file again to resume.</p>
          <input type="file" @change="handleResumeFileChange" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp" />
          <div class="resume-actions">
            <button class="btn-cancel" @click="showResumeDialog = false">Cancel</button>
            <button class="btn-resume" @click="handleResume" :disabled="!resumeFile || isStateLoading">
              {{ isStateLoading ? 'Resuming...' : 'Resume' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.job-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.job-modal {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  width: 90vw;
  max-width: 900px;
  height: 70vh;
  max-height: 600px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  border-radius: 6px;
  cursor: pointer;
  color: #9ca3af;
}
.close-btn:hover { background: #f3f4f6; color: #1f2937; }

.modal-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Left Panel: Job List */
.job-list-panel {
  width: 280px;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #f3f4f6;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  border: none;
  background: none;
  cursor: pointer;
  color: #9ca3af;
  padding: 4px;
  border-radius: 4px;
}
.refresh-btn:hover { background: #f3f4f6; color: #1f2937; }

.empty-list {
  padding: 32px 16px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
}

.job-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.job-list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.job-list-item:hover { background: #f9fafb; }
.job-list-item.active { background: #eff6ff; }

.item-status {
  font-size: 14px;
  font-weight: bold;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.item-name {
  font-size: 12px;
  font-weight: 500;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  font-size: 10px;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-badge {
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

/* Right Panel: Job Detail */
.job-detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.empty-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9ca3af;
  font-size: 13px;
  gap: 8px;
}

.detail-header {
  padding: 14px 20px;
  border-bottom: 1px solid #f3f4f6;
  flex-shrink: 0;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.detail-title h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.detail-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.detail-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #6b7280;
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.cancel-btn {
  padding: 4px 10px;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #dc2626;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}
.cancel-btn:hover { background: #fee2e2; }

.resume-btn {
  padding: 4px 10px;
  border: 1px solid #c4b5fd;
  background: #f5f3ff;
  color: #7c3aed;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}
.resume-btn:hover { background: #ede9fe; }

/* Detail Tabs */
.detail-tabs {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 20px;
  flex-shrink: 0;
}

.dtab {
  padding: 8px 14px;
  border: none;
  background: none;
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 4px;
}
.dtab:hover { color: #1f2937; }
.dtab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

.dtab-count {
  padding: 1px 5px;
  border-radius: 8px;
  background: #f3f4f6;
  font-size: 10px;
  color: #6b7280;
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 14px 20px;
}

/* Progress Tab */
.progress-bar-container {
  position: relative;
  height: 6px;
  background: #f3f4f6;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-label {
  position: absolute;
  right: 0;
  top: -18px;
  font-size: 11px;
  color: #6b7280;
}

.node-timeline {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 12px;
  border: 1px solid #f3f4f6;
}
.node-item.running { background: #eff6ff; border-color: #bfdbfe; }
.node-item.completed { background: #ecfdf5; border-color: #a7f3d0; }
.node-item.failed { background: #fef2f2; border-color: #fecaca; }
.node-item.retrying { background: #fff7ed; border-color: #fed7aa; }

.node-icon { font-size: 12px; font-weight: bold; }
.node-label { color: #374151; font-weight: 500; }
.retry-badge { font-size: 10px; color: #f97316; font-weight: 600; }
.node-error { font-size: 10px; color: #ef4444; margin-left: auto; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.job-error {
  margin-top: 12px;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  font-size: 12px;
  color: #dc2626;
}

/* State Tab */
.loading-state, .error-state {
  text-align: center;
  padding: 24px;
  font-size: 13px;
  color: #9ca3af;
}
.error-state { color: #ef4444; }

.node-states-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.state-item {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}
.state-item.completed { border-left: 3px solid #10b981; }
.state-item.failed { border-left: 3px solid #ef4444; }
.state-item.running { border-left: 3px solid #3b82f6; }

.state-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.15s;
}
.state-item-header:hover { background: #f9fafb; }

.state-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.state-dot.completed { background: #10b981; }
.state-dot.failed { background: #ef4444; }
.state-dot.running { background: #3b82f6; }
.state-dot.pending { background: #d1d5db; }

.state-node-id {
  font-size: 12px;
  font-weight: 600;
  color: #1f2937;
  font-family: 'SF Mono', ui-monospace, monospace;
}

.state-status-label {
  font-size: 10px;
  color: #6b7280;
}

.state-duration {
  font-size: 10px;
  color: #9ca3af;
  margin-left: auto;
}

.expand-icon {
  transition: transform 0.2s;
  color: #9ca3af;
  flex-shrink: 0;
}
.expand-icon.expanded { transform: rotate(180deg); }

.state-error {
  padding: 4px 12px 8px;
  font-size: 11px;
  color: #ef4444;
}

.state-output {
  border-top: 1px solid #f3f4f6;
  padding: 8px 12px;
  overflow-x: auto;
}

.state-output pre {
  margin: 0;
  font-size: 11px;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
  overflow-y: auto;
  font-family: 'SF Mono', ui-monospace, monospace;
}

/* Context Tab */
.context-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.context-item {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 12px;
}

.context-key {
  font-weight: 600;
  color: #3b82f6;
  font-family: 'SF Mono', ui-monospace, monospace;
  min-width: 140px;
  flex-shrink: 0;
}

.context-value {
  color: #374151;
  word-break: break-word;
}

/* Resume Dialog */
.resume-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.resume-dialog {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
}

.resume-dialog h4 { margin: 0 0 8px; font-size: 16px; color: #1f2937; }
.resume-dialog p { margin: 0 0 16px; font-size: 13px; color: #6b7280; }
.resume-dialog input { margin-bottom: 16px; font-size: 13px; }

.resume-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-cancel {
  padding: 8px 16px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}
.btn-cancel:hover { background: #f9fafb; }

.btn-resume {
  padding: 8px 16px;
  border: none;
  background: #7c3aed;
  color: white;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.btn-resume:hover:not(:disabled) { background: #6d28d9; }
.btn-resume:disabled { opacity: 0.5; cursor: not-allowed; }

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.expand-enter-active, .expand-leave-active { transition: all 0.2s ease; overflow: hidden; }
.expand-enter-from, .expand-leave-to { max-height: 0; opacity: 0; }
</style>
