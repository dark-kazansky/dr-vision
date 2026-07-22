/**
 * useOCR Composable
 * 
 * Manages OCR state and API calls for file processing.
 * 
 * Requirements: 10.2, 10.3, 10.4, 10.8, 11.7, 11.9
 */

export interface FileItem {
  id: string
  name: string
  type: 'image' | 'pdf'
  size: number
  status: 'pending' | 'processing' | 'completed' | 'error'
  result?: OCRResult
  uploadedAt: Date
}

export interface OCRResult {
  success: boolean
  text?: string
  error?: string
  error_type?: string
  pages?: number
  filename?: string
  model?: string
}

export interface OCRConfig {
  tier: 'Rapid' | 'Normal' | 'Advance'
  processAllPages: boolean
  modelId: string
  extractorModel?: string
  extractorTier?: string
  extractionConfig?: any
}

export interface HealthStatus {
  status: string
  server_running: boolean
  available_models: string[]
}

export function useOCR() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  
  // State
  const files = useState<FileItem[]>('ocr-files', () => [])
  const isProcessing = useState<boolean>('ocr-processing', () => false)
  const results = useState<any>('ocr-results', () => null)
  const availableModels = useState<string[]>('available-models', () => [])
  
  // AbortController for cancelling requests
  let abortController: AbortController | null = null
  
  /**
   * Upload files to the file list
   */
  const uploadFiles = async (newFiles: File[]) => {
    const duplicates: string[] = []
    const uniqueFiles: File[] = []
    
    // Check for duplicates by name and size
    for (const newFile of newFiles) {
      const isDuplicate = files.value.some(
        existingFile => 
          existingFile.name === newFile.name && 
          existingFile.size === newFile.size
      )
      
      if (isDuplicate) {
        duplicates.push(newFile.name)
      } else {
        uniqueFiles.push(newFile)
      }
    }
    
    // Add only unique files
    const fileItems: FileItem[] = uniqueFiles.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: file.name,
      type: file.name.toLowerCase().endsWith('.pdf') ? 'pdf' : 'image',
      size: file.size,
      status: 'pending' as const,
      uploadedAt: new Date()
    }))
    
    files.value = [...files.value, ...fileItems]
    
    // Return duplicate info
    return {
      added: uniqueFiles.length,
      duplicates: duplicates
    }
  }
  
  /**
   * Process a file with OCR
   */
  const processFile = async (fileId: string, file: File, config: OCRConfig) => {
    // Find file item
    const fileItem = files.value.find(f => f.id === fileId)
    if (!fileItem) {
      console.error('File not found:', fileId)
      return
    }
    
    // Update status to processing
    fileItem.status = 'processing'
    isProcessing.value = true
    
    // Create new AbortController for this request
    abortController = new AbortController()
    
    try {
      // Create form data
      const formData = new FormData()
      formData.append('file', file)
      formData.append('model_id', config.modelId)
      formData.append('process_all_pages', config.processAllPages.toString())
      formData.append('tier', config.tier)
      
      // Add extraction parameters if provided
      if (config.extractionConfig) {
        formData.append('extraction_enabled', 'true')
        formData.append('extraction_target', config.extractionConfig.target)
        formData.append('extraction_schema', JSON.stringify(config.extractionConfig.schema))
        
        // Add extractor model and tier if provided
        if (config.extractorModel) {
          formData.append('extractor_model', config.extractorModel)
        }
        if (config.extractorTier) {
          formData.append('extractor_tier', config.extractorTier)
        }
      } else {
        formData.append('extraction_enabled', 'false')
      }
      
      // Make API request with abort signal
      const response = await $fetch<OCRResult>(`${apiBaseUrl}/ocr`, {
        method: 'POST',
        body: formData,
        signal: abortController.signal
      })
      
      // Update file with result
      fileItem.status = 'completed'
      fileItem.result = response
      results.value = response
      
    } catch (error: any) {
      // Handle abort
      if (error.name === 'AbortError' || error.message?.includes('aborted')) {
        console.log('Request was cancelled')
        fileItem.status = 'pending'
        fileItem.result = {
          success: false,
          error: 'Processing was cancelled',
          error_type: 'cancelled'
        }
        results.value = null
        return
      }
      
      // Handle other errors
      console.error('OCR processing error:', error)
      
      fileItem.status = 'error'
      fileItem.result = {
        success: false,
        error: error.data?.detail || error.message || 'OCR processing failed',
        error_type: error.data?.error_type || 'processing_error'
      }
      
      results.value = fileItem.result
      
    } finally {
      isProcessing.value = false
      abortController = null
    }
  }
  
  /**
   * Classify a file
   */
  const classifyFile = async (fileId: string, file: File, config: any) => {
    // Find file item
    const fileItem = files.value.find(f => f.id === fileId)
    if (!fileItem) {
      console.error('File not found:', fileId)
      return
    }
    
    // Update status to processing
    fileItem.status = 'processing'
    isProcessing.value = true
    
    // Create new AbortController for this request
    abortController = new AbortController()
    
    try {
      // Create form data
      const formData = new FormData()
      formData.append('file', file)
      formData.append('parser_model_id', config.parserModelId)
      formData.append('classifier_model_id', config.classifierModelId)
      formData.append('tier', config.tier)
      formData.append('max_pages', config.maxPages.toString())
      formData.append('classification_rules', JSON.stringify(config.classificationRules))
      
      // Make API request with abort signal
      const response = await $fetch<any>(`${apiBaseUrl}/classify`, {
        method: 'POST',
        body: formData,
        signal: abortController.signal
      })
      
      // Update file with result
      fileItem.status = 'completed'
      fileItem.result = response
      results.value = response
      
    } catch (error: any) {
      // Handle abort
      if (error.name === 'AbortError' || error.message?.includes('aborted')) {
        console.log('Request was cancelled')
        fileItem.status = 'pending'
        fileItem.result = {
          success: false,
          error: 'Processing was cancelled',
          error_type: 'cancelled'
        }
        results.value = null
        return
      }
      
      // Handle other errors
      console.error('Classification error:', error)
      
      fileItem.status = 'error'
      fileItem.result = {
        success: false,
        error: error.data?.detail || error.message || 'Classification failed',
        error_type: error.data?.error_type || 'processing_error'
      }
      
      results.value = fileItem.result
      
    } finally {
      isProcessing.value = false
      abortController = null
    }
  }
  
  /**
   * Split a file into categorized chunks
   */
  const splitFile = async (fileId: string, file: File, config: any) => {
    // Find file item
    const fileItem = files.value.find(f => f.id === fileId)
    if (!fileItem) {
      console.error('File not found:', fileId)
      return
    }
    
    // Update status to processing
    fileItem.status = 'processing'
    isProcessing.value = true
    
    // Create new AbortController for this request
    abortController = new AbortController()
    
    try {
      // Create form data
      const formData = new FormData()
      formData.append('file', file)
      formData.append('categories', JSON.stringify(config.categories))
      formData.append('allow_uncategorized', config.allowUncategorized.toString())
      formData.append('parser_tier', config.parserTier || 'Normal')
      formData.append('splitter_tier', config.splitterTier || 'Normal')
      formData.append('split_mode', config.splitMode || 'sections')
      
      // Make API request with abort signal
      const response = await $fetch<any>(`${apiBaseUrl}/split`, {
        method: 'POST',
        body: formData,
        signal: abortController.signal
      })
      
      // Update file with result
      fileItem.status = 'completed'
      fileItem.result = response
      results.value = response
      
    } catch (error: any) {
      // Handle abort
      if (error.name === 'AbortError' || error.message?.includes('aborted')) {
        console.log('Request was cancelled')
        fileItem.status = 'pending'
        fileItem.result = {
          success: false,
          error: 'Processing was cancelled',
          error_type: 'cancelled'
        }
        results.value = null
        return
      }
      
      // Handle other errors
      console.error('Split processing error:', error)
      
      fileItem.status = 'error'
      fileItem.result = {
        success: false,
        error: error.data?.detail || error.message || 'Split processing failed',
        error_type: error.data?.error_type || 'processing_error'
      }
      
      results.value = fileItem.result
      
    } finally {
      isProcessing.value = false
      abortController = null
    }
  }
  
  /**
   * Remove a file from the list
   */
  const removeFile = (fileId: string) => {
    files.value = files.value.filter(f => f.id !== fileId)
    
    // Clear results if this was the active file
    if (results.value?.filename === files.value.find(f => f.id === fileId)?.name) {
      results.value = null
    }
  }
  
  /**
   * Check health status and get available models
   */
  const checkHealth = async () => {
    try {
      const health = await $fetch<HealthStatus>(`${apiBaseUrl}/health`)
      availableModels.value = health.available_models
      return health
    } catch (error) {
      console.error('Health check failed:', error)
      return null
    }
  }
  
  /**
   * Clear all files
   */
  const clearFiles = () => {
    files.value = []
    results.value = null
  }
  
  /**
   * Cancel ongoing processing
   */
  const cancelProcessing = () => {
    if (abortController) {
      abortController.abort()
      console.log('Processing cancelled')
    }
  }
  
  return {
    // State
    files,
    isProcessing,
    results,
    availableModels,
    
    // Methods
    uploadFiles,
    processFile,
    classifyFile,
    splitFile,
    removeFile,
    checkHealth,
    clearFiles,
    cancelProcessing
  }
}
