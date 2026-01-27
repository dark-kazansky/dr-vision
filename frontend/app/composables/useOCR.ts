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
  
  /**
   * Upload files to the file list
   */
  const uploadFiles = async (newFiles: File[]) => {
    const fileItems: FileItem[] = newFiles.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: file.name,
      type: file.name.toLowerCase().endsWith('.pdf') ? 'pdf' : 'image',
      size: file.size,
      status: 'pending' as const,
      uploadedAt: new Date()
    }))
    
    files.value = [...files.value, ...fileItems]
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
    
    try {
      // Create form data
      const formData = new FormData()
      formData.append('file', file)
      formData.append('model_id', config.modelId)
      formData.append('process_all_pages', config.processAllPages.toString())
      formData.append('tier', config.tier)
      
      // Make API request
      const response = await $fetch<OCRResult>(`${apiBaseUrl}/ocr`, {
        method: 'POST',
        body: formData
      })
      
      // Update file with result
      fileItem.status = 'completed'
      fileItem.result = response
      results.value = response
      
    } catch (error: any) {
      // Handle error
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
  
  return {
    // State
    files,
    isProcessing,
    results,
    availableModels,
    
    // Methods
    uploadFiles,
    processFile,
    removeFile,
    checkHealth,
    clearFiles
  }
}
