<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click="close">
        <div class="modal-container large" @click.stop>
          <div class="modal-header">
            <h2 class="modal-title">API Deployment - {{ currentTab }}</h2>
            <button class="modal-close" @click="close">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div class="modal-body">
            <div class="deploy-content">
              <!-- Parse API -->
              <div v-if="currentTab === 'Parse'" class="api-section">
                <h3>Parse API Endpoint</h3>
                <p class="api-description">Use this API to extract text from PDF and image files.</p>
                
                <div class="code-block">
                  <div class="code-header">
                    <span>POST</span>
                    <code>{{ baseUrl }}/api/parse</code>
                    <button class="copy-btn" @click="copyToClipboard(parseApiExample)">
                      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      Copy
                    </button>
                  </div>
                  <pre><code>{{ parseApiExample }}</code></pre>
                </div>
              </div>
              
              <!-- Classify API -->
              <div v-if="currentTab === 'Classify'" class="api-section">
                <h3>Classify API Endpoint</h3>
                <p class="api-description">Use this API to classify documents based on your rules.</p>
                
                <div class="code-block">
                  <div class="code-header">
                    <span>POST</span>
                    <code>{{ baseUrl }}/api/classify</code>
                    <button class="copy-btn" @click="copyToClipboard(classifyApiExample)">
                      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      Copy
                    </button>
                  </div>
                  <pre><code>{{ classifyApiExample }}</code></pre>
                </div>
              </div>
              
              <!-- Extract API -->
              <div v-if="currentTab === 'Extract'" class="api-section">
                <h3>Extract API Endpoint</h3>
                <p class="api-description">Use this API to extract structured data based on your schema.</p>
                
                <div class="code-block">
                  <div class="code-header">
                    <span>POST</span>
                    <code>{{ baseUrl }}/api/extract</code>
                    <button class="copy-btn" @click="copyToClipboard(extractApiExample)">
                      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      Copy
                    </button>
                  </div>
                  <pre><code>{{ extractApiExample }}</code></pre>
                </div>
              </div>
              
              <!-- Split API -->
              <div v-if="currentTab === 'Split'" class="api-section">
                <h3>Split API Endpoint</h3>
                <p class="api-description">Use this API to split documents into categories.</p>
                
                <div class="code-block">
                  <div class="code-header">
                    <span>POST</span>
                    <code>{{ baseUrl }}/api/split</code>
                    <button class="copy-btn" @click="copyToClipboard(splitApiExample)">
                      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      Copy
                    </button>
                  </div>
                  <pre><code>{{ splitApiExample }}</code></pre>
                </div>
              </div>
              
              <!-- Journey API -->
              <div v-if="currentTab === 'Doc Journey'" class="api-section">
                <h3>Journey API Endpoint</h3>
                <p class="api-description">Use this API to execute your custom document journey workflow.</p>
                
                <div class="code-block">
                  <div class="code-header">
                    <span>POST</span>
                    <code>{{ baseUrl }}/api/journey/execute</code>
                    <button class="copy-btn" @click="copyToClipboard(journeyApiExample)">
                      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      Copy
                    </button>
                  </div>
                  <pre><code>{{ journeyApiExample }}</code></pre>
                </div>
              </div>
              
              <div v-if="copied" class="success-message">
                API example copied to clipboard!
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
  config?: any
}

interface Emits {
  (e: 'close'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const copied = ref(false)
const baseUrl = ref('http://localhost:8000')

const parseApiExample = computed(() => `curl -X POST "${baseUrl.value}/api/parse" \\
  -H "Content-Type: multipart/form-data" \\
  -F "file=@document.pdf" \\
  -F "tier=Normal"`)

const classifyApiExample = computed(() => `curl -X POST "${baseUrl.value}/api/classify" \\
  -H "Content-Type: multipart/form-data" \\
  -F "file=@document.pdf" \\
  -F "parser_tier=Normal" \\
  -F "classifier_tier=Normal" \\
  -F "max_pages=5" \\
  -F 'classification_rules=[
    {"type": "invoice", "description": "Contains itemized charges"},
    {"type": "receipt", "description": "Proof of payment"}
  ]'`)

const extractApiExample = computed(() => `curl -X POST "${baseUrl.value}/api/extract" \\
  -H "Content-Type: multipart/form-data" \\
  -F "file=@document.pdf" \\
  -F "parser_tier=Normal" \\
  -F "extractor_tier=Normal" \\
  -F "extraction_target=documents" \\
  -F 'schema={
    "fields": [
      {"name": "invoice_number", "type": "string"},
      {"name": "total_amount", "type": "number"}
    ]
  }'`)

const splitApiExample = computed(() => `curl -X POST "${baseUrl.value}/api/split" \\
  -H "Content-Type: multipart/form-data" \\
  -F "file=@document.pdf" \\
  -F "parser_tier=Normal" \\
  -F "splitter_tier=Normal" \\
  -F 'categories=[
    {"name": "Introduction", "description": "Opening pages"},
    {"name": "Financial Tables", "description": "Pages with tables"}
  ]' \\
  -F "allow_uncategorized=true"`)

const journeyApiExample = computed(() => `curl -X POST "${baseUrl.value}/api/journey/execute" \\
  -H "Content-Type: multipart/form-data" \\
  -F "file=@document.pdf" \\
  -F 'workflow={
    "nodes": [
      {"id": "parse1", "type": "parse", "config": {"tier": "Normal"}},
      {"id": "classify1", "type": "classify", "config": {...}},
      {"id": "extract1", "type": "extract", "config": {...}}
    ],
    "connections": [
      {"from": "parse1", "to": "classify1"},
      {"from": "parse1", "to": "extract1"}
    ]
  }'`)

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

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
  max-width: 700px;
  width: 100%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.modal-container.large {
  max-width: 800px;
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

.deploy-content {
  color: var(--text-secondary);
}

.api-section h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.api-description {
  margin: 0 0 1.5rem 0;
  color: var(--text-secondary);
  line-height: 1.6;
}

.code-block {
  background: #1f2937;
  border-radius: 0.5rem;
  overflow: hidden;
  margin-bottom: 1rem;
}

.code-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: #111827;
  border-bottom: 1px solid #374151;
}

.code-header span {
  font-size: 0.75rem;
  font-weight: 600;
  color: #10b981;
  text-transform: uppercase;
}

.code-header code {
  flex: 1;
  font-size: 0.875rem;
  color: #e5e7eb;
  font-family: 'Courier New', monospace;
}

.copy-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: #e5e7eb;
  background: #374151;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all 0.15s;
}

.copy-btn:hover {
  background: #4b5563;
}

.code-block pre {
  margin: 0;
  padding: 1rem;
  overflow-x: auto;
}

.code-block code {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  color: #e5e7eb;
  white-space: pre;
}

.success-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  text-align: center;
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
