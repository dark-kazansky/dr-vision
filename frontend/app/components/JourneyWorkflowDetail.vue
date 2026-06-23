<script setup lang="ts">
/**
 * JourneyWorkflowDetail — Full page view for managing a workflow's jobs.
 * 
 * Shows workflow info + list of all jobs (running, completed, failed).
 * User can open the builder from here or view job details.
 * All data fetched from real APIs (PostgreSQL + MinIO backed).
 */
import { useJobManager } from '~/composables/workflow/useJobManager'
import type { Job } from '~/composables/workflow/useJobManager'

const props = defineProps<{
  workflowId: string
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'open-builder', workflowId: string): void
}>()

const config = useRuntimeConfig()
const apiBaseUrl = config.public.apiBaseUrl as string

const { fetchJobHistory, jobHistory, cancelJob } = useJobManager()

// Workflow info
const workflow = ref<any>(null)
const isLoadingWorkflow = ref(true)

// Jobs
const jobs = ref<Job[]>([])
const isLoadingJobs = ref(true)

// Polling for running jobs
let pollInterval: ReturnType<typeof setInterval> | null = null

// Expanded job detail
const expandedJobId = ref<string | null>(null)
const nodeOutputsCache = ref<Record<string, Record<string, any>>>({})

const toggleJobExpand = async (jobId: string) => {
  if (expandedJobId.value === jobId) {
    expandedJobId.value = null
    return
  }
  expandedJobId.value = jobId
  // Fetch node outputs for this job if not cached
  if (!nodeOutputsCache.value[jobId]) {
    try {
      const response = await $fetch<{ job_id: string; node_outputs: Record<string, any> }>(
        `${apiBaseUrl}/api/v1/jobs/${jobId}/state/nodes`
      )
      nodeOutputsCache.value[jobId] = response.node_outputs || {}
    } catch {
      nodeOutputsCache.value[jobId] = {}
    }
  }
}

const getNodeResult = (jobId: string, nodeId: string): any => {
  return nodeOutputsCache.value[jobId]?.[nodeId] || null
}

const formatNodeDuration = (node: any): string => {
  if (!node.started_at || !node.completed_at) return '—'
  const ms = new Date(node.completed_at).getTime() - new Date(node.started_at).getTime()
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

const getNodeStatusIcon = (status: string): string => {
  switch (status) {
    case 'completed': return '✓'
    case 'running': return '◉'
    case 'failed': return '✗'
    case 'skipped': return '–'
    case 'pending': return '○'
    case 'retrying': return '↻'
    default: return '○'
  }
}

// Action button conditions
const canDelete = (job: Job): boolean => {
  return ['completed', 'failed', 'cancelled'].includes(job.status)
}

const canStop = (job: Job): boolean => {
  return ['running', 'queued'].includes(job.status)
}

const canRetry = (job: Job): boolean => {
  return job.status === 'failed'
}

const handleDelete = async (job: Job) => {
  if (!canDelete(job)) return
  try {
    await $fetch(`${apiBaseUrl}/api/v1/jobs/${job.job_id}`, { method: 'DELETE' })
    jobs.value = jobs.value.filter(j => j.job_id !== job.job_id)
    if (expandedJobId.value === job.job_id) expandedJobId.value = null
  } catch (error) {
    console.error('Failed to delete job:', error)
  }
}

const handleStop = async (job: Job) => {
  if (!canStop(job)) return
  const success = await cancelJob(job.job_id)
  if (success) {
    const idx = jobs.value.findIndex(j => j.job_id === job.job_id)
    if (idx !== -1) {
      jobs.value[idx] = { ...jobs.value[idx], status: 'cancelled' } as Job
    }
  }
}

const handleRetry = async (job: Job) => {
  if (!canRetry(job)) return
  try {
    // Use the resume endpoint — re-runs from the failed node
    const formData = new FormData()
    // Resume doesn't require a new file if the original is in MinIO
    const response = await $fetch<{ new_job_id: string }>(`${apiBaseUrl}/api/v1/jobs/${job.job_id}/resume`, {
      method: 'POST',
      body: formData,
    })
    // Refresh job list to show the new job
    await fetchJobs()
  } catch (error) {
    console.error('Failed to retry job:', error)
  }
}

// Deploy — show integration popup
const showDeployModal = ref(false)
const copiedField = ref('')

const handleDeploy = () => {
  showDeployModal.value = true
}

const triggerUrl = computed(() => `${apiBaseUrl}/api/v1/workflows/${props.workflowId}/trigger`)
const embedCode = computed(() => `<iframe src="${apiBaseUrl}/embed/workflow/${props.workflowId}" width="100%" height="600" frameborder="0"></iframe>`)
const curlExample = computed(() => `curl -X POST "${triggerUrl.value}" \\\n  -F "file=@document.pdf" \\\n  -F "max_retries=3"`)
const pythonExample = computed(() => `import requests\n\nresponse = requests.post(\n    "${triggerUrl.value}",\n    files={"file": open("document.pdf", "rb")},\n    data={"max_retries": 3}\n)\nprint(response.json())`)

const copyToClipboard = async (text: string, field: string) => {
  try {
    await navigator.clipboard.writeText(text)
    copiedField.value = field
    setTimeout(() => { copiedField.value = '' }, 2000)
  } catch {
    // fallback
  }
}

const fetchWorkflow = async () => {
  isLoadingWorkflow.value = true
  try {
    const data = await $fetch<any>(
      `${apiBaseUrl}/api/v1/workflows/${props.workflowId}`
    )
    workflow.value = data
  } catch (error) {
    console.error('Failed to fetch workflow:', error)
  } finally {
    isLoadingWorkflow.value = false
  }
}

const fetchJobs = async () => {
  isLoadingJobs.value = jobs.value.length === 0
  try {
    await fetchJobHistory({ workflowId: props.workflowId, limit: 50 })
    jobs.value = [...jobHistory.value]
  } catch (error) {
    console.error('Failed to fetch jobs:', error)
  } finally {
    isLoadingJobs.value = false
  }
}

const hasRunningJobs = computed(() =>
  jobs.value.some(j => j.status === 'running' || j.status === 'queued')
)

const formatJobDate = (iso: string | null): string => {
  if (!iso) return '—'
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const formatDuration = (job: Job): string => {
  if (!job.started_at) return '—'
  const start = new Date(job.started_at).getTime()
  const end = job.completed_at ? new Date(job.completed_at).getTime() : Date.now()
  const seconds = Math.round((end - start) / 1000)
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'queued': return '#6b7280'
    case 'running': return '#3b82f6'
    case 'completed': return '#10b981'
    case 'failed': return '#ef4444'
    case 'cancelled': return '#f59e0b'
    default: return '#6b7280'
  }
}

const getStatusBg = (status: string): string => {
  switch (status) {
    case 'queued': return '#f3f4f6'
    case 'running': return '#eff6ff'
    case 'completed': return '#f0fdf4'
    case 'failed': return '#fef2f2'
    case 'cancelled': return '#fffbeb'
    default: return '#f3f4f6'
  }
}

onMounted(async () => {
  await Promise.all([fetchWorkflow(), fetchJobs()])
  // Poll every 5s if there are running jobs
  pollInterval = setInterval(() => {
    if (hasRunningJobs.value) {
      fetchJobs()
    }
  }, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <div class="wf-detail">
    <!-- Header -->
    <div class="wf-detail-header">
      <div class="header-left">
        <button class="back-btn" @click="emit('back')" title="Quay lại Dashboard">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </button>
        <div class="header-icon">
          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div class="header-info">
          <h2 class="header-title">{{ workflow?.name || 'Loading...' }}</h2>
          <p v-if="workflow?.description" class="header-desc">{{ workflow.description }}</p>
        </div>
      </div>
      <div class="header-actions">
        <button class="action-btn action-btn-secondary" @click="handleDeploy" title="Copy API URL để tích hợp">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
          Deploy
        </button>
        <button class="action-btn action-btn-primary" @click="emit('open-builder', props.workflowId)">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Edit Workflow
        </button>
      </div>
    </div>



    <!-- Content -->
    <div class="wf-detail-content">
      <!-- Loading -->
      <div v-if="isLoadingJobs && jobs.length === 0" class="loading-state">
        <div class="loading-spinner" />
        <span>Loading jobs...</span>
      </div>

      <!-- Empty -->
      <div v-else-if="jobs.length === 0" class="empty-state">
        <div class="empty-circle">
          <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <h3 class="empty-title">Chưa có job nào</h3>
        <p class="empty-desc">Mở workflow builder để execute và tạo job đầu tiên</p>
      </div>

      <!-- Job List -->
      <div v-else class="job-table">
        <div class="job-table-header">
          <span class="col-status">Status</span>
          <span class="col-file">File</span>
          <span class="col-nodes">Nodes</span>
          <span class="col-duration">Duration</span>
          <span class="col-time">Created</span>
          <span class="col-progress">Progress</span>
          <span class="col-actions">Actions</span>
        </div>
        <template v-for="job in jobs" :key="job.job_id">
          <div
            class="job-row"
            :class="{ 'job-row-active': job.status === 'running', 'job-row-expanded': expandedJobId === job.job_id }"
            @click="toggleJobExpand(job.job_id)"
          >
            <span class="col-status">
              <span
                class="status-badge"
                :style="{ color: getStatusColor(job.status), background: getStatusBg(job.status) }"
              >
                <span class="status-dot" :class="`dot-${job.status}`" />
                {{ job.status }}
              </span>
            </span>
            <span class="col-file">{{ job.filename || '—' }}</span>
            <span class="col-nodes">{{ job.nodes?.length || 0 }}</span>
            <span class="col-duration">{{ formatDuration(job) }}</span>
            <span class="col-time">{{ formatJobDate(job.created_at) }}</span>
            <span class="col-progress">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :class="`progress-${job.status}`"
                  :style="{ width: `${(job.progress || 0) * 100}%` }"
                />
              </div>
              <span class="progress-text">{{ Math.round((job.progress || 0) * 100) }}%</span>
            </span>
            <span class="col-actions" @click.stop>
              <button
                class="row-action-btn row-action-delete"
                :class="{ disabled: !canDelete(job) }"
                :disabled="!canDelete(job)"
                title="Xoá"
                @click="handleDelete(job)"
              >
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
              <button
                class="row-action-btn row-action-stop"
                :class="{ disabled: !canStop(job) }"
                :disabled="!canStop(job)"
                title="Dừng"
                @click="handleStop(job)"
              >
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
              </button>
              <button
                class="row-action-btn row-action-retry"
                :class="{ disabled: !canRetry(job) }"
                :disabled="!canRetry(job)"
                title="Retry"
                @click="handleRetry(job)"
              >
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </span>
          </div>

          <!-- Expanded Job Detail: Step-by-step -->
          <div v-if="expandedJobId === job.job_id" class="job-detail">
            <div class="job-detail-header">
              <span class="job-detail-label">Pipeline Steps</span>
              <span v-if="job.error" class="job-detail-error">{{ job.error }}</span>
            </div>
            <div class="step-timeline">
              <div
                v-for="(node, idx) in job.nodes"
                :key="node.node_id"
                class="step-item"
                :class="`step-${node.status}`"
              >
                <!-- Timeline connector -->
                <div class="step-connector">
                  <div class="step-icon" :style="{ color: getStatusColor(node.status) }">
                    {{ getNodeStatusIcon(node.status) }}
                  </div>
                  <div v-if="idx < job.nodes.length - 1" class="step-line" :class="`line-${node.status}`" />
                </div>

                <!-- Step content -->
                <div class="step-content">
                  <div class="step-header">
                    <span class="step-label">{{ node.node_label }}</span>
                    <span class="step-type">{{ node.node_type }}</span>
                    <span v-if="node.status === 'running'" class="step-running-indicator">
                      <span class="step-spinner" />
                      Processing...
                    </span>
                    <span v-else-if="node.retry_count > 0" class="step-retries">
                      {{ node.retry_count }} retries
                    </span>
                    <span class="step-duration">{{ formatNodeDuration(node) }}</span>
                  </div>

                  <!-- Node result -->
                  <div v-if="node.status === 'completed' && getNodeResult(job.job_id, node.node_id)" class="step-result">
                    <div v-if="getNodeResult(job.job_id, node.node_id).text" class="result-text">
                      <span class="result-label">Output:</span>
                      <pre class="result-pre">{{ getNodeResult(job.job_id, node.node_id).text.substring(0, 200) }}{{ getNodeResult(job.job_id, node.node_id).text.length > 200 ? '...' : '' }}</pre>
                    </div>
                    <div v-if="getNodeResult(job.job_id, node.node_id).doc_type" class="result-classify">
                      <span class="result-label">Classification:</span>
                      <span class="result-tag">{{ getNodeResult(job.job_id, node.node_id).doc_type }}</span>
                      <span class="result-confidence">{{ Math.round(getNodeResult(job.job_id, node.node_id).confidence * 100) }}% confidence</span>
                    </div>
                    <div v-if="getNodeResult(job.job_id, node.node_id).fields" class="result-fields">
                      <span class="result-label">Extracted Fields:</span>
                      <div class="fields-grid">
                        <div v-for="(value, key) in getNodeResult(job.job_id, node.node_id).fields" :key="key" class="field-item">
                          <span class="field-key">{{ key }}</span>
                          <span class="field-value">{{ value }}</span>
                        </div>
                      </div>
                    </div>
                    <div v-if="getNodeResult(job.job_id, node.node_id).files" class="result-files">
                      <span class="result-label">Files:</span>
                      <span>{{ getNodeResult(job.job_id, node.node_id).files.join(', ') }} ({{ getNodeResult(job.job_id, node.node_id).size }})</span>
                    </div>
                  </div>

                  <!-- Error message -->
                  <div v-if="node.error" class="step-error">
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    {{ node.error }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Deploy Modal -->
    <Teleport to="body">
      <div v-if="showDeployModal" class="deploy-overlay" @click.self="showDeployModal = false">
        <div class="deploy-modal">
          <div class="deploy-modal-header">
            <h3 class="deploy-modal-title">
              <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              Deploy & Integrate
            </h3>
            <button class="deploy-modal-close" @click="showDeployModal = false">
              <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="deploy-modal-body">
            <!-- API Trigger -->
            <div class="deploy-section">
              <div class="deploy-section-header">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>API Trigger</span>
              </div>
              <p class="deploy-section-desc">POST file trực tiếp để trigger workflow qua REST API</p>
              <div class="deploy-code-block">
                <code class="deploy-code">{{ triggerUrl }}</code>
                <button class="deploy-copy-btn" @click="copyToClipboard(triggerUrl, 'api')">
                  {{ copiedField === 'api' ? '✓' : 'Copy' }}
                </button>
              </div>
            </div>

            <!-- cURL -->
            <div class="deploy-section">
              <div class="deploy-section-header">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>cURL</span>
              </div>
              <div class="deploy-code-block deploy-code-multi">
                <pre class="deploy-pre">{{ curlExample }}</pre>
                <button class="deploy-copy-btn" @click="copyToClipboard(curlExample, 'curl')">
                  {{ copiedField === 'curl' ? '✓' : 'Copy' }}
                </button>
              </div>
            </div>

            <!-- Python -->
            <div class="deploy-section">
              <div class="deploy-section-header">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                <span>Python</span>
              </div>
              <div class="deploy-code-block deploy-code-multi">
                <pre class="deploy-pre">{{ pythonExample }}</pre>
                <button class="deploy-copy-btn" @click="copyToClipboard(pythonExample, 'python')">
                  {{ copiedField === 'python' ? '✓' : 'Copy' }}
                </button>
              </div>
            </div>

            <!-- Embed -->
            <div class="deploy-section">
              <div class="deploy-section-header">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                </svg>
                <span>Embed (iframe)</span>
              </div>
              <p class="deploy-section-desc">Nhúng workflow UI vào website của bạn</p>
              <div class="deploy-code-block deploy-code-multi">
                <pre class="deploy-pre">{{ embedCode }}</pre>
                <button class="deploy-copy-btn" @click="copyToClipboard(embedCode, 'embed')">
                  {{ copiedField === 'embed' ? '✓' : 'Copy' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.wf-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #ffffff;
  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.wf-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 32px 20px 16px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.back-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: linear-gradient(135deg, #FF6F3C 0%, #FF9A6C 100%);
  border-radius: 9px;
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: 0 3px 8px rgba(255, 111, 60, 0.25);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.header-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
  letter-spacing: -0.01em;
}

.header-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  border: none;
  font-family: inherit;
}

.action-btn-primary {
  background: #FF6F3C;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(255, 111, 60, 0.25);
}

.action-btn-primary:hover {
  background: #E55A2B;
  box-shadow: 0 4px 12px rgba(255, 111, 60, 0.35);
}

.action-btn-secondary {
  background: #ffffff;
  color: #374151;
  border: 1px solid #e5e7eb;
}

.action-btn-secondary:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}



/* ── Content ────────────────────────────────────────────────────────────── */
.wf-detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

/* ── Loading ────────────────────────────────────────────────────────────── */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 80px 32px;
  color: #6b7280;
  font-size: 14px;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #e5e7eb;
  border-top-color: #FF6F3C;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Empty State ────────────────────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 80px 32px;
  text-align: center;
}

.empty-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: #fff9f6;
  border: 1px solid #ffe8dc;
  color: #FF6F3C;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.empty-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  max-width: 300px;
  line-height: 1.5;
}

/* ── Job Table ──────────────────────────────────────────────────────────── */
.job-table {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.job-table-header {
  display: grid;
  grid-template-columns: 100px 1fr 50px 70px 110px 120px 100px;
  gap: 8px;
  padding: 10px 16px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.job-row {
  display: grid;
  grid-template-columns: 100px 1fr 50px 70px 110px 120px 100px;
  gap: 8px;
  padding: 12px 16px;
  align-items: center;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
  color: #374151;
  transition: background 0.1s;
  cursor: pointer;
}

.job-row:last-child {
  border-bottom: none;
}

.job-row:hover {
  background: #f9fafb;
}

.job-row-active {
  background: #eff6ff;
}

.job-row-active:hover {
  background: #dbeafe;
}

.job-row-expanded {
  background: #f9fafb;
  border-bottom-color: transparent;
}

.col-file {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.col-nodes,
.col-duration,
.col-time {
  font-size: 12px;
  color: #6b7280;
}

/* ── Row Action Buttons ─────────────────────────────────────────────────── */
.col-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.row-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  border-radius: 6px;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.15s;
}

.row-action-btn:hover:not(.disabled) {
  background: #f3f4f6;
}

.row-action-delete:hover:not(.disabled) {
  background: #fef2f2;
  color: #dc2626;
}

.row-action-stop:hover:not(.disabled) {
  background: #fffbeb;
  color: #d97706;
}

.row-action-retry:hover:not(.disabled) {
  background: #eff6ff;
  color: #2563eb;
}

.row-action-btn.disabled {
  color: #d1d5db;
  cursor: not-allowed;
  opacity: 0.5;
}

/* ── Status Badge ───────────────────────────────────────────────────────── */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  padding: 3px 10px;
  border-radius: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.dot-running {
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ── Progress Bar ───────────────────────────────────────────────────────── */
.col-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-running { background: #3b82f6; }
.progress-queued { background: #9ca3af; }
.progress-completed { background: #10b981; }
.progress-failed { background: #ef4444; }
.progress-cancelled { background: #f59e0b; }

.progress-text {
  font-size: 11px;
  font-weight: 500;
  color: #6b7280;
  min-width: 32px;
  text-align: right;
}

/* ── Deploy Modal ────────────────────────────────────────────────────────── */
.deploy-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.deploy-modal {
  background: #ffffff;
  border-radius: 14px;
  width: 100%;
  max-width: 580px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.deploy-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.deploy-modal-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.deploy-modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  border-radius: 6px;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.15s;
}

.deploy-modal-close:hover {
  background: #f3f4f6;
  color: #374151;
}

.deploy-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.deploy-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.deploy-section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.deploy-section-desc {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.deploy-code-block {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px 12px;
}

.deploy-code {
  flex: 1;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: #374151;
  word-break: break-all;
}

.deploy-code-multi {
  flex-direction: column;
}

.deploy-code-multi .deploy-copy-btn {
  align-self: flex-end;
}

.deploy-pre {
  flex: 1;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11px;
  line-height: 1.6;
  color: #374151;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.deploy-copy-btn {
  padding: 4px 10px;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.deploy-copy-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

/* ── Reduced Motion ─────────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .loading-spinner {
    animation: none;
  }
  .dot-running {
    animation: none;
  }
  .step-spinner {
    animation: none;
  }
}

/* ── Job Detail (Expanded) ──────────────────────────────────────────────── */
.job-detail {
  padding: 16px 20px 20px;
  background: #fafbfc;
  border-bottom: 1px solid #e5e7eb;
}

.job-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.job-detail-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.job-detail-error {
  font-size: 12px;
  color: #ef4444;
  background: #fef2f2;
  padding: 4px 10px;
  border-radius: 4px;
  max-width: 400px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Step Timeline ──────────────────────────────────────────────────────── */
.step-timeline {
  display: flex;
  flex-direction: column;
}

.step-item {
  display: flex;
  gap: 14px;
  min-height: 48px;
}

.step-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
}

.step-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid currentColor;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.step-completed .step-icon {
  background: #f0fdf4;
  border-color: #10b981;
}

.step-running .step-icon {
  background: #eff6ff;
  border-color: #3b82f6;
}

.step-failed .step-icon {
  background: #fef2f2;
  border-color: #ef4444;
}

.step-pending .step-icon {
  background: #f9fafb;
  border-color: #d1d5db;
  color: #d1d5db;
}

.step-skipped .step-icon {
  background: #f9fafb;
  border-color: #9ca3af;
}

.step-line {
  flex: 1;
  width: 2px;
  background: #e5e7eb;
  min-height: 16px;
  margin: 4px 0;
}

.line-completed { background: #10b981; }
.line-running { background: #3b82f6; }
.line-failed { background: #ef4444; }

.step-content {
  flex: 1;
  padding-bottom: 16px;
  min-width: 0;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 24px;
}

.step-label {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.step-type {
  font-size: 11px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 3px;
}

.step-running-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #3b82f6;
  font-weight: 500;
}

.step-spinner {
  width: 10px;
  height: 10px;
  border: 1.5px solid rgba(59, 130, 246, 0.3);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.step-retries {
  font-size: 11px;
  color: #f59e0b;
  font-weight: 500;
}

.step-duration {
  font-size: 11px;
  color: #9ca3af;
  margin-left: auto;
}

/* ── Step Result ────────────────────────────────────────────────────────── */
.step-result {
  margin-top: 8px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-label {
  font-size: 10px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-right: 6px;
}

.result-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-pre {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 11px;
  line-height: 1.5;
  color: #374151;
  background: #f9fafb;
  padding: 8px 10px;
  border-radius: 4px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
}

.result-classify {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.result-tag {
  font-size: 12px;
  font-weight: 600;
  color: #7c3aed;
  background: #f5f3ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.result-confidence {
  font-size: 11px;
  color: #6b7280;
}

.result-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fields-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 6px;
}

.field-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 4px 8px;
  background: #f9fafb;
  border-radius: 4px;
}

.field-key {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  white-space: nowrap;
}

.field-value {
  font-size: 12px;
  color: #1f2937;
  font-weight: 500;
}

.result-files {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #374151;
}

/* ── Step Error ─────────────────────────────────────────────────────────── */
.step-error {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  padding: 6px 10px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  font-size: 12px;
  color: #dc2626;
}
</style>
