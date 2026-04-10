/**
 * Journey Workflow Composable
 * 
 * Manages workflow state and execution for the Journey feature.
 */

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
  connections?: string[] // IDs of connected nodes
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
  
  // State
  const nodes = useState<WorkflowNode[]>('journey-nodes', () => [])
  const isProcessing = useState<boolean>('journey-processing', () => false)
  const workflowResults = useState<WorkflowResult[]>('journey-results', () => [])
  
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
        conditions: [],
        logic: 'AND',
        truePath: [],
        falsePath: []
      }
      inactive = true // Backend not implemented yet
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
  const executeWorkflow = async () => {
    if (nodes.value.length === 0) {
      throw new Error('No nodes in workflow')
    }
    
    const uploadNode = nodes.value.find(n => n.type === 'upload')
    if (!uploadNode || !uploadNode.files || uploadNode.files.length === 0) {
      throw new Error('No files uploaded')
    }
    
    isProcessing.value = true
    workflowResults.value = []
    
    try {
      let previousResult: any = null
      let ocrResult: any = null // Track OCR/Parse results for reuse
      
      for (const node of nodes.value) {
        // Skip inactive nodes
        if (node.inactive) {
          node.status = 'inactive'
          workflowResults.value.push({
            nodeId: node.id,
            nodeLabel: node.label,
            status: 'error',
            error: 'Node is inactive - backend implementation pending'
          })
          continue
        }
        
        node.status = 'processing'
        
        try {
          const result = await processNode(node, previousResult, uploadNode.files!, ocrResult)
          node.status = 'completed'
          node.result = result
          
          // Track OCR/Parse results for downstream nodes
          if (node.type === 'ocr' || node.type === 'parse') {
            ocrResult = result
          }
          
          workflowResults.value.push({
            nodeId: node.id,
            nodeLabel: node.label,
            status: 'success',
            data: result
          })
          
          previousResult = result
        } catch (error: any) {
          node.status = 'error'
          workflowResults.value.push({
            nodeId: node.id,
            nodeLabel: node.label,
            status: 'error',
            error: error.message
          })
          throw error // Stop workflow on error
        }
      }
    } finally {
      isProcessing.value = false
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
        throw new Error('Condition node backend not implemented yet')
      
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
    const tierConfig = {
      'Rapid': 'deepseek-ocr',
      'Normal': 'gemini-2.5-flash-image',
      'Advance': 'gemini-3-pro-image-preview'
    }
    const modelId = tierConfig[node.tier as keyof typeof tierConfig] || 'gemini-2.5-flash-image'
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
    const tierConfig = {
      'Rapid': 'deepseek-ocr',
      'Normal': 'gemini-2.5-flash-image',
      'Advance': 'gemini-3-pro-image-preview'
    }
    const modelId = tierConfig[node.tier as keyof typeof tierConfig] || 'gemini-2.5-flash-image'
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
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tier', node.tier)
    
    // Add classification rules from config
    if (node.config?.rules && node.config.rules.length > 0) {
      formData.append('classification_rules', JSON.stringify(node.config.rules))
    } else {
      throw new Error('No classification rules defined. Please add rules in node settings.')
    }
    
    // Classify endpoint always requires parser_model_id (doesn't support OCR reuse yet)
    const parserTierConfig = {
      'Rapid': 'deepseek-ocr',
      'Normal': 'gemini-2.5-flash-image',
      'Advance': 'gemini-3-pro-image-preview'
    }
    const parserModelId = parserTierConfig[node.tier as keyof typeof parserTierConfig] || 'gemini-2.5-flash-image'
    formData.append('parser_model_id', parserModelId)
    
    // Get classifier_model_id based on tier (for classification step)
    const classifierTierConfig = {
      'Rapid': 'gemini-2.5-flash-lite',
      'Normal': 'gemini-2.5-flash',
      'Advance': 'gemini-3-pro-preview'
    }
    const classifierModelId = classifierTierConfig[node.tier as keyof typeof classifierTierConfig] || 'gemini-2.5-flash'
    formData.append('classifier_model_id', classifierModelId)
    
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
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tier', node.tier)
    formData.append('extraction_enabled', 'true')
    formData.append('process_all_pages', 'true')
    formData.append('parse_formatting', 'true')
    
    // Parse endpoint doesn't support OCR reuse yet - always perform OCR
    const parserTierConfig = {
      'Rapid': 'deepseek-ocr',
      'Normal': 'gemini-2.5-flash-image',
      'Advance': 'gemini-3-pro-image-preview'
    }
    const modelId = parserTierConfig[node.tier as keyof typeof parserTierConfig] || 'gemini-2.5-flash-image'
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
    
    // Get extractor_model based on tier (for extraction step)
    const extractorTierConfig = {
      'Rapid': 'gemini-2.5-flash-lite',
      'Normal': 'gemini-2.5-flash',
      'Advance': 'gemini-3-pro-preview'
    }
    const extractorModel = extractorTierConfig[node.tier as keyof typeof extractorTierConfig] || 'gemini-2.5-flash'
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
            'Try using "Rapid" tier (deepseek-ocr) instead of Normal/Advance tier (Google models).'
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
  
  return {
    nodes,
    isProcessing,
    workflowResults,
    addNode,
    removeNode,
    clearWorkflow,
    updateNodeConfig,
    updateNodeFiles,
    executeWorkflow
  }
}
