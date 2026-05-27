<script setup lang="ts">
/**
 * Workflow Toolbar
 * 
 * Top toolbar with workflow name, execution controls,
 * undo/redo, zoom, and import/export actions.
 */
import { useWorkflowState } from '~/composables/workflow/useWorkflowState'
import { useWorkflowExecution } from '~/composables/workflow/useWorkflowExecution'
import { useWorkflowValidation } from '~/composables/workflow/useWorkflowValidation'
import { useJobManager } from '~/composables/workflow/useJobManager'

const emit = defineEmits<{
  (e: 'zoom-in'): void
  (e: 'zoom-out'): void
  (e: 'zoom-fit'): void
  (e: 'export'): void
  (e: 'import'): void
  (e: 'clear'): void
}>()

const {
  workflowName,
  nodes,
  edges,
  isDirty,
  canUndo,
  canRedo,
  undo,
  redo,
  clearWorkflow,
  resetAllNodeStatus,
} = useWorkflowState()

const { executionState, executeWorkflow, cancelExecution, resetExecution } = useWorkflowExecution()
const { validateWorkflow } = useWorkflowValidation()
const { jobPanelOpen, isRunning: isJobRunning } = useJobManager()

const isEditing = ref(false)
const nameInput = ref<HTMLInputElement | null>(null)

const validationErrors = computed(() => validateWorkflow(nodes.value, edges.value))
const hasErrors = computed(() => validationErrors.value.filter(e => e.type === 'cycle').length > 0)
const isRunning = computed(() => executionState.value.status === 'running')

const startEditing = () => {
  isEditing.value = true
  nextTick(() => nameInput.value?.focus())
}

const finishEditing = () => {
  isEditing.value = false
}

const onRun = async () => {
  if (isRunning.value) {
    cancelExecution()
    return
  }

  resetAllNodeStatus()
  resetExecution()

  try {
    await executeWorkflow(nodes.value, edges.value, (nodeId, status) => {
      const { updateNodeStatus } = useWorkflowState()
      updateNodeStatus(nodeId, status)
    })
  } catch (error: any) {
    console.error('Workflow execution failed:', error)
  }
}

const onExport = () => {
  emit('export')
}

const onImport = () => {
  emit('import')
}

const onClear = () => {
  if (confirm('Clear the entire workflow? This cannot be undone.')) {
    clearWorkflow()
    emit('clear')
  }
}
</script>

<template>
  <div class="workflow-toolbar">
    <!-- Left: Workflow name + status -->
    <div class="toolbar-left">
      <div class="workflow-name-area">
        <input
          v-if="isEditing"
          ref="nameInput"
          v-model="workflowName"
          class="name-input"
          @blur="finishEditing"
          @keydown.enter="finishEditing"
        />
        <button v-else class="name-display" @click="startEditing">
          {{ workflowName }}
          <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
        </button>
        <span v-if="isDirty" class="dirty-indicator" title="Unsaved changes">●</span>
      </div>

      <!-- Validation status -->
      <div v-if="hasErrors" class="validation-badge error">
        <svg width="12" height="12" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        {{ validationErrors.length }} issue{{ validationErrors.length > 1 ? 's' : '' }}
      </div>
      <div v-else-if="nodes.length > 0" class="validation-badge valid">
        <svg width="12" height="12" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
        </svg>
        Valid
      </div>
    </div>

    <!-- Center: Undo/Redo + Zoom -->
    <div class="toolbar-center">
      <button class="toolbar-btn" :disabled="!canUndo" @click="undo" title="Undo (⌘Z)">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
        </svg>
      </button>
      <button class="toolbar-btn" :disabled="!canRedo" @click="redo" title="Redo (⌘⇧Z)">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 10H11a8 8 0 00-8 8v2m18-10l-6 6m6-6l-6-6" />
        </svg>
      </button>

      <div class="toolbar-divider"></div>

      <button class="toolbar-btn" @click="emit('zoom-out')" title="Zoom Out">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
        </svg>
      </button>
      <button class="toolbar-btn" @click="emit('zoom-fit')" title="Fit View">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
        </svg>
      </button>
      <button class="toolbar-btn" @click="emit('zoom-in')" title="Zoom In">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>

    <!-- Right: Actions -->
    <div class="toolbar-right">
      <button class="toolbar-btn" @click="onImport" title="Import JSON">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
      </button>
      <button class="toolbar-btn" @click="onExport" title="Export JSON">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
      </button>
      <button class="toolbar-btn" @click="onClear" title="Clear Workflow">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>

      <div class="toolbar-divider"></div>

      <!-- Run button -->
      <button
        class="run-btn"
        :class="{ running: isRunning, disabled: hasErrors }"
        :disabled="hasErrors && !isRunning"
        @click="onRun"
      >
        <svg v-if="!isRunning" width="14" height="14" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
        </svg>
        <svg v-else width="14" height="14" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
        </svg>
        {{ isRunning ? 'Stop' : 'Run' }}
      </button>

      <!-- Jobs panel toggle -->
      <button
        class="toolbar-btn jobs-btn"
        :class="{ active: jobPanelOpen }"
        @click="jobPanelOpen = !jobPanelOpen"
        title="Toggle Jobs Panel"
      >
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
        <span v-if="isJobRunning" class="job-indicator" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.workflow-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  height: 52px;
  gap: 16px;
}

.toolbar-left,
.toolbar-center,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-left {
  flex: 1;
}

.workflow-name-area {
  display: flex;
  align-items: center;
  gap: 6px;
}

.name-display {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  cursor: pointer;
  border-radius: 4px;
}

.name-display:hover {
  background: #f3f4f6;
}

.name-display svg {
  color: #9ca3af;
}

.name-input {
  padding: 4px 8px;
  border: 1px solid #7c3aed;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  outline: none;
  width: 200px;
}

.dirty-indicator {
  color: #f59e0b;
  font-size: 10px;
}

.validation-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.validation-badge.error {
  background: #fef2f2;
  color: #dc2626;
}

.validation-badge.valid {
  background: #ecfdf5;
  color: #059669;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  border-radius: 6px;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.15s;
}

.toolbar-btn:hover:not(:disabled) {
  background: #f3f4f6;
  color: #1f2937;
}

.toolbar-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: #e5e7eb;
  margin: 0 4px;
}

.run-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: none;
  background: #7c3aed;
  color: #ffffff;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.run-btn:hover:not(:disabled) {
  background: #6d28d9;
}

.run-btn.running {
  background: #dc2626;
}

.run-btn.running:hover {
  background: #b91c1c;
}

.run-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.jobs-btn {
  position: relative;
}

.jobs-btn.active {
  background: #ede9fe;
  color: #7c3aed;
}

.job-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  background: #3b82f6;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
