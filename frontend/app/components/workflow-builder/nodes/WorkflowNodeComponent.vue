<script setup lang="ts">
/**
 * Custom Vue Flow Node Component
 * 
 * Renders workflow nodes with status indicators,
 * port handles, and execution state visualization.
 */
import { Handle, Position } from '@vue-flow/core'
import type { NodeTypeDefinition, NodeStatus } from '~/types/workflow'
import { useNodeRegistry } from '~/composables/workflow/useNodeRegistry'

const props = defineProps<{
  id: string
  data: {
    label: string
    config: Record<string, any>
    status: NodeStatus
    result?: any
    error?: string
    executionTime?: number
    groupId?: string
  }
  type: string
  selected: boolean
}>()

const emit = defineEmits<{
  (e: 'configure', nodeId: string): void
}>()

const { getNodeType } = useNodeRegistry()
const nodeDef = computed(() => getNodeType(props.type))

const statusColor = computed(() => {
  switch (props.data.status) {
    case 'running': return '#f59e0b'
    case 'success': return '#22c55e'
    case 'error': return '#ef4444'
    case 'queued': return '#6366f1'
    case 'skipped': return '#9ca3af'
    default: return 'transparent'
  }
})

const statusLabel = computed(() => {
  switch (props.data.status) {
    case 'running': return 'Running...'
    case 'success': return props.data.executionTime ? `Done (${props.data.executionTime}ms)` : 'Done'
    case 'error': return 'Error'
    case 'queued': return 'Queued'
    case 'skipped': return 'Skipped'
    default: return ''
  }
})

const isRunning = computed(() => props.data.status === 'running')
</script>

<template>
  <div
    class="workflow-node-wrapper"
    :class="[
      `node-status-${data.status}`,
      { 'node-selected': selected }
    ]"
    :style="{ '--node-color': nodeDef?.color || '#6b7280' }"
  >
    <!-- Status indicator ring -->
    <div v-if="data.status !== 'idle'" class="status-ring" :style="{ borderColor: statusColor }">
    </div>

    <!-- Running animation -->
    <div v-if="isRunning" class="running-pulse"></div>

    <!-- Input Handles -->
    <Handle
      v-for="input in nodeDef?.inputs || []"
      :key="input.id"
      :id="input.id"
      type="target"
      :position="Position.Left"
      class="handle-input"
      :title="input.label"
    />

    <!-- Node Content -->
    <div class="node-header">
      <span class="node-icon">{{ nodeDef?.icon || '⚡' }}</span>
      <span class="node-label">{{ data.label }}</span>
    </div>

    <!-- Status bar -->
    <div v-if="statusLabel" class="node-status-bar" :style="{ backgroundColor: statusColor + '20', color: statusColor }">
      <span class="status-dot" :style="{ backgroundColor: statusColor }"></span>
      {{ statusLabel }}
    </div>

    <!-- Error message -->
    <div v-if="data.error" class="node-error" :title="data.error">
      {{ data.error.slice(0, 60) }}{{ data.error.length > 60 ? '...' : '' }}
    </div>

    <!-- Output Handles -->
    <Handle
      v-for="output in nodeDef?.outputs || []"
      :key="output.id"
      :id="output.id"
      type="source"
      :position="Position.Right"
      class="handle-output"
      :title="output.label"
    />
  </div>
</template>

<style scoped>
.workflow-node-wrapper {
  background: #ffffff;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 16px;
  min-width: 180px;
  max-width: 260px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
  position: relative;
  cursor: grab;
}

.workflow-node-wrapper:hover {
  border-color: var(--node-color);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.node-selected {
  border-color: var(--node-color) !important;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--node-color) 20%, transparent) !important;
}

.status-ring {
  position: absolute;
  inset: -4px;
  border: 2px solid;
  border-radius: 14px;
  pointer-events: none;
}

.running-pulse {
  position: absolute;
  inset: -6px;
  border: 2px solid #f59e0b;
  border-radius: 16px;
  animation: pulse 1.5s ease-in-out infinite;
  pointer-events: none;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.02); }
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-icon {
  font-size: 18px;
  line-height: 1;
}

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-status-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.node-error {
  margin-top: 6px;
  padding: 4px 8px;
  background: #fef2f2;
  border-radius: 6px;
  font-size: 11px;
  color: #dc2626;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Handles */
.handle-input,
.handle-output {
  width: 12px !important;
  height: 12px !important;
  border: 2px solid #d1d5db !important;
  background: #ffffff !important;
  transition: all 0.15s ease;
}

.handle-input:hover,
.handle-output:hover {
  border-color: var(--node-color) !important;
  background: var(--node-color) !important;
  transform: scale(1.3);
}

.handle-input {
  left: -6px !important;
}

.handle-output {
  right: -6px !important;
}

/* Status-specific styles */
.node-status-running {
  border-color: #f59e0b;
}

.node-status-success {
  border-color: #22c55e;
}

.node-status-error {
  border-color: #ef4444;
}
</style>
