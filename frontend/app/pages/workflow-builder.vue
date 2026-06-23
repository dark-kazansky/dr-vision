<script setup lang="ts">
/**
 * Workflow Builder Page
 * 
 * Production-grade visual workflow editor using Vue Flow.
 * Features: infinite canvas, zoom/pan, drag-and-drop nodes,
 * edge validation, minimap, keyboard shortcuts, undo/redo,
 * auto-save, JSON export/import, DAG execution.
 */
import { VueFlow, useVueFlow, MarkerType, ConnectionMode } from '@vue-flow/core'
import { MiniMap } from '@vue-flow/minimap'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import type { Connection, Edge, Node, NodeDragEvent, NodeMouseEvent, EdgeMouseEvent } from '@vue-flow/core'
import type { ContextMenuItem } from '~/types/workflow'
import { useWorkflowState } from '~/composables/workflow/useWorkflowState'
import { useWorkflowValidation } from '~/composables/workflow/useWorkflowValidation'
import { useWorkflowExecution } from '~/composables/workflow/useWorkflowExecution'
import { useNodeRegistry } from '~/composables/workflow/useNodeRegistry'
import WorkflowNodeComponent from '~/components/workflow-builder/nodes/WorkflowNodeComponent.vue'
import NodeSidebar from '~/components/workflow-builder/panels/NodeSidebar.vue'
import ConfigPanel from '~/components/workflow-builder/panels/ConfigPanel.vue'
import WorkflowToolbar from '~/components/workflow-builder/panels/WorkflowToolbar.vue'
import ContextMenu from '~/components/workflow-builder/ContextMenu.vue'
import JobPanel from '~/components/workflow-builder/panels/JobPanel.vue'

// ─── State ───────────────────────────────────────────────────────────────────

const {
  nodes: workflowNodes,
  edges: workflowEdges,
  selectedNodes,
  selectedEdges,
  addNode,
  removeNodes,
  removeEdges,
  addEdge,
  updateNodePosition,
  selectNode,
  selectEdge,
  clearSelection,
  selectAll,
  undo,
  redo,
  copySelected,
  paste,
  duplicateSelected,
  exportToJSON,
  importFromJSON,
  loadFromLocalStorage,
  pushHistory,
} = useWorkflowState()

const { validateEdge } = useWorkflowValidation()
const { getNodeType } = useNodeRegistry()

// ─── Vue Flow Setup ──────────────────────────────────────────────────────────

const { 
  onConnect, 
  onNodeDragStop, 
  onPaneClick,
  addNodes,
  addEdges,
  project,
  fitView,
  zoomIn: vfZoomIn,
  zoomOut: vfZoomOut,
  getNodes,
  getEdges,
} = useVueFlow({
  defaultEdgeOptions: {
    animated: false,
    markerEnd: MarkerType.ArrowClosed,
    style: { stroke: '#9ca3af', strokeWidth: 2 },
  },
})

// Custom node types - use markRaw to avoid reactivity overhead
const nodeTypes: Record<string, any> = {
  'file-input': markRaw(WorkflowNodeComponent),
  'text-input': markRaw(WorkflowNodeComponent),
  'api-input': markRaw(WorkflowNodeComponent),
  'ocr': markRaw(WorkflowNodeComponent),
  'parser': markRaw(WorkflowNodeComponent),
  'text-splitter': markRaw(WorkflowNodeComponent),
  'layout-recognize': markRaw(WorkflowNodeComponent),
  'classifier': markRaw(WorkflowNodeComponent),
  'extractor': markRaw(WorkflowNodeComponent),
  'llm': markRaw(WorkflowNodeComponent),
  'summarizer': markRaw(WorkflowNodeComponent),
  'condition': markRaw(WorkflowNodeComponent),
  'merge': markRaw(WorkflowNodeComponent),
  'loop': markRaw(WorkflowNodeComponent),
  'json-output': markRaw(WorkflowNodeComponent),
  'webhook-output': markRaw(WorkflowNodeComponent),
  'file-output': markRaw(WorkflowNodeComponent),
}

// ─── Vue Flow Nodes/Edges (computed from workflow state) ─────────────────────

const vfNodes = computed(() => 
  workflowNodes.value.map(n => ({
    id: n.id,
    type: n.type,
    position: n.position,
    data: n.data,
    selected: selectedNodes.value.includes(n.id),
  }))
)

const vfEdges = computed(() =>
  workflowEdges.value.map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle,
    targetHandle: e.targetHandle,
    animated: e.animated,
    markerEnd: MarkerType.ArrowClosed,
    style: selectedEdges.value.includes(e.id)
      ? { stroke: '#7c3aed', strokeWidth: 3 }
      : { stroke: '#9ca3af', strokeWidth: 2 },
  }))
)

// ─── Connection Handling ─────────────────────────────────────────────────────

onConnect((params: Connection) => {
  const sourceNode = workflowNodes.value.find(n => n.id === params.source)
  const targetNode = workflowNodes.value.find(n => n.id === params.target)

  if (!sourceNode || !targetNode) return

  const validation = validateEdge(
    sourceNode,
    targetNode,
    params.sourceHandle || undefined,
    params.targetHandle || undefined,
    workflowEdges.value
  )

  if (validation.valid) {
    addEdge({
      source: params.source,
      target: params.target,
      sourceHandle: params.sourceHandle || undefined,
      targetHandle: params.targetHandle || undefined,
    })
  } else {
    console.warn('Invalid connection:', validation.reason)
  }
})

// ─── Node Drag ───────────────────────────────────────────────────────────────

onNodeDragStop((event: NodeDragEvent) => {
  for (const node of event.nodes) {
    updateNodePosition(node.id, node.position)
  }
})

// ─── Pane Click (deselect) ───────────────────────────────────────────────────

onPaneClick(() => {
  clearSelection()
  configNodeId.value = null
})

// ─── Drag & Drop from Sidebar ────────────────────────────────────────────────

const onDragOver = (event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

const onDrop = (event: DragEvent) => {
  const nodeType = event.dataTransfer?.getData('application/workflow-node')
  if (!nodeType) return

  // Get canvas position from screen coordinates
  const position = project({ x: event.clientX - 260, y: event.clientY - 52 })

  const node = addNode(nodeType, { x: position.x, y: position.y })
  selectNode(node.id)
  configNodeId.value = node.id
}

// ─── Node Selection & Config Panel ──────────────────────────────────────────

const configNodeId = ref<string | null>(null)

const onNodeClick = (event: NodeMouseEvent) => {
  selectNode(event.node.id)
  configNodeId.value = event.node.id
}

const onNodeDoubleClick = (event: NodeMouseEvent) => {
  configNodeId.value = event.node.id
}

const onEdgeClick = (event: EdgeMouseEvent) => {
  selectEdge(event.edge.id)
}

// ─── Context Menu ────────────────────────────────────────────────────────────

const contextMenuState = ref({
  visible: false,
  x: 0,
  y: 0,
  items: [] as ContextMenuItem[],
})

const onNodeContextMenu = (nodeEvent: NodeMouseEvent) => {
  const event = nodeEvent.event as MouseEvent
  event.preventDefault()
  const node = nodeEvent.node
  selectNode(node.id)

  contextMenuState.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    items: [
      { id: 'configure', label: 'Configure', icon: '⚙️', action: () => { configNodeId.value = node.id } },
      { id: 'duplicate', label: 'Duplicate', icon: '📋', shortcut: '⌘D', action: () => { selectNode(node.id); duplicateSelected() } },
      { id: 'sep1', label: '', separator: true },
      { id: 'delete', label: 'Delete', icon: '🗑️', shortcut: '⌫', danger: true, action: () => removeNodes([node.id]) },
    ],
  }
}

const onPaneContextMenu = (event: any) => {
  if (event.preventDefault) event.preventDefault()
  const clientX = event.clientX || event.x || 0
  const clientY = event.clientY || event.y || 0
  const position = project({ x: clientX - 260, y: clientY - 52 })

  contextMenuState.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    items: [
      { id: 'paste', label: 'Paste', icon: '📋', shortcut: '⌘V', action: () => paste() },
      { id: 'select-all', label: 'Select All', icon: '☐', shortcut: '⌘A', action: () => selectAll() },
      { id: 'sep1', label: '', separator: true },
      { id: 'fit', label: 'Fit View', icon: '🔲', action: () => fitView() },
      { id: 'sep2', label: '', separator: true },
      { id: 'add-file', label: 'Add File Input', icon: '📁', action: () => addNode('file-input', position) },
      { id: 'add-ocr', label: 'Add OCR', icon: '👁️', action: () => addNode('ocr', position) },
      { id: 'add-llm', label: 'Add LLM', icon: '🤖', action: () => addNode('llm', position) },
    ],
  }
}

const closeContextMenu = () => {
  contextMenuState.value.visible = false
}

// ─── Keyboard Shortcuts ──────────────────────────────────────────────────────

const onKeyDown = (event: KeyboardEvent) => {
  const meta = event.metaKey || event.ctrlKey

  // Delete selected
  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (selectedNodes.value.length > 0) {
      removeNodes([...selectedNodes.value])
      configNodeId.value = null
    }
    if (selectedEdges.value.length > 0) {
      removeEdges([...selectedEdges.value])
    }
    return
  }

  // Undo
  if (meta && event.key === 'z' && !event.shiftKey) {
    event.preventDefault()
    undo()
    return
  }

  // Redo
  if (meta && event.key === 'z' && event.shiftKey) {
    event.preventDefault()
    redo()
    return
  }

  // Copy
  if (meta && event.key === 'c') {
    event.preventDefault()
    copySelected()
    return
  }

  // Paste
  if (meta && event.key === 'v') {
    event.preventDefault()
    paste()
    return
  }

  // Duplicate
  if (meta && event.key === 'd') {
    event.preventDefault()
    duplicateSelected()
    return
  }

  // Select All
  if (meta && event.key === 'a') {
    event.preventDefault()
    selectAll()
    return
  }

  // Escape
  if (event.key === 'Escape') {
    clearSelection()
    configNodeId.value = null
    closeContextMenu()
    return
  }
}

// ─── Import/Export ───────────────────────────────────────────────────────────

const fileInput = ref<HTMLInputElement | null>(null)

const handleExport = () => {
  const json = exportToJSON()
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'workflow.json'
  a.click()
  URL.revokeObjectURL(url)
}

const handleImport = () => {
  fileInput.value?.click()
}

const onFileImport = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      importFromJSON(e.target?.result as string)
      nextTick(() => fitView())
    } catch (err) {
      alert('Invalid workflow file')
    }
  }
  reader.readAsText(file)
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  document.addEventListener('keydown', onKeyDown)
  // Load saved workflow
  loadFromLocalStorage()
  nextTick(() => {
    if (workflowNodes.value.length > 0) {
      fitView()
    }
  })
})

onUnmounted(() => {
  document.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <div class="workflow-builder-page">
    <!-- Toolbar -->
    <WorkflowToolbar
      @zoom-in="vfZoomIn"
      @zoom-out="vfZoomOut"
      @zoom-fit="fitView"
      @export="handleExport"
      @import="handleImport"
      @clear="configNodeId = null"
    />

    <div class="builder-body">
      <!-- Left Sidebar -->
      <NodeSidebar />

      <!-- Canvas -->
      <div
        class="canvas-container"
        @dragover="onDragOver"
        @drop="onDrop"
      >
        <VueFlow
          :nodes="vfNodes"
          :edges="vfEdges"
          :node-types="nodeTypes"
          :default-viewport="{ x: 0, y: 0, zoom: 1 }"
          :min-zoom="0.1"
          :max-zoom="4"
          :snap-to-grid="true"
          :snap-grid="[20, 20]"
          :connection-mode="ConnectionMode.Loose"
          :elevate-edges-on-select="true"
          fit-view-on-init
          @node-click="onNodeClick"
          @node-double-click="onNodeDoubleClick"
          @node-context-menu="onNodeContextMenu"
          @edge-click="onEdgeClick"
          @pane-context-menu="onPaneContextMenu"
        >
          <Background :gap="20" :size="1" pattern-color="#e5e7eb" />
          <MiniMap
            :node-color="(node: any) => getNodeType(node.type)?.color || '#6b7280'"
            :mask-color="'rgba(255, 255, 255, 0.8)'"
            position="bottom-right"
          />
          <Controls position="bottom-left" />
        </VueFlow>

        <!-- Empty state overlay -->
        <div v-if="workflowNodes.length === 0" class="empty-overlay">
          <div class="empty-content">
            <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3>Build Your AI Pipeline</h3>
            <p>Drag nodes from the sidebar to get started</p>
            <div class="shortcut-hints">
              <span>⌘Z Undo</span>
              <span>⌘C Copy</span>
              <span>⌘V Paste</span>
              <span>⌫ Delete</span>
            </div>
          </div>
        </div>

        <!-- Job Progress Panel -->
        <JobPanel />
      </div>

      <!-- Right Config Panel -->
      <ConfigPanel
        :node-id="configNodeId"
        @close="configNodeId = null"
      />
    </div>

    <!-- Context Menu -->
    <ContextMenu
      :visible="contextMenuState.visible"
      :x="contextMenuState.x"
      :y="contextMenuState.y"
      :items="contextMenuState.items"
      @close="closeContextMenu"
    />

    <!-- Hidden file input for import -->
    <input
      ref="fileInput"
      type="file"
      accept=".json"
      style="display: none"
      @change="onFileImport"
    />
  </div>
</template>

<style scoped>
.workflow-builder-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: #f9fafb;
}

.builder-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.canvas-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.empty-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 5;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #9ca3af;
  text-align: center;
}

.empty-content h3 {
  font-size: 18px;
  font-weight: 600;
  color: #6b7280;
}

.empty-content p {
  font-size: 14px;
}

.shortcut-hints {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.shortcut-hints span {
  font-size: 11px;
  padding: 3px 8px;
  background: #f3f4f6;
  border-radius: 4px;
  font-family: 'SF Mono', monospace;
  color: #6b7280;
}
</style>

<!-- Vue Flow global styles (unscoped) -->
<style>
/* Vue Flow base styles */
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
@import '@vue-flow/minimap/dist/style.css';
@import '@vue-flow/controls/dist/style.css';

/* Custom Vue Flow overrides */
.vue-flow__minimap {
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.vue-flow__controls {
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.vue-flow__controls .vue-flow__controls-button {
  border: none;
  border-bottom: 1px solid #f3f4f6;
}

.vue-flow__edge-path {
  stroke: #9ca3af;
  stroke-width: 2;
}

.vue-flow__edge.selected .vue-flow__edge-path {
  stroke: #7c3aed;
  stroke-width: 3;
}

.vue-flow__connection-line {
  stroke: #7c3aed;
  stroke-width: 2;
  stroke-dasharray: 5 5;
}
</style>
