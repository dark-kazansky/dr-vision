<template>
  <div class="config-panel">
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
    
    <!-- Classifier Model Selector -->
    <ModelSelector
      v-if="props.providers && props.providers.length > 0"
      v-model="selectedClassifierModelId"
      :providers="props.providers"
      :disabled="isProcessing"
      label="Classifier Model"
    />
    
    <!-- Parsing Configuration Section (merged with Classification Rules) -->
    <div class="parsing-config-card" role="settings-group" style="margin-top: 24px;">
      <div class="card-header">
        <div class="card-title">Parsing Configuration</div>
      </div>
      <div class="card-content">
        <div class="config-sections">
          <div class="max-pages-section">
            <div class="field-group">
              <div class="field-wrapper">
                <div class="field-container">
                  <div class="field-label-row">
                    <label for="parsing_configuration.max_pages" class="field-label">
                      <span class="label-text">Max pages</span>
                    </label>
                    <div class="help-icon" data-state="closed" data-slot="tooltip-trigger" title="Define number of used pages to classify">
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-help">
                        <circle cx="12" cy="12" r="10"></circle>
                        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                        <path d="M12 17h.01"></path>
                      </svg>
                      <div class="help-tooltip">
                        Define number of used pages to classify
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <input 
                class="number-input" 
                id="parsing_configuration.max_pages" 
                v-model.number="maxPages"
                min="1" 
                max="1000" 
                placeholder="5" 
                type="number" 
                name="parsing_configuration.max_pages"
                :disabled="isProcessing"
              />
            </div>
          </div>
          
          <!-- Process All Files Section -->
          <div class="process-all-section">
            <div class="checkbox-row">
              <label class="checkbox-container">
                <input 
                  type="checkbox" 
                  id="process_all_files"
                  v-model="processAllFiles"
                  :disabled="isProcessing"
                  class="checkbox-input"
                />
                <span class="checkbox-custom"></span>
              </label>
              <label for="process_all_files" class="checkbox-label">
                <span class="label-text">Process all files</span>
              </label>
              <div class="help-icon" data-state="closed" data-slot="tooltip-trigger" title="Process all uploaded files at once">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-help">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                  <path d="M12 17h.01"></path>
                </svg>
                <div class="help-tooltip">
                  Process all uploaded files at once
                </div>
              </div>
            </div>
          </div>
          
          <!-- Classification Rules Section -->
          <div class="classification-rules-section">
            <div class="section-header">
              <div class="section-title">Classification Rules</div>
            </div>
            
            <!-- Quick Add Buttons -->
            <div class="quick-add-container">
              <div class="quick-add-label-wrapper">
                <div class="quick-add-label-container">
                  <div class="quick-add-label-inner">
                    <div class="quick-add-label-row">
                      <label class="quick-add-label">
                        <span class="label-text">Quick add</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
              <!-- Top 5 Quick Add Buttons -->
              <button 
                v-for="docType in topDocumentTypes"
                :key="docType.type"
                type="button" 
                @click="addQuickRule(docType.type, docType.description)"
                class="quick-add-btn"
                :disabled="isProcessing"
                :title="docType.description"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="plus-icon">
                  <path d="M5 12h14"></path>
                  <path d="M12 5v14"></path>
                </svg>
                <span>{{ docType.type }}</span>
              </button>
              
              <!-- More Dropdown -->
              <div class="dropdown-wrapper">
                <button 
                  type="button"
                  @click="showMoreTemplates = !showMoreTemplates"
                  class="quick-add-btn dropdown-btn"
                  :disabled="isProcessing"
                >
                  <span>More</span>
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="chevron-icon">
                    <path d="m6 9 6 6 6-6"></path>
                  </svg>
                </button>
                
                <!-- Dropdown Menu -->
                <div v-if="showMoreTemplates" class="dropdown-menu">
                  <div 
                    v-for="group in remainingDocumentTypeGroups"
                    :key="group.name"
                    class="category-group"
                  >
                    <div class="group-header">
                      <span class="group-name">{{ group.name }}</span>
                    </div>
                    <button
                      v-for="docType in group.categories"
                      :key="docType.type"
                      type="button"
                      @click="addQuickRule(docType.type, docType.description); showMoreTemplates = false"
                      class="dropdown-item"
                      :title="docType.description"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="plus-icon">
                        <path d="M5 12h14"></path>
                        <path d="M12 5v14"></path>
                      </svg>
                      <span>{{ docType.type }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Rules Table Header -->
            <div class="rules-header">
              <div class="rules-counter-wrapper">
                <div class="rules-counter-container">
                  <div class="rules-counter-row">
                    <label class="rules-counter-label">
                      <span class="label-text">Rules ({{ classificationRules.length }}/20)</span>
                    </label>
                  </div>
                </div>
              </div>
              <div class="view-toggle-wrapper">
                <div class="view-toggle-group">
                  <button 
                    type="button" 
                    @click="viewMode = 'table'"
                    :class="viewMode === 'table' ? 'view-toggle-btn active' : 'view-toggle-btn'"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="toggle-icon">
                      <path d="M12 3v18"></path>
                      <rect width="18" height="18" x="3" y="3" rx="2"></rect>
                      <path d="M3 9h18"></path>
                      <path d="M3 15h18"></path>
                    </svg>
                  </button>
                  <button 
                    type="button"
                    @click="viewMode = 'code'"
                    :class="viewMode === 'code' ? 'view-toggle-btn active' : 'view-toggle-btn'"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="toggle-icon">
                      <path d="m18 16 4-4-4-4"></path>
                      <path d="m6 8-4 4 4 4"></path>
                      <path d="m14.5 4-5 16"></path>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Rules Table -->
            <div v-if="viewMode === 'table'" class="rules-table-container">
              <div class="table-wrapper">
                <table class="rules-table">
                  <thead class="table-header">
                    <tr class="header-row">
                      <th class="header-cell" style="width: 37.5%;">
                        <div>Document Type</div>
                      </th>
                      <th class="header-cell" style="width: 57.5%;">
                        <div>Description</div>
                      </th>
                      <th class="header-cell" style="width: 5%;">
                        <div></div>
                      </th>
                    </tr>
                  </thead>
                  <tbody class="table-body">
                    <tr 
                      v-for="(rule, index) in classificationRules" 
                      :key="index"
                      class="table-row"
                    >
                      <td class="table-cell" style="width: 37.5%;">
                        <div>
                          <textarea 
                            v-model="rule.type"
                            class="textarea-input"
                            placeholder="e.g., invoice"
                            maxlength="200"
                            style="height: 34px !important;"
                            :disabled="isProcessing"
                          ></textarea>
                        </div>
                      </td>
                      <td class="table-cell" style="width: 57.5%;">
                        <div>
                          <textarea 
                            v-model="rule.description"
                            class="textarea-input"
                            placeholder="e.g., Contains itemized charges, tax info, and payment terms"
                            maxlength="2000"
                            style="height: 34px !important;"
                            :disabled="isProcessing"
                          ></textarea>
                        </div>
                      </td>
                      <td class="table-cell" style="width: 5%; padding: 0.5rem 0.25rem;">
                        <div>
                          <button 
                            type="button"
                            @click="removeRule(index)"
                            class="remove-btn"
                            aria-label="Remove rule"
                            :disabled="isProcessing"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="trash-icon">
                              <path d="M3 6h18"></path>
                              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                              <line x1="10" x2="10" y1="11" y2="17"></line>
                              <line x1="14" x2="14" y1="11" y2="17"></line>
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                    <tr class="add-row">
                      <td class="table-cell" colspan="3">
                        <div>
                          <button 
                            type="button"
                            @click="addRule"
                            :disabled="classificationRules.length >= 20 || isProcessing"
                            class="add-rule-btn"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="plus-icon">
                              <path d="M5 12h14"></path>
                              <path d="M12 5v14"></path>
                            </svg>
                            <span>Add rule</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            
            <!-- Code View -->
            <div v-else class="code-view-container">
              <pre class="code-pre">{{ JSON.stringify(classificationRules, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>

    <!-- Result Tab Content -->
    <div v-if="props.activeTab === 'result'">
      <!-- Show content if there's extraction result (with or without selected file for batch processing) -->
      <div v-if="extractionResult" class="panel-content">
        <!-- View Toggle (List/Grouped) -->
        <div class="space-y-4 p-6">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <div class="flex items-center rounded-lg border bg-gray-50 p-1">
                <button 
                  type="button"
                  @click="resultViewMode = 'list'"
                  :class="resultViewMode === 'list' ? 'result-view-btn active' : 'result-view-btn'"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-list h-3 w-3">
                    <path d="M3 12h.01"></path>
                    <path d="M3 18h.01"></path>
                    <path d="M3 6h.01"></path>
                    <path d="M8 12h13"></path>
                    <path d="M8 18h13"></path>
                    <path d="M8 6h13"></path>
                  </svg>
                  <span>List</span>
                </button>
                <button 
                  type="button"
                  @click="resultViewMode = 'grouped'"
                  :class="resultViewMode === 'grouped' ? 'result-view-btn active' : 'result-view-btn'"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-grid3x3 h-3 w-3">
                    <rect width="18" height="18" x="3" y="3" rx="2"></rect>
                    <path d="M3 9h18"></path>
                    <path d="M3 15h18"></path>
                    <path d="M9 3v18"></path>
                    <path d="M15 3v18"></path>
                  </svg>
                  <span>Grouped</span>
                </button>
              </div>
            </div>
          </div>
          
          <!-- Results List -->
          <div v-if="resultViewMode === 'list'" class="space-y-3">
            <div 
              v-for="(result, index) in classificationResults" 
              :key="index"
              class="result-card"
            >
              <div class="result-card-content">
                <!-- File Header -->
                <div class="result-header">
                  <div class="file-info">
                    <div class="file-icon">
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-file-text">
                        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path>
                        <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
                        <path d="M10 9H8"></path>
                        <path d="M16 13H8"></path>
                        <path d="M16 17H8"></path>
                      </svg>
                    </div>
                    <div class="file-details">
                      <h3 class="file-name">{{ result.fileName || props.selectedFile?.name || 'Document ' + (index + 1) }}</h3>
                    </div>
                  </div>
                </div>
                
                <!-- Classification Result -->
                <div class="classification-info">
                  <div class="classification-header">
                    <div class="classification-badges">
                      <span class="document-type-badge">{{ result.documentType }}</span>
                      <div class="confidence-badge" :class="getConfidenceClass(result.confidence)">
                        {{ Math.round(result.confidence * 100) }}%
                      </div>
                    </div>
                  </div>
                  
                  <!-- Reasoning Section -->
                  <div v-if="result.reasoning" class="reasoning-section">
                    <span class="reasoning-label">Reasoning</span>
                    <div class="reasoning-content">
                      <p>{{ getReasoningPreview(result.reasoning, index) }}</p>
                      <button 
                        v-if="result.reasoning.length > 150"
                        type="button"
                        @click="toggleReasoning(index)"
                        class="show-more-btn"
                      >
                        <span>{{ expandedReasoning[index] ? 'Show less' : 'Show more' }}</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Grouped Results -->
          <div v-else class="space-y-4">
            <div 
              v-for="(results, groupName) in groupedResults"
              :key="groupName"
              class="grouped-section"
            >
              <!-- Group Header -->
              <button
                type="button"
                @click="toggleGroup(groupName)"
                class="group-header"
              >
                <div class="group-header-content">
                  <div class="group-title-wrapper">
                    <span class="group-title">{{ groupName }}</span>
                  </div>
                  <div class="group-count-badge">
                    {{ results.length }}
                  </div>
                </div>
                <div class="group-chevron">
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    width="24" 
                    height="24" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    stroke-width="2" 
                    stroke-linecap="round" 
                    stroke-linejoin="round"
                    :class="expandedGroups[groupName] ? 'rotate-180' : ''"
                  >
                    <path d="m6 9 6 6 6-6"></path>
                  </svg>
                </div>
              </button>
              
              <!-- Group Content -->
              <div v-if="expandedGroups[groupName]" class="group-content">
                <div 
                  v-for="(result, index) in results"
                  :key="index"
                  class="result-card"
                >
                  <div class="result-card-content">
                    <!-- File Header -->
                    <div class="result-header">
                      <div class="file-info">
                        <div class="file-icon">
                          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-file-text">
                            <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path>
                            <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
                            <path d="M10 9H8"></path>
                            <path d="M16 13H8"></path>
                            <path d="M16 17H8"></path>
                          </svg>
                        </div>
                        <div class="file-details">
                          <h3 class="file-name">{{ result.fileName || props.selectedFile?.name }}</h3>
                        </div>
                      </div>
                    </div>
                    
                    <!-- Classification Result -->
                    <div class="classification-info">
                      <div class="classification-header">
                        <div class="classification-badges">
                          <div class="confidence-badge" :class="getConfidenceClass(result.confidence)">
                            {{ Math.round(result.confidence * 100) }}%
                          </div>
                        </div>
                      </div>
                      
                      <!-- Reasoning Section -->
                      <div v-if="result.reasoning" class="reasoning-section">
                        <span class="reasoning-label">Reasoning</span>
                        <div class="reasoning-content">
                          <p>{{ getReasoningPreview(result.reasoning, index) }}</p>
                          <button 
                            v-if="result.reasoning.length > 150"
                            type="button"
                            @click="toggleReasoning(index)"
                            class="show-more-btn"
                          >
                            <span>{{ expandedReasoning[index] ? 'Show less' : 'Show more' }}</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Empty State -->
      <div v-else class="result-placeholder">
        <p>Results will appear here after processing</p>
      </div>
    </div>
    
    <!-- Config Panel Footer -->
    <div class="config-panel-footer">
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
        class="run-parse-btn"
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
import ModelSelector from './ModelSelector.vue'
import { documentTypes, getTopDocumentTypes, getRemainingDocumentTypeGroups } from '~/utils/documentTypes'
import type { DocumentType } from '~/utils/documentTypes'

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
  extractionResult?: any
  fieldErrors?: Record<string, string> | null
}

interface Emits {
  (e: 'process', config: { 
    parserModelId: string
    classifierModelId: string
    tier: string
    maxPages: number
    classificationRules: ClassificationRule[]
    isMultimodal: boolean
    processAllFiles: boolean
  }): void
  (e: 'update:activeTab', value: string): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const selectedParserModelId = ref('')
const selectedClassifierModelId = ref('')
const maxPages = ref(5)
const processAllFiles = ref(false)
const errorMessage = ref('')
const resultViewMode = ref<'list' | 'grouped'>('list')
const viewMode = ref<'table' | 'code'>('table')
const showMoreTemplates = ref(false)
const expandedReasoning = ref<Record<number, boolean>>({})
const expandedGroups = ref<Record<string, boolean>>({})

// Get top 5 and remaining document types
const topDocumentTypes = getTopDocumentTypes(5)
const remainingDocumentTypeGroups = getRemainingDocumentTypeGroups(5)

// Classification rules state
interface ClassificationRule {
  type: string
  description: string
}

const classificationRules = ref<ClassificationRule[]>([
  { type: '', description: '' }
])

// Classification result interface
interface ClassificationResult {
  fileName?: string
  documentType: string
  confidence: number
  reasoning?: string
}

// Parse classification results from extractionResult
const classificationResults = computed<ClassificationResult[]>(() => {
  if (!extractionResult.value) return []
  
  // Handle different result formats
  if (Array.isArray(extractionResult.value)) {
    return extractionResult.value
  } else if (typeof extractionResult.value === 'object') {
    return [extractionResult.value]
  }
  
  return []
})

// Group results by document type for grouped view
const groupedResults = computed(() => {
  const groups: Record<string, ClassificationResult[]> = {}
  
  classificationResults.value.forEach(result => {
    const type = result.documentType || 'unknown'
    if (!groups[type]) {
      groups[type] = []
    }
    groups[type].push(result)
  })
  
  return groups
})

// Get confidence badge class based on confidence level
const getConfidenceClass = (confidence: number) => {
  if (confidence >= 0.8) return 'confidence-high'
  if (confidence >= 0.5) return 'confidence-medium'
  return 'confidence-low'
}

// Get reasoning preview (truncated or full)
const getReasoningPreview = (reasoning: string, index: number) => {
  if (!reasoning) return ''
  if (expandedReasoning.value[index] || reasoning.length <= 150) {
    return reasoning
  }
  return reasoning.substring(0, 150) + '...'
}

// Toggle reasoning expansion
const toggleReasoning = (index: number) => {
  expandedReasoning.value[index] = !expandedReasoning.value[index]
}

// Toggle group expansion
const toggleGroup = (groupName: string) => {
  expandedGroups.value[groupName] = !expandedGroups.value[groupName]
}

// Add a new empty rule
const addRule = () => {
  if (classificationRules.value.length < 20) {
    classificationRules.value.push({ type: '', description: '' })
  }
}

// Remove a rule by index
const removeRule = (index: number) => {
  if (classificationRules.value.length > 1) {
    classificationRules.value.splice(index, 1)
  }
}

// Add a quick rule with predefined values
const addQuickRule = (type: string, description: string) => {
  // Check if rule already exists
  const exists = classificationRules.value.some(rule => rule.type.toLowerCase() === type.toLowerCase())
  if (!exists && classificationRules.value.length < 20) {
    // If there's an empty rule at the end, replace it
    const lastRule = classificationRules.value[classificationRules.value.length - 1]
    if (lastRule.type === '' && lastRule.description === '') {
      lastRule.type = type
      lastRule.description = description
    } else {
      classificationRules.value.push({ type, description })
    }
  }
}

// Use props for extraction result and field errors
const extractionResult = computed(() => props.extractionResult)
const fieldErrors = computed(() => props.fieldErrors || null)

const handleProcess = () => {
  errorMessage.value = ''
  
  if (!selectedParserModelId.value) {
    errorMessage.value = 'Please select a parser model'
    return
  }
  
  if (!selectedClassifierModelId.value) {
    errorMessage.value = 'Please select a classifier model'
    return
  }
  
  // Validate maxPages
  if (maxPages.value < 1 || maxPages.value > 1000) {
    errorMessage.value = 'Max pages must be between 1 and 1000'
    return
  }
  
  // Get classification rules - if none are defined, use all document types
  let validRules = classificationRules.value.filter(rule => rule.type.trim() !== '')
  
  // If no rules are manually added, use all document types from the list
  if (validRules.length === 0) {
    validRules = documentTypes.map(docType => ({
      type: docType.type,
      description: docType.description
    }))
  }
  
  emit('process', {
    parserModelId: selectedParserModelId.value,
    classifierModelId: selectedClassifierModelId.value,
    tier: 'Normal',
    maxPages: maxPages.value,
    classificationRules: validRules,
    isMultimodal: false,
    processAllFiles: processAllFiles.value,
  })
}

const handleCancel = () => {
  emit('cancel')
}

// Close dropdown when clicking outside
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
/* Card Structure */
.parsing-config-card {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
  background-color: #ffffff;
  padding: 1.5rem;
  color: #0f172a;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1;
  color: #0f172a;
}

.card-description {
  font-size: 0.875rem;
  color: #64748b;
}

.card-content {
  display: flex;
  flex-direction: column;
}

.config-sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Max Pages Section */
.max-pages-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-wrapper,
.field-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.field-container {
  gap: 0.25rem;
}

.field-label-row {
  display: flex;
  min-height: 1.25rem;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
}

.field-label {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 500;
}

.label-text {
  color: #0f172a;
}

.help-icon {
  display: flex;
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  color: #64748b;
  position: relative;
}

.help-icon:hover {
  color: #0f172a;
}

.help-icon svg {
  width: 100%;
  height: 100%;
}

.help-tooltip {
  position: absolute;
  bottom: calc(100% + 0.5rem);
  left: 50%;
  transform: translateX(-50%);
  min-width: 200px;
  max-width: 300px;
  padding: 0.75rem;
  background-color: #1f2937;
  color: white;
  border-radius: 0.375rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  font-size: 0.75rem;
  line-height: 1.5;
  z-index: 50;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s, visibility 0.2s;
  pointer-events: none;
  white-space: normal;
  text-align: center;
}

.help-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 0.375rem solid transparent;
  border-top-color: #1f2937;
}

.help-icon:hover .help-tooltip {
  opacity: 1;
  visibility: visible;
}

.number-input {
  display: flex;
  height: 2.25rem;
  width: 100%;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
  background-color: #ffffff;
  padding: 0.25rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.number-input::placeholder {
  color: #64748b;
}

.number-input:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}

.number-input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* Process All Files Section */
.process-all-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.checkbox-label .label-text {
  color: #0f172a;
}

.checkbox-container {
  display: flex;
  align-items: center;
  cursor: pointer;
  position: relative;
}

.checkbox-input {
  position: absolute;
  opacity: 0;
  cursor: pointer;
  height: 0;
  width: 0;
}

.checkbox-custom {
  display: flex;
  height: 1.25rem;
  width: 1.25rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  border: 1px solid #cbd5e1;
  background-color: #ffffff;
  transition: all 0.2s;
}

.checkbox-input:checked + .checkbox-custom {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

.checkbox-input:checked + .checkbox-custom::after {
  content: '';
  display: block;
  width: 0.375rem;
  height: 0.625rem;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
  margin-bottom: 0.125rem;
}

.checkbox-input:focus + .checkbox-custom {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}

.checkbox-input:disabled + .checkbox-custom {
  cursor: not-allowed;
  opacity: 0.5;
  background-color: #f1f5f9;
}

/* Classification Rules Section */
.classification-rules-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1;
  color: #0f172a;
}

.section-description {
  font-size: 0.875rem;
  color: #64748b;
}

/* Quick Add Buttons */
.quick-add-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.quick-add-label-wrapper,
.quick-add-label-container,
.quick-add-label-inner {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.quick-add-label-container {
  gap: 0.25rem;
}

.quick-add-label-row {
  display: flex;
  min-height: 1.25rem;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
}

.quick-add-label {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 500;
}

.quick-add-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
  flex-shrink: 0;
  outline: none;
  border: 1px solid #e2e8f0;
  background-color: #ffffff;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  height: 2rem;
  border-radius: 0.375rem;
  gap: 0.375rem;
  padding: 0 0.5rem;
}

.quick-add-btn:hover:not(:disabled) {
  background-color: #f1f5f9;
}

.quick-add-btn:disabled {
  pointer-events: none;
  opacity: 0.5;
}

.plus-icon {
  height: 0.5rem;
  width: 0.5rem;
}

/* Dropdown Styles */
.dropdown-wrapper {
  position: relative;
}

.dropdown-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  background-color: #FF6F3C;
  color: white;
  border-color: #FF6F3C;
}

.dropdown-btn:hover:not(:disabled) {
  background-color: #E55A2B;
  border-color: #E55A2B;
}

.chevron-icon {
  height: 0.875rem;
  width: 0.875rem;
  transition: transform 0.2s;
}

.dropdown-btn:hover .chevron-icon {
  transform: translateY(2px);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0;
  z-index: 50;
  min-width: 16rem;
  max-height: 28rem;
  overflow-y: auto;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
  background-color: #ffffff;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
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
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  border-radius: 0.25rem;
  padding: 0.5rem 0.75rem 0.5rem 0.5rem;
  padding-left: 0.5rem;
  font-size: 0.875rem;
  font-weight: 400;
  text-align: left;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
  color: #0f172a;
}

.dropdown-item:hover {
  background-color: #f1f5f9;
}

.dropdown-item .plus-icon {
  height: 0.75rem;
  width: 0.75rem;
  flex-shrink: 0;
  color: #9ca3af;
}

/* Rules Header */
.rules-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rules-counter-wrapper,
.rules-counter-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.rules-counter-container {
  gap: 0.25rem;
}

.rules-counter-row {
  display: flex;
  min-height: 1.25rem;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
}

.rules-counter-label {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  font-size: 0.875rem;
  font-weight: 500;
}

.view-toggle-wrapper {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.view-toggle-group {
  display: flex;
  border-radius: 0.375rem;
  border: 1px solid #e5e7eb;
  background-color: #f9fafb;
  padding: 0.125rem;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  border-radius: 0.25rem;
  padding: 0.375rem;
  transition: all 0.2s;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #6b7280;
}

.view-toggle-btn:hover {
  color: #374151;
}

.view-toggle-btn.active {
  background-color: #ffffff;
  color: #111827;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.toggle-icon {
  width: 0.875rem;
  height: 0.875rem;
}

/* Rules Table */
.rules-table-container {
  border-radius: 0.375rem;
  border: 1px solid #e5e7eb;
}

.table-wrapper {
  position: relative;
  width: 100%;
  overflow: auto;
}

.rules-table {
  width: 100%;
  font-size: 0.875rem;
}

.table-header tr {
  border-bottom: 1px solid #e5e7eb;
}

.table-header tr:hover {
  background: transparent;
}

.header-row {
  border-bottom: 1px solid #e5e7eb;
  transition: all 0.2s;
}

.header-cell {
  height: 2.5rem;
  padding: 0 0.5rem;
  vertical-align: middle;
  font-weight: 500;
  color: #0f172a;
  text-align: left;
}

.table-body tr:last-child {
  border-bottom: none;
}

.table-row {
  border-bottom: 1px solid #e5e7eb;
  transition: all 0.2s;
}

.table-row:hover {
  background-color: rgba(241, 245, 249, 0.5);
}

.add-row {
  border-bottom: 1px solid #e5e7eb;
  transition: all 0.2s;
}

.table-cell {
  padding: 0.5rem;
  vertical-align: middle;
  text-align: left;
  font-weight: normal;
}

.text-input {
  display: flex;
  height: 2.25rem;
  width: 100%;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
  background-color: #ffffff;
  padding: 0.25rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
}

.text-input::placeholder {
  color: #64748b;
}

.text-input:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}

.text-input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.textarea-input {
  display: flex;
  width: 100%;
  resize: none;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
  background-color: #ffffff;
  padding: 0.4rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1.5;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
  overflow-y: auto;
}

.textarea-input::placeholder {
  color: #64748b;
}

.textarea-input:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}

.textarea-input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.remove-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  white-space: nowrap;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
  flex-shrink: 0;
  outline: none;
  background: transparent;
  border: none;
  cursor: pointer;
  width: 2.25rem;
  height: 2.25rem;
}

.remove-btn:hover:not(:disabled) {
  background-color: #f1f5f9;
}

.remove-btn:disabled {
  pointer-events: none;
  opacity: 0.5;
}

.trash-icon {
  width: 1rem;
  height: 1rem;
}

.add-rule-btn {
  display: inline-flex;
  align-items: center;
  justify-center: center;
  white-space: nowrap;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
  flex-shrink: 0;
  outline: none;
  background: transparent;
  border: none;
  cursor: pointer;
  height: 2.25rem;
  padding: 0.5rem 0.75rem;
  gap: 0.375rem;
}

.add-rule-btn:hover:not(:disabled) {
  background-color: #f1f5f9;
}

.add-rule-btn:disabled {
  pointer-events: none;
  opacity: 0.5;
}

/* Code View */
.code-view-container {
  border-radius: 0.375rem;
  border: 1px solid #e5e7eb;
  background-color: #f9fafb;
  padding: 1rem;
}

.code-pre {
  font-size: 0.75rem;
  overflow: auto;
  margin: 0;
  font-family: 'Courier New', monospace;
}

/* Tailwind-like utility classes */
.bg-card {
  background-color: #ffffff;
}

.text-card-foreground {
  color: #0f172a;
}

.text-muted-foreground {
  color: #64748b;
}

.text-foreground {
  color: #0f172a;
}

.border {
  border: 1px solid #e2e8f0;
}

.border-input {
  border-color: #e2e8f0;
}

.bg-background {
  background-color: #ffffff;
}

.shadow-xs {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.space-y-4 > * + * {
  margin-top: 1rem;
}

.gap-1 {
  gap: 0.25rem;
}

.gap-1\.5 {
  gap: 0.375rem;
}

.gap-2 {
  gap: 0.5rem;
}

.gap-3 {
  gap: 0.75rem;
}

.gap-4 {
  gap: 1rem;
}

.gap-6 {
  gap: 1.5rem;
}

.bg-accent {
  background-color: #f1f5f9;
}

.text-accent-foreground {
  color: #0f172a;
}

.hover\:bg-accent:hover {
  background-color: #f1f5f9;
}

.hover\:text-accent-foreground:hover {
  color: #0f172a;
}

.focus-visible\:ring-ring\/50:focus-visible {
  --tw-ring-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 0 0 3px var(--tw-ring-color);
}

.focus-visible\:border-ring:focus-visible {
  border-color: #3b82f6;
}

.hover\:bg-muted\/50:hover {
  background-color: rgba(241, 245, 249, 0.5);
}

.panel-content {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
}

.result-placeholder {
  text-align: center;
  color: var(--text-tertiary, #9ca3af);
  padding: 3rem 1.25rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.result-placeholder p {
  font-size: 0.875rem;
  color: var(--text-secondary, #6b7280);
}

.config-panel {
  --accent-orange: #FF6F3C;
  background: white;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
  max-height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  width: 100%;
}

.config-panel h3 {
  margin: 0 0 1.5rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #2d3748;
}

/* Tier Selector Styles - Copied from TierSelector.vue */
.config-section {
  margin-bottom: 1.25rem;
  width: 100%;
  box-sizing: border-box;
}

.config-header {
  margin-bottom: 0.75rem;
}

.config-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #4a5568;
}

.tier-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}

.tier-bars {
  display: flex;
  gap: 3px;
  height: 0.5rem;
}

.tier-bar {
  flex: 1;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.tier-bar:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.tier-bar.rapid {
  background: #FFB399;
}

.tier-bar.normal {
  background: #FF8C5A;
}

.tier-bar.advance {
  background: #FF6F3C;
}

.tier-bar.multimodal {
  background: #E55A2B;
}

.tier-bar:hover:not(:disabled) {
  opacity: 0.8;
}

.tier-labels {
  display: flex;
  gap: 3px;
  margin-top: 0.25rem;
}

.tier-label-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.5rem;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
  color: #6b7280;
}

.tier-label-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.tier-label-btn.active {
  color: #111827;
  font-weight: 600;
}

.tier-indicator {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: transparent;
  transition: all 0.15s;
}

.tier-label-btn.active .tier-indicator {
  background-color: var(--accent-orange, #FF6F3C);
}

.tier-label-text {
  font-weight: inherit;
}

.config-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.config-checkbox input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
}

.config-checkbox input[type="checkbox"]:disabled {
  cursor: not-allowed;
}

.config-checkbox span {
  font-size: 0.875rem;
  color: #4a5568;
}

/* Config Panel Footer */
.config-panel-footer {
  padding: 0.5rem 0;
  margin-top: auto;
  border-top: 1px solid #e2e8f0;
  background-color: white;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.75rem;
  position: sticky;
  bottom: 0;
  z-index: 10;
}

.run-parse-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 0.5rem;
  background-color: var(--accent-orange, #FF6F3C);
  color: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.run-parse-btn:hover:not(:disabled) {
  background-color: #E55A2B;
}

.run-parse-btn:disabled {
  background-color: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.cancel-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border: 1px solid #dc2626;
  border-radius: 0.5rem;
  background-color: white;
  color: #dc2626;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.cancel-btn:hover {
  background-color: #dc2626;
  color: white;
}

.cancel-btn:active {
  background-color: #b91c1c;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #fed7d7;
  color: #c53030;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

/* Result Toggle Styles */
.result-view-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s;
  padding: 0.5rem 0.5rem;
  gap: 0.375rem;
  border-radius: 0.375rem;
  background-color: transparent;
  color: #6b7280;
  border: none;
  cursor: pointer;
  outline: none;
}

.result-view-btn:hover {
  background-color: #f1f5f9;
  color: #111827;
}

.result-view-btn.active {
  background-color: var(--accent-orange, #FF6F3C);
  color: white;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.result-view-btn svg {
  flex-shrink: 0;
}

/* Result Card Styles */
.result-card {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
  background-color: #ffffff;
  padding: 1.5rem;
  color: #0f172a;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
  position: relative;
}

.result-card-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-header {
  display: flex;
  width: 100%;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.file-info {
  display: flex;
  width: 100%;
  flex-direction: column;
  gap: 1rem;
}

.file-icon {
  display: flex;
  width: fit-content;
  align-items: center;
  justify-content: center;
  overflow: clip;
  border-radius: 0.125rem;
  border: 1px solid #e2e8f0;
  background-color: #ffffff;
  padding: 0.5rem;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.file-icon svg {
  width: 0.75rem;
  height: 0.75rem;
  flex-shrink: 0;
  margin-right: 0.5rem;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.file-name {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1;
  color: #0f172a;
}

.classification-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.classification-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.classification-badges {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.5rem;
}

.document-type-badge {
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
  gap: 0.25rem;
  background-color: rgba(255, 111, 60, 0.1);
  color: var(--accent-orange, #FF6F3C);
}

.confidence-badge {
  white-space: nowrap;
  border-radius: 0.375rem;
  border: 1px solid;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.confidence-high {
  color: #16a34a;
  background-color: #f0fdf4;
  border-color: #bbf7d0;
}

.confidence-medium {
  color: #ca8a04;
  background-color: #fefce8;
  border-color: #fde047;
}

.confidence-low {
  color: #dc2626;
  background-color: #fef2f2;
  border-color: #fecaca;
}

.reasoning-section {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.reasoning-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: #0f172a;
}

.reasoning-content {
  font-size: 0.75rem;
  color: #4b5563;
  line-height: 1.5;
}

.reasoning-content p {
  margin: 0;
}

.show-more-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s;
  padding: 0.5rem 0.5rem;
  gap: 0.375rem;
  border-radius: 0.375rem;
  background: transparent;
  border: none;
  cursor: pointer;
  outline: none;
  color: var(--accent-orange, #FF6F3C);
  margin-top: 0.25rem;
}

.show-more-btn:hover {
  background-color: rgba(255, 111, 60, 0.1);
}

/* Grouped View Styles */
.grouped-section {
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  overflow: hidden;
}

.group-header {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background-color: #ffffff;
  border: none;
  cursor: pointer;
  transition: background-color 0.15s;
  text-align: left;
}

.group-header:hover {
  background-color: #f9fafb;
}

.group-header-content {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 0.75rem;
}

.group-title-wrapper {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: 0.5rem;
}

.group-title {
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.25rem;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-count-badge {
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
  background-color: #f1f5f9;
  color: #64748b;
}

.group-chevron {
  display: flex;
  flex-shrink: 0;
}

.group-chevron svg {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  color: #9ca3af;
  transition: transform 0.2s;
}

.group-content {
  padding: 0 1rem 1rem 1rem;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Result Toggle Styles (old - keeping for compatibility) */
.result-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 0.25rem;
  background-color: #f3f4f6;
  border-radius: 0.5rem;
  width: fit-content;
}

.toggle-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.375rem;
  background-color: transparent;
  color: #6b7280;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.toggle-btn:hover {
  color: #111827;
}

.toggle-btn.active {
  background-color: white;
  color: #111827;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

/* Result Display Styles */
.result-display {
  flex: 1;
  overflow-y: auto;
}

.visual-result {
  padding: 1rem;
  background-color: white;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  line-height: 1.6;
}

.extraction-visual {
  color: #111827;
}

.result-item {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.result-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.result-item h4 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.object-content {
  margin-left: 0;
}

.field-row {
  margin-bottom: 0.5rem;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.field-row.field-error {
  background-color: #fef2f2;
  border-left: 3px solid #dc2626;
  padding: 0.5rem;
  margin-left: -0.5rem;
  border-radius: 0.25rem;
}

.field-error-message {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: 100%;
  margin-top: 0.25rem;
  padding: 0.375rem 0.5rem;
  background-color: #fee2e2;
  border-radius: 0.25rem;
  color: #991b1b;
  font-size: 0.8125rem;
  line-height: 1.4;
}

.field-error-message svg {
  flex-shrink: 0;
  color: #dc2626;
}

.field-error-message span {
  flex: 1;
}

.field-key {
  font-weight: 600;
  color: #374151;
  min-width: fit-content;
}

.field-value {
  color: #111827;
}

.field-value.null {
  color: #9ca3af;
  font-style: italic;
}

.field-value.boolean {
  color: #7c3aed;
  font-weight: 500;
}

.field-value.number {
  color: #059669;
  font-weight: 500;
}

.field-value.string {
  color: #111827;
}

.field-value.array,
.field-value.object {
  color: #6b7280;
  font-size: 0.8125rem;
  font-weight: 500;
}

.array-items {
  margin-top: 0.5rem;
  margin-left: 1rem;
}

.array-item {
  margin-bottom: 0.5rem;
  color: #4b5563;
}

.code-result {
  background-color: #1f2937;
  border-radius: 0.5rem;
  padding: 1rem;
  overflow-x: auto;
  overflow-y: auto;
  max-height: 600px;
}

.error-summary {
  background-color: #7f1d1d;
  border: 1px solid #991b1b;
  border-radius: 0.375rem;
  padding: 0.75rem;
  margin-bottom: 1rem;
}

.error-summary-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #fecaca;
  font-weight: 600;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.error-summary-header svg {
  color: #fca5a5;
}

.error-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.error-item {
  color: #fecaca;
  font-size: 0.8125rem;
  line-height: 1.5;
  padding-left: 1.5rem;
}

.error-item strong {
  color: #fca5a5;
  font-weight: 600;
}

.code-result pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 0.8125rem;
  line-height: 1.6;
}

.code-result code {
  color: #e5e7eb;
  font-family: 'Courier New', monospace;
}

/* JSON Syntax Highlighting */
.code-result :deep(.json-key) {
  color: #60a5fa;
  font-weight: 500;
}

.code-result :deep(.json-string) {
  color: #34d399;
}

.code-result :deep(.json-number) {
  color: #fbbf24;
}

.code-result :deep(.json-boolean) {
  color: #a78bfa;
  font-weight: 500;
}

.code-result :deep(.json-null) {
  color: #9ca3af;
  font-style: italic;
}
</style>
