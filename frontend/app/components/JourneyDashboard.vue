<script setup lang="ts">
/**
 * Journey Dashboard — Management UI for Doc Journey workflows.
 * 
 * Design: Glassmorphism + Plus Jakarta Sans
 * Colors: Orange primary (#FF6F3C), White background (#FFF9F6)
 */
import { useWorkflowList } from '~/composables/useWorkflowList'
import { useTranslation } from '~/composables/useTranslation'
import ConfirmDialog from '~/components/journey/ConfirmDialog.vue'
import SearchBox from '~/components/journey/SearchBox.vue'
import DurableRunsPanel from '~/components/journey/DurableRunsPanel.vue'

const { t } = useTranslation()

const {
  workflows,
  searchQuery,
  isLoading,
  isLoadingMore,
  hasMoreWorkflows,
  filteredWorkflows,
  fetchWorkflows,
  loadMoreWorkflows,
  deleteWorkflow,
} = useWorkflowList()

// Delete confirmation state
const showDeleteConfirm = ref(false)
const deleteTargetId = ref<string | null>(null)

const requestDelete = (workflowId: string) => {
  deleteTargetId.value = workflowId
  showDeleteConfirm.value = true
}

const confirmDelete = async () => {
  if (!deleteTargetId.value) return
  showDeleteConfirm.value = false
  await deleteWorkflow(deleteTargetId.value)
  deleteTargetId.value = null
}

const cancelDelete = () => {
  showDeleteConfirm.value = false
  deleteTargetId.value = null
}

// Emit to parent
const emit = defineEmits<{
  (e: 'open-builder', workflowId?: string): void
  (e: 'open-detail', workflowId: string): void
}>()

const openBuilder = (workflowId?: string) => {
  emit('open-builder', workflowId)
}

const handleCardClick = (workflowId: string) => {
  emit('open-detail', workflowId)
}

// Infinite scroll observer
const workflowSentinel = ref<HTMLElement | null>(null)
let workflowObserver: IntersectionObserver | null = null

const setupObserver = () => {
  if (workflowObserver) workflowObserver.disconnect()
  workflowObserver = new IntersectionObserver((entries) => {
    if (entries[0]?.isIntersecting && !isLoadingMore.value && hasMoreWorkflows.value) {
      loadMoreWorkflows()
    }
  }, { threshold: 0.1 })
}

watch(workflowSentinel, (el) => {
  if (el && workflowObserver) workflowObserver.observe(el)
})

onMounted(() => {
  setupObserver()
  fetchWorkflows()
})

onUnmounted(() => {
  workflowObserver?.disconnect()
})
</script>

<template>
  <div class="journey-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <div class="header-left">
        <div class="header-title-row">
          <div class="header-icon">
            <svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h2 class="dashboard-title">{{ t('journey.title') }}</h2>
            <p class="dashboard-subtitle">{{ t('journey.subtitle') }}</p>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <SearchBox v-model="searchQuery" />
        <button class="btn-create" @click="openBuilder()">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          {{ t('journey.create') }}
        </button>
      </div>
    </div>

    <!-- Durable Workflow Runs (feat-054) -->
    <div class="durable-section">
      <DurableRunsPanel />
    </div>

    <!-- Content -->
    <div class="dashboard-content">
      <!-- Skeleton Loading -->
      <div v-if="isLoading" class="skeleton-grid">
        <div v-for="i in 6" :key="i" class="skeleton-card">
          <div class="skeleton-line skeleton-title" />
          <div class="skeleton-line skeleton-desc" />
          <div class="skeleton-line skeleton-desc short" />
          <div class="skeleton-meta-row">
            <div class="skeleton-line skeleton-badge" />
            <div class="skeleton-line skeleton-badge" />
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="workflows.length === 0" class="empty-state">
        <div class="empty-illustration">
          <div class="empty-circle">
            <svg width="40" height="40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>
        <h3 class="empty-title">Chưa có workflow nào</h3>
        <p class="empty-desc">Tạo workflow đầu tiên để bắt đầu xử lý tài liệu tự động</p>
        <button class="btn-create" @click="openBuilder()">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          {{ t('journey.create') }}
        </button>
      </div>

      <!-- No search results -->
      <div v-else-if="filteredWorkflows.length === 0 && searchQuery" class="empty-state empty-search">
        <svg width="36" height="36" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <h3 class="empty-title">Không tìm thấy workflow</h3>
        <p class="empty-desc">Thử tìm với từ khóa khác</p>
      </div>

      <!-- Workflow grid -->
      <div v-else class="workflow-grid">
        <div
          v-for="workflow in filteredWorkflows"
          :key="workflow.workflow_id"
          class="wf-card"
          @click="handleCardClick(workflow.workflow_id)"
        >
          <div class="wf-card-accent" />
          <div class="wf-card-body">
            <div class="wf-card-header">
              <div class="wf-card-icon">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h4 class="wf-card-title">{{ workflow.name }}</h4>
              <button
                class="wf-card-delete"
                title="Xóa"
                @click.stop="requestDelete(workflow.workflow_id)"
              >
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
            <p v-if="workflow.description" class="wf-card-desc">{{ workflow.description }}</p>
            <div class="wf-card-footer">
              <span class="wf-badge wf-badge-steps">
                <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
                {{ workflow.step_count }} steps
              </span>
              <span class="wf-badge wf-badge-time">
                <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {{ new Date(workflow.updated_at).toLocaleDateString('vi-VN') }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Load more sentinel -->
      <div v-if="hasMoreWorkflows && !isLoading" ref="workflowSentinel" class="load-more-indicator">
        <div class="load-spinner" />
        <span>Loading more...</span>
      </div>
    </div>

    <!-- Delete Confirm -->
    <ConfirmDialog
      :visible="showDeleteConfirm"
      message="Delete this workflow? This cannot be undone."
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.journey-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: #ffffff;
  font-family: 'Plus Jakarta Sans', sans-serif;
}

/* ── Durable Section ─────────────────────────────────────────────────── */
.durable-section {
  padding: 0 32px 16px;
  flex-shrink: 0;
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 32px 16px;
  flex-shrink: 0;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  background: linear-gradient(135deg, #FF6F3C 0%, #FF9A6C 100%);
  border-radius: 12px;
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(255, 111, 60, 0.3);
}

.dashboard-title {
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
  letter-spacing: -0.02em;
}

.dashboard-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin: 2px 0 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-create {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  background: #FF6F3C;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(255, 111, 60, 0.25);
  font-family: inherit;
}

.btn-create:hover {
  background: #E55A2B;
  box-shadow: 0 4px 16px rgba(255, 111, 60, 0.35);
  transform: translateY(-1px);
}

.btn-create:active {
  transform: translateY(0);
}

/* ── Content ────────────────────────────────────────────────────────────── */
.dashboard-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 32px 32px;
  display: flex;
  flex-direction: column;
}

.dashboard-content::-webkit-scrollbar {
  width: 6px;
}

.dashboard-content::-webkit-scrollbar-track {
  background: transparent;
}

.dashboard-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.dashboard-content::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

/* ── Skeleton Loading ───────────────────────────────────────────────────── */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.skeleton-card {
  background: #fff9f6;
  border: 1px solid #ffe8dc;
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  border-radius: 6px;
  background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-title { height: 16px; width: 55%; }
.skeleton-desc { height: 12px; width: 85%; }
.skeleton-desc.short { width: 45%; }
.skeleton-meta-row { display: flex; gap: 8px; margin-top: 8px; }
.skeleton-badge { height: 22px; width: 72px; border-radius: 11px; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Empty State ────────────────────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 80px 24px;
  text-align: center;
}

.empty-search { padding: 48px 24px; }

.empty-illustration { margin-bottom: 8px; }

.empty-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
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

/* ── Workflow Grid ──────────────────────────────────────────────────────── */
.workflow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

/* ── Workflow Card (Glassmorphism) ───────────────────────────────────────── */
.wf-card {
  position: relative;
  background: #fff9f6;
  border: 1px solid #ffe8dc;
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
}

.wf-card:hover {
  background: #fff4ee;
  border-color: rgba(255, 111, 60, 0.4);
  box-shadow: 0 8px 24px rgba(255, 111, 60, 0.08);
  transform: translateY(-2px);
}

.wf-card-accent {
  height: 3px;
  background: linear-gradient(90deg, #FF6F3C 0%, #FF9A6C 50%, #FFBE98 100%);
  opacity: 0;
  transition: opacity 0.2s;
}

.wf-card:hover .wf-card-accent {
  opacity: 1;
}

.wf-card-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wf-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wf-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: rgba(255, 111, 60, 0.08);
  border-radius: 7px;
  color: #FF6F3C;
  flex-shrink: 0;
}

.wf-card-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wf-card-delete {
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
  transition: all 0.15s;
  flex-shrink: 0;
}

.wf-card-delete:hover {
  background: #fef2f2;
  color: #dc2626;
}

.wf-card-desc {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.wf-card-footer {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.wf-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 3px 9px;
  border-radius: 6px;
}

.wf-badge-steps {
  background: rgba(255, 111, 60, 0.06);
  color: #FF6F3C;
}

.wf-badge-time {
  background: #f3f4f6;
  color: #6b7280;
}

/* ── Load More ──────────────────────────────────────────────────────────── */
.load-more-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  color: #6b7280;
  font-size: 12px;
}

.load-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #e5e7eb;
  border-top-color: #FF6F3C;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Reduced Motion ─────────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .wf-card,
  .btn-create {
    transition: none;
  }
  .wf-card:hover {
    transform: none;
  }
  .btn-create:hover {
    transform: none;
  }
  .skeleton-line {
    animation: none;
  }
}
</style>
