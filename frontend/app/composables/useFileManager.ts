/**
 * Composable for managing file uploads, selection, drag-drop, and preview URLs.
 */
import { useOCR } from '~/composables/useOCR'
import { useFilePreview } from '~/composables/useFilePreview'
import { useNotification } from '~/composables/useNotification'

export function useFileManager() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  const { files, uploadFiles, removeFile, clearFiles, loadUploads } = useOCR()
  const { setPreviewFile } = useFilePreview()

  // Local state
  const selectedFile = ref<any>(null)
  const uploadedFiles = ref<Map<string, File>>(new Map())
  const previewFileUrl = ref<string>('')
  const fileInput = ref<HTMLInputElement | null>(null)
  const isDragging = ref(false)
  const isSidebarDragging = ref(false)

  const triggerFileInput = () => {
    fileInput.value?.click()
  }

  const handleFileSelect = async (e: Event) => {
    const target = e.target as HTMLInputElement
    const newFiles = Array.from(target.files || [])
    await handleUpload(newFiles)
    if (target) target.value = ''
  }

  const handleUpload = async (newFiles: File[]) => {
    const result = await uploadFiles(newFiles)

    if (result.duplicates.length > 0) {
      const { warning } = useNotification()
      if (result.duplicates.length === 1) {
        warning(`File "${result.duplicates[0]}" is already uploaded`)
      } else {
        warning(`${result.duplicates.length} duplicate files skipped: ${result.duplicates.slice(0, 2).join(', ')}${result.duplicates.length > 2 ? '...' : ''}`)
      }
    }

    if (files.value.length > 0 && result.added > 0) {
      const newlyAddedFiles = files.value.slice(-result.added)
      const uniqueNewFiles = newFiles.filter(f => !result.duplicates.includes(f.name))
      newlyAddedFiles.forEach((fileItem, index) => {
        const fileObj = uniqueNewFiles[index]
        if (fileObj) uploadedFiles.value.set(fileItem.id, fileObj)
      })
    }
  }

  const handleFileDragStart = (event: DragEvent, file: any) => {
    if (!event.dataTransfer) return
    event.dataTransfer.effectAllowed = 'copy'
    event.dataTransfer.setData('application/x-drvision-file', JSON.stringify({
      id: file.id,
      name: file.name,
      type: file.type,
    }))
    isSidebarDragging.value = true
    const cleanup = () => {
      isSidebarDragging.value = false
      document.removeEventListener('dragend', cleanup)
    }
    document.addEventListener('dragend', cleanup)
  }

  const handlePreviewDrop = async (event: DragEvent) => {
    isDragging.value = false
    isSidebarDragging.value = false
    const data = event.dataTransfer?.getData('application/x-drvision-file')
    if (data) {
      const fileInfo = JSON.parse(data)
      const file = files.value.find(f => f.id === fileInfo.id)
      if (file) {
        selectedFile.value = file
        setPreviewFile(file)
        const fileObj = uploadedFiles.value.get(file.id)
        if (fileObj) {
          if (previewFileUrl.value) URL.revokeObjectURL(previewFileUrl.value)
          previewFileUrl.value = URL.createObjectURL(fileObj)
        } else {
          previewFileUrl.value = `${apiBaseUrl}/api/v1/uploads/${file.id}/download`
        }
      }
      return
    }
    const newFiles = Array.from(event.dataTransfer?.files || [])
    await handleUpload(newFiles)
  }

  const handleSelectFile = (file: any) => {
    let resolvedPreviewUrl = ''
    const fileObj = uploadedFiles.value.get(file.id)
    if (fileObj) {
      try { resolvedPreviewUrl = URL.createObjectURL(fileObj) } catch { resolvedPreviewUrl = '' }
    } else {
      resolvedPreviewUrl = `${apiBaseUrl}/api/v1/uploads/${file.id}/download`
    }
    return { file, previewUrl: resolvedPreviewUrl }
  }

  const handleRemoveFile = (fileId: string) => {
    if (selectedFile.value?.id === fileId && previewFileUrl.value) {
      URL.revokeObjectURL(previewFileUrl.value)
      previewFileUrl.value = ''
    }
    uploadedFiles.value.delete(fileId)
    removeFile(fileId)
    if (selectedFile.value?.id === fileId) {
      selectedFile.value = null
      setPreviewFile(null)
    }
  }

  const getFileForProcessing = async (fileId: string, fileName: string): Promise<File | null> => {
    const localFile = uploadedFiles.value.get(fileId)
    if (localFile) return localFile
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/uploads/${fileId}/download`)
      if (!response.ok) return null
      const blob = await response.blob()
      return new File([blob], fileName, { type: blob.type })
    } catch (error) {
      console.error('Failed to download file for processing:', error)
      return null
    }
  }

  const resetFiles = () => {
    clearFiles()
    selectedFile.value = null
    setPreviewFile(null)
    uploadedFiles.value.forEach(() => {
      if (previewFileUrl.value) {
        try { URL.revokeObjectURL(previewFileUrl.value) } catch {}
      }
    })
    uploadedFiles.value.clear()
    previewFileUrl.value = ''
  }

  return {
    files,
    selectedFile,
    uploadedFiles,
    previewFileUrl,
    fileInput,
    isDragging,
    isSidebarDragging,
    triggerFileInput,
    handleFileSelect,
    handleUpload,
    handleFileDragStart,
    handlePreviewDrop,
    handleSelectFile,
    handleRemoveFile,
    getFileForProcessing,
    resetFiles,
    loadUploads,
  }
}
