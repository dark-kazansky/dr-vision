/**
 * useFilePreview Composable
 * 
 * Manages file preview state including zoom and page navigation.
 * 
 * Requirements: 10.2, 10.3, 10.4, 11.2, 11.3
 */

import type { FileItem } from './useOCR'

export interface PreviewState {
  file: FileItem | null
  zoom: number
  currentPage: number
  totalPages: number
  previewUrl: string | null
}

export function useFilePreview() {
  // State
  const previewFile = useState<FileItem | null>('preview-file', () => null)
  const zoom = useState<number>('preview-zoom', () => 100)
  const currentPage = useState<number>('preview-page', () => 1)
  const totalPages = useState<number>('preview-total-pages', () => 1)
  const previewUrl = useState<string | null>('preview-url', () => null)
  
  /**
   * Set the file to preview
   */
  const setPreviewFile = (file: FileItem | null) => {
    previewFile.value = file
    
    if (file) {
      // Reset preview state
      zoom.value = 100
      currentPage.value = 1
      
      // Set total pages based on file type
      if (file.type === 'pdf' && file.result?.pages) {
        totalPages.value = file.result.pages
      } else {
        totalPages.value = 1
      }
    } else {
      previewUrl.value = null
      totalPages.value = 1
    }
  }
  
  /**
   * Zoom in (max 200%)
   */
  const zoomIn = () => {
    zoom.value = Math.min(zoom.value + 10, 200)
  }
  
  /**
   * Zoom out (min 50%)
   */
  const zoomOut = () => {
    zoom.value = Math.max(zoom.value - 10, 50)
  }
  
  /**
   * Reset zoom to 100%
   */
  const resetZoom = () => {
    zoom.value = 100
  }
  
  /**
   * Go to next page (for PDFs)
   */
  const nextPage = () => {
    if (currentPage.value < totalPages.value) {
      currentPage.value++
    }
  }
  
  /**
   * Go to previous page (for PDFs)
   */
  const prevPage = () => {
    if (currentPage.value > 1) {
      currentPage.value--
    }
  }
  
  /**
   * Go to specific page
   */
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages.value) {
      currentPage.value = page
    }
  }
  
  /**
   * Check if can go to next page
   */
  const canGoNext = computed(() => currentPage.value < totalPages.value)
  
  /**
   * Check if can go to previous page
   */
  const canGoPrev = computed(() => currentPage.value > 1)
  
  /**
   * Check if can zoom in
   */
  const canZoomIn = computed(() => zoom.value < 200)
  
  /**
   * Check if can zoom out
   */
  const canZoomOut = computed(() => zoom.value > 50)
  
  return {
    // State
    previewFile,
    zoom,
    currentPage,
    totalPages,
    previewUrl,
    
    // Computed
    canGoNext,
    canGoPrev,
    canZoomIn,
    canZoomOut,
    
    // Methods
    setPreviewFile,
    zoomIn,
    zoomOut,
    resetZoom,
    nextPage,
    prevPage,
    goToPage
  }
}
