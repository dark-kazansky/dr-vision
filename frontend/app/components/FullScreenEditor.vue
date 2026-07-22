<template>
  <Teleport to="body">
    <Transition name="fullscreen">
      <div v-if="isOpen" class="fullscreen-overlay">
        <div class="fullscreen-container">
          <!-- Header with Pagination -->
          <div class="fullscreen-header">
            <div class="header-left">
              <h2 class="header-title">M<span class="logo-dot">.</span>DocAI Editor</h2>
            </div>
            
            <div class="header-center">
              <div class="pagination-controls">
                <button class="pagination-btn" @click="prevPage" :disabled="!canGoPrev">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <span class="pagination-text">Page {{ currentPage }} / {{ totalPages }}</span>
                <button class="pagination-btn" @click="nextPage" :disabled="!canGoNext">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
            
            <div class="header-right">
              <button class="close-btn" @click="close">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
          
          <!-- Three Column Layout -->
          <div class="fullscreen-content">
            <!-- Column 1: PDF Preview -->
            <div class="editor-column preview-column">
              <div class="column-header">
                <h3 class="column-title">Preview</h3>
              </div>
              <div class="column-content">
                <div v-if="previewFile && previewFile.type === 'pdf'" class="pdf-preview">
                  <iframe 
                    v-if="pdfUrl"
                    :src="`${pdfUrl}#page=${currentPage}`" 
                    type="application/pdf" 
                    class="pdf-iframe"
                    frameborder="0"
                  />
                  <div v-else class="preview-placeholder">
                    <p>No PDF preview available</p>
                  </div>
                </div>
                <div v-else-if="previewFile && previewFile.type !== 'pdf'" class="image-preview">
                  <img 
                    v-if="imageUrl"
                    :src="imageUrl" 
                    :alt="previewFile.name"
                    class="preview-image"
                  />
                  <div v-else class="preview-placeholder">
                    <p>No image preview available</p>
                  </div>
                </div>
                <div v-else class="preview-placeholder">
                  <p>No file selected</p>
                </div>
              </div>
            </div>
            
            <!-- Column 2: Raw Result (Editable) -->
            <div class="editor-column raw-column">
              <div class="column-header">
                <h3 class="column-title">Raw Result</h3>
              </div>
              <div class="column-content">
                <textarea
                  ref="textareaRef"
                  v-model="rawText"
                  class="editor-textarea"
                  placeholder="OCR result will appear here..."
                  @input="handleRawTextChange"
                  @keydown="handleKeydown"
                  @mousedown="handleMouseDown"
                  @click="handleClick"
                  spellcheck="false"
                  wrap="soft"
                ></textarea>
              </div>
            </div>
            
            <!-- Column 3: Parsed Result (Read-only) -->
            <div class="editor-column parsed-column">
              <div class="column-header">
                <h3 class="column-title">Parsed Result</h3>
              </div>
              <div class="column-content">
                <div class="parsed-content" v-html="parsedHtml"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { marked } from 'marked'

const props = defineProps<{
  isOpen: boolean
  previewFile: any
  pdfUrl: string
  imageUrl: string
  initialText: string
  totalPages: number
  initialPage: number
}>()

const emit = defineEmits<{
  close: []
  update: [text: string]
  pageChange: [page: number]
}>()

const currentPage = ref(props.initialPage)
const rawText = ref(props.initialText)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isLocalEdit = ref(false)
const updateTimeout = ref<number | null>(null)

// Watch for prop changes
watch(() => props.initialText, (newText) => {
  // Only update if it's not a local edit
  if (!isLocalEdit.value) {
    rawText.value = newText
  }
  isLocalEdit.value = false
})

watch(() => props.initialPage, (newPage) => {
  currentPage.value = newPage
})

// Computed
const canGoPrev = computed(() => currentPage.value > 1)
const canGoNext = computed(() => currentPage.value < props.totalPages)

// Parse raw text to HTML
const parsedHtml = computed(() => {
  if (!rawText.value) return '<p class="placeholder-text">Parsed result will appear here...</p>'
  
  const text = rawText.value
  let html = ''
  
  // Detect if content contains HTML tables
  const hasHtmlTable = /<table[\s\S]*?<\/table>/i.test(text)
  
  // Detect if content has HTML tags
  const hasHtmlTags = /<(?!table|\/table|tr|\/tr|td|\/td|th|\/th|tbody|\/tbody|thead|\/thead)[a-z][\s\S]*?>/i.test(text)
  
  // Detect Markdown syntax
  const hasMarkdownSyntax = /(\*\*|__|\#|\[.*?\]\(.*?\)|```|^\s*[-*]|\n\d+\.)/.test(text)
  
  // Strategy 1: Mixed HTML and Markdown
  if (hasHtmlTable && hasMarkdownSyntax) {
    try {
      const tables: string[] = []
      const markers: string[] = []
      
      let processedText = text.replace(/<table[\s\S]*?<\/table>/gi, (match) => {
        const index = tables.length
        tables.push(match)
        const marker = `|||TABLE_MARKER_${index}|||`
        markers.push(marker)
        return marker
      })
      
      html = marked.parse(processedText, {
        breaks: true,
        gfm: true,
        pedantic: false
      }) as string
      
      tables.forEach((table, index) => {
        const marker = markers[index]
        const patterns = [
          new RegExp(`<p>\\|\\|\\|TABLE_MARKER_${index}\\|\\|\\|</p>`, 'g'),
          new RegExp(`\\|\\|\\|TABLE_MARKER_${index}\\|\\|\\|`, 'g')
        ]
        
        patterns.forEach(pattern => {
          html = html.replace(pattern, table)
        })
      })
      
      html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      return html
    } catch (error) {
      console.error('Mixed content parsing error:', error)
    }
  }
  
  // Strategy 2: Pure HTML content
  if (hasHtmlTable || (hasHtmlTags && !hasMarkdownSyntax)) {
    html = text
    html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    html = html.replace(/<\/(p|div|table|h[1-6])>/gi, '</$1>\n')
    return html
  }
  
  // Strategy 3: Markdown content
  if (hasMarkdownSyntax) {
    try {
      html = marked.parse(text, {
        breaks: true,
        gfm: true,
        pedantic: false,
        headerIds: false,
        mangle: false
      }) as string
      return html
    } catch (error) {
      console.error('Markdown parsing error:', error)
    }
  }
  
  // Strategy 4: Plain text
  html = text
  
  // Detect and format tables in plain text
  if (text.includes('|')) {
    const lines = text.split('\n')
    let inTable = false
    let tableHtml = ''
    let nonTableHtml = ''
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      
      if (line.includes('|')) {
        if (!inTable) {
          inTable = true
          tableHtml = '<table><tbody>'
        }
        
        if (/^\|[\s\-:]+\|$/.test(line)) {
          continue
        }
        
        const cells = line.split('|').filter(cell => cell.trim())
        const isHeader = i === 0 || (i === 1 && /^\|[\s\-:]+\|$/.test(lines[i - 1]))
        
        if (isHeader && tableHtml === '<table><tbody>') {
          tableHtml = '<table><thead><tr>'
          cells.forEach(cell => {
            tableHtml += `<th>${cell.trim()}</th>`
          })
          tableHtml += '</tr></thead><tbody>'
        } else {
          tableHtml += '<tr>'
          cells.forEach(cell => {
            tableHtml += `<td>${cell.trim()}</td>`
          })
          tableHtml += '</tr>'
        }
      } else {
        if (inTable) {
          tableHtml += '</tbody></table>'
          nonTableHtml += tableHtml
          tableHtml = ''
          inTable = false
        }
        nonTableHtml += line + '\n'
      }
    }
    
    if (inTable) {
      tableHtml += '</tbody></table>'
      nonTableHtml += tableHtml
    }
    
    html = nonTableHtml
  }
  
  // Convert paragraphs
  html = html.replace(/\n\n+/g, '</p><p>')
  html = '<p>' + html + '</p>'
  
  // Convert line breaks
  html = html.replace(/\n/g, '<br>')
  
  // Bold text
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>')
  
  // Italic text
  html = html.replace(/(?<!\*)\*([^\*]+?)\*(?!\*)/g, '<em>$1</em>')
  html = html.replace(/(?<!_)_([^_]+?)_(?!_)/g, '<em>$1</em>')
  
  // Headers
  html = html.replace(/<p>(.+?):<\/p>/g, '<h3>$1:</h3>')
  
  return html
})

// Handlers
const close = () => {
  // Clear any pending updates
  if (updateTimeout.value) {
    clearTimeout(updateTimeout.value)
  }
  
  // Emit final update before closing
  emit('update', rawText.value)
  
  // Close the editor
  emit('close')
}

const prevPage = () => {
  if (canGoPrev.value) {
    currentPage.value--
    emit('pageChange', currentPage.value)
  }
}

const nextPage = () => {
  if (canGoNext.value) {
    currentPage.value++
    emit('pageChange', currentPage.value)
  }
}

const handleRawTextChange = () => {
  // Mark as local edit to prevent prop update from resetting cursor
  isLocalEdit.value = true
  
  // Debounce the emit to reduce updates
  if (updateTimeout.value) {
    clearTimeout(updateTimeout.value)
  }
  
  updateTimeout.value = setTimeout(() => {
    emit('update', rawText.value)
  }, 300)
}

const handleMouseDown = (e: MouseEvent) => {
  // Don't interfere with mouse events
  e.stopPropagation()
}

const handleClick = (e: MouseEvent) => {
  // Just ensure focus, let browser handle cursor positioning
  const target = e.target as HTMLTextAreaElement
  if (target) {
    target.focus()
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  // Allow ESC key to close the editor
  if (e.key === 'Escape') {
    e.preventDefault()
    close()
    return
  }
}

// Close on Escape key (backup handler)
onMounted(() => {
  const handleEscape = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && props.isOpen) {
      e.preventDefault()
      close()
    }
  }
  window.addEventListener('keydown', handleEscape)
  
  onUnmounted(() => {
    window.removeEventListener('keydown', handleEscape)
  })
})
</script>

<style scoped>
.fullscreen-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(32, 21, 21, 0.8);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fullscreen-container {
  width: 100%;
  height: 100%;
  background: var(--color-cream);
  display: flex;
  flex-direction: column;
}

/* Header */
.fullscreen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--color-sand);
  background-color: var(--color-cream);
}

.header-left,
.header-center,
.header-right {
  flex: 1;
  display: flex;
  align-items: center;
}

.header-center {
  justify-content: center;
}

.header-right {
  justify-content: flex-end;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.pagination-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  background-color: var(--color-cream);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background-color: var(--bg-tertiary);
  border-color: var(--color-sand);
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  min-width: 100px;
  text-align: center;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 6px;
  background-color: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

/* Content */
.fullscreen-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0;
  overflow: hidden;
}

.editor-column {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-sand);
  overflow: hidden;
}

.editor-column:last-child {
  border-right: none;
}

.column-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-sand);
  background-color: var(--bg-secondary);
}

.column-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.column-content {
  flex: 1;
  overflow: auto;
  position: relative;
}

/* PDF Preview */
.pdf-preview,
.image-preview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-tertiary);
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.preview-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--text-tertiary);
  font-size: 14px;
}

/* Raw Result Textarea */
.editor-textarea {
  width: 100%;
  height: 100%;
  min-height: 100%;
  padding: 16px;
  margin: 0;
  border: none;
  outline: none;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  background-color: var(--color-cream);
  color: var(--text-primary);
  cursor: text;
  overflow: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  box-sizing: border-box;
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
}

.editor-textarea:focus {
  background-color: var(--color-cream-alt);
  cursor: text;
}

.editor-textarea::selection {
  background-color: var(--accent-orange);
  color: var(--color-cream);
}

.editor-textarea::placeholder {
  color: var(--text-tertiary);
}

/* Parsed Result */
.parsed-content {
  padding: 24px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
}

.placeholder-text {
  color: var(--text-tertiary);
  font-style: italic;
}

.parsed-content h1,
.parsed-content h2,
.parsed-content h3,
.parsed-content h4,
.parsed-content h5,
.parsed-content h6 {
  margin-top: 24px;
  margin-bottom: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.parsed-content p {
  margin-bottom: 12px;
}

.parsed-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.parsed-content th,
.parsed-content td {
  border: 1px solid var(--color-sand);
  padding: 8px 12px;
  text-align: left;
}

.parsed-content th {
  background-color: var(--bg-secondary);
  font-weight: 600;
}

.parsed-content ul,
.parsed-content ol {
  margin: 12px 0;
  padding-left: 24px;
}

.parsed-content li {
  margin-bottom: 6px;
}

.parsed-content strong {
  font-weight: 600;
}

.parsed-content em {
  font-style: italic;
}

/* Transitions */
.fullscreen-enter-active,
.fullscreen-leave-active {
  transition: opacity 0.3s ease;
}

.fullscreen-enter-from,
.fullscreen-leave-to {
  opacity: 0;
}
</style>
