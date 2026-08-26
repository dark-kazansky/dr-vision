<template>
  <div class="preview-area">
    <div v-if="!file" class="empty-preview">
      <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
      <p>Select a file to preview</p>
    </div>
    
    <div v-else class="preview-content">
      <div class="preview-header">
        <h3>{{ file.name }}</h3>
        <div class="preview-controls">
          <!-- Zoom controls -->
          <div class="control-group">
            <button
              @click="$emit('zoom-out')"
              :disabled="!canZoomOut"
              class="control-button"
              title="Zoom out"
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
              </svg>
            </button>
            <span class="zoom-level">{{ zoom }}%</span>
            <button
              @click="$emit('zoom-in')"
              :disabled="!canZoomIn"
              class="control-button"
              title="Zoom in"
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
              </svg>
            </button>
          </div>
          
          <!-- Page navigation (for PDFs) -->
          <div v-if="file.type === 'pdf' && totalPages > 1" class="control-group">
            <button
              @click="$emit('prev-page')"
              :disabled="!canGoPrev"
              class="control-button"
              title="Previous page"
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
            <button
              @click="$emit('next-page')"
              :disabled="!canGoNext"
              class="control-button"
              title="Next page"
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      
      <div class="preview-viewport">
        <div class="preview-placeholder" :style="{ transform: `scale(${zoom / 100})` }">
          <div v-if="file.type === 'pdf'" class="pdf-preview">
            <svg class="preview-icon" fill="currentColor" viewBox="0 0 20 20">
              <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
            </svg>
            <p>PDF Preview</p>
            <p class="preview-note">Page {{ currentPage }} of {{ totalPages }}</p>
          </div>
          <div v-else class="image-preview">
            <svg class="preview-icon" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
            </svg>
            <p>Image Preview</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FileItem } from '~/composables/useOCR'

interface Props {
  file: FileItem | null
  zoom: number
  currentPage: number
  totalPages: number
  canZoomIn: boolean
  canZoomOut: boolean
  canGoNext: boolean
  canGoPrev: boolean
}

interface Emits {
  (e: 'zoom-in'): void
  (e: 'zoom-out'): void
  (e: 'next-page'): void
  (e: 'prev-page'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
</script>

<style scoped>
.preview-area {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-cream);
  border-radius: 0.5rem;
  overflow: hidden;
}

.empty-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-tertiary);
}

.empty-icon {
  width: 4rem;
  height: 4rem;
  margin-bottom: 1rem;
}

.preview-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--color-sand);
  gap: 1rem;
}

.preview-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-controls {
  display: flex;
  gap: 1rem;
  flex-shrink: 0;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem;
  background-color: var(--bg-secondary);
  border-radius: 0.375rem;
}

.control-button {
  width: 2rem;
  height: 2rem;
  padding: 0.25rem;
  background: var(--color-cream);
  border: 1px solid var(--color-sand);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.control-button:hover:not(:disabled) {
  background-color: var(--bg-tertiary);
  border-color: var(--color-orange);
  color: var(--accent-orange);
}

.control-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.control-button svg {
  width: 100%;
  height: 100%;
}

.zoom-level,
.page-info {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  min-width: 3rem;
  text-align: center;
}

.preview-viewport {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-secondary);
  padding: 2rem;
}

.preview-placeholder {
  transition: transform 0.2s;
  transform-origin: center;
}

.pdf-preview,
.image-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  background: var(--color-cream);
  border: 2px dashed var(--color-sand);
  border-radius: 0.5rem;
  min-width: 300px;
  min-height: 400px;
}

.preview-icon {
  width: 5rem;
  height: 5rem;
  color: var(--accent-orange);
  margin-bottom: 1rem;
}

.pdf-preview p,
.image-preview p {
  margin: 0.5rem 0;
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--text-primary);
}

.preview-note {
  font-size: 0.875rem !important;
  color: var(--text-tertiary) !important;
  font-weight: 400 !important;
}
</style>
