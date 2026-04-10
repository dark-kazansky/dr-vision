<template>
  <div class="file-list">
    <div class="file-list-header">
      <h3>Files ({{ files.length }})</h3>
      <button v-if="files.length > 0" @click="$emit('clear')" class="clear-button">
        Clear All
      </button>
    </div>
    
    <div v-if="files.length === 0" class="empty-state">
      <p>No files uploaded yet</p>
    </div>
    
    <div v-else class="file-items">
      <div
        v-for="file in files"
        :key="file.id"
        class="file-item"
        :class="{ selected: selectedId === file.id }"
        @click="$emit('select', file)"
      >
        <div class="file-icon">
          <svg v-if="file.type === 'pdf'" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
          </svg>
          <svg v-else fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
          </svg>
        </div>
        
        <div class="file-info">
          <div class="file-name">{{ file.name }}</div>
          <div class="file-meta">
            {{ formatSize(file.size) }} • {{ file.type.toUpperCase() }}
          </div>
        </div>
        
        <div class="file-status">
          <span :class="`status-badge status-${file.status}`">
            {{ file.status }}
          </span>
        </div>
        
        <button
          class="remove-button"
          @click.stop="$emit('remove', file.id)"
          title="Remove file"
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FileItem } from '~/composables/useOCR'

interface Props {
  files: FileItem[]
  selectedId?: string
}

interface Emits {
  (e: 'select', file: FileItem): void
  (e: 'remove', fileId: string): void
  (e: 'clear'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<style scoped>
.file-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.file-list-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #2d3748;
}

.clear-button {
  background: none;
  border: none;
  color: #e53e3e;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
}

.clear-button:hover {
  text-decoration: underline;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #a0aec0;
}

.file-items {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;
  border: 1px solid transparent;
}

.file-item:hover {
  background-color: #f7fafc;
}

.file-item.selected {
  background-color: #ebf8ff;
  border-color: #4299e1;
}

.file-icon {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  color: #4299e1;
}

.file-icon svg {
  width: 100%;
  height: 100%;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: #2d3748;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 0.75rem;
  color: #718096;
  margin-top: 0.125rem;
}

.file-status {
  flex-shrink: 0;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.status-pending {
  background-color: #edf2f7;
  color: #4a5568;
}

.status-processing {
  background-color: #fef5e7;
  color: #d69e2e;
}

.status-completed {
  background-color: #c6f6d5;
  color: #2f855a;
}

.status-error {
  background-color: #fed7d7;
  color: #c53030;
}

.remove-button {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  background: none;
  border: none;
  color: #a0aec0;
  cursor: pointer;
  transition: color 0.2s;
}

.remove-button:hover {
  color: #e53e3e;
}

.remove-button svg {
  width: 100%;
  height: 100%;
}
</style>
