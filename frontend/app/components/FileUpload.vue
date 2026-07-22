<template>
  <div
    class="file-upload"
    :class="{ 'drag-over': isDragging }"
    @dragover.prevent="handleDragOver"
    @dragleave.prevent="handleDragLeave"
    @drop.prevent="handleDrop"
  >
    <div class="upload-content">
      <svg class="upload-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
      
      <h3 class="upload-title">Drop files here or click to upload</h3>
      <p class="upload-subtitle">
        Supported: {{ acceptedTypes.join(', ').toUpperCase() }} (max {{ maxSizeMB }}MB)
      </p>
      
      <input
        ref="fileInput"
        type="file"
        :accept="acceptedTypes.map(t => `.${t}`).join(',')"
        :multiple="maxFiles > 1"
        class="file-input"
        @change="handleFileSelect"
      />
      
      <button type="button" class="upload-button" @click="triggerFileInput">
        Choose Files
      </button>
      
      <p v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  maxFiles?: number
  maxSizeMB?: number
  acceptedTypes?: string[]
}

interface Emits {
  (e: 'upload', files: File[]): void
}

const props = withDefaults(defineProps<Props>(), {
  maxFiles: 10,
  maxSizeMB: 10,
  acceptedTypes: () => ['png', 'jpg', 'jpeg', 'pdf']
})

const emit = defineEmits<Emits>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const errorMessage = ref('')

const triggerFileInput = () => {
  fileInput.value?.click()
}

const validateFiles = (files: File[]): { valid: File[], errors: string[] } => {
  const valid: File[] = []
  const errors: string[] = []
  
  // Check file count
  if (files.length > props.maxFiles) {
    errors.push(`Maximum ${props.maxFiles} files allowed`)
    return { valid, errors }
  }
  
  // Validate each file
  for (const file of files) {
    // Check file type
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (!extension || !props.acceptedTypes.includes(extension)) {
      errors.push(`${file.name}: Invalid file type. Allowed: ${props.acceptedTypes.join(', ')}`)
      continue
    }
    
    // Check file size
    const sizeMB = file.size / (1024 * 1024)
    if (sizeMB > props.maxSizeMB) {
      errors.push(`${file.name}: File too large (${sizeMB.toFixed(2)}MB). Max: ${props.maxSizeMB}MB`)
      continue
    }
    
    valid.push(file)
  }
  
  return { valid, errors }
}

const handleDragOver = (e: DragEvent) => {
  isDragging.value = true
}

const handleDragLeave = (e: DragEvent) => {
  isDragging.value = false
}

const handleDrop = (e: DragEvent) => {
  isDragging.value = false
  errorMessage.value = ''
  
  const files = Array.from(e.dataTransfer?.files || [])
  const { valid, errors } = validateFiles(files)
  
  if (errors.length > 0) {
    errorMessage.value = errors.join('; ')
  }
  
  if (valid.length > 0) {
    emit('upload', valid)
  }
}

const handleFileSelect = (e: Event) => {
  errorMessage.value = ''
  
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  const { valid, errors } = validateFiles(files)
  
  if (errors.length > 0) {
    errorMessage.value = errors.join('; ')
  }
  
  if (valid.length > 0) {
    emit('upload', valid)
  }
  
  // Reset input
  if (target) {
    target.value = ''
  }
}
</script>

<style scoped>
.file-upload {
  border: 2px dashed var(--color-sand);
  border-radius: 0.5rem;
  padding: 2rem;
  text-align: center;
  transition: all 0.3s ease;
  background-color: var(--color-cream);
  cursor: pointer;
}

.file-upload:hover {
  border-color: var(--color-sand-mid);
  background-color: var(--color-cream-alt);
}

.file-upload.drag-over {
  border-color: var(--color-orange);
  background-color: rgba(255, 79, 0, 0.03);
  transform: scale(1.02);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.upload-icon {
  width: 3rem;
  height: 3rem;
  color: var(--accent-orange);
}

.upload-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.upload-subtitle {
  font-size: 0.875rem;
  color: var(--text-tertiary);
  margin: 0;
}

.file-input {
  display: none;
}

.upload-button {
  background-color: var(--accent-orange);
  color: var(--color-cream);
  padding: 0.5rem 1.5rem;
  border-radius: 0.375rem;
  border: none;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.upload-button:hover {
  background-color: #e54700;
}

.error-message {
  color: #c54444;
  font-size: 0.875rem;
  margin: 0;
  max-width: 100%;
  word-wrap: break-word;
}
</style>
