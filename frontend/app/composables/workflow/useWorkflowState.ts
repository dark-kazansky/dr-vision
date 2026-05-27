/**
 * Workflow State Management Composable
 * 
 * Central state management for the workflow builder.
 * Handles: nodes, edges, selection, history (undo/redo),
 * clipboard (copy/paste), auto-save, and JSON import/export.
 */

import type {
  WorkflowNode,
  WorkflowEdge,
  WorkflowDefinition,
  NodeGroup,
  HistoryEntry,
  ClipboardData,
  ContextMenuState,
  NodeStatus,
} from '~/types/workflow'
import { useNodeRegistry } from './useNodeRegistry'

const MAX_HISTORY = 50
const AUTO_SAVE_DELAY = 2000

export function useWorkflowState() {
  const { getNodeType } = useNodeRegistry()

  // ─── Core State ────────────────────────────────────────────────────────
  const nodes = useState<WorkflowNode[]>('wf-builder-nodes', () => [])
  const edges = useState<WorkflowEdge[]>('wf-builder-edges', () => [])
  const groups = useState<NodeGroup[]>('wf-builder-groups', () => [])

  // ─── Metadata ──────────────────────────────────────────────────────────
  const workflowId = useState<string>('wf-builder-id', () => generateId())
  const workflowName = useState<string>('wf-builder-name', () => 'Untitled Workflow')
  const workflowDescription = useState<string>('wf-builder-description', () => '')
  const isDirty = useState<boolean>('wf-builder-dirty', () => false)

  // ─── Selection State ───────────────────────────────────────────────────
  const selectedNodes = useState<string[]>('wf-builder-selected-nodes', () => [])
  const selectedEdges = useState<string[]>('wf-builder-selected-edges', () => [])

  // ─── History (Undo/Redo) ───────────────────────────────────────────────
  const history = useState<HistoryEntry[]>('wf-builder-history', () => [])
  const historyIndex = useState<number>('wf-builder-history-index', () => -1)

  // ─── Clipboard ─────────────────────────────────────────────────────────
  const clipboard = useState<ClipboardData | null>('wf-builder-clipboard', () => null)

  // ─── Context Menu ──────────────────────────────────────────────────────
  const contextMenu = useState<ContextMenuState>('wf-builder-context-menu', () => ({
    visible: false,
    x: 0,
    y: 0,
    items: [],
  }))

  // ─── Auto-save ─────────────────────────────────────────────────────────
  let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

  const triggerAutoSave = () => {
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => {
      saveToLocalStorage()
      isDirty.value = false
    }, AUTO_SAVE_DELAY)
  }

  // ─── Node Operations ──────────────────────────────────────────────────

  const addNode = (type: string, position: { x: number; y: number }): WorkflowNode => {
    const def = getNodeType(type)
    if (!def) throw new Error(`Unknown node type: ${type}`)

    const node: WorkflowNode = {
      id: generateId(),
      type,
      position,
      data: {
        label: def.label,
        config: { ...def.defaultConfig },
        status: 'idle',
      },
    }

    nodes.value = [...nodes.value, node]
    pushHistory('Add node')
    isDirty.value = true
    triggerAutoSave()
    return node
  }

  const removeNodes = (nodeIds: string[]) => {
    // Remove edges connected to these nodes
    edges.value = edges.value.filter(
      e => !nodeIds.includes(e.source) && !nodeIds.includes(e.target)
    )
    // Remove nodes
    nodes.value = nodes.value.filter(n => !nodeIds.includes(n.id))
    // Clear selection
    selectedNodes.value = selectedNodes.value.filter(id => !nodeIds.includes(id))
    pushHistory('Remove nodes')
    isDirty.value = true
    triggerAutoSave()
  }

  const updateNodePosition = (nodeId: string, position: { x: number; y: number }) => {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.position = position
      isDirty.value = true
      triggerAutoSave()
    }
  }

  const updateNodeConfig = (nodeId: string, config: Record<string, any>) => {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.data.config = { ...node.data.config, ...config }
      pushHistory('Update config')
      isDirty.value = true
      triggerAutoSave()
    }
  }

  const updateNodeLabel = (nodeId: string, label: string) => {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.data.label = label
      isDirty.value = true
      triggerAutoSave()
    }
  }

  const updateNodeStatus = (nodeId: string, status: NodeStatus, result?: any, error?: string) => {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.data.status = status
      if (result !== undefined) node.data.result = result
      if (error !== undefined) node.data.error = error
    }
  }

  const resetAllNodeStatus = () => {
    for (const node of nodes.value) {
      node.data.status = 'idle'
      node.data.result = undefined
      node.data.error = undefined
      node.data.executionTime = undefined
    }
  }

  // ─── Edge Operations ──────────────────────────────────────────────────

  const addEdge = (edge: Omit<WorkflowEdge, 'id'>): WorkflowEdge => {
    const newEdge: WorkflowEdge = {
      ...edge,
      id: `e-${edge.source}-${edge.target}-${Date.now()}`,
    }
    edges.value = [...edges.value, newEdge]
    pushHistory('Add edge')
    isDirty.value = true
    triggerAutoSave()
    return newEdge
  }

  const removeEdges = (edgeIds: string[]) => {
    edges.value = edges.value.filter(e => !edgeIds.includes(e.id))
    selectedEdges.value = selectedEdges.value.filter(id => !edgeIds.includes(id))
    pushHistory('Remove edges')
    isDirty.value = true
    triggerAutoSave()
  }

  // ─── Selection ─────────────────────────────────────────────────────────

  const selectNode = (nodeId: string, addToSelection = false) => {
    if (addToSelection) {
      if (selectedNodes.value.includes(nodeId)) {
        selectedNodes.value = selectedNodes.value.filter(id => id !== nodeId)
      } else {
        selectedNodes.value = [...selectedNodes.value, nodeId]
      }
    } else {
      selectedNodes.value = [nodeId]
      selectedEdges.value = []
    }
  }

  const selectEdge = (edgeId: string) => {
    selectedEdges.value = [edgeId]
    selectedNodes.value = []
  }

  const selectAll = () => {
    selectedNodes.value = nodes.value.map(n => n.id)
  }

  const clearSelection = () => {
    selectedNodes.value = []
    selectedEdges.value = []
  }

  const selectNodesInRect = (rect: { x: number; y: number; width: number; height: number }) => {
    const selected = nodes.value.filter(n =>
      n.position.x >= rect.x &&
      n.position.x <= rect.x + rect.width &&
      n.position.y >= rect.y &&
      n.position.y <= rect.y + rect.height
    )
    selectedNodes.value = selected.map(n => n.id)
  }

  // ─── Groups ────────────────────────────────────────────────────────────

  const createGroup = (label: string, nodeIds: string[], color = '#6366f1'): NodeGroup => {
    const group: NodeGroup = {
      id: generateId(),
      label,
      color,
      nodeIds,
    }
    groups.value = [...groups.value, group]
    // Tag nodes with group
    for (const nodeId of nodeIds) {
      const node = nodes.value.find(n => n.id === nodeId)
      if (node) node.data.groupId = group.id
    }
    pushHistory('Create group')
    isDirty.value = true
    triggerAutoSave()
    return group
  }

  const removeGroup = (groupId: string) => {
    const group = groups.value.find(g => g.id === groupId)
    if (group) {
      for (const nodeId of group.nodeIds) {
        const node = nodes.value.find(n => n.id === nodeId)
        if (node) node.data.groupId = undefined
      }
    }
    groups.value = groups.value.filter(g => g.id !== groupId)
    pushHistory('Remove group')
    isDirty.value = true
    triggerAutoSave()
  }

  // ─── History (Undo/Redo) ───────────────────────────────────────────────

  const pushHistory = (action: string) => {
    // Remove any future history if we're not at the end
    if (historyIndex.value < history.value.length - 1) {
      history.value = history.value.slice(0, historyIndex.value + 1)
    }

    const entry: HistoryEntry = {
      timestamp: Date.now(),
      action,
      snapshot: {
        nodes: JSON.parse(JSON.stringify(nodes.value)),
        edges: JSON.parse(JSON.stringify(edges.value)),
        groups: JSON.parse(JSON.stringify(groups.value)),
      },
    }

    history.value.push(entry)
    if (history.value.length > MAX_HISTORY) {
      history.value.shift()
    }
    historyIndex.value = history.value.length - 1
  }

  const undo = () => {
    if (historyIndex.value > 0) {
      historyIndex.value--
      const entry = history.value[historyIndex.value]
      if (entry) {
        nodes.value = JSON.parse(JSON.stringify(entry.snapshot.nodes))
        edges.value = JSON.parse(JSON.stringify(entry.snapshot.edges))
        groups.value = JSON.parse(JSON.stringify(entry.snapshot.groups))
        isDirty.value = true
        triggerAutoSave()
      }
    }
  }

  const redo = () => {
    if (historyIndex.value < history.value.length - 1) {
      historyIndex.value++
      const entry = history.value[historyIndex.value]
      if (entry) {
        nodes.value = JSON.parse(JSON.stringify(entry.snapshot.nodes))
        edges.value = JSON.parse(JSON.stringify(entry.snapshot.edges))
        groups.value = JSON.parse(JSON.stringify(entry.snapshot.groups))
        isDirty.value = true
        triggerAutoSave()
      }
    }
  }

  const canUndo = computed(() => historyIndex.value > 0)
  const canRedo = computed(() => historyIndex.value < history.value.length - 1)

  // ─── Clipboard (Copy/Paste) ────────────────────────────────────────────

  const copySelected = () => {
    if (selectedNodes.value.length === 0) return

    const selectedNodeSet = new Set(selectedNodes.value)
    const copiedNodes = nodes.value.filter(n => selectedNodeSet.has(n.id))
    const copiedEdges = edges.value.filter(
      e => selectedNodeSet.has(e.source) && selectedNodeSet.has(e.target)
    )

    clipboard.value = {
      nodes: JSON.parse(JSON.stringify(copiedNodes)),
      edges: JSON.parse(JSON.stringify(copiedEdges)),
    }
  }

  const paste = (offset = { x: 50, y: 50 }) => {
    if (!clipboard.value) return

    const idMap = new Map<string, string>()

    // Create new nodes with new IDs
    const newNodes: WorkflowNode[] = clipboard.value.nodes.map(n => {
      const newId = generateId()
      idMap.set(n.id, newId)
      return {
        ...n,
        id: newId,
        position: { x: n.position.x + offset.x, y: n.position.y + offset.y },
        data: { ...n.data, status: 'idle' as NodeStatus, result: undefined, error: undefined },
      }
    })

    // Create new edges with mapped IDs
    const newEdges: WorkflowEdge[] = clipboard.value.edges.map(e => ({
      ...e,
      id: generateId(),
      source: idMap.get(e.source) || e.source,
      target: idMap.get(e.target) || e.target,
    }))

    nodes.value = [...nodes.value, ...newNodes]
    edges.value = [...edges.value, ...newEdges]

    // Select pasted nodes
    selectedNodes.value = newNodes.map(n => n.id)

    pushHistory('Paste')
    isDirty.value = true
    triggerAutoSave()
  }

  const duplicateSelected = () => {
    copySelected()
    paste({ x: 100, y: 100 })
  }

  // ─── Import/Export ─────────────────────────────────────────────────────

  const exportWorkflow = (): WorkflowDefinition => {
    return {
      id: workflowId.value,
      name: workflowName.value,
      description: workflowDescription.value,
      version: '1.0.0',
      nodes: JSON.parse(JSON.stringify(nodes.value)),
      edges: JSON.parse(JSON.stringify(edges.value)),
      groups: JSON.parse(JSON.stringify(groups.value)),
      metadata: {
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    }
  }

  const importWorkflow = (definition: WorkflowDefinition) => {
    workflowId.value = definition.id || generateId()
    workflowName.value = definition.name || 'Imported Workflow'
    workflowDescription.value = definition.description || ''
    nodes.value = definition.nodes || []
    edges.value = definition.edges || []
    groups.value = definition.groups || []
    selectedNodes.value = []
    selectedEdges.value = []
    history.value = []
    historyIndex.value = -1
    pushHistory('Import workflow')
    isDirty.value = false
  }

  const exportToJSON = (): string => {
    return JSON.stringify(exportWorkflow(), null, 2)
  }

  const importFromJSON = (json: string) => {
    try {
      const definition = JSON.parse(json) as WorkflowDefinition
      importWorkflow(definition)
    } catch (e) {
      throw new Error('Invalid workflow JSON')
    }
  }

  // ─── Local Storage ─────────────────────────────────────────────────────

  const STORAGE_KEY = 'dr-vision-workflow-builder'

  const saveToLocalStorage = () => {
    if (typeof window === 'undefined') return
    try {
      const data = exportWorkflow()
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch (e) {
      console.warn('Failed to save workflow to localStorage:', e)
    }
  }

  const loadFromLocalStorage = () => {
    if (typeof window === 'undefined') return false
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const data = JSON.parse(raw) as WorkflowDefinition
        importWorkflow(data)
        return true
      }
    } catch (e) {
      console.warn('Failed to load workflow from localStorage:', e)
    }
    return false
  }

  // ─── Clear ─────────────────────────────────────────────────────────────

  const clearWorkflow = () => {
    nodes.value = []
    edges.value = []
    groups.value = []
    selectedNodes.value = []
    selectedEdges.value = []
    workflowName.value = 'Untitled Workflow'
    workflowDescription.value = ''
    workflowId.value = generateId()
    history.value = []
    historyIndex.value = -1
    isDirty.value = false
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  // ─── Helpers ───────────────────────────────────────────────────────────

  function generateId(): string {
    return `${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 9)}`
  }

  return {
    // State
    nodes,
    edges,
    groups,
    workflowId,
    workflowName,
    workflowDescription,
    isDirty,
    selectedNodes,
    selectedEdges,
    contextMenu,
    clipboard,
    canUndo,
    canRedo,

    // Node operations
    addNode,
    removeNodes,
    updateNodePosition,
    updateNodeConfig,
    updateNodeLabel,
    updateNodeStatus,
    resetAllNodeStatus,

    // Edge operations
    addEdge,
    removeEdges,

    // Selection
    selectNode,
    selectEdge,
    selectAll,
    clearSelection,
    selectNodesInRect,

    // Groups
    createGroup,
    removeGroup,

    // History
    undo,
    redo,
    pushHistory,

    // Clipboard
    copySelected,
    paste,
    duplicateSelected,

    // Import/Export
    exportWorkflow,
    importWorkflow,
    exportToJSON,
    importFromJSON,

    // Persistence
    saveToLocalStorage,
    loadFromLocalStorage,
    clearWorkflow,
  }
}
