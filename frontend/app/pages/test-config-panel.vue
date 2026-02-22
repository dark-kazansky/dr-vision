<template>
  <div class="test-page">
    <div class="test-header">
      <h1>ConfigPanel Integration Test</h1>
      <p>This page demonstrates the integrated extraction configuration in ConfigPanel</p>
    </div>

    <div class="test-content">
      <div class="panel-container">
        <ConfigPanel
          :available-models="availableModels"
          :is-processing="isProcessing"
          :can-process="canProcess"
          @process="handleProcess"
        />
      </div>

      <div class="output-container">
        <h2>Process Event Output</h2>
        <div v-if="lastProcessConfig" class="output-box">
          <pre>{{ JSON.stringify(lastProcessConfig, null, 2) }}</pre>
        </div>
        <div v-else class="output-placeholder">
          <p>Click "Process OCR" to see the emitted configuration</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import ConfigPanel from '~/components/ConfigPanel.vue'
import type { ExtractionConfig } from '~/types/extraction'

// Test data
const availableModels = ref(['assistant', 'gemini-3-flash', 'gemini-3-pro', 'qwen3-max', 'claude-opus-4.5'])
const isProcessing = ref(false)
const canProcess = ref(true)
const lastProcessConfig = ref<any>(null)

// Handler for process event
const handleProcess = (config: {
  modelId: string
  tier: string
  processAllPages: boolean
  extractionConfig?: ExtractionConfig
}) => {
  console.log('Process event received:', config)
  lastProcessConfig.value = config

  // Simulate processing
  isProcessing.value = true
  setTimeout(() => {
    isProcessing.value = false
  }, 2000)
}
</script>

<style scoped>
.test-page {
  min-height: 100vh;
  background-color: #f7fafc;
  padding: 2rem;
}

.test-header {
  max-width: 1200px;
  margin: 0 auto 2rem;
}

.test-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.test-header p {
  font-size: 1rem;
  color: #718096;
}

.test-content {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.panel-container {
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.output-container {
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.output-container h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 1rem;
}

.output-box {
  background-color: #1a202c;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 0.375rem;
  overflow-x: auto;
}

.output-box pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
}

.output-placeholder {
  padding: 2rem;
  text-align: center;
  color: #718096;
  border: 2px dashed #cbd5e0;
  border-radius: 0.375rem;
}

@media (max-width: 768px) {
  .test-content {
    grid-template-columns: 1fr;
  }
}
</style>
