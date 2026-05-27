<script setup lang="ts">
/**
 * Right Configuration Panel
 * 
 * Shows configuration options for the selected node.
 * Dynamically renders form fields based on node type's configSchema.
 */
import type { WorkflowNode, ConfigField } from '~/types/workflow'
import { useNodeRegistry } from '~/composables/workflow/useNodeRegistry'
import { useWorkflowState } from '~/composables/workflow/useWorkflowState'

const props = defineProps<{
  nodeId: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { getNodeType } = useNodeRegistry()
const { nodes, updateNodeConfig, updateNodeLabel, removeNodes } = useWorkflowState()

const selectedNode = computed(() => {
  if (!props.nodeId) return null
  return nodes.value.find(n => n.id === props.nodeId) || null
})

const nodeDef = computed(() => {
  if (!selectedNode.value) return null
  return getNodeType(selectedNode.value.type)
})

const nodeLabel = ref('')

watch(() => selectedNode.value?.data.label, (val) => {
  if (val) nodeLabel.value = val
}, { immediate: true })

const onLabelChange = () => {
  if (props.nodeId && nodeLabel.value.trim()) {
    updateNodeLabel(props.nodeId, nodeLabel.value.trim())
  }
}

const onConfigChange = (key: string, value: any) => {
  if (props.nodeId) {
    updateNodeConfig(props.nodeId, { [key]: value })
  }
}

const onDelete = () => {
  if (props.nodeId) {
    removeNodes([props.nodeId])
    emit('close')
  }
}

const getFieldValue = (field: ConfigField) => {
  return selectedNode.value?.data.config[field.key] ?? field.default ?? ''
}
</script>

<template>
  <aside class="config-panel" v-if="selectedNode && nodeDef">
    <div class="panel-header">
      <div class="panel-title-row">
        <span class="panel-icon">{{ nodeDef.icon }}</span>
        <h3 class="panel-title">{{ nodeDef.label }}</h3>
      </div>
      <button class="close-btn" @click="emit('close')" title="Close">
        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="panel-body">
      <!-- Node Label -->
      <div class="config-field">
        <label class="field-label">Node Name</label>
        <input
          v-model="nodeLabel"
          type="text"
          class="field-input"
          @blur="onLabelChange"
          @keydown.enter="onLabelChange"
        />
      </div>

      <!-- Node Description -->
      <p class="node-description">{{ nodeDef.description }}</p>

      <!-- Dynamic Config Fields -->
      <div class="config-section">
        <h4 class="section-title">Configuration</h4>

        <div v-for="field in nodeDef.configSchema || []" :key="field.key" class="config-field">
          <label class="field-label">{{ field.label }}</label>

          <!-- Text input -->
          <input
            v-if="field.type === 'text'"
            :value="getFieldValue(field)"
            @input="onConfigChange(field.key, ($event.target as HTMLInputElement).value)"
            type="text"
            class="field-input"
            :placeholder="field.placeholder"
          />

          <!-- Number input -->
          <input
            v-else-if="field.type === 'number'"
            :value="getFieldValue(field)"
            @input="onConfigChange(field.key, Number(($event.target as HTMLInputElement).value))"
            type="number"
            class="field-input"
          />

          <!-- Select -->
          <select
            v-else-if="field.type === 'select'"
            :value="getFieldValue(field)"
            @change="onConfigChange(field.key, ($event.target as HTMLSelectElement).value)"
            class="field-select"
          >
            <option v-for="opt in field.options" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>

          <!-- Boolean -->
          <label v-else-if="field.type === 'boolean'" class="field-toggle">
            <input
              type="checkbox"
              :checked="getFieldValue(field)"
              @change="onConfigChange(field.key, ($event.target as HTMLInputElement).checked)"
            />
            <span class="toggle-label">{{ getFieldValue(field) ? 'Enabled' : 'Disabled' }}</span>
          </label>

          <!-- Textarea -->
          <textarea
            v-else-if="field.type === 'textarea'"
            :value="getFieldValue(field)"
            @input="onConfigChange(field.key, ($event.target as HTMLTextAreaElement).value)"
            class="field-textarea"
            :placeholder="field.placeholder"
            rows="4"
          ></textarea>

          <!-- JSON -->
          <textarea
            v-else-if="field.type === 'json'"
            :value="JSON.stringify(getFieldValue(field), null, 2)"
            @blur="onConfigChange(field.key, JSON.parse(($event.target as HTMLTextAreaElement).value || '{}'))"
            class="field-textarea field-json"
            rows="6"
            spellcheck="false"
          ></textarea>
        </div>
      </div>

      <!-- Node Info -->
      <div class="config-section">
        <h4 class="section-title">Ports</h4>
        <div class="ports-info">
          <div v-if="nodeDef.inputs.length > 0" class="port-group">
            <span class="port-direction">Inputs:</span>
            <span v-for="port in nodeDef.inputs" :key="port.id" class="port-badge input-badge">
              {{ port.label }} ({{ port.type }})
            </span>
          </div>
          <div v-if="nodeDef.outputs.length > 0" class="port-group">
            <span class="port-direction">Outputs:</span>
            <span v-for="port in nodeDef.outputs" :key="port.id" class="port-badge output-badge">
              {{ port.label }} ({{ port.type }})
            </span>
          </div>
        </div>
      </div>

      <!-- Execution Result -->
      <div v-if="selectedNode.data.result" class="config-section">
        <h4 class="section-title">Last Result</h4>
        <pre class="result-preview">{{ JSON.stringify(selectedNode.data.result, null, 2).slice(0, 500) }}</pre>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="panel-footer">
      <button class="delete-btn" @click="onDelete">
        <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        Delete Node
      </button>
    </div>
  </aside>

  <!-- Empty state -->
  <aside class="config-panel config-panel-empty" v-else>
    <div class="empty-state">
      <svg width="40" height="40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p>Select a node to configure</p>
    </div>
  </aside>
</template>

<style scoped>
.config-panel {
  width: 320px;
  min-width: 320px;
  background: #ffffff;
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.config-panel-empty {
  justify-content: center;
  align-items: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #9ca3af;
}

.empty-state p {
  font-size: 13px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-icon {
  font-size: 18px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.close-btn {
  padding: 4px;
  border: none;
  background: none;
  cursor: pointer;
  color: #6b7280;
  border-radius: 4px;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.node-description {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 16px;
  line-height: 1.5;
}

.config-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
}

.config-field {
  margin-bottom: 14px;
}

.field-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 4px;
}

.field-input,
.field-select,
.field-textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
  background: #ffffff;
}

.field-input:focus,
.field-select:focus,
.field-textarea:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
}

.field-textarea {
  resize: vertical;
  font-family: inherit;
}

.field-json {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}

.field-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.toggle-label {
  font-size: 13px;
  color: #374151;
}

.ports-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.port-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.port-direction {
  font-size: 12px;
  color: #6b7280;
  min-width: 60px;
}

.port-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.input-badge {
  background: #ede9fe;
  color: #7c3aed;
}

.output-badge {
  background: #ecfdf5;
  color: #059669;
}

.result-preview {
  font-size: 11px;
  font-family: 'SF Mono', monospace;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px;
  overflow: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-all;
}

.panel-footer {
  padding: 12px 16px;
  border-top: 1px solid #f3f4f6;
}

.delete-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #dc2626;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.delete-btn:hover {
  background: #fee2e2;
  border-color: #f87171;
}
</style>
