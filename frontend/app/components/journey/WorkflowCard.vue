<script setup lang="ts">
/**
 * WorkflowCard — Single workflow card in the Journey Dashboard grid.
 */

defineProps<{
  workflow: {
    workflow_id: string
    name: string
    description?: string
    step_count: number
    updated_at: string
  }
}>()

const emit = defineEmits<{
  (e: 'open', workflowId: string): void
  (e: 'delete', workflowId: string): void
}>()

const formatDate = (iso: string): string => {
  if (!iso) return '—'
  const d = new Date(iso)
  const today = new Date()
  const isToday = d.getDate() === today.getDate() &&
    d.getMonth() === today.getMonth() &&
    d.getFullYear() === today.getFullYear()

  if (isToday) {
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }
  return d.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}
</script>

<template>
  <div class="workflow-card" @click="emit('open', workflow.workflow_id)">
    <div class="card-header">
      <h4 class="card-title">{{ workflow.name }}</h4>
      <div class="card-actions">
        <button
          class="card-action-btn danger"
          title="Xóa"
          @click.stop="emit('delete', workflow.workflow_id)"
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
    <p v-if="workflow.description" class="card-description">{{ workflow.description }}</p>
    <div class="card-meta">
      <span class="meta-item">
        <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
        {{ workflow.step_count }} steps
      </span>
      <span class="meta-item">
        <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ formatDate(workflow.updated_at) }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.workflow-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  transition: all 0.15s;
  cursor: pointer;
}

.workflow-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.card-actions {
  display: flex;
  gap: 4px;
}

.card-action-btn {
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
}

.card-action-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.card-action-btn.danger:hover {
  background: #fef2f2;
  color: #dc2626;
}

.card-description {
  font-size: 12px;
  color: #6b7280;
  margin: 0 0 12px;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #9ca3af;
}
</style>
