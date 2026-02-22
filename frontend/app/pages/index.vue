<template>
  <div class="app-container">
    <!-- Notification Container -->
    <NotificationContainer />
    
    <!-- Feedback Dialog -->
    <FeedbackDialog 
      :is-open="showFeedbackDialog" 
      @close="showFeedbackDialog = false"
      @submit="handleFeedbackSubmit"
    />
    
    <!-- Help Dialog -->
    <HelpDialog 
      :is-open="showHelpDialog" 
      :current-tab="getTabName(activeView)"
      @close="showHelpDialog = false"
    />
    
    <!-- Deploy Dialog -->
    <DeployDialog 
      :is-open="showDeployDialog" 
      :current-tab="getTabName(activeView)"
      @close="showDeployDialog = false"
    />
    
    <!-- Full Screen Editor -->
    <FullScreenEditor
      :is-open="showFullScreenEditor"
      :preview-file="previewFile"
      :pdf-url="previewFileUrl"
      :image-url="previewFileUrl"
      :initial-text="currentPageResult"
      :total-pages="totalResultPages"
      :initial-page="currentResultPage"
      @close="showFullScreenEditor = false"
      @update="handleEditorUpdate"
      @page-change="handleEditorPageChange"
    />
    
    <!-- Top Bar -->
    <div class="top-bar">
      <div class="logo logo-clickable">
        <img src="/assets/logo.png" alt="Dr.Vision" class="logo-icon" @click="handleRefresh" />
        <span class="logo-text" @click="handleRefresh">Dr.Vision</span>
      </div>
      <div class="top-bar-actions">
        <button class="top-bar-btn" @click="handleDeploy">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
          Deploy
        </button>
        <button class="top-bar-btn" @click="handleFeedback">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          Feedback
        </button>
        <button class="top-bar-btn" @click="handleHelp">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Help
        </button>
      </div>
    </div>

    <!-- Sidebar -->
    <div class="sidebar">
      <div class="sidebar-nav">
        <a href="#" class="nav-item" :class="{ active: activeView === 'parse' }" @click.prevent="activeView = 'parse'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 22h14a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v4"></path>
            <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
            <path d="m5 12-3 3 3 3"></path>
            <path d="m9 18 3-3-3-3"></path>
          </svg>
          Parse
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'classify' }" @click.prevent="activeView = 'classify'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m15 5 6.3 6.3a2.4 2.4 0 0 1 0 3.4L17 19"></path>
            <path d="M9.586 5.586A2 2 0 0 0 8.172 5H3a1 1 0 0 0-1 1v5.172a2 2 0 0 0 .586 1.414L8.29 18.29a2.426 2.426 0 0 0 3.42 0l3.58-3.58a2.426 2.426 0 0 0 0-3.42z"></path>
            <circle cx="6.5" cy="9.5" r=".5" fill="currentColor"></circle>
          </svg>
          Classify
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'extraction' }" @click.prevent="activeView = 'extraction'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
            <path d="M4 7V4a2 2 0 0 1 2-2 2 2 0 0 0-2 2"></path>
            <path d="M4.063 20.999a2 2 0 0 0 2 1L18 22a2 2 0 0 0 2-2V7l-5-5H6"></path>
            <path d="m5 11-3 3"></path>
            <path d="m5 17-3-3h10"></path>
          </svg>
          Extract
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'split' }" @click.prevent="activeView = 'split'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="6" cy="6" r="3"></circle>
            <path d="M8.12 8.12 12 12"></path>
            <path d="M20 4 8.12 15.88"></path>
            <circle cx="6" cy="18" r="3"></circle>
            <path d="M14.8 14.8 20 20"></path>
          </svg>
          Split
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'journey' }" @click.prevent="activeView = 'journey'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 12H3"></path>
            <path d="M16 6H3"></path>
            <path d="M12 18H3"></path>
            <path d="m16 12 5 3-5 3v-6Z"></path>
          </svg>
          Doc Journey
        </a>
      </div>

      <!-- File List -->
      <div class="file-list-section">
        <div class="file-list-header">
          <span class="file-list-title">Uploaded Files</span>
          <button class="add-more-btn" @click="triggerFileInput">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
        <div class="file-list">
          <div
            v-for="file in files"
            :key="file.id"
            class="file-item"
            :class="{ 
              selected: selectedFile?.id === file.id,
              processing: file.status === 'processing',
              completed: file.status === 'completed',
              error: file.status === 'error'
            }"
            @click="handleSelectFile(file)"
          >
            <svg class="file-item-icon" width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
              <path v-if="file.type === 'pdf'" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
              <path v-else fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
            </svg>
            <span class="file-item-name">{{ file.name }}</span>
            <div v-if="file.status === 'processing'" class="file-item-status">
              <div class="file-item-spinner"></div>
            </div>
            <button class="file-item-delete" @click.stop="handleRemoveFile(file.id)">
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Parse View -->
      <div v-if="activeView === 'parse'" class="content-wrapper">
        <!-- Upload/Preview Section -->
        <div class="upload-section">
          <!-- Upload Dropzone or Preview -->
          <div v-if="!previewFile" 
            class="upload-dropzone"
            :class="{ 'drag-over': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="dropzone-text">Drop files here or click to upload</p>
            <p class="dropzone-subtext">Supported: PNG, JPG, JPEG, PDF (max 10MB)</p>
          </div>

          <div v-else class="preview-area">
            <div v-if="previewFile && previewFile.type === 'pdf'" class="pdf-preview-wrapper">
              <iframe 
                v-if="pdfSourceUrl"
                :key="`pdf-${previewFile.id}`"
                :src="pdfSourceUrl" 
                type="application/pdf" 
                class="pdf-embed"
                frameborder="0"
              />
              <div v-else class="preview-error">
                <p>Unable to load PDF preview</p>
                <p style="font-size: 12px; color: #6b7280;">Debug: pdfSourceUrl={{ pdfSourceUrl }}, previewFileUrl={{ previewFileUrl }}</p>
              </div>
            </div>
            <div v-else-if="previewFile && previewFile.type !== 'pdf'" class="image-preview-wrapper">
              <img 
                v-if="previewFileUrl"
                :src="previewFileUrl" 
                :alt="previewFile.name"
                class="image-embed"
                :style="{ transform: `scale(${zoom / 100})` }"
              />
              <div v-else class="preview-error">
                <p>Unable to load image preview</p>
                <p style="font-size: 12px; color: #6b7280;">Debug: previewFileUrl is empty</p>
              </div>
            </div>
          </div>

          <input
            ref="fileInput"
            type="file"
            accept=".png,.jpg,.jpeg,.pdf"
            multiple
            style="display: none"
            @change="handleFileSelect"
          />
        </div>

        <!-- Config Panel -->
        <div class="config-panel">
          <div class="panel-tabs">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              class="panel-tab"
              :class="{ active: activeTab === tab.id }"
              @click="activeTab = tab.id"
            >
              <!-- Sliders icon for Build tab -->
              <svg v-if="tab.icon === 'sliders'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="21" x2="14" y1="4" y2="4"></line>
                <line x1="10" x2="3" y1="4" y2="4"></line>
                <line x1="21" x2="12" y1="12" y2="12"></line>
                <line x1="8" x2="3" y1="12" y2="12"></line>
                <line x1="21" x2="16" y1="20" y2="20"></line>
                <line x1="12" x2="3" y1="20" y2="20"></line>
                <line x1="14" x2="14" y1="2" y2="6"></line>
                <line x1="8" x2="8" y1="10" y2="14"></line>
                <line x1="16" x2="16" y1="18" y2="22"></line>
              </svg>
              <!-- Document icon for Result tabs -->
              <svg v-else-if="tab.icon === 'document'" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {{ tab.label }}
            </button>
          </div>

          <div class="panel-content">
            <!-- Build Tab -->
            <div v-if="activeTab === 'build'" class="config-section">
              <div class="config-header">
                <span class="config-label" style="display: flex; align-items: center; gap: 6px; margin-bottom: 12px;">Parser Tiers</span>
              </div>
              <div class="tier-selector">
                <div class="tier-bars">
                  <button class="tier-bar rapid" @click="selectTier('Rapid')"></button>
                  <button class="tier-bar normal" @click="selectTier('Normal')"></button>
                  <button class="tier-bar advance" @click="selectTier('Advance')"></button>
                </div>
                <div class="tier-labels">
                  <button
                    class="tier-label-btn"
                    :class="{ active: selectedTier === 'Rapid' }"
                    @click="selectTier('Rapid')"
                  >
                    <div class="tier-indicator"></div>
                    <span class="tier-label-text">Rapid</span>
                  </button>
                  <button
                    class="tier-label-btn"
                    :class="{ active: selectedTier === 'Normal' }"
                    @click="selectTier('Normal')"
                  >
                    <div class="tier-indicator"></div>
                    <span class="tier-label-text">Normal</span>
                  </button>
                  <button
                    class="tier-label-btn"
                    :class="{ active: selectedTier === 'Advance' }"
                    @click="selectTier('Advance')"
                  >
                    <div class="tier-indicator"></div>
                    <span class="tier-label-text">Advance</span>
                  </button>
                </div>
              </div>

              <div class="config-header" style="margin-top: 24px;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                  <input type="checkbox" v-model="processAllPages" />
                  <span class="config-label">Process all PDF pages</span>
                </label>
              </div>

              <div class="config-header" style="margin-top: 12px;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                  <input type="checkbox" v-model="processAllFiles" />
                  <span class="config-label">Process all files</span>
                </label>
              </div>
            </div>

            <!-- Results Tabs -->
            <div v-if="activeTab !== 'build'" class="results-section">
              <div v-if="!results" class="results-placeholder">
                <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>No results yet</p>
              </div>
              <div v-else-if="!results.success" class="results-container">
                <p style="color: #dc2626;">Error: {{ results.error }}</p>
              </div>
              <div v-else>
                <!-- Raw Result -->
                <div v-if="activeTab === 'raw'" class="results-container">
                  {{ currentPageResult }}
                </div>
                
                <!-- Parsed Result -->
                <div v-if="activeTab === 'parsed'" class="parsed-result-container" v-html="parsedResultHtml"></div>
              </div>
            </div>
          </div>

          <!-- Panel Footer -->
          <div class="panel-footer">
            <div class="panel-footer-left">
              <!-- Edit Button -->
              <button
                v-if="results && results.success && activeTab !== 'build'"
                class="edit-btn"
                @click="openFullScreenEditor"
              >
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit
              </button>
            </div>
            <div class="panel-footer-center">
              <!-- Spinner when processing -->
              <div v-if="isProcessing" class="spinner"></div>
              
              <!-- Pagination for results -->
              <div v-else-if="results && results.success && totalResultPages > 1 && activeTab !== 'build'" class="results-pagination">
                <button class="pagination-btn" @click="prevResultPage" :disabled="!canGoPrevResult">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <span class="pagination-indicator">{{ currentResultPage }} / {{ totalResultPages }}</span>
                <button class="pagination-btn" @click="nextResultPage" :disabled="!canGoNextResult">
                  <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="panel-footer-right">
              <button
                v-if="isProcessing"
                class="cancel-btn"
                @click="handleCancel"
              >
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
                Cancel
              </button>
              <button
                class="run-parse-btn"
                :disabled="!canProcess || isProcessing"
                @click="handleProcess"
              >
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {{ isProcessing ? 'Processing...' : 'Process' }}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Classify View -->
      <div v-if="activeView === 'classify'" class="content-wrapper">
        <!-- Upload/Preview Section -->
        <div class="upload-section">
          <!-- Upload Dropzone or Preview -->
          <div v-if="!previewFile" 
            class="upload-dropzone"
            :class="{ 'drag-over': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="dropzone-text">Drop files here or click to upload</p>
            <p class="dropzone-subtext">Supported: PNG, JPG, JPEG, PDF (max 10MB)</p>
          </div>

          <div v-else class="preview-area">
            <div v-if="previewFile && previewFile.type === 'pdf'" class="pdf-preview-wrapper">
              <iframe 
                v-if="pdfSourceUrl"
                :key="`pdf-${previewFile.id}`"
                :src="pdfSourceUrl" 
                type="application/pdf" 
                class="pdf-embed"
                frameborder="0"
              />
              <div v-else class="preview-error">
                <p>Unable to load PDF preview</p>
              </div>
            </div>
            <div v-else-if="previewFile && previewFile.type !== 'pdf'" class="image-preview-wrapper">
              <img 
                v-if="previewFileUrl"
                :src="previewFileUrl" 
                :alt="previewFile.name"
                class="image-embed"
                :style="{ transform: `scale(${zoom / 100})` }"
              />
              <div v-else class="preview-error">
                <p>Unable to load image preview</p>
              </div>
            </div>
          </div>
          
          <!-- Hidden file input for classify view -->
          <input
            ref="fileInput"
            type="file"
            accept=".png,.jpg,.jpeg,.pdf"
            multiple
            style="display: none"
            @change="handleFileSelect"
          />
        </div>

        <!-- Classify Config Panel -->
        <div class="config-panel">
          <div class="panel-tabs">
            <button
              v-for="tab in classifyTabs"
              :key="tab.id"
              class="panel-tab"
              :class="{ active: classifyActiveTab === tab.id }"
              @click="classifyActiveTab = tab.id"
            >
              <!-- Sliders icon for Build tab -->
              <svg v-if="tab.icon === 'sliders'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="21" x2="14" y1="4" y2="4"></line>
                <line x1="10" x2="3" y1="4" y2="4"></line>
                <line x1="21" x2="12" y1="12" y2="12"></line>
                <line x1="8" x2="3" y1="12" y2="12"></line>
                <line x1="21" x2="16" y1="20" y2="20"></line>
                <line x1="12" x2="3" y1="20" y2="20"></line>
                <line x1="14" x2="14" y1="2" y2="6"></line>
                <line x1="8" x2="8" y1="10" y2="14"></line>
                <line x1="16" x2="16" y1="18" y2="22"></line>
              </svg>
              <!-- Document icon for Result tabs -->
              <svg v-else-if="tab.icon === 'document'" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {{ tab.label }}
            </button>
          </div>
          
          <ClassifyConfigPanel
            :available-models="availableModels"
            :is-processing="isProcessing"
            :can-process="canProcess"
            :active-tab="classifyActiveTab"
            :selected-file="selectedFileObject"
            :extraction-result="results?.results"
            :field-errors="results?.field_errors"
            @process="handleClassifyProcess"
            @cancel="handleClassifyCancel"
            @update:activeTab="classifyActiveTab = $event"
          />
        </div>
      </div>
      
      <!-- Extraction View -->
      <div v-if="activeView === 'extraction'" class="content-wrapper">
        <!-- Upload/Preview Section -->
        <div class="upload-section">
          <!-- Upload Dropzone or Preview -->
          <div v-if="!previewFile" 
            class="upload-dropzone"
            :class="{ 'drag-over': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="dropzone-text">Drop files here or click to upload</p>
            <p class="dropzone-subtext">Supported: PNG, JPG, JPEG, PDF (max 10MB)</p>
          </div>

          <div v-else class="preview-area">
            <div v-if="previewFile && previewFile.type === 'pdf'" class="pdf-preview-wrapper">
              <iframe 
                v-if="pdfSourceUrl"
                :key="`pdf-${previewFile.id}`"
                :src="pdfSourceUrl" 
                type="application/pdf" 
                class="pdf-embed"
                frameborder="0"
              />
              <div v-else class="preview-error">
                <p>Unable to load PDF preview</p>
              </div>
            </div>
            <div v-else-if="previewFile && previewFile.type !== 'pdf'" class="image-preview-wrapper">
              <img 
                v-if="previewFileUrl"
                :src="previewFileUrl" 
                :alt="previewFile.name"
                class="image-embed"
                :style="{ transform: `scale(${zoom / 100})` }"
              />
              <div v-else class="preview-error">
                <p>Unable to load image preview</p>
              </div>
            </div>
          </div>
          
          <!-- Hidden file input for extraction view -->
          <input
            ref="fileInput"
            type="file"
            accept=".png,.jpg,.jpeg,.pdf"
            multiple
            style="display: none"
            @change="handleFileSelect"
          />
        </div>

        <!-- Extraction Config Panel -->
        <div class="config-panel">
          <div class="panel-tabs">
            <button
              v-for="tab in extractionTabs"
              :key="tab.id"
              class="panel-tab"
              :class="{ active: extractionActiveTab === tab.id }"
              @click="extractionActiveTab = tab.id"
            >
              <!-- Sliders icon for Build tab -->
              <svg v-if="tab.icon === 'sliders'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="21" x2="14" y1="4" y2="4"></line>
                <line x1="10" x2="3" y1="4" y2="4"></line>
                <line x1="21" x2="12" y1="12" y2="12"></line>
                <line x1="8" x2="3" y1="12" y2="12"></line>
                <line x1="21" x2="16" y1="20" y2="20"></line>
                <line x1="12" x2="3" y1="20" y2="20"></line>
                <line x1="14" x2="14" y1="2" y2="6"></line>
                <line x1="8" x2="8" y1="10" y2="14"></line>
                <line x1="16" x2="16" y1="18" y2="22"></line>
              </svg>
              <!-- Document icon for Result tabs -->
              <svg v-else-if="tab.icon === 'document'" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {{ tab.label }}
            </button>
          </div>
          
          <ConfigPanel
            :available-models="availableModels"
            :is-processing="isProcessing"
            :can-process="canProcess"
            :active-tab="extractionActiveTab"
            :selected-file="selectedFileObject"
            :extraction-result="results?.extraction?.structured_data"
            :field-errors="results?.extraction?.field_errors"
            @process="handleExtractionProcess"
            @cancel="handleExtractionCancel"
            @update:activeTab="extractionActiveTab = $event"
          />
        </div>
      </div>
      
      <!-- Split View -->
      <div v-if="activeView === 'split'" class="content-wrapper">
        <!-- Upload/Preview Section -->
        <div class="upload-section">
          <!-- Upload Dropzone or Preview -->
          <div v-if="!previewFile" 
            class="upload-dropzone"
            :class="{ 'drag-over': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="dropzone-text">Drop files here or click to upload</p>
            <p class="dropzone-subtext">Supported: PNG, JPG, JPEG, PDF (max 10MB)</p>
          </div>

          <div v-else class="preview-area">
            <div v-if="previewFile && previewFile.type === 'pdf'" class="pdf-preview-wrapper">
              <iframe 
                v-if="pdfSourceUrl"
                :key="`pdf-${previewFile.id}`"
                :src="pdfSourceUrl" 
                type="application/pdf" 
                class="pdf-embed"
                frameborder="0"
              />
              <div v-else class="preview-error">
                <p>Unable to load PDF preview</p>
              </div>
            </div>
            <div v-else-if="previewFile && previewFile.type !== 'pdf'" class="image-preview-wrapper">
              <img 
                v-if="previewFileUrl"
                :src="previewFileUrl" 
                :alt="previewFile.name"
                class="image-embed"
                :style="{ transform: `scale(${zoom / 100})` }"
              />
              <div v-else class="preview-error">
                <p>Unable to load image preview</p>
              </div>
            </div>
          </div>
          
          <!-- Hidden file input for split view -->
          <input
            ref="fileInput"
            type="file"
            accept=".png,.jpg,.jpeg,.pdf"
            multiple
            style="display: none"
            @change="handleFileSelect"
          />
        </div>

        <!-- Split Config Panel -->
        <div class="config-panel">
          <div class="panel-tabs">
            <button
              v-for="tab in splitTabs"
              :key="tab.id"
              class="panel-tab"
              :class="{ active: splitActiveTab === tab.id }"
              @click="splitActiveTab = tab.id"
            >
              <!-- Sliders icon for Build tab -->
              <svg v-if="tab.icon === 'sliders'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="21" x2="14" y1="4" y2="4"></line>
                <line x1="10" x2="3" y1="4" y2="4"></line>
                <line x1="21" x2="12" y1="12" y2="12"></line>
                <line x1="8" x2="3" y1="12" y2="12"></line>
                <line x1="21" x2="16" y1="20" y2="20"></line>
                <line x1="12" x2="3" y1="20" y2="20"></line>
                <line x1="14" x2="14" y1="2" y2="6"></line>
                <line x1="8" x2="8" y1="10" y2="14"></line>
                <line x1="16" x2="16" y1="18" y2="22"></line>
              </svg>
              <!-- Document icon for Result tabs -->
              <svg v-else-if="tab.icon === 'document'" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {{ tab.label }}
            </button>
          </div>
          
          <SplitConfigPanel
            :available-models="availableModels"
            :is-processing="isProcessing"
            :can-process="canProcess"
            :active-tab="splitActiveTab"
            :selected-file="selectedFileObject"
            :split-result="results"
            :field-errors="results?.field_errors"
            @process="handleSplitProcess"
            @cancel="handleSplitCancel"
            @update:activeTab="splitActiveTab = $event"
          />
        </div>
      </div>
      
      <!-- Journey View -->
      <JourneyWorkflow v-if="activeView === 'journey'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import { useOCR } from '~/composables/useOCR'
import { useFilePreview } from '~/composables/useFilePreview'
import ConfigPanel from '~/components/ConfigPanel.vue'
import ClassifyConfigPanel from '~/components/ClassifyConfigPanel.vue'
import SplitConfigPanel from '~/components/SplitConfigPanel.vue'
import JourneyWorkflow from '~/components/JourneyWorkflow.vue'
import HelpDialog from '~/components/HelpDialog.vue'
import DeployDialog from '~/components/DeployDialog.vue'

// Composables
const {
  files,
  isProcessing,
  results,
  availableModels,
  uploadFiles,
  processFile,
  classifyFile,
  splitFile,
  removeFile,
  checkHealth,
  clearFiles,
  cancelProcessing
} = useOCR()

const {
  previewFile,
  zoom,
  currentPage,
  totalPages,
  canGoNext,
  canGoPrev,
  canZoomIn,
  canZoomOut,
  setPreviewFile,
  zoomIn,
  zoomOut,
  nextPage,
  prevPage
} = useFilePreview()

// Local state
const activeView = ref('parse') // 'parse' or 'extraction'
const selectedFile = ref<any>(null)
const uploadedFiles = ref<Map<string, File>>(new Map())
const previewFileUrl = ref<string>('')
const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const activeTab = ref('build')
const selectedTier = ref('Normal')
const processAllPages = ref(true)
const processAllFiles = ref(false)
const currentResultPage = ref(1)
const resultsPerPage = 1000 // characters per page
const isCancelling = ref(false)
const isEditMode = ref(false)
const editableRawResult = ref('')
const editableParsedResult = ref('')
const showFullScreenEditor = ref(false)

const tabs = [
  { 
    id: 'build', 
    label: 'Build',
    icon: 'sliders'
  },
  { 
    id: 'raw', 
    label: 'Raw Result',
    icon: 'document'
  },
  { 
    id: 'parsed', 
    label: 'Parsed Result',
    icon: 'document'
  }
]

const extractionTabs = [
  { 
    id: 'build', 
    label: 'Build',
    icon: 'sliders'
  },
  { 
    id: 'result', 
    label: 'Result',
    icon: 'document'
  }
]

const classifyTabs = [
  { 
    id: 'build', 
    label: 'Build',
    icon: 'sliders'
  },
  { 
    id: 'result', 
    label: 'Result',
    icon: 'document'
  }
]

const splitTabs = [
  { 
    id: 'build', 
    label: 'Build',
    icon: 'sliders'
  },
  { 
    id: 'result', 
    label: 'Result',
    icon: 'document'
  }
]

const extractionActiveTab = ref('build')
const classifyActiveTab = ref('build')
const splitActiveTab = ref('build')

// Tier to model mapping
const tierToModel: Record<string, string> = {
  'Rapid': 'assistant',
  'Normal': 'gemini-3-flash',
  'Advance': 'gemini-3-pro'
}

// Check health on mount
onMounted(async () => {
  await checkHealth()
})

// Watch for changes to previewFileUrl
watch(previewFileUrl, (newVal, oldVal) => {
  console.log('previewFileUrl changed from', oldVal, 'to', newVal)
})

// Watch for changes to currentResultPage
watch(currentResultPage, (newVal, oldVal) => {
  console.log('currentResultPage changed from', oldVal, 'to', newVal)
  console.log('previewFileUrl is:', previewFileUrl.value)
  console.log('previewFile is:', previewFile.value)
})

// Computed
const canProcess = computed(() => {
  // If "Process all files" is enabled, check if there are any files without results
  if (processAllFiles.value) {
    return files.value.some(f => !f.result || f.status === 'pending' || f.status === 'error') && !isProcessing.value
  }
  // Otherwise, check if a file is selected
  return selectedFile.value && !isProcessing.value
})

const selectedModel = computed(() => {
  return tierToModel[selectedTier.value]
})

// Get the actual File object for the selected file
const selectedFileObject = computed(() => {
  if (!selectedFile.value) return null
  return uploadedFiles.value.get(selectedFile.value.id) || null
})

// Parse results into pages (split by "--- Page X ---" markers)
const resultPages = computed(() => {
  if (!results.value?.text) return []
  
  const text = results.value.text
  
  // Check if text contains page markers (from process_all_pages)
  if (text.includes('--- Page')) {
    // Split by page markers
    const pages = text.split(/--- Page \d+ ---\n/).filter(p => p.trim())
    return pages
  }
  
  // Single page result
  return [text]
})

// Results pagination
const totalResultPages = computed(() => {
  return Math.max(resultPages.value.length, 1)
})

const currentPageResult = computed(() => {
  if (resultPages.value.length === 0) return ''
  const pageIndex = currentResultPage.value - 1
  return resultPages.value[pageIndex] || resultPages.value[0]
})

const canGoNextResult = computed(() => currentResultPage.value < totalResultPages.value)
const canGoPrevResult = computed(() => currentResultPage.value > 1)

// Computed property for PDF source URL (stable reference)
const pdfSourceUrl = computed(() => {
  if (!previewFileUrl.value) return ''
  return `${previewFileUrl.value}#page=${currentResultPage.value}`
})

// Cache for parsed HTML to avoid expensive recomputation
const parsedHtmlCache = ref<Map<string, string>>(new Map())

// Parsed result (parse markdown, HTML, and mixed content into human-readable format)
const parsedResultHtml = computed(() => {
  if (!currentPageResult.value) return ''
  
  const text = currentPageResult.value
  
  // Create a cache key based on the text content
  const cacheKey = `${currentResultPage.value}-${text.substring(0, 100)}`
  
  // Return cached result if available
  if (parsedHtmlCache.value.has(cacheKey)) {
    return parsedHtmlCache.value.get(cacheKey)!
  }
  
  let html = ''
  
  // Detect if content contains HTML tables
  const hasHtmlTable = /<table[\s\S]*?<\/table>/i.test(text)
  
  // Detect if content has HTML tags (but not just table tags)
  const hasHtmlTags = /<(?!table|\/table|tr|\/tr|td|\/td|th|\/th|tbody|\/tbody|thead|\/thead)[a-z][\s\S]*?>/i.test(text)
  
  // Detect CommonMark/Markdown syntax (simplified to avoid catastrophic backtracking)
  const hasMarkdownSyntax = /(\*\*|__|\#|\[.*?\]\(.*?\)|```|^\s*[-*]|\n\d+\.)/.test(text)
  
  // Strategy 1: Mixed HTML and Markdown (some models output HTML tables with markdown text)
  if (hasHtmlTable && hasMarkdownSyntax) {
    try {
      // Extract HTML tables and replace with unique markers
      const tables: string[] = []
      const markers: string[] = []
      
      let processedText = text.replace(/<table[\s\S]*?<\/table>/gi, (match) => {
        const index = tables.length
        tables.push(match)
        // Use a unique marker that won't be escaped by marked
        const marker = `|||TABLE_MARKER_${index}|||`
        markers.push(marker)
        return marker
      })
      
      // Parse the markdown parts
      let html = marked.parse(processedText, {
        breaks: true,
        gfm: true,
        pedantic: false
      }) as string
      
      // Restore HTML tables - try multiple patterns
      tables.forEach((table, index) => {
        const marker = markers[index]
        // Try different patterns that marked might create
        const patterns = [
          new RegExp(`<p>\\|\\|\\|TABLE_MARKER_${index}\\|\\|\\|</p>`, 'g'),
          new RegExp(`\\|\\|\\|TABLE_MARKER_${index}\\|\\|\\|`, 'g')
        ]
        
        patterns.forEach(pattern => {
          html = html.replace(pattern, table)
        })
      })
      
      // Remove script tags for security
      html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      
      // Cache and return
      parsedHtmlCache.value.set(cacheKey, html)
      return html
    } catch (error) {
      console.error('Mixed content parsing error:', error)
    }
  }
  
  // Strategy 2: Pure HTML content (including tables without markdown)
  if (hasHtmlTable || (hasHtmlTags && !hasMarkdownSyntax)) {
    // Sanitize and return HTML
    html = text
    // Remove script tags for security
    html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    // Ensure proper spacing around block elements
    html = html.replace(/<\/(p|div|table|h[1-6])>/gi, '</$1>\n')
    
    // Cache and return
    parsedHtmlCache.value.set(cacheKey, html)
    return html
  }
  
  // Strategy 3: CommonMark/Markdown content
  if (hasMarkdownSyntax) {
    try {
      // Configure marked for CommonMark compliance
      html = marked.parse(text, {
        breaks: true,
        gfm: true, // GitHub Flavored Markdown (superset of CommonMark)
        pedantic: false,
        headerIds: false,
        mangle: false
      }) as string
      
      // Cache and return
      parsedHtmlCache.value.set(cacheKey, html)
      return html
    } catch (error) {
      console.error('Markdown parsing error:', error)
    }
  }
  
  // Strategy 4: Plain text - apply intelligent formatting
  html = text
  
  // Detect and format tables in plain text (pipe-separated)
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
        
        // Check if it's a separator line (|---|---|)
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
  
  // Bold text **text** or __text__
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>')
  
  // Italic text *text* or _text_
  html = html.replace(/(?<!\*)\*([^\*]+?)\*(?!\*)/g, '<em>$1</em>')
  html = html.replace(/(?<!_)_([^_]+?)_(?!_)/g, '<em>$1</em>')
  
  // Headers (lines that end with :)
  html = html.replace(/<p>(.+?):<\/p>/g, '<h3>$1:</h3>')
  
  // Lists (lines starting with - or *)
  html = html.replace(/<br>[\-\*]\s+(.+?)(?=<br>|<\/p>)/g, '<li>$1</li>')
  html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>')
  
  // Numbered lists
  html = html.replace(/<br>\d+\.\s+(.+?)(?=<br>|<\/p>)/g, '<li>$1</li>')
  html = html.replace(/(<li>.*?<\/li>)+/g, (match) => {
    if (!match.includes('<ul>')) {
      return '<ol>' + match + '</ol>'
    }
    return match
  })
  
  // Cache and return
  parsedHtmlCache.value.set(cacheKey, html)
  return html
})

// Handlers
const selectTier = (tier: string) => {
  selectedTier.value = tier
}

// Handlers
const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const newFiles = Array.from(target.files || [])
  await handleUpload(newFiles)
  if (target) target.value = ''
}

const handleDrop = async (e: DragEvent) => {
  isDragging.value = false
  const newFiles = Array.from(e.dataTransfer?.files || [])
  await handleUpload(newFiles)
}

const handleUpload = async (newFiles: File[]) => {
  // Upload files first to get the file items with IDs
  const result = await uploadFiles(newFiles)
  
  // Show notification for duplicates
  if (result.duplicates.length > 0) {
    const { warning } = useNotification()
    if (result.duplicates.length === 1) {
      warning(`File "${result.duplicates[0]}" is already uploaded`)
    } else {
      warning(`${result.duplicates.length} duplicate files skipped: ${result.duplicates.slice(0, 2).join(', ')}${result.duplicates.length > 2 ? '...' : ''}`)
    }
  }
  
  // Store the actual File objects with matching IDs
  if (files.value.length > 0 && result.added > 0) {
    // Get the newly added files (last N files where N = result.added)
    const newlyAddedFiles = files.value.slice(-result.added)
    
    // Map only the unique files that were actually added
    const uniqueNewFiles = newFiles.filter(f => !result.duplicates.includes(f.name))
    
    newlyAddedFiles.forEach((fileItem, index) => {
      uploadedFiles.value.set(fileItem.id, uniqueNewFiles[index])
    })
    
    // Auto-select first file if none selected
    if (!selectedFile.value) {
      const firstFile = newlyAddedFiles[0]
      selectedFile.value = firstFile
      setPreviewFile(firstFile)
      
      // Generate preview URL for the first file
      const fileObj = uniqueNewFiles[0]
      if (fileObj) {
        try {
          previewFileUrl.value = URL.createObjectURL(fileObj)
        } catch (error) {
          console.error('Error creating object URL:', error)
          previewFileUrl.value = ''
        }
      }
    }
  }
}

const handleSelectFile = (file: any) => {
  console.log('handleSelectFile called with:', file)
  selectedFile.value = file
  setPreviewFile(file)
  currentResultPage.value = 1 // Reset to page 1 when selecting a new file
  
  // Load the file's result if it exists
  if (file.result) {
    results.value = file.result
    console.log('Loaded existing result for file:', file.name)
  } else {
    results.value = null
    console.log('No result available for file:', file.name)
  }
  
  // Generate preview URL once when file is selected
  const fileObj = uploadedFiles.value.get(file.id)
  console.log('File object from map:', fileObj)
  if (fileObj) {
    try {
      // Revoke old URL if exists
      if (previewFileUrl.value) {
        URL.revokeObjectURL(previewFileUrl.value)
      }
      previewFileUrl.value = URL.createObjectURL(fileObj)
      console.log('Created preview URL:', previewFileUrl.value)
    } catch (error) {
      console.error('Error creating object URL:', error)
      previewFileUrl.value = ''
    }
  } else {
    console.error('File not found in uploadedFiles map')
    previewFileUrl.value = ''
  }
}

const handleRemoveFile = (fileId: string) => {
  // Revoke the object URL if this is the selected file
  if (selectedFile.value?.id === fileId && previewFileUrl.value) {
    URL.revokeObjectURL(previewFileUrl.value)
    previewFileUrl.value = ''
  }
  
  uploadedFiles.value.delete(fileId)
  removeFile(fileId)
  
  if (selectedFile.value?.id === fileId) {
    selectedFile.value = null
    setPreviewFile(null)
  }
}

const handleProcess = async () => {
  console.log('handleProcess called')
  console.log('selectedFile:', selectedFile.value)
  console.log('processAllFiles:', processAllFiles.value)
  console.log('canProcess:', canProcess.value)
  console.log('isProcessing:', isProcessing.value)
  
  // If "Process all files" is enabled, process all files without results
  if (processAllFiles.value) {
    const filesToProcess = files.value.filter(f => !f.result || f.status === 'pending' || f.status === 'error')
    
    if (filesToProcess.length === 0) {
      console.log('No files to process - all files already have results')
      return
    }
    
    console.log(`Processing ${filesToProcess.length} files`)
    
    // Process each file sequentially
    for (const fileItem of filesToProcess) {
      const file = uploadedFiles.value.get(fileItem.id)
      
      if (!file) {
        console.error('File not found in uploaded files map:', fileItem.id)
        continue
      }
      
      console.log('Processing file:', fileItem.name, 'with model:', selectedModel.value)
      
      await processFile(fileItem.id, file, {
        modelId: selectedModel.value,
        tier: selectedTier.value as 'Rapid' | 'Normal' | 'Advance',
        processAllPages: processAllPages.value
      })
    }
    
    // Switch to raw text tab after processing
    activeTab.value = 'raw'
    return
  }
  
  // Single file processing (original behavior)
  if (!selectedFile.value) {
    console.log('No file selected')
    return
  }
  
  const file = uploadedFiles.value.get(selectedFile.value.id)
  console.log('File from map:', file)
  console.log('uploadedFiles map:', uploadedFiles.value)
  
  if (!file) {
    console.error('File not found in uploaded files map')
    return
  }
  
  console.log('Processing with model:', selectedModel.value)
  
  // Reset to page 1 before processing
  currentResultPage.value = 1
  
  // Clear parsed HTML cache when processing new file
  parsedHtmlCache.value.clear()
  
  await processFile(selectedFile.value.id, file, {
    modelId: selectedModel.value,
    tier: selectedTier.value as 'Rapid' | 'Normal' | 'Advance',
    processAllPages: processAllPages.value
  })
  
  // Switch to raw text tab after processing
  activeTab.value = 'raw'
}

const handleCancel = () => {
  console.log('Cancel clicked - stopping OCR process')
  // Set cancelling flag
  isCancelling.value = true
  
  // Force stop processing by resetting the processing state
  isProcessing.value = false
  
  // Update file statuses to cancelled
  files.value.forEach(file => {
    if (file.status === 'processing') {
      file.status = 'error'
    }
  })
  
  // Reset cancelling flag
  setTimeout(() => {
    isCancelling.value = false
  }, 100)
  
  console.log('OCR process cancelled')
}

const handleRefresh = async () => {
  console.log('Refresh clicked!')
  
  // Clear all uploaded files
  clearFiles()
  
  // Reset local state
  selectedFile.value = null
  setPreviewFile(null)
  activeTab.value = 'build'
  selectedTier.value = 'Normal'
  processAllPages.value = true
  processAllFiles.value = false
  currentResultPage.value = 1
  
  // Revoke all object URLs to free memory
  uploadedFiles.value.forEach((file, id) => {
    if (previewFileUrl.value) {
      try {
        URL.revokeObjectURL(previewFileUrl.value)
      } catch (error) {
        console.error('Error revoking URL:', error)
      }
    }
  })
  
  // Clear uploaded files map
  uploadedFiles.value.clear()
  previewFileUrl.value = ''
  
  // Clear parsed HTML cache
  parsedHtmlCache.value.clear()
  
  // Check backend health
  await checkHealth()
  
  console.log('App reset completed')
}

const showFeedbackDialog = ref(false)
const showHelpDialog = ref(false)
const showDeployDialog = ref(false)

const handleFeedback = () => {
  showFeedbackDialog.value = true
}

const handleHelp = () => {
  showHelpDialog.value = true
}

const handleDeploy = () => {
  showDeployDialog.value = true
}

const getTabName = (view: string) => {
  const tabNames: Record<string, string> = {
    'parse': 'Parse',
    'classify': 'Classify',
    'extraction': 'Extract',
    'split': 'Split',
    'journey': 'Doc Journey'
  }
  return tabNames[view] || 'Parse'
}

const handleFeedbackSubmit = (feedback: { type: string; message: string }) => {
  console.log('Feedback submitted:', feedback)
  // Here you can add API call to send feedback to backend
  // For now, just log it
}

const nextResultPage = () => {
  if (canGoNextResult.value) {
    currentResultPage.value++
  }
}

const prevResultPage = () => {
  if (canGoPrevResult.value) {
    currentResultPage.value--
  }
}

const openFullScreenEditor = () => {
  showFullScreenEditor.value = true
}

const handleEditorUpdate = (text: string) => {
  // Update the result text
  if (results.value && results.value.text) {
    const pageIndex = currentResultPage.value - 1
    if (resultPages.value.length > 0) {
      resultPages.value[pageIndex] = text
      // Reconstruct the full text with page markers
      const updatedPages = resultPages.value.map((page, idx) => {
        if (idx === 0) return page
        return `--- Page ${idx + 1} ---\n${page}`
      })
      results.value.text = updatedPages.join('\n')
    } else {
      results.value.text = text
    }
    
    // Update the selected file's result to persist changes
    if (selectedFile.value && selectedFile.value.result) {
      selectedFile.value.result.text = results.value.text
    }
    
    // Clear parsed HTML cache to force re-render
    parsedHtmlCache.value.clear()
  }
}

const handleEditorPageChange = (page: number) => {
  currentResultPage.value = page
}

const handleExtractionProcess = async (config: any) => {
  console.log('Extraction process triggered with config:', config)
  
  // Clear current results before processing
  results.value = null
  
  // If processAllFiles is enabled, process all unprocessed files
  if (config.processAllFiles) {
    console.log('Processing all unprocessed files with extraction')
    
    // Get all files that don't have results yet (status is 'pending')
    const unprocessedFiles = files.value.filter(f => f.status === 'pending')
    
    if (unprocessedFiles.length === 0) {
      console.log('No unprocessed files to extract')
      return
    }
    
    // Process each unprocessed file sequentially
    for (const fileItem of unprocessedFiles) {
      const file = uploadedFiles.value.get(fileItem.id)
      if (file) {
        console.log(`Processing file: ${fileItem.name}`)
        await processFile(fileItem.id, file, config)
      }
    }
    
    // Switch to result tab after processing all files
    extractionActiveTab.value = 'result'
    return
  }
  
  // Single file processing
  if (!selectedFile.value) {
    console.log('No file selected for extraction')
    return
  }
  
  const file = uploadedFiles.value.get(selectedFile.value.id)
  
  if (!file) {
    console.error('File not found in uploaded files map')
    return
  }
  
  console.log('Processing extraction with config:', config)
  
  // Reset to page 1 before processing
  currentResultPage.value = 1
  
  // Clear parsed HTML cache when processing new file
  parsedHtmlCache.value.clear()
  
  await processFile(selectedFile.value.id, file, config)
  
  // Switch to result tab after processing
  extractionActiveTab.value = 'result'
}

const handleExtractionCancel = () => {
  console.log('Cancelling extraction process')
  cancelProcessing()
}

const handleClassifyProcess = async (config: any) => {
  console.log('Classify process triggered with config:', config)
  
  // Clear current results before processing
  results.value = null
  
  // If processAllFiles is enabled, process all unprocessed files
  if (config.processAllFiles) {
    console.log('Processing all unprocessed files with classification')
    
    // Get all files that don't have results yet (status is 'pending')
    const unprocessedFiles = files.value.filter(f => f.status === 'pending')
    
    if (unprocessedFiles.length === 0) {
      console.log('No unprocessed files to classify')
      return
    }
    
    // Array to collect all classification results
    const allResults: any[] = []
    
    // Process each unprocessed file sequentially
    for (const fileItem of unprocessedFiles) {
      const file = uploadedFiles.value.get(fileItem.id)
      if (file) {
        console.log(`Classifying file: ${fileItem.name}`)
        await classifyFile(fileItem.id, file, config)
        
        // Collect result if successful
        if (fileItem.result?.success && fileItem.result?.results) {
          allResults.push(...fileItem.result.results)
        }
      }
    }
    
    // Set aggregated results
    if (allResults.length > 0) {
      results.value = {
        success: true,
        results: allResults
      }
    }
    
    // Switch to result tab after processing all files
    classifyActiveTab.value = 'result'
    return
  }
  
  // Single file processing
  if (!selectedFile.value) {
    console.log('No file selected for classification')
    return
  }
  
  const file = uploadedFiles.value.get(selectedFile.value.id)
  
  if (!file) {
    console.error('File not found in uploaded files map')
    return
  }
  
  console.log('Classifying with config:', config)
  
  await classifyFile(selectedFile.value.id, file, config)
  
  // Switch to result tab after processing
  classifyActiveTab.value = 'result'
}

const handleClassifyCancel = () => {
  console.log('Cancelling classify process')
  cancelProcessing()
}

const handleSplitProcess = async (config: any) => {
  console.log('[index.vue] Split process triggered with config:', config)
  console.log('[index.vue] selectedFile:', selectedFile.value)
  console.log('[index.vue] isProcessing:', isProcessing.value)
  
  // Clear current results before processing
  results.value = null
  
  // If processAllFiles is enabled, process all unprocessed files
  if (config.processAllFiles) {
    console.log('[index.vue] Processing all unprocessed files with split')
    
    // Get all files that don't have results yet (status is 'pending')
    const unprocessedFiles = files.value.filter(f => f.status === 'pending')
    
    if (unprocessedFiles.length === 0) {
      console.log('[index.vue] No unprocessed files to split')
      return
    }
    
    // Process each unprocessed file sequentially
    for (const fileItem of unprocessedFiles) {
      const file = uploadedFiles.value.get(fileItem.id)
      if (file) {
        console.log(`[index.vue] Splitting file: ${fileItem.name}`)
        await splitFile(fileItem.id, file, config)
      }
    }
    
    // Switch to result tab after processing all files
    splitActiveTab.value = 'result'
    return
  }
  
  // Single file processing
  if (!selectedFile.value) {
    console.log('[index.vue] No file selected for split')
    return
  }
  
  const file = uploadedFiles.value.get(selectedFile.value.id)
  
  if (!file) {
    console.error('[index.vue] File not found in uploaded files map')
    console.error('[index.vue] selectedFile.id:', selectedFile.value.id)
    console.error('[index.vue] uploadedFiles keys:', Array.from(uploadedFiles.value.keys()))
    return
  }
  
  console.log('[index.vue] Calling splitFile with:', {
    fileId: selectedFile.value.id,
    fileName: file.name,
    config
  })
  
  await splitFile(selectedFile.value.id, file, config)
  
  console.log('[index.vue] splitFile completed, switching to result tab')
  
  // Switch to result tab after processing
  splitActiveTab.value = 'result'
}

const handleSplitCancel = () => {
  console.log('Cancelling split process')
  cancelProcessing()
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
</style>
