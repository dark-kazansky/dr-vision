<script setup lang="ts">
/**
 * Observability Dashboard — feat-010
 *
 * Displays: system health, workflow metrics, error analytics,
 * execution timeline, and audit log.
 */
const {
  dashboard,
  metrics,
  errors,
  auditLog,
  timeline,
  isLoading,
  error,
  fetchDashboard,
  fetchMetrics,
  fetchErrors,
  fetchAuditLog,
  fetchTimeline,
  formatDuration,
  healthColor,
  healthBg,
} = useObservability()

// Active tab
const activeTab = ref<'overview' | 'metrics' | 'errors' | 'audit' | 'timeline'>('overview')

// Period selector
const period = ref(7)

// Timeline job ID input
const timelineJobId = ref('')

// Load data on mount and when period changes
const loadData = async () => {
  await Promise.all([
    fetchDashboard(period.value),
    fetchMetrics({ days: period.value }),
    fetchErrors({ days: period.value }),
    fetchAuditLog({ days: period.value }),
  ])
}

watch(period, loadData)
onMounted(loadData)

// Load timeline for a specific job
const loadTimeline = async () => {
  if (timelineJobId.value.trim()) {
    await fetchTimeline(timelineJobId.value.trim())
  }
}

// Status badge classes
const statusBadge = (status: string): string => {
  switch (status) {
    case 'completed': return 'bg-emerald-100 text-emerald-700'
    case 'failed': return 'bg-red-100 text-red-700'
    case 'running': return 'bg-blue-100 text-blue-700'
    case 'queued': return 'bg-gray-100 text-gray-700'
    case 'cancelled': return 'bg-amber-100 text-amber-700'
    default: return 'bg-gray-100 text-gray-600'
  }
}

const formatDate = (iso: string | null): string => {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <!-- Header -->
    <div class="max-w-7xl mx-auto">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-semibold text-gray-900">Journey Observability</h1>
          <p class="text-sm text-gray-500 mt-1">Monitoring, analytics & audit cho workflow executions</p>
        </div>

        <!-- Period selector -->
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-500">Period:</span>
          <select
            v-model="period"
            class="rounded-lg border border-gray-200 px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20"
          >
            <option :value="1">1 day</option>
            <option :value="7">7 days</option>
            <option :value="14">14 days</option>
            <option :value="30">30 days</option>
          </select>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 mb-6 bg-white rounded-xl p-1 border border-gray-200 shadow-sm w-fit">
        <button
          v-for="tab in (['overview', 'metrics', 'errors', 'audit', 'timeline'] as const)"
          :key="tab"
          :class="[
            'px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer',
            activeTab === tab
              ? 'bg-orange-500 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
          ]"
          @click="activeTab = tab"
        >
          {{ tab === 'overview' ? 'Overview' : tab === 'metrics' ? 'Performance' : tab === 'errors' ? 'Errors' : tab === 'audit' ? 'Audit Log' : 'Timeline' }}
        </button>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="flex items-center justify-center py-20">
        <div class="animate-spin w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full"></div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
        {{ error }}
      </div>

      <!-- Overview Tab -->
      <div v-else-if="activeTab === 'overview' && dashboard">
        <!-- System Health Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div class="text-sm text-gray-500 mb-1">Total Jobs</div>
            <div class="text-2xl font-semibold text-gray-900">{{ dashboard.system.total_jobs }}</div>
          </div>
          <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div class="text-sm text-gray-500 mb-1">Success Rate</div>
            <div class="text-2xl font-semibold" :class="healthColor(dashboard.system.health)">
              {{ dashboard.system.success_rate }}%
            </div>
          </div>
          <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div class="text-sm text-gray-500 mb-1">Active Now</div>
            <div class="text-2xl font-semibold text-blue-600">
              {{ dashboard.system.running + dashboard.system.queued }}
            </div>
          </div>
          <div :class="['rounded-xl border p-5 shadow-sm', healthBg(dashboard.system.health)]">
            <div class="text-sm text-gray-500 mb-1">System Health</div>
            <div class="text-2xl font-semibold capitalize" :class="healthColor(dashboard.system.health)">
              {{ dashboard.system.health }}
            </div>
          </div>
        </div>

        <!-- Per Workflow Table -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100">
            <h2 class="text-base font-medium text-gray-900">Workflow Health</h2>
          </div>
          <div v-if="dashboard.workflows.length === 0" class="p-8 text-center text-gray-400">
            No workflow data in this period
          </div>
          <table v-else class="w-full text-sm">
            <thead class="bg-gray-50 text-gray-500">
              <tr>
                <th class="text-left px-5 py-3 font-medium">Workflow</th>
                <th class="text-center px-3 py-3 font-medium">Jobs</th>
                <th class="text-center px-3 py-3 font-medium">Success</th>
                <th class="text-center px-3 py-3 font-medium">Failed</th>
                <th class="text-center px-3 py-3 font-medium">Rate</th>
                <th class="text-center px-3 py-3 font-medium">Avg Duration</th>
                <th class="text-center px-3 py-3 font-medium">Health</th>
                <th class="text-right px-5 py-3 font-medium">Last Run</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="wf in dashboard.workflows" :key="wf.workflow_id" class="hover:bg-gray-50">
                <td class="px-5 py-3 font-medium text-gray-900">{{ wf.workflow_name || wf.workflow_id.slice(0, 8) }}</td>
                <td class="text-center px-3 py-3 text-gray-600">{{ wf.total_jobs }}</td>
                <td class="text-center px-3 py-3 text-emerald-600">{{ wf.completed }}</td>
                <td class="text-center px-3 py-3 text-red-600">{{ wf.failed }}</td>
                <td class="text-center px-3 py-3 font-medium" :class="healthColor(wf.health)">{{ wf.success_rate }}%</td>
                <td class="text-center px-3 py-3 text-gray-600">{{ formatDuration(wf.avg_duration_ms) }}</td>
                <td class="text-center px-3 py-3">
                  <span :class="['inline-block w-2 h-2 rounded-full', wf.health === 'healthy' ? 'bg-emerald-500' : wf.health === 'warning' ? 'bg-amber-500' : 'bg-red-500']"></span>
                </td>
                <td class="text-right px-5 py-3 text-gray-500 text-xs">{{ formatDate(wf.last_run) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Metrics Tab -->
      <div v-else-if="activeTab === 'metrics' && metrics">
        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div class="text-sm text-gray-500 mb-1">Avg Duration</div>
            <div class="text-xl font-semibold text-gray-900">{{ formatDuration(metrics.summary.avg_duration_ms) }}</div>
            <div class="text-xs text-gray-400 mt-1">
              Min: {{ formatDuration(metrics.summary.min_duration_ms) }} / Max: {{ formatDuration(metrics.summary.max_duration_ms) }}
            </div>
          </div>
          <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div class="text-sm text-gray-500 mb-1">Total Executions</div>
            <div class="text-xl font-semibold text-gray-900">{{ metrics.summary.total_jobs }}</div>
          </div>
          <div class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div class="text-sm text-gray-500 mb-1">Success Rate</div>
            <div class="text-xl font-semibold text-emerald-600">{{ metrics.summary.success_rate }}%</div>
          </div>
        </div>

        <!-- Node Type Performance -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100">
            <h2 class="text-base font-medium text-gray-900">Performance by Node Type</h2>
          </div>
          <div v-if="metrics.node_types.length === 0" class="p-8 text-center text-gray-400">
            No node execution data in this period
          </div>
          <table v-else class="w-full text-sm">
            <thead class="bg-gray-50 text-gray-500">
              <tr>
                <th class="text-left px-5 py-3 font-medium">Node Type</th>
                <th class="text-center px-3 py-3 font-medium">Executions</th>
                <th class="text-center px-3 py-3 font-medium">Successes</th>
                <th class="text-center px-3 py-3 font-medium">Failures</th>
                <th class="text-center px-3 py-3 font-medium">Failure Rate</th>
                <th class="text-center px-3 py-3 font-medium">Avg</th>
                <th class="text-center px-3 py-3 font-medium">Min</th>
                <th class="text-right px-5 py-3 font-medium">Max</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="nt in metrics.node_types" :key="nt.node_type" class="hover:bg-gray-50">
                <td class="px-5 py-3 font-medium text-gray-900 capitalize">{{ nt.node_type }}</td>
                <td class="text-center px-3 py-3 text-gray-600">{{ nt.execution_count }}</td>
                <td class="text-center px-3 py-3 text-emerald-600">{{ nt.success_count }}</td>
                <td class="text-center px-3 py-3 text-red-600">{{ nt.failure_count }}</td>
                <td class="text-center px-3 py-3" :class="nt.failure_rate > 20 ? 'text-red-600 font-medium' : 'text-gray-600'">
                  {{ nt.failure_rate }}%
                </td>
                <td class="text-center px-3 py-3 text-gray-600">{{ formatDuration(nt.avg_duration_ms) }}</td>
                <td class="text-center px-3 py-3 text-gray-500">{{ formatDuration(nt.min_duration_ms) }}</td>
                <td class="text-right px-5 py-3 text-gray-500">{{ formatDuration(nt.max_duration_ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Errors Tab -->
      <div v-else-if="activeTab === 'errors' && errors">
        <!-- Failure Rates -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-6">
          <div class="px-5 py-4 border-b border-gray-100">
            <h2 class="text-base font-medium text-gray-900">Failure Rate by Node Type</h2>
          </div>
          <div v-if="errors.failure_rates.length === 0" class="p-8 text-center text-gray-400">
            No failure data in this period
          </div>
          <div v-else class="p-5 space-y-3">
            <div v-for="fr in errors.failure_rates" :key="fr.node_type" class="flex items-center gap-3">
              <span class="text-sm font-medium text-gray-700 w-20 capitalize">{{ fr.node_type }}</span>
              <div class="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                <div
                  class="h-full rounded-full transition-all"
                  :class="fr.failure_rate > 20 ? 'bg-red-400' : fr.failure_rate > 5 ? 'bg-amber-400' : 'bg-emerald-400'"
                  :style="{ width: `${Math.max(fr.failure_rate, 2)}%` }"
                ></div>
              </div>
              <span class="text-sm text-gray-600 w-20 text-right">
                {{ fr.failures }}/{{ fr.total }} ({{ fr.failure_rate }}%)
              </span>
            </div>
          </div>
        </div>

        <!-- Top Errors -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100">
            <h2 class="text-base font-medium text-gray-900">Top Errors</h2>
          </div>
          <div v-if="errors.top_errors.length === 0" class="p-8 text-center text-gray-400">
            No errors in this period
          </div>
          <div v-else class="divide-y divide-gray-100">
            <div v-for="(err, i) in errors.top_errors" :key="i" class="px-5 py-4">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-gray-900 capitalize">{{ err.node_type }} — {{ err.node_label }}</span>
                <span class="text-xs text-gray-500">{{ err.occurrence_count }}x</span>
              </div>
              <p class="text-sm text-red-600 font-mono truncate">{{ err.error_message }}</p>
              <p class="text-xs text-gray-400 mt-1">Last: {{ formatDate(err.last_occurred) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Audit Tab -->
      <div v-else-if="activeTab === 'audit' && auditLog">
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 class="text-base font-medium text-gray-900">Audit Log</h2>
            <span class="text-xs text-gray-400">{{ auditLog.total }} entries</span>
          </div>
          <div v-if="auditLog.entries.length === 0" class="p-8 text-center text-gray-400">
            No audit entries in this period
          </div>
          <table v-else class="w-full text-sm">
            <thead class="bg-gray-50 text-gray-500">
              <tr>
                <th class="text-left px-5 py-3 font-medium">Time</th>
                <th class="text-left px-3 py-3 font-medium">Workflow</th>
                <th class="text-left px-3 py-3 font-medium">File</th>
                <th class="text-center px-3 py-3 font-medium">Status</th>
                <th class="text-right px-5 py-3 font-medium">Duration</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr
                v-for="entry in auditLog.entries"
                :key="entry.job_id"
                class="hover:bg-gray-50 cursor-pointer"
                @click="timelineJobId = entry.job_id; activeTab = 'timeline'; loadTimeline()"
              >
                <td class="px-5 py-3 text-gray-500 text-xs whitespace-nowrap">{{ formatDate(entry.created_at) }}</td>
                <td class="px-3 py-3 text-gray-900 font-medium truncate max-w-[200px]">{{ entry.workflow_name || '—' }}</td>
                <td class="px-3 py-3 text-gray-600 truncate max-w-[150px]">{{ entry.filename || '—' }}</td>
                <td class="text-center px-3 py-3">
                  <span :class="['inline-block px-2 py-0.5 rounded-full text-xs font-medium', statusBadge(entry.status)]">
                    {{ entry.status }}
                  </span>
                </td>
                <td class="text-right px-5 py-3 text-gray-600">{{ formatDuration(entry.duration_ms) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Timeline Tab -->
      <div v-else-if="activeTab === 'timeline'">
        <!-- Job ID Input -->
        <div class="flex gap-3 mb-6">
          <input
            v-model="timelineJobId"
            placeholder="Enter Job ID to view timeline..."
            class="flex-1 rounded-xl border border-gray-200 px-4 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-300"
            @keydown.enter="loadTimeline"
          />
          <button
            class="px-5 py-2.5 bg-orange-500 text-white rounded-xl text-sm font-medium hover:bg-orange-600 transition-colors cursor-pointer"
            @click="loadTimeline"
          >
            Load Timeline
          </button>
        </div>

        <!-- Timeline Display -->
        <div v-if="timeline" class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-base font-medium text-gray-900">{{ timeline.workflow_name || 'Job Timeline' }}</h2>
                <p class="text-xs text-gray-400 mt-0.5">{{ timeline.job_id }}</p>
              </div>
              <div class="flex items-center gap-3">
                <span :class="['px-2.5 py-1 rounded-full text-xs font-medium', statusBadge(timeline.status)]">
                  {{ timeline.status }}
                </span>
                <span class="text-sm text-gray-600">Total: {{ formatDuration(timeline.total_duration_ms) }}</span>
              </div>
            </div>
          </div>

          <!-- Node Timeline -->
          <div class="p-5 space-y-3">
            <div
              v-for="(node, i) in timeline.nodes"
              :key="node.node_id"
              class="flex items-center gap-4"
            >
              <!-- Step number -->
              <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium shrink-0"
                :class="node.status === 'completed' ? 'bg-emerald-100 text-emerald-700' : node.status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'"
              >
                {{ i + 1 }}
              </div>

              <!-- Bar -->
              <div class="flex-1">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm font-medium text-gray-900">{{ node.node_label }}</span>
                  <span class="text-xs text-gray-500">{{ formatDuration(node.duration_ms) }}</span>
                </div>
                <div class="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="node.status === 'completed' ? 'bg-emerald-400' : node.status === 'failed' ? 'bg-red-400' : 'bg-gray-300'"
                    :style="{
                      width: timeline.total_duration_ms && node.duration_ms
                        ? `${Math.max((node.duration_ms / timeline.total_duration_ms) * 100, 5)}%`
                        : '100%'
                    }"
                  ></div>
                </div>
                <p v-if="node.error" class="text-xs text-red-500 mt-1 truncate">{{ node.error }}</p>
              </div>

              <!-- Type badge -->
              <span class="text-xs text-gray-400 capitalize shrink-0 w-14 text-right">{{ node.node_type }}</span>
            </div>
          </div>
        </div>

        <div v-else-if="!isLoading" class="text-center py-16 text-gray-400">
          <p>Enter a Job ID above, or click a row in the Audit Log tab</p>
        </div>
      </div>
    </div>
  </div>
</template>
