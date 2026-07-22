<template>
  <div class="results-display">
    <div class="results-header">
      <h3>OCR Results</h3>
      <button
        v-if="results && results.success"
        @click="copyToClipboard"
        class="copy-button"
        :class="{ copied: showCopied }"
      >
        <svg v-if="!showCopied" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span>{{ showCopied ? 'Copied!' : 'Copy' }}</span>
      </button>
    </div>
    
    <div v-if="!results" class="empty-results">
      <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p>No results yet</p>
      <p class="empty-subtitle">Process a file to see OCR results</p>
    </div>
    
    <div v-else-if="!results.success" class="error-results">
      <svg class="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <h4>OCR Processing Failed</h4>
      <p class="error-type">{{ results.error_type || 'processing_error' }}</p>
      <p class="error-message">{{ results.error }}</p>
    </div>
    
    <div v-else class="results-content">
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="tab"
          :class="{ active: activeTab === tab.id }"
        >
          {{ tab.label }}
        </button>
      </div>
      
      <div class="tab-content">
        <div v-if="activeTab === 'raw'" class="text-content">
          <pre>{{ results.text }}</pre>
        </div>
        
        <div v-else-if="activeTab === 'build'" class="text-content">
          <div class="build-info">
            <div class="info-item">
              <span class="info-label">Filename:</span>
              <span class="info-value">{{ results.filename }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Model:</span>
              <span class="info-value">{{ results.model }}</span>
            </div>
            <div v-if="results.pages" class="info-item">
              <span class="info-label">Pages:</span>
              <span class="info-value">{{ results.pages }}</span>
            </div>
          </div>
          <pre>{{ results.text }}</pre>
        </div>
        
        <div v-else-if="activeTab === 'parsed'" class="text-content">
          <pre>{{ formatParsed(results.text) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { OCRResult } from '~/composables/useOCR'

interface Props {
  results: OCRResult | null
}

const props = defineProps<Props>()

const activeTab = ref('raw')
const showCopied = ref(false)

const tabs = [
  { id: 'build', label: 'Build' },
  { id: 'raw', label: 'Raw Text' },
  { id: 'parsed', label: 'Parsed Result' }
]

const copyToClipboard = async () => {
  if (!props.results?.text) return
  
  try {
    await navigator.clipboard.writeText(props.results.text)
    showCopied.value = true
    setTimeout(() => {
      showCopied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}

const formatParsed = (text: string | undefined): string => {
  if (!text) return ''
  
  // Simple parsing: split by lines and format
  const lines = text.split('\n')
  return lines
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .join('\n')
}
</script>

<style scoped>
.results-display {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-cream);
  border-radius: 0.5rem;
  overflow: hidden;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--color-sand);
}

.results-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.copy-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: var(--accent-orange);
  color: var(--color-cream);
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.copy-button:hover {
  background-color: #e54700;
}

.copy-button.copied {
  background-color: #48bb78;
}

.copy-button svg {
  width: 1.25rem;
  height: 1.25rem;
}

.empty-results,
.error-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 3rem;
  color: var(--text-tertiary);
}

.empty-icon,
.error-icon {
  width: 4rem;
  height: 4rem;
  margin-bottom: 1rem;
}

.error-icon {
  color: #e53e3e;
}

.empty-results p {
  margin: 0.5rem 0;
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.empty-subtitle {
  font-size: 0.875rem !important;
  color: var(--text-tertiary) !important;
  font-weight: 400 !important;
}

.error-results h4 {
  margin: 0.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #e53e3e;
}

.error-type {
  margin: 0.5rem 0;
  padding: 0.25rem 0.75rem;
  background-color: #fed7d7;
  color: #c53030;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
}

.error-message {
  margin: 1rem 0;
  color: var(--text-secondary);
  text-align: center;
  max-width: 500px;
}

.results-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.tabs {
  display: flex;
  border-bottom: 1px solid var(--color-sand);
  background-color: var(--bg-secondary);
}

.tab {
  flex: 1;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover {
  color: var(--accent-orange);
  background-color: var(--bg-tertiary);
}

.tab.active {
  color: var(--accent-orange);
  border-bottom-color: transparent;
  box-shadow: rgb(255, 79, 0) 0px -4px 0px 0px inset;
  background-color: var(--color-cream);
}

.tab-content {
  flex: 1;
  overflow: auto;
}

.text-content {
  padding: 1.5rem;
}

.text-content pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-wrap: break-word;
}

.build-info {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: var(--bg-secondary);
  border-radius: 0.375rem;
  border-left: 4px solid var(--accent-orange);
}

.info-item {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 80px;
}

.info-value {
  color: var(--text-primary);
}
</style>
