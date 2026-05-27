/**
 * Workflow Execution Engine
 * 
 * Implements async execution pipeline with:
 * - Topological sort-based execution order
 * - Parallel execution where possible
 * - Real-time status updates
 * - Cancellation support
 */

import type {
  WorkflowNode,
  WorkflowEdge,
  ExecutionState,
  ExecutionStatus,
  NodeStatus,
  NodeExecutionResult,
} from '~/types/workflow'
import { useWorkflowValidation } from './useWorkflowValidation'

export function useWorkflowExecution() {
  const { topologicalSort, getExecutionLevels, validateWorkflow } = useWorkflowValidation()
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  // Execution state
  const executionState = useState<ExecutionState>('workflow-execution-state', () => ({
    status: 'idle' as ExecutionStatus,
    completedNodes: [] as string[],
    failedNodes: [] as string[],
    skippedNodes: [] as string[],
    results: new Map<string, NodeExecutionResult>(),
  }))

  let abortController: AbortController | null = null

  /**
   * Execute the entire workflow
   */
  const executeWorkflow = async (
    nodes: WorkflowNode[],
    edges: WorkflowEdge[],
    onNodeStatusChange?: (nodeId: string, status: NodeStatus) => void
  ): Promise<Map<string, NodeExecutionResult>> => {
    // Validate first
    const errors = validateWorkflow(nodes, edges)
    const blockingErrors = errors.filter(e => e.type === 'cycle')
    if (blockingErrors.length > 0) {
      throw new Error(`Workflow has validation errors: ${blockingErrors[0]!.message}`)
    }

    // Get execution levels for parallel execution
    const levels = getExecutionLevels(nodes, edges)
    if (levels.length === 0) {
      throw new Error('No executable nodes found')
    }

    // Initialize execution state
    abortController = new AbortController()
    executionState.value = {
      status: 'running',
      completedNodes: [],
      failedNodes: [],
      skippedNodes: [],
      startTime: Date.now(),
      results: new Map(),
    }

    const nodeOutputs = new Map<string, any>()

    try {
      // Execute level by level (nodes in same level run in parallel)
      for (const level of levels) {
        if (abortController.signal.aborted) {
          executionState.value.status = 'cancelled'
          break
        }

        // Execute all nodes in this level in parallel
        const promises = level.map(async (nodeId) => {
          const node = nodes.find(n => n.id === nodeId)
          if (!node) return

          // Check if any dependency failed
          const deps = edges.filter(e => e.target === nodeId).map(e => e.source)
          const hasFailedDep = deps.some(d => executionState.value.failedNodes.includes(d))
          
          if (hasFailedDep) {
            executionState.value.skippedNodes.push(nodeId)
            onNodeStatusChange?.(nodeId, 'skipped')
            return
          }

          // Gather inputs from connected nodes
          const inputs = gatherInputs(nodeId, edges, nodeOutputs)

          // Update status
          executionState.value.currentNodeId = nodeId
          onNodeStatusChange?.(nodeId, 'running')

          const startTime = Date.now()

          try {
            const output = await executeNode(node, inputs, abortController!.signal)
            const endTime = Date.now()

            const result: NodeExecutionResult = {
              nodeId,
              status: 'success',
              output,
              startTime,
              endTime,
              duration: endTime - startTime,
            }

            nodeOutputs.set(nodeId, output)
            executionState.value.results.set(nodeId, result)
            executionState.value.completedNodes.push(nodeId)
            onNodeStatusChange?.(nodeId, 'success')
          } catch (error: any) {
            const endTime = Date.now()

            const result: NodeExecutionResult = {
              nodeId,
              status: 'error',
              error: error.message,
              startTime,
              endTime,
              duration: endTime - startTime,
            }

            executionState.value.results.set(nodeId, result)
            executionState.value.failedNodes.push(nodeId)
            onNodeStatusChange?.(nodeId, 'error')
          }
        })

        await Promise.all(promises)
      }

      // Determine final status
      executionState.value.endTime = Date.now()
      if (executionState.value.failedNodes.length > 0) {
        executionState.value.status = 'failed'
      } else if (executionState.value.status !== 'cancelled') {
        executionState.value.status = 'completed'
      }
    } catch (error: any) {
      executionState.value.status = 'failed'
      executionState.value.endTime = Date.now()
      throw error
    }

    return executionState.value.results
  }

  /**
   * Cancel running execution
   */
  const cancelExecution = () => {
    if (abortController) {
      abortController.abort()
      executionState.value.status = 'cancelled'
      executionState.value.endTime = Date.now()
    }
  }

  /**
   * Reset execution state
   */
  const resetExecution = () => {
    executionState.value = {
      status: 'idle',
      completedNodes: [],
      failedNodes: [],
      skippedNodes: [],
      results: new Map(),
    }
  }

  /**
   * Execute a single node
   */
  const executeNode = async (
    node: WorkflowNode,
    inputs: Record<string, any>,
    signal: AbortSignal
  ): Promise<any> => {
    if (signal.aborted) {
      throw new Error('Execution cancelled')
    }

    switch (node.type) {
      case 'file-input':
        return executeFileInput(node)
      case 'text-input':
        return executeTextInput(node)
      case 'api-input':
        return executeApiInput(node)
      case 'ocr':
        return executeOCR(node, inputs, signal)
      case 'parser':
        return executeParser(node, inputs, signal)
      case 'text-splitter':
        return executeTextSplitter(node, inputs)
      case 'classifier':
        return executeClassifier(node, inputs, signal)
      case 'extractor':
        return executeExtractor(node, inputs, signal)
      case 'llm':
        return executeLLM(node, inputs, signal)
      case 'summarizer':
        return executeSummarizer(node, inputs, signal)
      case 'condition':
        return executeCondition(node, inputs)
      case 'merge':
        return executeMerge(node, inputs)
      case 'loop':
        return executeLoop(node, inputs)
      case 'json-output':
        return executeJsonOutput(node, inputs)
      case 'webhook-output':
        return executeWebhookOutput(node, inputs, signal)
      case 'file-output':
        return executeFileOutput(node, inputs)
      default:
        throw new Error(`Unknown node type: ${node.type}`)
    }
  }

  // ─── Node Executors ──────────────────────────────────────────────────────

  const executeFileInput = async (node: WorkflowNode) => {
    // File input returns the configured files (set via UI)
    return { files: node.data.config._files || [], type: 'file' }
  }

  const executeTextInput = async (node: WorkflowNode) => {
    return { text: node.data.config.content || '', type: 'text' }
  }

  const executeApiInput = async (node: WorkflowNode) => {
    // API input would be triggered externally
    return { data: node.data.config._inputData || {}, type: 'json' }
  }

  const executeOCR = async (node: WorkflowNode, inputs: Record<string, any>, signal: AbortSignal) => {
    const fileData = inputs.file || inputs['*']
    if (!fileData?.files?.[0]) throw new Error('No file input for OCR')

    const formData = new FormData()
    formData.append('file', fileData.files[0])
    formData.append('tier', node.data.config.tier || 'Normal')
    formData.append('process_all_pages', String(node.data.config.processAllPages ?? true))
    formData.append('parse_formatting', 'false')

    const response = await $fetch(`${apiBaseUrl}/parse`, {
      method: 'POST',
      body: formData,
      signal,
    })
    return response
  }

  const executeParser = async (node: WorkflowNode, inputs: Record<string, any>, signal: AbortSignal) => {
    const fileData = inputs.file || inputs['*']
    if (!fileData?.files?.[0]) throw new Error('No file input for Parser')

    const formData = new FormData()
    formData.append('file', fileData.files[0])
    formData.append('tier', node.data.config.tier || 'Normal')
    formData.append('process_all_pages', 'true')
    formData.append('parse_formatting', String(node.data.config.parseFormatting ?? true))

    const response = await $fetch(`${apiBaseUrl}/parse`, {
      method: 'POST',
      body: formData,
      signal,
    })
    return response
  }

  const executeTextSplitter = async (node: WorkflowNode, inputs: Record<string, any>) => {
    const textData = inputs.text || inputs['*']
    const text = textData?.text || textData || ''
    const { method, chunkSize, overlap } = node.data.config

    // Simple client-side splitting (could be moved to backend)
    if (method === 'fixed') {
      const chunks: string[] = []
      for (let i = 0; i < text.length; i += chunkSize - overlap) {
        chunks.push(text.slice(i, i + chunkSize))
      }
      return { chunks, count: chunks.length }
    }

    // For semantic splitting, use backend
    return { chunks: [text], count: 1 }
  }

  const executeClassifier = async (node: WorkflowNode, inputs: Record<string, any>, signal: AbortSignal) => {
    const textData = inputs.text || inputs['*']
    const text = textData?.text || textData || ''

    const formData = new FormData()
    formData.append('text', text)
    formData.append('tier', node.data.config.tier || 'Normal')
    if (node.data.config.rules?.length > 0) {
      formData.append('classification_rules', JSON.stringify(node.data.config.rules))
    }

    const response = await $fetch(`${apiBaseUrl}/classify-text`, {
      method: 'POST',
      body: formData,
      signal,
    })
    return response
  }

  const executeExtractor = async (node: WorkflowNode, inputs: Record<string, any>, signal: AbortSignal) => {
    const textData = inputs.text || inputs['*']
    const text = textData?.text || textData || ''

    const formData = new FormData()
    formData.append('text', text)
    formData.append('extraction_target', node.data.config.target || 'document')
    if (node.data.config.schema?.fields?.length > 0) {
      formData.append('extraction_schema', JSON.stringify(node.data.config.schema.fields))
    }

    const response = await $fetch(`${apiBaseUrl}/extract-text`, {
      method: 'POST',
      body: formData,
      signal,
    })
    return response
  }

  const executeLLM = async (node: WorkflowNode, inputs: Record<string, any>, signal: AbortSignal) => {
    const textData = inputs.text || inputs['*']
    const text = textData?.text || textData || ''

    const response = await $fetch(`${apiBaseUrl}/api/v1/llm/complete`, {
      method: 'POST',
      body: {
        model: node.data.config.model,
        prompt: node.data.config.prompt,
        input: text,
        temperature: node.data.config.temperature,
        max_tokens: node.data.config.maxTokens,
      },
      signal,
    })
    return response
  }

  const executeSummarizer = async (node: WorkflowNode, inputs: Record<string, any>, signal: AbortSignal) => {
    const textData = inputs.text || inputs['*']
    const text = textData?.text || textData || ''

    const response = await $fetch(`${apiBaseUrl}/api/v1/llm/complete`, {
      method: 'POST',
      body: {
        model: 'gemini-3-flash',
        prompt: `Summarize the following text in a ${node.data.config.style} style, max ${node.data.config.maxLength} words:\n\n${text}`,
        input: text,
      },
      signal,
    })
    return response
  }

  const executeCondition = async (node: WorkflowNode, inputs: Record<string, any>) => {
    const inputData = inputs.input || inputs['*'] || {}
    const { field, operator, value } = node.data.config

    // Navigate to field value
    const fieldValue = field.split('.').reduce((obj: any, key: string) => obj?.[key], inputData)

    let result = false
    switch (operator) {
      case 'equals': result = String(fieldValue) === String(value); break
      case 'not_equals': result = String(fieldValue) !== String(value); break
      case 'contains': result = String(fieldValue).includes(String(value)); break
      case 'gt': result = Number(fieldValue) > Number(value); break
      case 'lt': result = Number(fieldValue) < Number(value); break
    }

    return { condition: result, branch: result ? 'true' : 'false', value: fieldValue }
  }

  const executeMerge = async (node: WorkflowNode, inputs: Record<string, any>) => {
    const values = Object.values(inputs).filter(Boolean)
    const { strategy } = node.data.config

    switch (strategy) {
      case 'combine':
        return { merged: values, count: values.length }
      case 'wait_all':
        return { merged: values, count: values.length }
      case 'first':
        return values[0] || null
      default:
        return { merged: values }
    }
  }

  const executeLoop = async (node: WorkflowNode, inputs: Record<string, any>) => {
    const itemsData = inputs.items || inputs['*']
    const items = Array.isArray(itemsData) ? itemsData : itemsData?.chunks || [itemsData]
    return { items, count: items.length, type: 'loop' }
  }

  const executeJsonOutput = async (node: WorkflowNode, inputs: Record<string, any>) => {
    const data = inputs.data || inputs['*']
    const formatted = node.data.config.format === 'pretty'
      ? JSON.stringify(data, null, 2)
      : JSON.stringify(data)
    return { output: formatted, format: 'json' }
  }

  const executeWebhookOutput = async (node: WorkflowNode, inputs: Record<string, any>, signal: AbortSignal) => {
    const data = inputs.data || inputs['*']
    const { url, method } = node.data.config

    if (!url) throw new Error('Webhook URL not configured')

    const response = await $fetch(url, {
      method: method || 'POST',
      body: data,
      signal,
    })
    return { sent: true, response }
  }

  const executeFileOutput = async (node: WorkflowNode, inputs: Record<string, any>) => {
    const data = inputs.data || inputs['*']
    const { filename, format } = node.data.config

    let content: string
    let mimeType: string

    switch (format) {
      case 'csv':
        content = convertToCSV(data)
        mimeType = 'text/csv'
        break
      case 'md':
        content = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
        mimeType = 'text/markdown'
        break
      default:
        content = JSON.stringify(data, null, 2)
        mimeType = 'application/json'
    }

    return { content, filename: `${filename}.${format}`, mimeType, size: content.length }
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  const gatherInputs = (
    nodeId: string,
    edges: WorkflowEdge[],
    nodeOutputs: Map<string, any>
  ): Record<string, any> => {
    const inputs: Record<string, any> = {}
    const incomingEdges = edges.filter(e => e.target === nodeId)

    for (const edge of incomingEdges) {
      const output = nodeOutputs.get(edge.source)
      const handleKey = edge.targetHandle || '*'
      inputs[handleKey] = output
    }

    return inputs
  }

  const convertToCSV = (data: any): string => {
    if (Array.isArray(data)) {
      if (data.length === 0) return ''
      const headers = Object.keys(data[0])
      const rows = data.map(item => headers.map(h => JSON.stringify(item[h] ?? '')).join(','))
      return [headers.join(','), ...rows].join('\n')
    }
    return JSON.stringify(data)
  }

  return {
    executionState: readonly(executionState),
    executeWorkflow,
    cancelExecution,
    resetExecution,
  }
}
