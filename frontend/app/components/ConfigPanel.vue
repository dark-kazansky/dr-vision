<template>
  <div class="config-panel">
    <!-- Build Tab Content -->
    <div v-if="props.activeTab === 'build'" class="panel-content">
    
    <!-- Parser Tiers Section -->
    <TierSelector
      v-model="selectedParserTier"
      label="Parser Tiers"
      :disabled="isProcessing"
    />
    
    <!-- Extractor Tiers Section -->
    <TierSelector
      v-model="selectedExtractorTier"
      label="Extractor Tiers"
      :disabled="isProcessing"
    />
    
    <div class="config-section">
      <label class="config-checkbox">
        <input
          type="checkbox"
          v-model="processAllPages"
          :disabled="isProcessing"
        />
        <span>Process all PDF Pages</span>
      </label>
      
      <label class="config-checkbox">
        <input
          type="checkbox"
          v-model="processAllFiles"
          :disabled="isProcessing"
        />
        <span>Process all PDF Files</span>
      </label>
    </div>
    
    <!-- Extraction Configuration Section -->
    <div class="config-section extraction-section">
      <div class="section-divider"></div>
      <h4 class="section-title">Structured Data Extraction</h4>
      
      <label class="config-checkbox">
        <input
          type="checkbox"
          v-model="extractionEnabled"
          :disabled="isProcessing"
        />
        <span>Enable extraction</span>
      </label>
      
      <!-- Show extraction UI when enabled -->
      <div v-if="extractionEnabled" class="extraction-config">
        <ExtractionTargetSelector
          v-model="extractionTarget"
          :disabled="isProcessing"
        />
        
        <SchemaBuilder
          v-model="extractionSchema"
          :disabled="isProcessing"
          :selected-file="props.selectedFile"
          @validation-change="handleSchemaValidation"
        />
      </div>
    </div>
    </div>

    <!-- Result Tab Content -->
    <div v-if="props.activeTab === 'result'">
      <!-- Only show content if there's a selected file and extraction result -->
      <div v-if="props.selectedFile && extractionResult" class="panel-content">
        <!-- Toggle Button for Visual/Code -->
        <div class="view-toggle-group">
          <button
            @click="resultViewMode = 'visual'"
            :class="{ active: resultViewMode === 'visual' }"
            class="view-toggle-btn"
            type="button"
            title="Visual View"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="toggle-icon">
              <path d="M12 3v18"></path>
              <rect width="18" height="18" x="3" y="3" rx="2"></rect>
              <path d="M3 9h18"></path>
              <path d="M3 15h18"></path>
            </svg>
          </button>
          <button
            @click="resultViewMode = 'code'"
            :class="{ active: resultViewMode === 'code' }"
            class="view-toggle-btn"
            type="button"
            title="Code View"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="toggle-icon">
              <path d="m18 16 4-4-4-4"></path>
              <path d="m6 8-4 4 4 4"></path>
              <path d="m14.5 4-5 16"></path>
            </svg>
          </button>
        </div>
      
      <!-- Result Display -->
      <div v-if="!extractionResult" class="result-placeholder">
        <p>Results will appear here after processing</p>
      </div>
      <div v-else class="result-display">
        <!-- Visual Mode -->
        <div v-if="resultViewMode === 'visual'" class="visual-result">
          <div v-html="formattedVisualResult"></div>
        </div>
        
        <!-- Code Mode (JSON) -->
        <div v-else class="code-result">
          <!-- Error Summary (if errors exist) -->
          <div v-if="fieldErrors && Object.keys(fieldErrors).length > 0" class="error-summary">
            <div class="error-summary-header">
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>Field Extraction Errors ({{ Object.keys(fieldErrors).length }})</span>
            </div>
            <div class="error-list">
              <div v-for="(error, field) in fieldErrors" :key="field" class="error-item">
                <strong>{{ field }}:</strong> {{ error }}
              </div>
            </div>
          </div>
          
          <pre><code v-html="highlightedJsonResult"></code></pre>
        </div>
      </div>
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
        :disabled="isProcessing || !canProcess || !isConfigValid"
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
    
    <!-- Helper message when extraction is enabled but schema is empty -->
    <div v-if="extractionEnabled && !isSchemaValid && extractionSchema.length === 0" class="info-message">
      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      Add at least one field to the schema or use "Auto Generate" to enable processing
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ExtractionConfig, ExtractionTarget, SchemaField } from '~/types/extraction'
import ExtractionTargetSelector from './ExtractionTargetSelector.vue'
import SchemaBuilder from './SchemaBuilder.vue'
import TierSelector from './TierSelector.vue'

interface Props {
  availableModels: string[]
  isProcessing: boolean
  canProcess: boolean
  activeTab: string
  selectedFile?: File | null
  extractionResult?: any
  fieldErrors?: Record<string, string> | null
}

interface Emits {
  (e: 'process', config: { 
    modelId: string
    tier: string
    processAllPages: boolean
    processAllFiles: boolean
    extractionConfig?: ExtractionConfig
  }): void
  (e: 'update:activeTab', value: string): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Use tier config composable
const { getParserModel, getExtractorModel } = useTierConfig()

const selectedParserTier = ref('Normal')
const selectedExtractorTier = ref('Normal')
const processAllPages = ref(false)
const processAllFiles = ref(false)
const errorMessage = ref('')
const resultViewMode = ref<'visual' | 'code'>('visual')

// Use props for extraction result and field errors
const extractionResult = computed(() => props.extractionResult)
const fieldErrors = computed(() => props.fieldErrors || null)

// Extraction configuration state
const extractionEnabled = ref(true)
const extractionTarget = ref<ExtractionTarget>('document')
const extractionSchema = ref<SchemaField[]>([])
const isSchemaValid = ref(false)

// Handle schema validation changes from SchemaBuilder
// SchemaBuilder emits validation-change event with isValid boolean
// - isValid is true when: no validation errors AND at least one field exists
// - isValid is false when: validation errors exist OR schema is empty
const handleSchemaValidation = (isValid: boolean) => {
  isSchemaValid.value = isValid
}

// Computed property to check if config is valid
// This determines whether the Process button should be enabled
const isConfigValid = computed(() => {
  // If extraction is disabled, config is always valid
  if (!extractionEnabled.value) {
    return true
  }
  
  // If extraction is enabled, schema must be valid
  // (no duplicate names, no empty names, at least one field)
  return isSchemaValid.value
})

// Format extraction result for visual display (human-readable HTML)
const formattedVisualResult = computed(() => {
  if (!extractionResult.value) return ''
  
  const result = extractionResult.value
  let html = '<div class="extraction-visual">'
  
  // Handle different result structures
  if (Array.isArray(result)) {
    // List of results (for page or table row extraction)
    result.forEach((item, index) => {
      html += `<div class="result-item">`
      html += `<h4>Item ${index + 1}</h4>`
      html += formatObject(item)
      html += `</div>`
    })
  } else if (typeof result === 'object') {
    // Single result (for document extraction)
    html += formatObject(result)
  } else {
    // Fallback for primitive values
    html += `<p>${result}</p>`
  }
  
  html += '</div>'
  return html
})

// Helper function to format numbers with thousand separators (.)
function formatNumber(num: number): string {
  // Convert to string and split by decimal point
  const parts = num.toString().split('.')
  // Add thousand separators to integer part
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  // Join back with decimal point if exists
  return parts.join(',')
}

// Helper function to format object as HTML
function formatObject(obj: any, level = 0): string {
  let html = '<div class="object-content">'
  
  for (const [key, value] of Object.entries(obj)) {
    const hasError = fieldErrors.value && fieldErrors.value[key]
    const errorClass = hasError ? ' field-error' : ''
    
    html += `<div class="field-row${errorClass}" style="margin-left: ${level * 1.5}rem;">`
    html += `<span class="field-key">${key}:</span> `
    
    if (value === null || value === undefined) {
      html += `<span class="field-value null">null</span>`
    } else if (Array.isArray(value)) {
      html += `<span class="field-value array">[${value.length} items]</span>`
      html += '<div class="array-items">'
      value.forEach((item, idx) => {
        if (typeof item === 'object') {
          html += `<div class="array-item"><strong>Item ${idx + 1}:</strong></div>`
          html += formatObject(item, level + 1)
        } else {
          html += `<div class="array-item" style="margin-left: ${(level + 1) * 1.5}rem;">${item}</div>`
        }
      })
      html += '</div>'
    } else if (typeof value === 'object') {
      html += '<span class="field-value object">{object}</span>'
      html += formatObject(value, level + 1)
    } else if (typeof value === 'boolean') {
      html += `<span class="field-value boolean">${value}</span>`
    } else if (typeof value === 'number') {
      html += `<span class="field-value number">${formatNumber(value)}</span>`
    } else {
      html += `<span class="field-value string">${value}</span>`
    }
    
    // Add error message if field has an error
    if (hasError) {
      html += `<div class="field-error-message">
        <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>${fieldErrors.value![key]}</span>
      </div>`
    }
    
    html += `</div>`
  }
  
  html += '</div>'
  return html
}

// Format extraction result as JSON with syntax highlighting
const formattedJsonResult = computed(() => {
  if (!extractionResult.value) return ''
  return JSON.stringify(extractionResult.value, null, 2)
})

// Apply syntax highlighting to JSON
const highlightedJsonResult = computed(() => {
  if (!formattedJsonResult.value) return ''
  
  return formattedJsonResult.value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Highlight keys
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")\s*:/g, '<span class="json-key">$1</span>:')
    // Highlight string values
    .replace(/:\s*("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")/g, ': <span class="json-string">$1</span>')
    // Highlight numbers
    .replace(/:\s*(-?\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
    // Highlight booleans
    .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
    // Highlight null
    .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>')
})

const handleProcess = () => {
  errorMessage.value = ''
  
  // Get parser model from parser tier using composable
  const parserModel = getParserModel(selectedParserTier.value)
  
  // Get extractor model from extractor tier using composable
  const extractorModel = getExtractorModel(selectedExtractorTier.value)
  
  if (!parserModel) {
    errorMessage.value = 'Please select a parser tier'
    return
  }
  
  if (!extractorModel) {
    errorMessage.value = 'Please select an extractor tier'
    return
  }
  
  // Validate extraction config if enabled
  if (extractionEnabled.value && !isSchemaValid.value) {
    errorMessage.value = 'Please fix validation errors in the extraction schema'
    return
  }
  
  // Build extraction config if enabled
  const extractionConfig: ExtractionConfig | undefined = extractionEnabled.value
    ? {
        enabled: true,
        target: extractionTarget.value,
        schema: extractionSchema.value
      }
    : undefined
  
  emit('process', {
    modelId: parserModel,
    tier: selectedParserTier.value,
    extractorModel: extractorModel,
    extractorTier: selectedExtractorTier.value,
    processAllPages: processAllPages.value,
    processAllFiles: processAllFiles.value,
    extractionConfig
  })
}

const handleCancel = () => {
  // Emit cancel event to parent component
  emit('cancel')
}
</script>

<style scoped>
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

/* Extraction Section Styles */
.extraction-section {
  margin-top: 1.5rem;
}

.section-divider {
  height: 1px;
  background-color: #e2e8f0;
  margin-bottom: 1.5rem;
}

.section-title {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #2d3748;
}

.extraction-config {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #ffffff;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
  width: 100%;
  box-sizing: border-box;
}

/* View Toggle Styles */
.view-toggle-group {
  display: flex;
  border-radius: 0.25rem;
  border: 1px solid #e5e7eb;
  background-color: #f9fafb;
  padding: 0.075rem;
  margin-bottom: 1rem;
  width: fit-content;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.3rem;
  background-color: transparent;
  color: #6b7280;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.15rem;
}

.view-toggle-btn:hover {
  background-color: #e5e7eb;
  color: #4b5563;
}

.view-toggle-btn.active {
  background-color: #ffffff;
  color: #111827;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.toggle-icon {
  width: 0.75rem;
  height: 0.75rem;
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
  color: #60a5fa; /* Light blue for keys */
  font-weight: 500;
}

.code-result :deep(.json-string) {
  color: #34d399; /* Green for strings */
}

.code-result :deep(.json-number) {
  color: #fbbf24; /* Amber for numbers */
}

.code-result :deep(.json-boolean) {
  color: #a78bfa; /* Purple for booleans */
  font-weight: 500;
}

.code-result :deep(.json-null) {
  color: #9ca3af; /* Gray for null */
  font-style: italic;
}
</style>

.info-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 0.375rem;
  color: #1e40af;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.info-message svg {
  flex-shrink: 0;
}
