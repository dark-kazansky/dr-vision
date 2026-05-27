<template>
  <div class="data-store-panel">
    <!-- Header -->
    <div class="data-header">
      <h2 class="data-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
          <path d="M3 5V19A9 3 0 0 0 21 19V5"></path>
          <path d="M3 12A9 3 0 0 0 21 12"></path>
        </svg>
        Data Store
      </h2>
      <span class="data-count">{{ filteredEntries.length }} entries</span>
    </div>

    <!-- Filter Tags -->
    <div class="filter-section">
      <button
        class="filter-tag"
        :class="{ active: activeFilter === 'all' }"
        @click="activeFilter = 'all'"
      >
        All
      </button>
      <button
        v-for="tag in availableTags"
        :key="tag"
        class="filter-tag"
        :class="{ active: activeFilter === tag, [tag.toLowerCase()]: true }"
        @click="activeFilter = tag"
      >
        {{ tag }}
      </button>
    </div>

    <!-- Entries List -->
    <div class="entries-list" v-if="filteredEntries.length > 0">
      <div
        v-for="entry in filteredEntries"
        :key="entry.id"
        class="entry-card"
        @click="openEntryDialog(entry)"
      >
        <div class="entry-header">
          <div class="entry-info">
            <span class="entry-tag" :class="entry.action_tag.toLowerCase()">
              {{ entry.action_tag }}
            </span>
            <span class="entry-filename">{{ entry.filename }}</span>
          </div>
          <div class="entry-meta">
            <span class="entry-time">{{ formatTime(entry.created_at) }}</span>
            <button class="entry-delete" @click.stop="deleteEntry(entry.id)" title="Delete">
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
        <path d="M3 5V19A9 3 0 0 0 21 19V5"></path>
        <path d="M3 12A9 3 0 0 0 21 12"></path>
      </svg>
      <p class="empty-title">No data yet</p>
      <p class="empty-subtitle">Results from Parse, Classify, Extract, Split, and Workflow executions will appear here automatically.</p>
    </div>

    <!-- Detail Dialog (Popup) -->
    <Teleport to="body">
      <div v-if="dialogEntry" class="dialog-overlay" @click.self="closeDialog">
        <div class="dialog-container">
          <!-- Dialog Header -->
          <div class="dialog-header">
            <div class="dialog-title-row">
              <span class="entry-tag" :class="dialogEntry.action_tag.toLowerCase()">
                {{ dialogEntry.action_tag }}
              </span>
              <h3 class="dialog-filename">{{ dialogEntry.filename }}</h3>
              <span class="dialog-meta">{{ formatFullTime(dialogEntry.created_at) }}</span>
              <span v-if="dialogEntry.model_used" class="dialog-model">{{ dialogEntry.model_used }}</span>
            </div>
            <button class="dialog-close" @click="closeDialog">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Dialog Body: Split View -->
          <div class="dialog-body">
            <!-- Left: Original Document -->
            <div class="dialog-left">
              <div class="panel-label">Original Document</div>
              <div class="document-preview">
                <iframe
                  v-if="dialogPreviewUrl && dialogEntry.filename.toLowerCase().endsWith('.pdf')"
                  :src="dialogPreviewUrl"
                  class="document-iframe"
                  frameborder="0"
                />
                <img
                  v-else-if="dialogPreviewUrl"
                  :src="dialogPreviewUrl"
                  :alt="dialogEntry.filename"
                  class="document-image"
                />
                <div v-else class="document-unavailable">
                  <svg width="40" height="40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p>Document preview not available</p>
                  <p class="unavailable-hint">File may not exist in storage</p>
                </div>
              </div>
            </div>

            <!-- Right: OCR Result -->
            <div class="dialog-right">
              <div class="panel-label-row">
                <span class="panel-label">OCR Result</span>
                <div class="result-actions">
                  <button
                    class="result-tab-btn"
                    :class="{ active: dialogViewMode === 'preview' }"
                    @click="dialogViewMode = 'preview'"
                  >
                    Preview
                  </button>
                  <button
                    class="result-tab-btn"
                    :class="{ active: dialogViewMode === 'raw' }"
                    @click="dialogViewMode = 'raw'"
                  >
                    Raw JSON
                  </button>
                  <button class="copy-btn" @click="copyResult(dialogEntry)" title="Copy to clipboard">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"></path>
                    </svg>
                  </button>
                </div>
              </div>
              <div class="result-content">
                <div v-if="dialogViewMode === 'preview'" class="result-preview">
                  <pre class="result-text">{{ formatResultPreview(dialogEntry.result_data) }}</pre>
                </div>
                <div v-else class="result-raw">
                  <pre class="result-json">{{ JSON.stringify(dialogEntry.result_data, null, 2) }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { useDataStore, type DataStoreEntry } from '~/composables/useDataStore'

interface Props {
  providers?: any[]
}

defineProps<Props>()

const { entries, isLoading, loadEntries, deleteEntry: removeEntry } = useDataStore()

const activeFilter = ref('all')
const dialogEntry = ref<DataStoreEntry | null>(null)
const dialogPreviewUrl = ref('')
const dialogViewMode = ref<'preview' | 'raw'>('preview')

const availableTags = ['Parse', 'Classify', 'Extract', 'Split', 'WF']

const filteredEntries = computed(() => {
  const filtered = activeFilter.value === 'all'
    ? entries.value
    : entries.value.filter(e => e.action_tag === activeFilter.value)
  return [...filtered].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})

const openEntryDialog = async (entry: DataStoreEntry) => {
  dialogEntry.value = entry
  dialogViewMode.value = 'preview'
  dialogPreviewUrl.value = ''

  // Try to load document preview from uploads
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  try {
    // Search for matching upload by filename
    const response = await $fetch<{ uploads: any[] }>(`${apiBaseUrl}/api/v1/uploads`)
    const matchingUpload = response.uploads.find((u: any) => u.filename === entry.filename)
    if (matchingUpload) {
      dialogPreviewUrl.value = `${apiBaseUrl}/api/v1/uploads/${matchingUpload.upload_id}/download`
    }
  } catch {
    // Preview not available
  }
}

const closeDialog = () => {
  dialogEntry.value = null
  dialogPreviewUrl.value = ''
}

const deleteEntry = async (id: string) => {
  await removeEntry(id)
  if (dialogEntry.value?.id === id) {
    closeDialog()
  }
}

const copyResult = (entry: DataStoreEntry) => {
  const text = typeof entry.result_data === 'string'
    ? entry.result_data
    : JSON.stringify(entry.result_data, null, 2)
  navigator.clipboard.writeText(text)
}

const formatResultPreview = (data: any): string => {
  if (typeof data === 'string') return data
  
  // Extract readable text from OCR result objects
  if (data && typeof data === 'object') {
    // Parse/OCR result: { success: true, text: "..." }
    if (data.text) return data.text
    
    // Classify result: { success: true, results: [...] }
    if (data.results && Array.isArray(data.results)) {
      return data.results.map((r: any, i: number) => {
        const parts = [`${i + 1}. ${r.category || r.type || 'Item'}`]
        if (r.confidence) parts.push(`   Confidence: ${(r.confidence * 100).toFixed(0)}%`)
        if (r.pages) parts.push(`   Pages: ${Array.isArray(r.pages) ? r.pages.join(', ') : r.pages}`)
        if (r.content_preview) parts.push(`   ${r.content_preview}`)
        return parts.join('\n')
      }).join('\n\n')
    }
    
    // Split result: { success: true, categories: [...] }
    if (data.categories && Array.isArray(data.categories)) {
      return data.categories.map((c: any, i: number) => {
        const parts = [`${i + 1}. ${c.name}`]
        if (c.pages) parts.push(`   Pages: ${c.pages}`)
        if (c.content_preview) parts.push(`   ${c.content_preview}`)
        return parts.join('\n')
      }).join('\n\n')
    }
    
    // Workflow result: { workflow_name, nodes: [...] }
    if (data.workflow_name && data.nodes) {
      const header = `Workflow: ${data.workflow_name}\n${'─'.repeat(40)}\n`
      const nodes = data.nodes.map((n: any, i: number) => {
        return `${i + 1}. [${n.type}] ${n.label}\n   Result: ${JSON.stringify(n.result, null, 2).split('\n').join('\n   ')}`
      }).join('\n\n')
      return header + nodes
    }
    
    // Extract result: key-value pairs
    if (data.success !== undefined && Object.keys(data).length > 2) {
      const entries = Object.entries(data)
        .filter(([k]) => k !== 'success' && k !== 'error' && k !== 'error_type')
        .map(([k, v]) => {
          const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
          const value = typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)
          return `${label}: ${value}`
        })
      return entries.join('\n')
    }
  }
  
  return JSON.stringify(data, null, 2)
}

const formatTime = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

const formatFullTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

// Close dialog on Escape key
onMounted(() => {
  loadEntries()
  const handler = (e: KeyboardEvent) => {
    if (e.key === 'Escape') closeDialog()
  }
  document.addEventListener('keydown', handler)
  onUnmounted(() => document.removeEventListener('keydown', handler))
})
</script>

<style scoped>
.data-store-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  padding: 2rem;
  overflow-y: auto;
  max-width: 100%;
}

.data-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.data-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.data-count {
  font-size: 0.8125rem;
  color: #6b7280;
  background: #f3f4f6;
  padding: 0.25rem 0.625rem;
  border-radius: 999px;
}

/* Filter Tags */
.filter-section {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.filter-tag {
  padding: 0.375rem 0.75rem;
  border-radius: 999px;
  border: 1.5px solid #e5e7eb;
  background: #fff;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-tag:hover { border-color: #d1d5db; color: #374151; }
.filter-tag.active { background: #FF6F3C; border-color: #FF6F3C; color: #fff; }
.filter-tag.active.parse { background: #3b82f6; border-color: #3b82f6; }
.filter-tag.active.classify { background: #8b5cf6; border-color: #8b5cf6; }
.filter-tag.active.extract { background: #10b981; border-color: #10b981; }
.filter-tag.active.split { background: #f59e0b; border-color: #f59e0b; }
.filter-tag.active.wf { background: #ec4899; border-color: #ec4899; }

/* Entry Cards */
.entries-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.entry-card {
  border: 1.5px solid #e5e7eb;
  border-radius: 0.625rem;
  padding: 0.875rem 1rem;
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
}

.entry-card:hover {
  border-color: #FF6F3C;
  box-shadow: 0 2px 8px rgba(255, 111, 60, 0.08);
}

.entry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.entry-info {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.entry-tag {
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.entry-tag.parse { background: #dbeafe; color: #1d4ed8; }
.entry-tag.classify { background: #ede9fe; color: #6d28d9; }
.entry-tag.extract { background: #d1fae5; color: #065f46; }
.entry-tag.split { background: #fef3c7; color: #92400e; }
.entry-tag.wf { background: #fce7f3; color: #9d174d; }

.entry-filename {
  font-size: 0.875rem;
  font-weight: 500;
  color: #111827;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.entry-time {
  font-size: 0.75rem;
  color: #9ca3af;
}

.entry-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 0.375rem;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.15s;
}

.entry-delete:hover { background: #fef2f2; color: #ef4444; }

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  text-align: center;
  color: #9ca3af;
}

.empty-state svg { margin-bottom: 1rem; opacity: 0.5; }
.empty-title { font-size: 1rem; font-weight: 600; color: #6b7280; margin: 0 0 0.5rem; }
.empty-subtitle { font-size: 0.875rem; color: #9ca3af; margin: 0; max-width: 320px; line-height: 1.5; }

/* ===== Dialog (Popup) ===== */
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.dialog-container {
  background: #fff;
  border-radius: 1rem;
  width: 100%;
  max-width: 1200px;
  height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.dialog-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.dialog-filename {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.dialog-meta {
  font-size: 0.8125rem;
  color: #6b7280;
}

.dialog-model {
  font-size: 0.75rem;
  background: #f3f4f6;
  padding: 0.2rem 0.5rem;
  border-radius: 0.25rem;
  color: #374151;
}

.dialog-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 0.5rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.dialog-close:hover { background: #f3f4f6; color: #111827; }

/* Dialog Body: Split View */
.dialog-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.dialog-left,
.dialog-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dialog-left {
  border-right: 1px solid #e5e7eb;
}

.panel-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid #f3f4f6;
  flex-shrink: 0;
}

.panel-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid #f3f4f6;
  flex-shrink: 0;
}

.panel-label-row .panel-label {
  padding: 0;
  border: none;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.result-tab-btn {
  padding: 0.25rem 0.625rem;
  border: none;
  background: transparent;
  font-size: 0.8125rem;
  color: #6b7280;
  cursor: pointer;
  border-radius: 0.25rem;
  transition: all 0.15s;
}

.result-tab-btn.active {
  background: #f3f4f6;
  color: #111827;
  font-weight: 600;
}

.copy-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 0.25rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.copy-btn:hover { background: #e5e7eb; color: #111827; }

/* Document Preview */
.document-preview {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
}

.document-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.document-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.document-unavailable {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: #9ca3af;
  text-align: center;
  padding: 2rem;
}

.document-unavailable p { margin: 0; font-size: 0.875rem; }
.unavailable-hint { font-size: 0.75rem; color: #d1d5db; }

/* Result Content */
.result-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
}

.result-preview,
.result-raw {
  height: 100%;
}

.result-text,
.result-json {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.8125rem;
  line-height: 1.7;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.result-preview .result-text {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 0.875rem;
  line-height: 1.8;
  color: #1f2937;
}
</style>
