/**
 * Workflow Validation Composable
 * 
 * Handles DAG validation, cycle detection, edge validation,
 * and node dependency resolution.
 */

import type { WorkflowNode, WorkflowEdge, ValidationError, NodeTypeDefinition } from '~/types/workflow'
import { useNodeRegistry } from './useNodeRegistry'

export function useWorkflowValidation() {
  const { getNodeType } = useNodeRegistry()

  /**
   * Detect cycles in the graph using DFS
   * Returns array of node IDs forming the cycle, or empty if no cycle
   */
  const detectCycles = (nodes: WorkflowNode[], edges: WorkflowEdge[]): string[][] => {
    const adjacency = buildAdjacencyList(nodes, edges)
    const visited = new Set<string>()
    const recursionStack = new Set<string>()
    const cycles: string[][] = []

    const dfs = (nodeId: string, path: string[]): boolean => {
      visited.add(nodeId)
      recursionStack.add(nodeId)
      path.push(nodeId)

      const neighbors = adjacency.get(nodeId) || []
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          if (dfs(neighbor, [...path])) {
            return true
          }
        } else if (recursionStack.has(neighbor)) {
          // Found a cycle
          const cycleStart = path.indexOf(neighbor)
          cycles.push(path.slice(cycleStart))
          return true
        }
      }

      recursionStack.delete(nodeId)
      return false
    }

    for (const node of nodes) {
      if (!visited.has(node.id)) {
        dfs(node.id, [])
      }
    }

    return cycles
  }

  /**
   * Topological sort using Kahn's algorithm
   * Returns ordered node IDs or null if graph has cycles
   */
  const topologicalSort = (nodes: WorkflowNode[], edges: WorkflowEdge[]): string[] | null => {
    const inDegree = new Map<string, number>()
    const adjacency = buildAdjacencyList(nodes, edges)

    // Initialize in-degrees
    for (const node of nodes) {
      inDegree.set(node.id, 0)
    }
    for (const edge of edges) {
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
    }

    // Start with nodes that have no incoming edges
    const queue: string[] = []
    for (const [nodeId, degree] of inDegree) {
      if (degree === 0) {
        queue.push(nodeId)
      }
    }

    const sorted: string[] = []
    while (queue.length > 0) {
      const current = queue.shift()!
      sorted.push(current)

      const neighbors = adjacency.get(current) || []
      for (const neighbor of neighbors) {
        const newDegree = (inDegree.get(neighbor) || 0) - 1
        inDegree.set(neighbor, newDegree)
        if (newDegree === 0) {
          queue.push(neighbor)
        }
      }
    }

    // If sorted doesn't contain all nodes, there's a cycle
    if (sorted.length !== nodes.length) {
      return null
    }

    return sorted
  }

  /**
   * Get execution levels (nodes that can run in parallel)
   * Returns array of arrays, each inner array is a parallel execution group
   */
  const getExecutionLevels = (nodes: WorkflowNode[], edges: WorkflowEdge[]): string[][] => {
    const inDegree = new Map<string, number>()
    const adjacency = buildAdjacencyList(nodes, edges)

    for (const node of nodes) {
      inDegree.set(node.id, 0)
    }
    for (const edge of edges) {
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
    }

    const levels: string[][] = []
    const remaining = new Set(nodes.map(n => n.id))

    while (remaining.size > 0) {
      const currentLevel: string[] = []

      for (const nodeId of remaining) {
        if ((inDegree.get(nodeId) || 0) === 0) {
          currentLevel.push(nodeId)
        }
      }

      if (currentLevel.length === 0) {
        // Cycle detected, break
        break
      }

      levels.push(currentLevel)

      for (const nodeId of currentLevel) {
        remaining.delete(nodeId)
        const neighbors = adjacency.get(nodeId) || []
        for (const neighbor of neighbors) {
          inDegree.set(neighbor, (inDegree.get(neighbor) || 0) - 1)
        }
      }
    }

    return levels
  }

  /**
   * Validate an edge connection between two nodes
   */
  const validateEdge = (
    sourceNode: WorkflowNode,
    targetNode: WorkflowNode,
    sourceHandle: string | undefined,
    targetHandle: string | undefined,
    existingEdges: WorkflowEdge[]
  ): { valid: boolean; reason?: string } => {
    // Cannot connect to self
    if (sourceNode.id === targetNode.id) {
      return { valid: false, reason: 'Cannot connect a node to itself' }
    }

    // Check if connection already exists
    const exists = existingEdges.some(
      e => e.source === sourceNode.id && e.target === targetNode.id
    )
    if (exists) {
      return { valid: false, reason: 'Connection already exists' }
    }

    // Validate port types
    const sourceDef = getNodeType(sourceNode.type)
    const targetDef = getNodeType(targetNode.type)

    if (sourceDef && targetDef) {
      const sourcePort = sourceDef.outputs.find(o => o.id === sourceHandle) || sourceDef.outputs[0]
      const targetPort = targetDef.inputs.find(i => i.id === targetHandle) || targetDef.inputs[0]

      if (sourcePort && targetPort) {
        // 'any' type is compatible with everything
        if (sourcePort.type !== 'any' && targetPort.type !== 'any') {
          if (sourcePort.type !== targetPort.type) {
            return {
              valid: false,
              reason: `Incompatible types: ${sourcePort.type} → ${targetPort.type}`
            }
          }
        }
      }

      // Check if target port already has a connection (unless it accepts multiple)
      if (targetPort && !targetPort.multiple) {
        const hasConnection = existingEdges.some(
          e => e.target === targetNode.id && e.targetHandle === targetHandle
        )
        if (hasConnection) {
          return { valid: false, reason: 'Input port already connected' }
        }
      }
    }

    return { valid: true }
  }

  /**
   * Validate the entire workflow
   */
  const validateWorkflow = (nodes: WorkflowNode[], edges: WorkflowEdge[]): ValidationError[] => {
    const errors: ValidationError[] = []

    if (nodes.length === 0) return errors

    // Check for cycles
    const cycles = detectCycles(nodes, edges)
    for (const cycle of cycles) {
      errors.push({
        type: 'cycle',
        message: `Cycle detected: ${cycle.join(' → ')}`,
        nodeIds: cycle,
      })
    }

    // Check for disconnected nodes (no inputs and no outputs connected)
    for (const node of nodes) {
      const hasIncoming = edges.some(e => e.target === node.id)
      const hasOutgoing = edges.some(e => e.source === node.id)
      const def = getNodeType(node.type)

      if (def) {
        // Input nodes don't need incoming edges
        if (def.inputs.length > 0 && !hasIncoming) {
          errors.push({
            type: 'disconnected',
            message: `Node "${node.data.label}" has no incoming connections`,
            nodeIds: [node.id],
          })
        }
        // Output nodes don't need outgoing edges
        if (def.outputs.length > 0 && !hasOutgoing && def.category !== 'output') {
          // This is a warning, not blocking
        }
      }
    }

    // Check for missing required config
    for (const node of nodes) {
      const def = getNodeType(node.type)
      if (def?.configSchema) {
        for (const field of def.configSchema) {
          if (field.required && !node.data.config[field.key]) {
            errors.push({
              type: 'config_error',
              message: `Node "${node.data.label}" is missing required config: ${field.label}`,
              nodeIds: [node.id],
            })
          }
        }
      }
    }

    return errors
  }

  /**
   * Get node dependencies (which nodes must complete before this one)
   */
  const getNodeDependencies = (nodeId: string, edges: WorkflowEdge[]): string[] => {
    return edges.filter(e => e.target === nodeId).map(e => e.source)
  }

  /**
   * Get node dependents (which nodes depend on this one)
   */
  const getNodeDependents = (nodeId: string, edges: WorkflowEdge[]): string[] => {
    return edges.filter(e => e.source === nodeId).map(e => e.target)
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  const buildAdjacencyList = (nodes: WorkflowNode[], edges: WorkflowEdge[]): Map<string, string[]> => {
    const adj = new Map<string, string[]>()
    for (const node of nodes) {
      adj.set(node.id, [])
    }
    for (const edge of edges) {
      const list = adj.get(edge.source) || []
      list.push(edge.target)
      adj.set(edge.source, list)
    }
    return adj
  }

  return {
    detectCycles,
    topologicalSort,
    getExecutionLevels,
    validateEdge,
    validateWorkflow,
    getNodeDependencies,
    getNodeDependents,
  }
}
