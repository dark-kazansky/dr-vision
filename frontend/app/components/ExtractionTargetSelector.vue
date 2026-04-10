<template>
  <div class="extraction-target-selector">
    <label class="config-label">
      Extraction Target
    </label>
    
    <div class="radio-group">
      <label class="radio-option">
        <input
          type="radio"
          name="extraction-target"
          value="document"
          :checked="modelValue === 'document'"
          :disabled="disabled"
          @change="handleChange"
        />
        <span class="radio-label">
          Document
          <span class="help-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-help">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
              <path d="M12 17h.01"></path>
            </svg>
            <div class="help-tooltip">
              {{ tooltips.document }}
            </div>
          </span>
        </span>
      </label>
      
      <label class="radio-option">
        <input
          type="radio"
          name="extraction-target"
          value="page"
          :checked="modelValue === 'page'"
          :disabled="disabled"
          @change="handleChange"
        />
        <span class="radio-label">
          Page
          <span class="help-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-help">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
              <path d="M12 17h.01"></path>
            </svg>
            <div class="help-tooltip">
              {{ tooltips.page }}
            </div>
          </span>
        </span>
      </label>
      
      <label class="radio-option">
        <input
          type="radio"
          name="extraction-target"
          value="table_row"
          :checked="modelValue === 'table_row'"
          :disabled="disabled"
          @change="handleChange"
        />
        <span class="radio-label">
          Table Row
          <span class="help-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-circle-help">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
              <path d="M12 17h.01"></path>
            </svg>
            <div class="help-tooltip">
              {{ tooltips.table_row }}
            </div>
          </span>
        </span>
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ExtractionTarget } from '~/types/extraction'

interface Props {
  modelValue: ExtractionTarget
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', target: ExtractionTarget): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const tooltips = {
  document: 'Extract from the entire document at once (single result)',
  page: 'Extract from each page separately (list of results)',
  table_row: 'Extract from each row of a table structure (list of results)'
}

const handleChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value as ExtractionTarget)
}
</script>

<style scoped>
.extraction-target-selector {
  margin-bottom: 1.25rem;
}

.config-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #4a5568;
}

.help-icon {
  display: inline-flex;
  align-items: center;
  cursor: help;
  color: #718096;
  transition: color 0.2s;
  position: relative;
}

.help-icon:hover {
  color: #4299e1;
}

.help-icon svg {
  width: 1rem;
  height: 1rem;
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

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  user-select: none;
  padding: 0.5rem;
  border-radius: 0.375rem;
  transition: background-color 0.2s;
}

.radio-option:hover:not(:has(input:disabled)) {
  background-color: #f7fafc;
}

.radio-option input[type="radio"] {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
  accent-color: #4299e1;
}

.radio-option input[type="radio"]:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  color: #2d3748;
}

.radio-option:has(input:disabled) .radio-label {
  color: #a0aec0;
  cursor: not-allowed;
}
</style>
