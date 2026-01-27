<template>
  <div class="config-panel">
    <h3>OCR Configuration</h3>
    
    <div class="config-section">
      <label class="config-label">Model</label>
      <select v-model="selectedModel" class="config-select" :disabled="isProcessing">
        <option v-for="model in availableModels" :key="model" :value="model">
          {{ model }}
        </option>
      </select>
    </div>
    
    <div class="config-section">
      <label class="config-label">Processing Tier</label>
      <select v-model="selectedTier" class="config-select" :disabled="isProcessing">
        <option value="Rapid">Rapid</option>
        <option value="Normal">Normal</option>
        <option value="Advance">Advance</option>
      </select>
    </div>
    
    <div class="config-section">
      <label class="config-checkbox">
        <input
          type="checkbox"
          v-model="processAllPages"
          :disabled="isProcessing"
        />
        <span>Process all PDF pages</span>
      </label>
    </div>
    
    <button
      @click="handleProcess"
      :disabled="isProcessing || !canProcess"
      class="process-button"
    >
      <svg v-if="isProcessing" class="spinner" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span v-if="isProcessing">Processing...</span>
      <span v-else>Process OCR</span>
    </button>
    
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  availableModels: string[]
  isProcessing: boolean
  canProcess: boolean
}

interface Emits {
  (e: 'process', config: { modelId: string, tier: string, processAllPages: boolean }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const selectedModel = ref(props.availableModels[0] || 'lightonocr-2-1b')
const selectedTier = ref('Normal')
const processAllPages = ref(false)
const errorMessage = ref('')

// Watch for available models changes
watch(() => props.availableModels, (newModels) => {
  if (newModels.length > 0 && !newModels.includes(selectedModel.value)) {
    selectedModel.value = newModels[0]
  }
})

const handleProcess = () => {
  errorMessage.value = ''
  
  if (!selectedModel.value) {
    errorMessage.value = 'Please select a model'
    return
  }
  
  emit('process', {
    modelId: selectedModel.value,
    tier: selectedTier.value,
    processAllPages: processAllPages.value
  })
}
</script>

<style scoped>
.config-panel {
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.config-panel h3 {
  margin: 0 0 1.5rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #2d3748;
}

.config-section {
  margin-bottom: 1.25rem;
}

.config-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #4a5568;
}

.config-select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e0;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #2d3748;
  background-color: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.config-select:hover:not(:disabled) {
  border-color: #4299e1;
}

.config-select:focus {
  outline: none;
  border-color: #4299e1;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}

.config-select:disabled {
  background-color: #f7fafc;
  cursor: not-allowed;
  opacity: 0.6;
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

.process-button {
  width: 100%;
  padding: 0.75rem 1.5rem;
  background-color: #4299e1;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1.5rem;
}

.process-button:hover:not(:disabled) {
  background-color: #3182ce;
}

.process-button:disabled {
  background-color: #a0aec0;
  cursor: not-allowed;
}

.spinner {
  width: 1.25rem;
  height: 1.25rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #fed7d7;
  color: #c53030;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}
</style>
