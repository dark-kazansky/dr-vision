<template>
  <div class="upload-section">
    <!-- Upload Dropzone or Preview -->
    <div v-if="!previewFile" 
      class="upload-dropzone"
      :class="{ 'drag-over': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="$emit('trigger-upload')"
    >
      <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
      <p class="dropzone-text">Drop files here or click to upload</p>
      <p class="dropzone-subtext">Supported: PNG, JPG, JPEG, PDF (max 10MB)</p>
    </div>

    <div v-else class="preview-area">
      <div v-if="previewFile.type === 'pdf'" class="pdf-preview-wrapper">
        <iframe 
          v-if="pdfUrl"
          :key="`pdf-${previewFile.id}`"
          :src="pdfUrl" 
          type="application/pdf" 
          class="pdf-embed"
          frameborder="0"
        />
        <div v-else class="preview-error">
          <p>Unable to load PDF preview</p>
        </div>
      </div>
      <div v-else class="image-preview-wrapper">
        <img 
          v-if="imageUrl"
          :src="imageUrl" 
          :alt="previewFile.name"
          class="image-embed"
          :style="{ transform: `scale(${zoom / 100})` }"
        />
        <div v-else class="preview-error">
          <p>Unable to load image preview</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  previewFile: any
  pdfUrl?: string
  imageUrl?: string
  zoom?: number
}

interface Emits {
  (e: 'trigger-upload'): void
  (e: 'drop', files: File[]): void
}

const props = withDefaults(defineProps<Props>(), {
  zoom: 100
})

const emit = defineEmits<Emits>()

const isDragging = ref(false)

const handleDrop = (e: DragEvent) => {
  isDragging.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  emit('drop', files)
}
</script>
