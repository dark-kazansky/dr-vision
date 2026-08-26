/**
 * Journey Workflow Composable
 * 
 * Manages workflow state and execution for the Journey feature.
 */

export interface Connection {
  targetId: string
  outputIndex?: number // For nodes with multiple outputs (e.g., condition nodes)
}

export interface WorkflowNode {
  id: string
  type: 'upload' | 'ocr' | 'parse' | 'classify' | 'extract' | 'split' | 'condition' | 'validate' | 'script'
  label: string
  x: number
  y: number
  tier: string
  status: 'pending' | 'processing' | 'completed' | 'error' | 'inactive'
  files?: File[]
  config?: any
  result?: any
  connections?: Connection[] // Connections to other nodes with output index
  inactive?: boolean // Mark node as inactive (UI only, backend not implemented)
}

export interface WorkflowResult {
  nodeId: string
  nodeLabel: string
  status: 'success' | 'error'
  data?: any
  error?: string
}

export function useJourney() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  const { getParserModel, getExtractorModel } = useTierConfig()
  const jobs = useJobs()
  
  // State
  const nodes = useState<WorkflowNode[]>('journey-nodes', () => [])
  const isProcessing = useState<boolean>('journey-processing', () => false)
  const workflowResults = useState<WorkflowResult[]>('journey-results', () => [])
  const currentRunId = useState<string | null>('journey-current-run', () => null)

  /**
   * Normalize node connections coming from older serialized state where a
   * connection could be a bare id string. Always store the object form so
   * downstream code can rely on `connection.targetId`.
   */
  const normalizeConnections = (list: WorkflowNode[]): WorkflowNode[] => {
    for (const node of list) {
      if (!node.connections) continue
      node.connections = node.connections.map((c: any) =>
        typeof c === 'string' ? { targetId: c } : c
      )
    }
    return list
  }

  /**
   * Replace the current workflow with a previously saved set of nodes.
   * Resets transient state (status, results) and clears file objects on
   * upload nodes since they cannot be persisted.
   */
  const loadWorkflow = (savedNodes: WorkflowNode[]) => {
    const cloned = JSON.parse(JSON.stringify(savedNodes)) as WorkflowNode[]
    for (const n of cloned) {
      n.status = n.inactive ? 'inactive' : 'pending'
      delete n.result
      if (n.type === 'upload') n.files = []
    }
    nodes.value = normalizeConnections(cloned)
    workflowResults.value = []
  }

  /**
   * Send the graph + files to the backend orchestrator and reflect run
   * state back into the local node statuses for visual feedback.
   *
   * Returns when the backend run reaches a terminal state.
   */
  const runWorkflowOnBackend = async (
    files: File[],
    meta: { workflowId?: string | null; workflowName?: string } | undefined,
    api: ReturnType<typeof useWorkflowApi>,
  ): Promise<void> => {
    isProcessing.value = true
    workflowResults.value = []

    // Reset node statuses so the canvas reflects the new run.
    for (const n of nodes.value) {
      n.status = n.inactive ? 'inactive' : 'pending'
      delete n.result
    }

    try {
      let runResponse: { run: any; result: any }
      if (meta?.workflowId) {
        runResponse = await api.runSavedWorkflow(meta.workflowId, files)
      } else {
        // Strip File objects from nodes before sending JSON.
        const cleanedNodes = nodes.value.map((n) => {
          const { files: _files, result: _result, status: _status, ...rest } = n
          return rest as WorkflowNode
        })
        runResponse = await api.runAdhocWorkflow({
          nodes: cleanedNodes,
          files,
          workflowName: meta?.workflowName,
        })
      }

      // Sync final node statuses back onto the canvas.
      const run = runResponse.run
      currentRunId.value = run.id
      for (const remoteNode of run.nodes || []) {
        const localNode = nodes.value.find((n) => n.id === remoteNode.nodeId)
        if (!localNode) continue
        if (remoteNode.status === 'completed') localNode.status = 'completed'
        else if (remoteNode.status === 'failed') localNode.status = 'error'
        else if (remoteNode.status === 'skipped') localNode.status = 'inactive'
        else localNode.status = 'pending'
      }

      // Mirror per-node results into workflowResults for the existing
      // results modal, keyed by node id.
      const perFile = runResponse.result?.files?.[0]?.results || {}
      for (const node of nodes.value) {
        if (node.type === 'upload' || node.inactive) continue
        const data = perFile[node.id]
        if (data) {
          node.result = data
          workflowResults.value.push({
            nodeId: node.id,
            nodeLabel: node.label,
            status: 'success',
            data,
          })
        }
      }

      if (run.status !== 'completed') {
        throw new Error(run.error || `Workflow ${run.status}`)
      }
    } finally {
      isProcessing.value = false
      currentRunId.value = null
    }
  }
  
  /**
   * Add a node to the workflow
   */
  const addNode = (type: WorkflowNode['type'], viewportX?: number, viewportY?: number) => {
    const labels = {
      upload: 'Upload Files',
      ocr: 'OCR',
      parse: 'Parse',
      classify: 'Classify',
      extract: 'Extract Data',
      split: 'Split Document',
      condition: 'Condition',
      validate: 'Validate',
      script: 'User Script'
    }
    
    // Initialize config based on node type
    let config: any = undefined
    let inactive = false
    
    if (type === 'classify') {
      config = { rules: [] }
    } else if (type === 'extract') {
      config = { 
        target: 'document', 
        schema: { fields: [] },
        schemaMode: 'auto',
        manualMode: 'form',
        schemaPrompt: ''
      }
    } else if (type === 'split') {
      config = { categories: [] }
    } else if (type === 'condition') {
      config = { 
        conditions: [
          { operator: 'equals', value: '' }
        ]
      }
      // Condition node is now functional with backend support
    } else if (type === 'validate') {
      config = { 
        rules: [],
        onError: 'flag'
      }
      inactive = true // Backend not implemented yet
    } else if (type === 'script') {
      config = { 
        scriptFile: null,
        scriptType: 'python',
        parameters: {}
      }
      inactive = true // Backend not implemented yet
    }
    
    // Calculate position - use viewport center if provided, otherwise use default layout
    let x: number
    let y: number
    
    if (viewportX !== undefined && viewportY !== undefined) {
      // Center node in viewport (node width ~300px, height ~200px)
      x = Math.max(20, viewportX - 150)
      y = Math.max(20, viewportY - 100)
    } else {
      // Fallback to horizontal spread layout
      x = 100 + nodes.value.length * 350
      y = 100
    }
    
    const node: WorkflowNode = {
      id: `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      label: labels[type],
      x,
      y,
      tier: 'Normal',
      status: inactive ? 'inactive' : 'pending',
      files: type === 'upload' ? [] : undefined,
      config,
      inactive
    }
    
    nodes.value.push(node)
    return node
  }
  
  /**
   * Remove a node from the workflow
   */
  const removeNode = (nodeId: string) => {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
  }
  
  /**
   * Clear all nodes
   */
  const clearWorkflow = () => {
    nodes.value = []
    workflowResults.value = []
  }
  
  /**
   * Update node configuration
   */
  const updateNodeConfig = (nodeId: string, config: any) => {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.config = config
    }
  }
  
  /**
   * Update node files (for upload node)
   */
  const updateNodeFiles = (nodeId: string, files: File[]) => {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node && node.type === 'upload') {
      node.files = files
    }
  }
  
  /**
   * Execute the workflow
   */
  const executeWorkflow = async (meta?: { workflowId?: string | null; workflowName?: string }) => {
    if (nodes.value.length === 0) {
      throw new Error('No nodes in workflow')
    }
    
    const uploadNode = nodes.value.find(n => n.type === 'upload')
    if (!uploadNode || !uploadNode.files || uploadNode.files.length === 0) {
      throw new Error('No files uploaded')
    }

    // Prefer the backend orchestrator when reachable. Falls back to the
    // legacy in-browser executor below if the probe fails.
    try {
      const api = useWorkflowApi()
      const available = await api.checkAvailable()
      if (available) {
        return await runWorkflowOnBackend(uploadNode.files, meta, api)
      }
    } catch (err) {
      console.warn('Backend orchestrator unavailable, falling back to in-browser execution:', err)
    }

    isProcessing.value = true
    workflowResults.value = []

    // Create a job record up front so the Jobs tab shows the run immediately.
    const runRecord = jobs.create({
      workflowId: meta?.workflowId ?? null,
      workflowName: meta?.workflowName || 'Ad-hoc workflow',
      inputFiles: uploadNode.files.map((f) => f.name),
      nodes: nodes.value.map((n) => ({ id: n.id, label: n.label, type: n.type })),
    })
    const runId = runRecord.id
    currentRunId.value = runId
    jobs.start(runId)

    try {
      // Build execution graph based on connections
      const nodeResults = new Map<string, any>()
      const ocrCache = new Map<string, any>() // Cache OCR results per file
      
      // Process all files through the workflow
      const files = uploadNode.files!
      const allFileResults: any[] = []
      
      for (let fileIndex = 0; fileIndex < files.length; fileIndex++) {
        const file = files[fileIndex]
        console.log(`Processing file ${fileIndex + 1}/${files.length}: ${file.name}`)
        jobs.log(runId, `Processing file ${fileIndex + 1}/${files.length}: ${file.name}`)
        
        // Reset node results for this file
        nodeResults.clear()
        
        // Execute nodes in order (assuming linear workflow for now)
        for (const node of nodes.value) {
          // Skip upload node (already processed)
          if (node.type === 'upload') {
            nodeResults.set(node.id, { files: [file.name], count: 1 })
            if (fileIndex === 0) {
              jobs.updateNode(runId, node.id, {
                status: 'completed',
                startedAt: Date.now(),
                finishedAt: Date.now(),
                output: { files: [file.name] },
              })
            }
            continue
          }
          
          // Skip inactive nodes
          if (node.inactive) {
            if (fileIndex === 0) { // Only add status once
              node.status = 'inactive'
              workflowResults.value.push({
                nodeId: node.id,
                nodeLabel: node.label,
                status: 'error',
                error: 'Node is inactive - backend implementation pending'
              })
              jobs.updateNode(runId, node.id, {
                status: 'skipped',
                error: 'Node is inactive - backend implementation pending',
              })
            }
            continue
          }
          
          if (fileIndex === 0) {
            node.status = 'processing'
            jobs.updateNode(runId, node.id, { status: 'running', startedAt: Date.now() })
          }
          
          try {
            // Get previous result (from connected node or last node)
            const previousResult = getPreviousNodeResult(node, nodeResults)
            
            // Check if we have cached OCR result for this file
            const cachedOcr = ocrCache.get(file.name)
            
            const result = await processNode(
              node, 
              previousResult, 
              [file], // Process one file at a time
              cachedOcr
            )
            
            // Cache OCR/Parse results for reuse
            if (node.type === 'ocr' || node.type === 'parse') {
              ocrCache.set(file.name, result)
            }
            
            nodeResults.set(node.id, result)
            
            // Store result for this file
            if (fileIndex === 0) {
              node.status = 'completed'
              node.result = result
              jobs.updateNode(runId, node.id, {
                status: 'completed',
                finishedAt: Date.now(),
                output: result,
              })
            }
            
          } catch (error: any) {
            if (fileIndex === 0) {
              node.status = 'error'
              workflowResults.value.push({
                nodeId: node.id,
                nodeLabel: node.label,
                status: 'error',
                error: error.message
              })
              jobs.updateNode(runId, node.id, {
                status: 'failed',
                finishedAt: Date.now(),
                error: error.message,
              })
              jobs.log(runId, `Node ${node.label} failed: ${error.message}`, 'error', node.id)
            }
            throw error // Stop workflow on error
          }
        }
        
        // Collect results for this file
        allFileResults.push({
          fileName: file.name,
          results: Object.fromEntries(nodeResults)
        })
      }
      
      // Concatenate results from all files
      for (const node of nodes.value) {
        if (node.type === 'upload' || node.inactive) continue
        
        const concatenatedResult = concatenateNodeResults(node, allFileResults)
        
        workflowResults.value.push({
          nodeId: node.id,
          nodeLabel: node.label,
          status: 'success',
          data: concatenatedResult
        })
      }

      jobs.finish(runId, 'completed')

    } catch (err: any) {
      jobs.finish(runId, 'failed', err?.message || String(err))
      throw err
    } finally {
      isProcessing.value = false
      currentRunId.value = null
    }
  }
  
  /**
   * Get previous node result based on connections
   */
  const getPreviousNodeResult = (node: WorkflowNode, nodeResults: Map<string, any>): any => {
    // Find nodes that connect to this node
    const connectedNode = nodes.value.find(n => 
      n.connections?.some(conn => 
        typeof conn === 'string' ? conn === node.id : conn.targetId === node.id
      )
    )
    
    if (connectedNode) {
      return nodeResults.get(connectedNode.id)
    }
    
    // Fallback: get last processed node result
    const nodeIds = Array.from(nodeResults.keys())
    if (nodeIds.length > 0) {
      return nodeResults.get(nodeIds[nodeIds.length - 1])
    }
    
    return null
  }
  
  /**
   * Concatenate results from multiple files for a node
   */
  const concatenateNodeResults = (node: WorkflowNode, allFileResults: any[]): any => {
    if (allFileResults.length === 0) return null
    if (allFileResults.length === 1) return allFileResults[0].results[node.id]
    
    const nodeType = node.type
    const results = allFileResults.map(fr => fr.results[node.id]).filter(r => r)
    
    // Concatenate based on node type
    if (nodeType === 'ocr' || nodeType === 'parse') {
      // Combine text from all files
      return {
        success: true,
        text: results.map((r, i) => `--- File: ${allFileResults[i].fileName} ---\n${r.text}`).join('\n\n'),
        files: allFileResults.map(fr => fr.fileName),
        file_count: allFileResults.length
      }
    } else if (nodeType === 'classify') {
      // Combine classification results
      return {
        success: true,
        results: results.flatMap(r => r.results || []),
        file_count: allFileResults.length
      }
    } else if (nodeType === 'extract') {
      // Combine extraction results
      return {
        success: true,
        extraction: {
          success: true,
          structured_data: results.map((r, i) => ({
            file: allFileResults[i].fileName,
            data: r.extraction?.structured_data || r.structured_data
          }))
        },
        file_count: allFileResults.length
      }
    } else if (nodeType === 'split') {
      // Combine split results
      return {
        success: true,
        chunks: results.flatMap(r => r.chunks || []),
        unknown_chunks: results.flatMap(r => r.unknown_chunks || []),
        file_count: allFileResults.length
      }
    } else if (nodeType === 'condition') {
      // For condition, use first file result (or majority vote)
      return results[0]
    }
    
    // Default: return all results
    return {
      success: true,
      results: results,
      file_count: allFileResults.length
    }
  }
  
  /**
   * Process a single node
   */
  const processNode = async (
    node: WorkflowNode,
    previousResult: any,
    files: File[],
    ocrResult?: any
  ): Promise<any> => {
    switch (node.type) {
      case 'upload':
        return { files: files.map(f => f.name), count: files.length }
      
      case 'ocr':
        return await processOCRNode(node, files)
      
      case 'parse':
        return await processParseNode(node, files)
      
      case 'classify':
        return await processClassifyNode(node, files, previousResult, ocrResult)
      
      case 'extract':
        return await processExtractNode(node, files, previousResult, ocrResult)
      
      case 'split':
        return await processSplitNode(node, files, previousResult, ocrResult)
      
      case 'condition':
        return await processConditionNode(node, previousResult)
      
      case 'validate':
        throw new Error('Validate node backend not implemented yet')
      
      case 'script':
        throw new Error('User Script node backend not implemented yet')
      
      default:
        throw new Error(`Unknown node type: ${node.type}`)
    }
  }
  
  /**
   * Process OCR node (raw text extraction)
   */
  const processOCRNode = async (node: WorkflowNode, files: File[]): Promise<any> => {
    const file = files[0]
    if (!file) throw new Error('No file available')
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tier', node.tier)
    formData.append('process_all_pages', 'true')
    formData.append('parse_formatting', 'false') // Raw text only
    
    // Get model_id based on tier from backend tier config
    const modelId = getParserModel(node.tier)
    formData.append('model_id', modelId)
    
    const response = await $fetch(`${apiBaseUrl}/parse`, {
      method: 'POST',
      body: formData
    })
    
    return response
  }
  
  /**
   * Process parse node (formatted text with markdown/DOCX conversion)
   */
  const processParseNode = async (node: WorkflowNode, files: File[]): Promise<any> => {
    const file = files[0] // Process first file for now
    if (!file) throw new Error('No file available')
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tier', node.tier)
    formData.append('process_all_pages', 'true')
    formData.append('parse_formatting', 'true') // Parse to formatted text
    
    // Get model_id based on tier from backend tier config
    const modelId = getParserModel(node.tier)
    formData.append('model_id', modelId)
    
    const response = await $fetch(`${apiBaseUrl}/parse`, {
      method: 'POST',
      body: formData
    })
    
    return response
  }
  
  /**
   * Process classify node
   */
  const processClassifyNode = async (
    node: WorkflowNode,
    files: File[],
    previousResult: any,
    ocrResult?: any
  ): Promise<any> => {
    const file = files[0]
    if (!file) throw new Error('No file available')
    
    // Check if we can reuse OCR result from previous node
    if (ocrResult && (previousResult?.text || ocrResult.text)) {
      console.log('Reusing OCR result for classify node')
      
      // Use text-based classification (no file upload needed)
      const text = previousResult?.text || ocrResult.text
      
      // Add classification rules from config
      if (!node.config?.rules || node.config.rules.length === 0) {
        throw new Error('No classification rules defined. Please add rules in node settings.')
      }
      
      // Call classifier directly with text (tier config will determine model)
      const formData = new FormData()
      formData.append('text', text)
      formData.append('classification_rules', JSON.stringify(node.config.rules))
      formData.append('tier', node.tier)  // Send tier, backend will use TierConfig
      
      try {
        const response = await $fetch(`${apiBaseUrl}/classify-text`, {
          method: 'POST',
          body: formData
        })
        return response
      } catch (error: any) {
        console.warn('Text-based classification not available, falling back to file-based')
        // Fall through to file-based classification
      }
    }
    
    // File-based classification (with OCR)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tier', node.tier)
    
    // Add classification rules from config
    if (node.config?.rules && node.config.rules.length > 0) {
      formData.append('classification_rules', JSON.stringify(node.config.rules))
    } else {
      throw new Error('No classification rules defined. Please add rules in node settings.')
    }
    
    // Get parser model from tier config
    const parserModelId = getParserModel(node.tier)
    formData.append('parser_model_id', parserModelId)
    
    // Backend will use TierConfig to determine classifier model based on tier
    // No need to send classifier_model_id explicitly
    
    const response = await $fetch(`${apiBaseUrl}/classify`, {
      method: 'POST',
      body: formData
    })
    
    return response
  }
  
  /**
   * Process extract node
   */
  const processExtractNode = async (
    node: WorkflowNode,
    files: File[],
    previousResult: any,
    ocrResult?: any
  ): Promise<any> => {
    const file = files[0]
    if (!file) throw new Error('No file available')
    
    // Check if we can reuse OCR result from previous node
    if (ocrResult && (previousResult?.text || ocrResult.text)) {
      console.log('Reusing OCR result for extract node')
      
      const text = previousResult?.text || ocrResult.text
      
      // Add extraction schema from config
      if (!node.config?.schema || !node.config.schema.fields || node.config.schema.fields.length === 0) {
        throw new Error('No extraction schema defined. Please add schema fields or generate schema in node settings.')
      }
      
      // Resolve extractor model from tier config (single source of truth)
      const extractorModel = getExtractorModel(node.tier)
      
      // Call extract endpoint with text
      const formData = new FormData()
      formData.append('text', text)
      formData.append('extraction_schema', JSON.stringify(node.config.schema.fields))
      formData.append('extraction_target', node.config?.target || 'document')
      formData.append('extractor_model_id', extractorModel)
      
      try {
        const response = await $fetch(`${apiBaseUrl}/extract-text`, {
          method: 'POST',
          body: formData
        })
        return response
      } catch (error: any) {
        console.warn('Text-based extraction not available, falling back to file-based')
        // Fall through to file-based extraction
      }
    }
    
    // File-based extraction (with OCR)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tier', node.tier)
    formData.append('extraction_enabled', 'true')
    formData.append('process_all_pages', 'true')
    formData.append('parse_formatting', 'true')
    
    // Parse endpoint doesn't support OCR reuse yet - always perform OCR
    const modelId = getParserModel(node.tier)
    formData.append('model_id', modelId)
    
    // Add extraction target
    if (node.config?.target) {
      formData.append('extraction_target', node.config.target)
    } else {
      formData.append('extraction_target', 'document')
    }
    
    // Add extraction schema from config
    if (node.config?.schema && node.config.schema.fields && node.config.schema.fields.length > 0) {
      // Backend expects array of fields directly, not { fields: [...] }
      const schemaFields = node.config.schema.fields
      console.log('Sending extraction schema:', schemaFields)
      formData.append('extraction_schema', JSON.stringify(schemaFields))
    } else {
      throw new Error('No extraction schema defined. Please add schema fields or generate schema in node settings.')
    }
    
    // Get extractor_model based on tier (for extraction step) — uses tier config
    const extractorModel = getExtractorModel(node.tier)
    formData.append('extractor_model', extractorModel)
    
    console.log('Extract node parameters:', {
      tier: node.tier,
      model_id: modelId,
      extraction_target: node.config?.target || 'document',
      extractor_model: extractorModel,
      extraction_enabled: true,
      schema_fields_count: node.config?.schema?.fields?.length || 0
    })
    
    try {
      const response = await $fetch(`${apiBaseUrl}/parse`, {
        method: 'POST',
        body: formData
      })
      
      return response
    } catch (error: any) {
      console.error('Extract node error:', error)
      
      // Check for Google API copyright/safety issues
      if (error.data?.detail && typeof error.data.detail === 'string') {
        const detail = error.data.detail
        
        if (detail.includes('finish_reason') && detail.includes('4')) {
          throw new Error(
            'Google API blocked this document (copyrighted material detected). ' +
            'Try using "Rapid" tier which uses a different OCR model, or use a different document.'
          )
        }
        
        if (detail.includes('reciting from copyrighted material')) {
          throw new Error(
            'Document contains copyrighted material. ' +
            'Try using "Rapid" tier (lightonocr-2-1b) instead of Normal/Advance tier.'
          )
        }
        
        throw new Error(detail)
      }
      
      throw error
    }
  }
  
  /**
   * Process split node
   */
  const processSplitNode = async (
    node: WorkflowNode,
    files: File[],
    previousResult: any,
    ocrResult?: any
  ): Promise<any> => {
    const file = files[0]
    if (!file) throw new Error('No file available')
    
    const formData = new FormData()
    formData.append('file', file)
    
    // Add split categories from config
    if (node.config?.categories && node.config.categories.length > 0) {
      formData.append('categories', JSON.stringify(node.config.categories))
    } else {
      throw new Error('No split categories defined. Please add categories in node settings.')
    }
    
    // Split endpoint doesn't support OCR reuse yet - always perform OCR
    formData.append('parser_tier', node.tier)
    formData.append('splitter_tier', node.tier)
    formData.append('allow_uncategorized', 'true')
    
    const response = await $fetch(`${apiBaseUrl}/split`, {
      method: 'POST',
      body: formData
    })
    
    return response
  }
  
  /**
   * Process condition node
   */
  const processConditionNode = async (
    node: WorkflowNode,
    previousResult: any
  ): Promise<any> => {
    if (!previousResult) {
      throw new Error('Condition node requires a previous result to evaluate')
    }
    
    if (!node.config?.conditions || node.config.conditions.length === 0) {
      throw new Error('No conditions defined. Please add conditions in node settings.')
    }
    
    const formData = new FormData()
    formData.append('conditions', JSON.stringify(node.config.conditions))
    formData.append('previous_result', JSON.stringify(previousResult))
    formData.append('field_name', 'document_type') // Default field to evaluate
    
    const response = await $fetch(`${apiBaseUrl}/condition/evaluate`, {
      method: 'POST',
      body: formData
    })
    
    return response
  }
  
  return {
    nodes,
    isProcessing,
    workflowResults,
    currentRunId,
    addNode,
    removeNode,
    clearWorkflow,
    updateNodeConfig,
    updateNodeFiles,
    executeWorkflow,
    loadWorkflow
  }
}
