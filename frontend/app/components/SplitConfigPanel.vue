<template>
  <div class="split-config-panel">
    <!-- Build Tab Content -->
    <div v-if="props.activeTab === 'build'" class="panel-content">
      <!-- Parser Model Selector -->
      <ModelSelector
        v-if="props.providers && props.providers.length > 0"
        v-model="selectedParserModelId"
        :providers="props.providers"
        :disabled="isProcessing"
        label="Parser Model"
      />
      
      <!-- Splitter Model Selector -->
      <ModelSelector
        v-if="props.providers && props.providers.length > 0"
        v-model="selectedSplitterModelId"
        :providers="props.providers"
        :disabled="isProcessing"
        label="Splitter Model"
      />
      
      <!-- Combined Config Card -->
      <div class="config-card">
        <!-- Splitting Strategy Section -->
        <div class="card-header">
          <h3 class="card-title">Splitting Strategy</h3>
        </div>
        
        <div class="card-body">
          <!-- Split Mode Toggle -->
          <div class="split-mode-toggle" :class="{ disabled: isProcessing }">
            <button
              type="button"
              :class="['split-mode-btn', { active: splitMode === 'sections' }]"
              :disabled="isProcessing"
              @click="splitMode = 'sections'"
            >
              Split by Sections
            </button>
            <button
              type="button"
              :class="['split-mode-btn', { active: splitMode === 'document_type' }]"
              :disabled="isProcessing"
              @click="splitMode = 'document_type'"
            >
              Split by Document Type
            </button>
          </div>

          <div v-if="splitMode === 'sections'" class="strategy-option">
            <div class="option-content">
              <div class="option-title">Allow uncategorized pages</div>
              <div class="option-description">Group unmatched pages together.</div>
            </div>
            <label class="switch">
              <input 
                type="checkbox" 
                v-model="allowUncategorized"
                :disabled="isProcessing"
              />
              <span class="slider"></span>
            </label>
          </div>
        </div>
        
        <!-- Categories Section -->
        <div class="card-header">
          <h3 class="card-title">Categories</h3>
          <p class="card-description">{{ splitMode === 'sections' ? 'Define categories that represent different sections or types of content in your document.' : 'Define document types that may appear in your multi-page file.' }}</p>
        </div>
        
        <div class="card-body">
          <!-- Quick Add Section -->
          <div class="quick-add-section">
            <span class="quick-add-label">Quick add</span>
            <button 
              v-for="category in topCategories"
              :key="category.name"
              type="button"
              @click="addQuickCategory(category.name, category.description)"
              class="quick-add-btn"
              :disabled="isProcessing"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12h14"></path>
                <path d="M12 5v14"></path>
              </svg>
              {{ category.name }}
            </button>
            
            <!-- More Templates Dropdown -->
            <div class="dropdown-wrapper">
              <button 
                type="button"
                @click="showMoreTemplates = !showMoreTemplates"
                class="quick-add-btn dropdown-trigger"
                :disabled="isProcessing"
              >
                More
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m6 9 6 6 6-6"></path>
                </svg>
              </button>
              
              <div v-if="showMoreTemplates" class="dropdown-menu">
                <div 
                  v-for="group in categoryGroups"
                  :key="group.name"
                  class="category-group"
                >
                  <div class="group-header">
                    <span class="group-name">{{ group.name }}</span>
                  </div>
                  <button
                    v-for="category in group.categories"
                    :key="category.name"
                    type="button"
                    @click="addQuickCategory(category.name, category.description); showMoreTemplates = false"
                    class="dropdown-item"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M5 12h14"></path>
                      <path d="M12 5v14"></path>
                    </svg>
                    {{ category.name }}
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Categories Header -->
          <div class="categories-header">
            <span class="categories-count">Categories ({{ categories.length }}/50)</span>
            <div class="view-toggle">
              <button 
                type="button"
                @click="viewMode = 'table'"
                :class="['toggle-btn', { active: viewMode === 'table' }]"
                title="Table view"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect width="18" height="18" x="3" y="3" rx="2"></rect>
                  <path d="M3 9h18"></path>
                  <path d="M3 15h18"></path>
                  <path d="M9 3v18"></path>
                  <path d="M15 3v18"></path>
                </svg>
              </button>
              <button 
                type="button"
                @click="viewMode = 'code'"
                :class="['toggle-btn', { active: viewMode === 'code' }]"
                title="Code view"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m18 16 4-4-4-4"></path>
                  <path d="m6 8-4 4 4 4"></path>
                  <path d="m14.5 4-5 16"></path>
                </svg>
              </button>
            </div>
          </div>
          
          <!-- Categories Table -->
          <div v-if="viewMode === 'table'" class="categories-table">
            <div class="table-header">
              <div class="header-cell name-col">Category Name</div>
              <div class="header-cell desc-col">Description (optional)</div>
              <div class="header-cell action-col"></div>
            </div>
            
            <div class="table-body">
              <div 
                v-for="(category, index) in categories" 
                :key="index"
                class="table-row"
              >
                <div class="table-cell name-col">
                  <input 
                    v-model="category.name"
                    type="text"
                    class="category-input"
                    placeholder="e.g., Introduction"
                    maxlength="200"
                    :disabled="isProcessing"
                  />
                </div>
                <div class="table-cell desc-col">
                  <input 
                    v-model="category.description"
                    type="text"
                    class="category-input"
                    placeholder="e.g., Pages containing financial tables"
                    maxlength="2000"
                    :disabled="isProcessing"
                  />
                </div>
                <div class="table-cell action-col">
                  <button 
                    type="button"
                    @click="removeCategory(index)"
                    class="delete-btn"
                    :disabled="isProcessing"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M3 6h18"></path>
                      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                    </svg>
                  </button>
                </div>
              </div>
              
              <div class="table-row add-row">
                <div class="table-cell" style="grid-column: 1 / -1;">
                  <button 
                    type="button"
                    @click="addCategory"
                    :disabled="categories.length >= 50 || isProcessing"
                    class="add-category-btn"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M5 12h14"></path>
                      <path d="M12 5v14"></path>
                    </svg>
                    Add Category
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Code View -->
          <div v-else class="code-view">
            <pre>{{ JSON.stringify(categories, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Result Tab Content -->
    <div v-if="props.activeTab === 'result'">
      <!-- Error Display -->
      <div v-if="props.selectedFile && splitResult && !splitResult.success" class="panel-content">
        <div class="error-display">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="error-icon">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <h3 class="error-title">Processing Failed</h3>
          <p class="error-text">{{ splitResult.error || 'An unknown error occurred' }}</p>
        </div>
      </div>
      
      <!-- Success Display -->
      <div v-else-if="props.selectedFile && splitResult && splitResult.success" class="panel-content">
        <!-- Document Type Mode Results -->
        <div v-if="isDocumentTypeMode" class="split-results-container">
          <div 
            v-for="(dtResult, index) in documentTypeResults" 
            :key="index"
            class="category-result-card doc-type-result-card"
          >
            <div class="category-header">
              <h4 class="category-name">{{ dtResult.typeName }}</h4>
              <span class="page-count-badge">{{ dtResult.pageCount }} {{ dtResult.pageCount === 1 ? 'page' : 'pages' }}</span>
            </div>
            <div class="doc-type-page-range">{{ dtResult.formattedPageRange }}</div>
            <div v-if="dtResult.confidence != null" class="confidence-badge-wrapper">
              <span class="confidence-badge" :class="getConfidenceClass(dtResult.confidence)">
                {{ getConfidenceLabel(dtResult.confidence) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Section Mode Results -->
        <div v-else class="split-results-container">
          <div 
            v-for="(result, index) in splitResults" 
            :key="index"
            class="category-result-card"
          >
            <!-- Category Header -->
            <div class="category-header">
              <h4 class="category-name">{{ result.category }}</h4>
              <span class="page-count-badge">{{ result.pageCount }} {{ result.pageCount === 1 ? 'page' : 'pages' }}</span>
            </div>
            
            <!-- Confidence Badge (if available) -->
            <div v-if="result.confidence" class="confidence-badge-wrapper">
              <span class="confidence-badge" :class="getConfidenceClass(result.confidence)">
                {{ getConfidenceLabel(result.confidence) }}
              </span>
            </div>
            
            <!-- Page Content with Citations -->
            <div class="page-content-list">
              <div 
                v-for="page in result.pages" 
                :key="page.pageNumber"
                class="page-content-item"
              >
                <div class="page-citation">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path>
                    <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
                  </svg>
                  <span class="page-number">Page {{ page.pageNumber }}</span>
                  <span v-if="page.confidence" class="page-confidence">({{ (page.confidence * 100).toFixed(0) }}% confidence)</span>
                </div>
                <div class="page-content-preview">
                  {{ getContentPreview(page.content) }}
                </div>
                <button 
                  v-if="page.content && page.content.length > 200"
                  @click="toggleContentExpansion(result.category, page.pageNumber)"
                  class="expand-btn"
                >
                  {{ isContentExpanded(result.category, page.pageNumber) ? 'Show less' : 'Show more' }}
                </button>
                <div v-if="isContentExpanded(result.category, page.pageNumber)" class="page-content-full">
                  {{ page.content }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Placeholder -->
      <div v-else class="result-placeholder">
        <p>Results will appear here after processing</p>
      </div>
    </div>
    
    <!-- Footer -->
    <div class="panel-footer">
      <button
        v-if="isProcessing"
        class="cancel-btn"
        @click="handleCancel"
      >
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
        Cancel
      </button>
      <button
        @click="handleProcess"
        :disabled="isProcessing || !canProcess"
        class="process-btn"
      >
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ isProcessing ? 'Processing...' : 'Process' }}
      </button>
    </div>
    
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { getTopChunkCategories, getRemainingChunkCategoryGroups } from '~/utils/chunkCategories'
import type { ChunkCategory } from '~/utils/chunkCategories'
import { formatPageRanges } from '~/utils/formatPageRanges'
import ModelSelector from './ModelSelector.vue'

interface Provider {
  id: string
  name: string
  type: string
  configured: boolean
  models: { model_id: string; name: string; provider: string }[]
}

interface Props {
  availableModels: string[]
  providers?: Provider[]
  isProcessing: boolean
  canProcess: boolean
  activeTab: string
  selectedFile?: File | null
  splitResult?: any
  fieldErrors?: Record<string, string> | null
}

interface Emits {
  (e: 'process', config: { 
    categories: Category[]
    allowUncategorized: boolean
    parserTier: string
    splitterTier: string
    splitMode: string
    parserModelId?: string
    splitterModelId?: string
  }): void
  (e: 'update:activeTab', value: string): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const errorMessage = ref('')
const viewMode = ref<'table' | 'code'>('table')
const showMoreTemplates = ref(false)
const allowUncategorized = ref(false)
const splitMode = ref<'sections' | 'document_type'>('sections')
const selectedParserModelId = ref('')
const selectedSplitterModelId = ref('')

interface Category {
  name: string
  description: string
}

const categories = ref<Category[]>([
  { name: 'default', description: '' }
])

// Get top 5 categories for quick-add buttons
const topCategories = getTopChunkCategories(5)

// Get remaining categories grouped for dropdown
const categoryGroups = getRemainingChunkCategoryGroups(5)

interface PageInfo {
  pageNumber: number
  content: string
  confidence?: number
  thumbnailUrl?: string
}

interface SplitResult {
  fileName?: string
  category: string
  pageCount: number
  pages: PageInfo[]
  confidence?: number
}

interface DocumentTypeDisplayResult {
  typeName: string
  pageNumbers: number[]
  pageCount: number
  formattedPageRange: string
  confidence?: number
}

const expandedContent = ref<Set<string>>(new Set())

const documentTypeResults = computed<DocumentTypeDisplayResult[]>(() => {
  if (!splitResult.value || !splitResult.value.success) return []
  if (!splitResult.value.document_types || !Array.isArray(splitResult.value.document_types)) return []
  
  return splitResult.value.document_types.map((dt: any) => ({
    typeName: dt.type_name,
    pageNumbers: dt.page_numbers,
    pageCount: dt.page_numbers.length,
    formattedPageRange: formatPageRanges(dt.page_numbers),
    confidence: dt.confidence ?? undefined
  }))
})

const isDocumentTypeMode = computed(() => {
  return splitResult.value?.document_types && Array.isArray(splitResult.value.document_types) && splitResult.value.document_types.length > 0
})

const splitResults = computed<SplitResult[]>(() => {
  console.log('[SplitConfigPanel] splitResults computed - splitResult.value:', splitResult.value)
  
  if (!splitResult.value) {
    console.log('[SplitConfigPanel] No splitResult.value')
    return []
  }
  
  // Handle error case
  if (!splitResult.value.success) {
    console.log('[SplitConfigPanel] Split failed:', splitResult.value.error)
    return []
  }
  
  console.log('[SplitConfigPanel] Processing successful split result')
  console.log('[SplitConfigPanel] chunks:', splitResult.value.chunks)
  console.log('[SplitConfigPanel] unknown_chunks:', splitResult.value.unknown_chunks)
  
  // Group chunks by category
  const categoryMap = new Map<string, { chunks: any[], confidence: number }>()
  
  // Process regular chunks
  if (splitResult.value.chunks && Array.isArray(splitResult.value.chunks)) {
    console.log('[SplitConfigPanel] Processing', splitResult.value.chunks.length, 'chunks')
    splitResult.value.chunks.forEach((chunk: any) => {
      const category = chunk.category
      if (!categoryMap.has(category)) {
        categoryMap.set(category, { chunks: [], confidence: 0 })
      }
      const categoryData = categoryMap.get(category)!
      categoryData.chunks.push(chunk)
      // Track average confidence
      if (chunk.confidence !== null && chunk.confidence !== undefined) {
        categoryData.confidence = (categoryData.confidence + chunk.confidence) / 2
      }
    })
  }
  
  // Process unknown chunks if they exist
  if (splitResult.value.unknown_chunks && Array.isArray(splitResult.value.unknown_chunks) && splitResult.value.unknown_chunks.length > 0) {
    console.log('[SplitConfigPanel] Processing', splitResult.value.unknown_chunks.length, 'unknown chunks')
    const unknownChunks = splitResult.value.unknown_chunks
    categoryMap.set('Unknown', { chunks: unknownChunks, confidence: 0 })
  }
  
  console.log('[SplitConfigPanel] categoryMap size:', categoryMap.size)
  
  // Convert to display format
  const results: SplitResult[] = []
  categoryMap.forEach((data, category) => {
    const pages = data.chunks.map((chunk: any) => ({
      pageNumber: chunk.page_number,
      content: chunk.content || '',
      confidence: chunk.confidence,
      thumbnailUrl: undefined
    }))
    
    results.push({
      category,
      pageCount: data.chunks.length,
      pages,
      confidence: data.confidence > 0 ? data.confidence : undefined
    })
  })
  
  console.log('[SplitConfigPanel] Returning', results.length, 'category results:', results)
  return results
})

// Get content preview (first 200 characters)
const getContentPreview = (content: string) => {
  if (!content) return 'No content available'
  return content.length > 200 ? content.substring(0, 200) + '...' : content
}

// Toggle content expansion
const toggleContentExpansion = (category: string, pageNumber: number) => {
  const key = `${category}-${pageNumber}`
  if (expandedContent.value.has(key)) {
    expandedContent.value.delete(key)
  } else {
    expandedContent.value.add(key)
  }
}

// Check if content is expanded
const isContentExpanded = (category: string, pageNumber: number) => {
  const key = `${category}-${pageNumber}`
  return expandedContent.value.has(key)
}

// Get confidence class based on confidence level
const getConfidenceClass = (confidence: number) => {
  if (confidence >= 0.8) return 'high-confidence'
  if (confidence >= 0.5) return 'medium-confidence'
  return 'low-confidence'
}

// Get confidence label
const getConfidenceLabel = (confidence: number) => {
  if (confidence >= 0.8) return 'High confidence'
  if (confidence >= 0.5) return 'Medium confidence'
  return 'Low confidence'
}

const addCategory = () => {
  if (categories.value.length < 50) {
    categories.value.push({ name: '', description: '' })
  }
}

const removeCategory = (index: number) => {
  if (categories.value.length > 1) {
    categories.value.splice(index, 1)
  }
}

const addQuickCategory = (name: string, description: string) => {
  const exists = categories.value.some(cat => cat.name.toLowerCase() === name.toLowerCase())
  if (!exists && categories.value.length < 50) {
    const lastCategory = categories.value[categories.value.length - 1]
    if (lastCategory && lastCategory.name === '' && lastCategory.description === '') {
      lastCategory.name = name
      lastCategory.description = description
    } else {
      categories.value.push({ name, description })
    }
  }
}

const splitResult = computed(() => props.splitResult)

const handleProcess = () => {
  console.log('[SplitConfigPanel] handleProcess called')
  console.log('[SplitConfigPanel] categories:', categories.value)
  console.log('[SplitConfigPanel] isProcessing:', props.isProcessing)
  console.log('[SplitConfigPanel] canProcess:', props.canProcess)
  
  errorMessage.value = ''
  
  const validCategories = categories.value.filter(cat => cat.name.trim() !== '')
  
  console.log('[SplitConfigPanel] validCategories:', validCategories)
  
  if (validCategories.length === 0) {
    errorMessage.value = 'Please add at least one category'
    console.log('[SplitConfigPanel] Error: No valid categories')
    return
  }
  
  // Add order field to each category based on array index
  const categoriesWithOrder = validCategories.map((cat, index) => ({
    name: cat.name,
    description: cat.description || '',
    order: index
  }))
  
  const config = {
    categories: categoriesWithOrder,
    allowUncategorized: allowUncategorized.value,
    parserTier: 'Normal',
    splitterTier: 'Normal',
    splitMode: splitMode.value,
    parserModelId: selectedParserModelId.value || undefined,
    splitterModelId: selectedSplitterModelId.value || undefined,
  }
  
  console.log('[SplitConfigPanel] Emitting process event with config:', config)
  emit('process', config)
}

const handleCancel = () => {
  emit('cancel')
}

onMounted(() => {
  const handleClickOutside = (event: MouseEvent) => {
    const target = event.target as HTMLElement
    const dropdown = target.closest('.dropdown-wrapper')
    if (!dropdown && showMoreTemplates.value) {
      showMoreTemplates.value = false
    }
  }
  
  document.addEventListener('click', handleClickOutside)
  
  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
  })
})
</script>

<style scoped>
.split-config-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
}

.panel-content {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: white;
  min-height: 0;
}

/* Config Card */
.config-card {
  background: white;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  padding: 1rem;
}

.card-header {
  margin-bottom: 0.75rem;
}

.card-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.25rem 0;
}

.card-description {
  font-size: 0.8125rem;
  color: #6b7280;
  margin: 0;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

/* Quick Add Section */
.quick-add-section {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.quick-add-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-right: 0.5rem;
}

.quick-add-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s;
}

.quick-add-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}

.quick-add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quick-add-btn svg {
  width: 14px;
  height: 14px;
}

/* Dropdown */
.dropdown-wrapper {
  position: relative;
}

.dropdown-trigger {
  gap: 0.5rem;
  background: #FF6F3C;
  color: white;
  border-color: #FF6F3C;
}

.dropdown-trigger:hover:not(:disabled) {
  background: #E55A2B;
  border-color: #E55A2B;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0;
  z-index: 50;
  min-width: 16rem;
  max-height: 28rem;
  overflow-y: auto;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  padding: 0.5rem;
}

.category-group {
  margin-bottom: 0.5rem;
}

.category-group:last-child {
  margin-bottom: 0;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 0.25rem;
}

.group-name {
  flex: 1;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.75rem 0.5rem 0.5rem;
  font-size: 0.875rem;
  color: #374151;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: #f3f4f6;
}

.dropdown-item svg {
  width: 14px;
  height: 14px;
  color: #9ca3af;
  flex-shrink: 0;
}

/* Categories Header */
.categories-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.5rem;
}

.categories-count {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.view-toggle {
  display: flex;
  gap: 0.25rem;
  background: #f3f4f6;
  padding: 0.25rem;
  border-radius: 0.375rem;
  border: 1px solid #e5e7eb;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem;
  background: transparent;
  border: none;
  border-radius: 0.25rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.toggle-btn:hover {
  color: #374151;
}

.toggle-btn.active {
  background: white;
  color: #111827;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.toggle-btn svg {
  width: 14px;
  height: 14px;
}

/* Categories Table */
.categories-table {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  overflow: hidden;
}

.table-header {
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.header-cell {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.table-body {
  background: white;
}

.table-row {
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f3f4f6;
  align-items: center;
}

.table-row:last-child {
  border-bottom: none;
}

.table-row:hover:not(.add-row) {
  background: #f9fafb;
}

.table-cell {
  display: flex;
  align-items: center;
}

.category-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: #111827;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  transition: all 0.15s;
}

.category-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.category-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.category-input::placeholder {
  color: #9ca3af;
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.delete-btn:hover:not(:disabled) {
  background: #fef2f2;
  color: #dc2626;
}

.delete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-category-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s;
}

.add-category-btn:hover:not(:disabled) {
  background: #f3f4f6;
}

.add-category-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Code View */
.code-view {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1rem;
  overflow-x: auto;
}

.code-view pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  color: #374151;
}

/* Strategy Option */
.strategy-option {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

/* Split Mode Toggle */
.split-mode-toggle {
  display: flex;
  background: #f3f4f6;
  padding: 0.25rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  gap: 0.25rem;
}

.split-mode-toggle.disabled {
  opacity: 0.5;
}

.split-mode-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #6b7280;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.split-mode-btn:hover:not(:disabled):not(.active) {
  color: #374151;
}

.split-mode-btn.active {
  background: white;
  color: #111827;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.split-mode-btn:disabled {
  cursor: not-allowed;
}

.option-content {
  flex: 1;
}

.option-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: #111827;
  margin-bottom: 0.25rem;
}

.option-description {
  font-size: 0.875rem;
  color: #6b7280;
}

/* Switch */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #e5e7eb;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

input:checked + .slider {
  background-color: #FF6F3C;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Split Results */
.split-results-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.category-result-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  background: white;
  padding: 1rem;
  flex-shrink: 0;
  box-shadow: none;
}

.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0.75rem;
}

.category-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.page-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: 1px solid #e5e7eb;
  padding: 0 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  width: fit-content;
  white-space: nowrap;
  flex-shrink: 0;
  color: #374151;
}

.confidence-badge-wrapper {
  position: relative;
  top: -0.5rem;
  left: 0.5rem;
  z-index: 10;
}

.confidence-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: 1px solid transparent;
  padding: 0 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  width: fit-content;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s;
}

.confidence-badge.high-confidence {
  background: rgba(34, 197, 94, 0.1);
  color: #16a34a;
}

.confidence-badge.medium-confidence {
  background: rgba(251, 191, 36, 0.1);
  color: #d97706;
}

.confidence-badge.low-confidence {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.page-thumbnails-container {
  overflow-x: auto;
}

.page-thumbnails-scroll {
  display: flex;
  gap: 1rem;
}

/* Page Content List */
.page-content-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.page-content-item {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1rem;
  background: #f9fafb;
}

.page-citation {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  color: #6b7280;
  font-size: 0.875rem;
  font-weight: 500;
}

.page-citation svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.page-number {
  color: #111827;
}

.page-confidence {
  color: #6b7280;
  font-weight: 400;
}

.page-content-preview {
  font-size: 0.875rem;
  line-height: 1.5;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
}

.page-content-full {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e5e7eb;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.expand-btn {
  margin-top: 0.5rem;
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #FF6F3C;
  background: white;
  border: 1px solid #FF6F3C;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s;
}

.expand-btn:hover {
  background: #FF6F3C;
  color: white;
}

.page-thumbnail-card {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  background: white;
  padding: 1.5rem;
  width: 10rem;
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: none;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.page-thumbnail-card:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.page-thumbnail-wrapper {
  display: flex;
  flex-direction: column;
}

.page-thumbnail-aspect {
  aspect-ratio: 8.5 / 11;
  background: #f3f4f6;
  border-radius: 0.25rem;
  overflow: hidden;
}

.page-thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}

.page-thumbnail-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  padding: 0.5rem;
}

.page-number-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: #111827;
}

.result-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #9ca3af;
}

/* Footer */
.panel-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  background: white;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  flex-shrink: 0;
  margin-top: auto;
}

.cancel-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #dc2626;
  background: white;
  border: 1px solid #dc2626;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.15s;
}

.cancel-btn:hover {
  background: #dc2626;
  color: white;
}

.process-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: white;
  background: #FF6F3C;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.15s;
}

.process-btn:hover:not(:disabled) {
  background: #E55A2B;
}

.process-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  margin: 0 1.5rem 1rem;
  padding: 0.75rem;
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  flex-shrink: 0;
}

.error-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
}

.error-icon {
  color: #dc2626;
  margin-bottom: 1rem;
}

.error-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.5rem 0;
}

.error-text {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
}

/* Document Type Result Cards */
.doc-type-result-card {
  gap: 0.5rem;
}

.doc-type-page-range {
  font-size: 0.8125rem;
  color: #6b7280;
  padding: 0 0.25rem;
}
</style>
