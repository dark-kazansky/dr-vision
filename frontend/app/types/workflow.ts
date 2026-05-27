/**
 * Workflow Builder Type Definitions
 * 
 * Core types for the visual workflow builder system.
 * Covers nodes, edges, execution state, and validation.
 */

// ─── Node Types ───────────────────────────────────────────────────────────────

export type NodeCategory = 'input' | 'processing' | 'ai' | 'logic' | 'output'

export type NodeStatus = 'idle' | 'queued' | 'running' | 'success' | 'error' | 'skipped'

export interface PortDefinition {
  id: string
  label: string
  type: 'any' | 'text' | 'file' | 'json' | 'boolean'
  multiple?: boolean // Can accept multiple connections
}

export interface NodeTypeDefinition {
  type: string
  label: string
  description: string
  category: NodeCategory
  icon: string
  color: string
  inputs: PortDefinition[]
  outputs: PortDefinition[]
  defaultConfig: Record<string, any>
  configSchema?: ConfigField[]
  /** Whether this node can be executed */
  executable?: boolean
}

export interface ConfigField {
  key: string
  label: string
  type: 'text' | 'number' | 'select' | 'boolean' | 'json' | 'textarea' | 'array'
  options?: { label: string; value: string }[]
  default?: any
  required?: boolean
  placeholder?: string
}

export interface WorkflowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: {
    label: string
    config: Record<string, any>
    status: NodeStatus
    result?: any
    error?: string
    executionTime?: number
    groupId?: string
  }
}

// ─── Edge Types ───────────────────────────────────────────────────────────────

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
  animated?: boolean
  style?: Record<string, any>
  data?: {
    validated?: boolean
  }
}

// ─── Workflow Definition ──────────────────────────────────────────────────────

export interface WorkflowDefinition {
  id: string
  name: string
  description: string
  version: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  groups: NodeGroup[]
  metadata: {
    createdAt: string
    updatedAt: string
    author?: string
    tags?: string[]
  }
}

// ─── Node Groups ─────────────────────────────────────────────────────────────

export interface NodeGroup {
  id: string
  label: string
  color: string
  nodeIds: string[]
  collapsed?: boolean
}

// ─── Execution Types ─────────────────────────────────────────────────────────

export type ExecutionStatus = 'idle' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface ExecutionState {
  status: ExecutionStatus
  currentNodeId?: string
  completedNodes: string[]
  failedNodes: string[]
  skippedNodes: string[]
  startTime?: number
  endTime?: number
  results: Map<string, NodeExecutionResult>
}

export interface NodeExecutionResult {
  nodeId: string
  status: NodeStatus
  output?: any
  error?: string
  startTime: number
  endTime: number
  duration: number
}

// ─── Validation Types ────────────────────────────────────────────────────────

export interface ValidationError {
  type: 'cycle' | 'disconnected' | 'invalid_edge' | 'missing_input' | 'config_error'
  message: string
  nodeIds?: string[]
  edgeId?: string
}

// ─── History (Undo/Redo) ─────────────────────────────────────────────────────

export interface HistoryEntry {
  timestamp: number
  action: string
  snapshot: {
    nodes: WorkflowNode[]
    edges: WorkflowEdge[]
    groups: NodeGroup[]
  }
}

// ─── Clipboard ───────────────────────────────────────────────────────────────

export interface ClipboardData {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

// ─── Context Menu ────────────────────────────────────────────────────────────

export interface ContextMenuItem {
  id: string
  label: string
  icon?: string
  shortcut?: string
  disabled?: boolean
  danger?: boolean
  separator?: boolean
  action?: () => void
}

export interface ContextMenuState {
  visible: boolean
  x: number
  y: number
  items: ContextMenuItem[]
  targetNodeId?: string
  targetEdgeId?: string
}
