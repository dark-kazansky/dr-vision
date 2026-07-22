<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h2 class="modal-title">Help - {{ currentTab }}</h2>
            <button class="modal-close" @click="close">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div class="modal-body">
            <div class="help-content">
              <div v-if="currentTab === 'Parse'" class="help-section">
                <h3>Parse Function</h3>
                <p>The Parse function extracts text content from PDF and image files using OCR technology.</p>
                <ul>
                  <li><strong>Parser Tiers:</strong> Select the OCR quality level (Rapid, Normal, or Advance)</li>
                  <li><strong>Process Options:</strong> Choose to process all pages or all files at once</li>
                  <li><strong>Output:</strong> Extracted text content that can be viewed and edited</li>
                </ul>
              </div>
              
              <div v-if="currentTab === 'Classify'" class="help-section">
                <h3>Classify Function</h3>
                <p>The Classify function automatically categorizes documents based on their content.</p>
                <ul>
                  <li><strong>Parser Tiers:</strong> Select OCR quality for text extraction</li>
                  <li><strong>Classifier Tiers:</strong> Choose classification model (Rapid, Normal, or Advance)</li>
                  <li><strong>Classification Rules:</strong> Define document types and descriptions to guide classification</li>
                  <li><strong>Output:</strong> Document type with confidence score and reasoning</li>
                </ul>
              </div>
              
              <div v-if="currentTab === 'Extract'" class="help-section">
                <h3>Extract Function</h3>
                <p>The Extract function pulls structured data from documents based on custom schemas.</p>
                <ul>
                  <li><strong>Parser Tiers:</strong> Select OCR quality for text extraction</li>
                  <li><strong>Extractor Tiers:</strong> Choose extraction model quality</li>
                  <li><strong>Extraction Target:</strong> Select between Documents, Pages, or Table Mode</li>
                  <li><strong>Schema Builder:</strong> Define fields to extract with auto-generation support</li>
                  <li><strong>Output:</strong> Structured JSON data matching your schema</li>
                </ul>
              </div>
              
              <div v-if="currentTab === 'Split'" class="help-section">
                <h3>Split Function</h3>
                <p>The Split function divides documents into sections based on content categories.</p>
                <ul>
                  <li><strong>Parser Tier:</strong> Select OCR quality for text extraction</li>
                  <li><strong>Splitter Tier:</strong> Choose categorization model quality</li>
                  <li><strong>Categories:</strong> Define content categories with descriptions</li>
                  <li><strong>Uncategorized Pages:</strong> Option to group unmatched pages</li>
                  <li><strong>Output:</strong> Pages grouped by category with confidence scores</li>
                </ul>
              </div>
              
              <div v-if="currentTab === 'Doc Journey'" class="help-section">
                <h3>Doc Journey Function</h3>
                <p>The Doc Journey function creates custom workflows by chaining multiple processing steps.</p>
                <ul>
                  <li><strong>Workflow Builder:</strong> Drag and drop nodes to create processing pipelines</li>
                  <li><strong>Available Nodes:</strong> Parse, Classify, Extract, and Split operations</li>
                  <li><strong>Connections:</strong> Link nodes to define data flow</li>
                  <li><strong>Configuration:</strong> Each node can be configured independently</li>
                  <li><strong>Output:</strong> Combined results from all workflow steps</li>
                </ul>
              </div>
            </div>
          </div>
          
          <div class="modal-footer">
            <button class="btn-secondary" @click="close">Close</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
interface Props {
  isOpen: boolean
  currentTab: string
}

interface Emits {
  (e: 'close'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const close = () => {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(32, 21, 21, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-container {
  background: var(--color-cream);
  border-radius: var(--radius-comfortable);
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid var(--color-sand);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.modal-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-body {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

.help-content {
  color: var(--text-secondary);
}

.help-section h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.75rem 0;
}

.help-section p {
  margin: 0 0 1rem 0;
  line-height: 1.6;
}

.help-section ul {
  margin: 0;
  padding-left: 1.5rem;
  list-style: disc;
}

.help-section li {
  margin-bottom: 0.5rem;
  line-height: 1.6;
}

.help-section li strong {
  color: var(--text-primary);
  font-weight: 600;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid var(--color-sand);
}

.btn-secondary {
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--color-cream);
  border: 1px solid var(--color-sand);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-secondary:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
