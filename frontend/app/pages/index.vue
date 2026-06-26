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

    <!-- File Compare Dialog (Original vs OCR Result) -->
    <div v-if="showFileCompareDialog" class="file-compare-overlay" @click.self="showFileCompareDialog = false">
      <div class="file-compare-container">
        <!-- Header -->
        <div class="file-compare-header">
          <div class="file-compare-title">
            <svg class="file-item-icon" width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
              <path v-if="compareFile?.type === 'pdf'" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
              <path v-else fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
            </svg>
            <span>{{ compareFile?.name }}</span>
          </div>
          <button class="file-compare-close" @click="showFileCompareDialog = false">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <!-- Body: Split View -->
        <div class="file-compare-body">
          <!-- Left: Original Document -->
          <div class="file-compare-left">
            <div class="file-compare-panel-label">Original Document</div>
            <div class="file-compare-preview">
              <iframe
                v-if="comparePreviewUrl && compareFile?.type === 'pdf'"
                :src="comparePreviewUrl"
                class="file-compare-iframe"
                frameborder="0"
              />
              <img
                v-else-if="comparePreviewUrl"
                :src="comparePreviewUrl"
                :alt="compareFile?.name"
                class="file-compare-image"
              />
              <div v-else class="file-compare-unavailable">
                <svg width="40" height="40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>Preview not available</p>
              </div>
            </div>
          </div>
          <!-- Right: OCR Result -->
          <div class="file-compare-right">
            <div class="file-compare-panel-label">OCR Result</div>
            <div class="file-compare-result">
              <div v-if="compareFile?.result?.text || compareFile?.result?.success" class="file-compare-result-content">
                <pre class="file-compare-text">{{ compareFile?.result?.text || JSON.stringify(compareFile?.result, null, 2) }}</pre>
              </div>
              <div v-else class="file-compare-no-result">
                <svg width="40" height="40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>No OCR result yet</p>
                <p class="file-compare-hint">Process this file first to see results</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
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
        <img src="/assets/logo.png" alt="Doc Intelligence" class="logo-icon" @click="handleRefresh" />
        <span class="logo-text" @click="handleRefresh">Doc Intelligence</span>
      </div>
      <div class="top-bar-actions">
        <button class="top-bar-btn" @click="handleFeedback">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          {{ t('topbar.feedback') }}
        </button>
        <button class="top-bar-btn" @click="handleHelp">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {{ t('topbar.help') }}
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
          {{ t('sidebar.parse') }}
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'classify' }" @click.prevent="activeView = 'classify'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m15 5 6.3 6.3a2.4 2.4 0 0 1 0 3.4L17 19"></path>
            <path d="M9.586 5.586A2 2 0 0 0 8.172 5H3a1 1 0 0 0-1 1v5.172a2 2 0 0 0 .586 1.414L8.29 18.29a2.426 2.426 0 0 0 3.42 0l3.58-3.58a2.426 2.426 0 0 0 0-3.42z"></path>
            <circle cx="6.5" cy="9.5" r=".5" fill="currentColor"></circle>
          </svg>
          {{ t('sidebar.classify') }}
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'extraction' }" @click.prevent="activeView = 'extraction'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
            <path d="M4 7V4a2 2 0 0 1 2-2 2 2 0 0 0-2 2"></path>
            <path d="M4.063 20.999a2 2 0 0 0 2 1L18 22a2 2 0 0 0 2-2V7l-5-5H6"></path>
            <path d="m5 11-3 3"></path>
            <path d="m5 17-3-3h10"></path>
          </svg>
          {{ t('sidebar.extract') }}
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'split' }" @click.prevent="activeView = 'split'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="6" cy="6" r="3"></circle>
            <path d="M8.12 8.12 12 12"></path>
            <path d="M20 4 8.12 15.88"></path>
            <circle cx="6" cy="18" r="3"></circle>
            <path d="M14.8 14.8 20 20"></path>
          </svg>
          {{ t('sidebar.split') }}
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'data' }" @click.prevent="activeView = 'data'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
            <path d="M3 5V19A9 3 0 0 0 21 19V5"></path>
            <path d="M3 12A9 3 0 0 0 21 12"></path>
          </svg>
          Data
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'search' }" @click.prevent="activeView = 'search'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.3-4.3"></path>
          </svg>
          Search
        </a>
        <a href="#" class="nav-item" :class="{ active: activeView === 'journey' }" @click.prevent="activeView = 'journey'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 12H3"></path>
            <path d="M16 6H3"></path>
            <path d="M12 18H3"></path>
            <path d="m16 12 5 3-5 3v-6Z"></path>
          </svg>
          {{ t('sidebar.journey') }}
        </a>
      </div>

      <!-- File List -->
      <div class="file-list-section">
        <div class="file-list-header">
          <span class="file-list-title">{{ t('page.uploadedFiles') }}</span>
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
            draggable="true"
            @dragstart="handleFileDragStart($event, file)"
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

      <!-- Settings at bottom -->
      <div class="sidebar-bottom">
        <a href="#" class="nav-item nav-item-settings" :class="{ active: activeView === 'settings' }" @click.prevent="activeView = 'settings'">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          Settings
        </a>
      </div>
    </div>

    <!-- Global hidden file input (always rendered, accessible from any view) -->
    <input
      ref="fileInput"
      type="file"
      accept=".png,.jpg,.jpeg,.pdf"
      multiple
      style="display: none"
      @change="handleFileSelect"
    />

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
            @drop.prevent="handlePreviewDrop"
            @click="triggerFileInput"
          >
            <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="dropzone-text">{{ t('page.dropzone') }}</p>
            <p class="dropzone-subtext">{{ t('page.dropzoneFormats') }}</p>
          </div>

          <div v-else class="preview-area">
            <!-- Permanent drop zone overlay (always present, activates on drag via CSS) -->
            <div
              class="preview-drop-zone"
              :class="{ active: isSidebarDragging }"
              @dragover.prevent="isSidebarDragging = true"
              @dragleave.prevent="isSidebarDragging = false"
              @drop.prevent="handlePreviewDrop"
            >
              <p>Drop file here to replace</p>
            </div>
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
                <p>{{ t('page.previewError.pdf') }}</p>
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
                <p>{{ t('page.previewError.image') }}</p>
              </div>
            </div>
          </div>

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
              <!-- Model Selector for Parse -->
              <ModelSelector
                v-if="providers && providers.length > 0"
                v-model="parseSelectedModel"
                :providers="providers"
                :disabled="isProcessing"
                label="Parser Model"
              />

              <div class="config-header" style="margin-top: 24px;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                  <input type="checkbox" v-model="processAllPages" />
                  <span class="config-label">{{ t('page.processAllPages') }}</span>
                </label>
              </div>

              <div class="config-header" style="margin-top: 12px;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                  <input type="checkbox" v-model="processAllFiles" />
                  <span class="config-label">{{ t('page.processAllFiles') }}</span>
                </label>
              </div>
            </div>

            <!-- Results Tabs -->
            <div v-if="activeTab !== 'build'" class="results-section">
              <div v-if="!results" class="results-placeholder">
                <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p>{{ t('page.noResults') }}</p>
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
                {{ t('page.edit') }}
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
                {{ isProcessing ? t('page.processing') : t('page.process') }}
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
            @drop.prevent="handlePreviewDrop"
            @click="triggerFileInput"
          >
            <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="dropzone-text">{{ t('page.dropzone') }}</p>
            <p class="dropzone-subtext">{{ t('page.dropzoneFormats') }}</p>
          </div>

          <div v-else class="preview-area">
            <!-- Permanent drop zone overlay (always present, activates on drag via CSS) -->
            <div
              class="preview-drop-zone"
              :class="{ active: isSidebarDragging }"
              @dragover.prevent="isSidebarDragging = true"
              @dragleave.prevent="isSidebarDragging = false"
              @drop.prevent="handlePreviewDrop"
            >
              <p>Drop file here to replace</p>
            </div>
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
                <p>{{ t('page.previewError.pdf') }}</p>
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
                <p>{{ t('page.previewError.image') }}</p>
              </div>
            </div>
          </div>
          
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
            :providers="providers"
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
            @drop.prevent="handlePreviewDrop"
            @click="triggerFileInput"
          >
            <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="dropzone-text">{{ t('page.dropzone') }}</p>
            <p class="dropzone-subtext">{{ t('page.dropzoneFormats') }}</p>
          </div>

          <div v-else class="preview-area">
            <!-- Permanent drop zone overlay (always present, activates on drag via CSS) -->
            <div
              class="preview-drop-zone"
              :class="{ active: isSidebarDragging }"
              @dragover.prevent="isSidebarDragging = true"
              @dragleave.prevent="isSidebarDragging = false"
              @drop.prevent="handlePreviewDrop"
            >
              <p>Drop file here to replace</p>
            </div>
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
                <p>{{ t('page.previewError.pdf') }}</p>
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
                <p>{{ t('page.previewError.image') }}</p>
              </div>
            </div>
          </div>
          
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
            :providers="providers"
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
            @drop.prevent="handlePreviewDrop"
            @click="triggerFileInput"
          >
            <svg class="dropzone-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p class="dropzone-text">{{ t('page.dropzone') }}</p>
            <p class="dropzone-subtext">{{ t('page.dropzoneFormats') }}</p>
          </div>

          <div v-else class="preview-area">
            <!-- Permanent drop zone overlay (always present, activates on drag via CSS) -->
            <div
              class="preview-drop-zone"
              :class="{ active: isSidebarDragging }"
              @dragover.prevent="isSidebarDragging = true"
              @dragleave.prevent="isSidebarDragging = false"
              @drop.prevent="handlePreviewDrop"
            >
              <p>Drop file here to replace</p>
            </div>
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
                <p>{{ t('page.previewError.pdf') }}</p>
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
                <p>{{ t('page.previewError.image') }}</p>
              </div>
            </div>
          </div>
          
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
            :providers="providers"
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
      <JourneyDashboard v-if="activeView === 'journey' && !journeyBuilderOpen && !journeyDetailOpen" @open-builder="handleOpenJourneyBuilder" @open-detail="handleOpenJourneyDetail" />
      <JourneyWorkflowDetail v-if="activeView === 'journey' && journeyDetailOpen && !journeyBuilderOpen" :workflow-id="editingWorkflowId!" @back="journeyDetailOpen = false" @open-builder="handleOpenJourneyBuilderFromDetail" />
      <JourneyWorkflow v-if="activeView === 'journey' && journeyBuilderOpen" :workflow-id="editingWorkflowId" @back="handleBackFromBuilder" />

      <!-- Data Store View -->
      <DataStorePanel
        v-if="activeView === 'data'"
        :providers="providers"
      />

      <!-- Document Search View (feat-070) -->
      <SearchPanel v-if="activeView === 'search'" />

      <!-- Settings View -->
      <div v-if="activeView === 'settings'" class="content-wrapper settings-view">
        <div class="settings-inner">

        <!-- Error tooltip portal -->
        <Teleport to="body">
          <div
            v-if="errorTooltip.visible"
            class="error-tooltip"
            :style="{ top: errorTooltip.y + 'px', left: errorTooltip.x + 'px' }"
          >
            <div class="error-tooltip-header">
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Error Details
            </div>
            <div class="error-tooltip-body">{{ errorTooltip.message }}</div>
          </div>
        </Teleport>
          <!-- Settings Sidebar Nav -->
          <aside class="settings-aside">
            <nav class="settings-nav">
              <button
                class="settings-nav-item"
                :class="{ active: settingsTab === 'providers' }"
                @click="settingsTab = 'providers'"
              >
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Providers
              </button>
              <button
                class="settings-nav-item"
                :class="{ active: settingsTab === 'tiers' }"
                @click="settingsTab = 'tiers'"
              >
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
                Tier Config
              </button>
              <button
                class="settings-nav-item"
                :class="{ active: settingsTab === 'language' }"
                @click="settingsTab = 'language'"
              >
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
                Language
              </button>
            </nav>
          </aside>

          <!-- Settings Main Content -->
          <main class="settings-main">

            <!-- Providers Tab -->
            <section v-if="settingsTab === 'providers'">
              <div class="settings-section-header">
                <div class="section-header-row">
                  <div>
                    <h2 class="settings-section-title">AI Providers</h2>
                    <p class="settings-section-desc">Configure the AI providers used for OCR, classification, extraction, and splitting.</p>
                  </div>
                  <button class="add-provider-btn" @click="openAddProviderModal">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M5 12h14"></path>
                      <path d="M12 5v14"></path>
                    </svg>
                    Add AI Provider
                  </button>
                </div>
              </div>

              <div v-if="settingsLoading" class="settings-loading">
                <div class="spinner"></div>
                <span>Loading providers…</span>
              </div>
              <div v-else-if="settingsError" class="settings-error-banner">
                {{ settingsError }}
                <button class="retry-btn" @click="reloadProviders">Retry</button>
              </div>
              <div v-else class="provider-grid">
                <div
                  v-for="provider in settingsProviders"
                  :key="provider.id"
                  class="provider-card"
                  :class="{ configured: provider.configured, unconfigured: !provider.configured }"
                >
                  <div class="card-header">
                    <div class="provider-identity">
                      <div class="provider-icon" :class="`icon-${provider.id}`">
                        {{ provider.name.charAt(0).toUpperCase() }}
                      </div>
                      <div>
                        <h3 class="provider-name">{{ provider.name }}</h3>
                        <span class="provider-type-badge" :class="provider.type">
                          {{ provider.type === 'cloud' ? '☁ Cloud' : '🖥 Local' }}
                        </span>
                      </div>
                    </div>
                    <div class="card-header-right">
                      <div class="status-pill" :class="provider.status">
                        <span class="status-dot"></span>
                        {{ ({
                          not_configured: 'Not Configured',
                          configured: 'Configured',
                          ready: 'Ready',
                          timeout: 'Time Out',
                          error: 'Error'
                        } as Record<string, string>)[provider.status] ?? provider.status }}
                      </div>
                      <!-- Gear icon to open config modal -->
                      <button
                        class="gear-btn"
                        :title="`Configure ${provider.name}`"
                        @click="openConfigModal(provider)"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
                          <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                      </button>
                    </div>
                  </div>

                  <p class="provider-desc">{{ provider.description }}</p>

                  <!-- Inline API key editor — always shown for all providers -->
                  <div class="inline-key-row">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="key-icon">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                    </svg>
                    <div class="inline-key-field">
                      <input
                        :type="inlineKeyVisible[provider.id] ? 'text' : 'password'"
                        class="inline-key-input"
                        :class="{ 'has-value': provider.credential_set, 'no-key': !provider.credential_key }"
                        :value="inlineKeyValues[provider.id] ?? ''"
                        :placeholder="provider.credential_set
                          ? (provider.credential_preview ?? provider.key_placeholder ?? 'No API key required')
                          : (provider.key_placeholder ?? 'No API key required')"
                        :disabled="!provider.credential_key"
                        @input="(e) => debounceSaveKey(provider, (e.target as HTMLInputElement).value)"
                        autocomplete="off"
                      />
                      <div class="inline-key-actions">
                        <button v-if="provider.credential_key" type="button" class="inline-key-btn"
                          @click="inlineKeyVisible[provider.id] = !inlineKeyVisible[provider.id]">
                          <svg v-if="inlineKeyVisible[provider.id]" width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                          </svg>
                          <svg v-else width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </button>
                        <!-- saving indicator -->
                        <svg v-if="inlineSaving[provider.id + '_key']" class="spin" width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      </div>
                    </div>
                  </div>

                  <div class="url-row">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                    <div class="inline-key-field">
                      <input
                        type="text"
                        class="inline-key-input"
                        :value="inlineUrlValues[provider.id] ?? provider.base_url ?? ''"
                        :placeholder="provider.type === 'local' ? 'http://localhost:1234' : 'https://api.example.com'"
                        @input="(e) => debounceSaveUrl(provider, (e.target as HTMLInputElement).value)"
                      />
                      <svg v-if="inlineSaving[provider.id + '_url']" class="spin" width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </div>
                  </div>

                  <div class="rpm-row">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span class="rpm-label">RPM:</span>
                    <div class="inline-key-field">
                      <input
                        type="number"
                        min="1"
                        step="1"
                        class="inline-key-input"
                        :value="inlineRpmValues[provider.id] ?? provider.rpm ?? ''"
                        :placeholder="provider.type === 'local' ? '10' : '60'"
                        @input="(e) => { const v = parseInt((e.target as HTMLInputElement).value); if (v > 0) debounceSaveRpm(provider, v) }"
                      />
                      <svg v-if="inlineSaving[provider.id + '_rpm']" class="spin" width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </div>
                  </div>

                  <div v-if="provider.models.length" class="models-section">
                    <p class="models-label">Models ({{ provider.models.length }})</p>
                    <div class="models-chips">
                      <span v-for="model in provider.models" :key="model.model_id" class="model-chip" :title="model.model_id">
                        {{ model.name }}
                      </span>
                    </div>
                  </div>
                  <div v-else class="no-models">No models configured for this provider.</div>

                  <div class="card-footer">
                    <div class="test-result" v-if="settingsTestResults[provider.id]">
                      <span
                        class="test-badge"
                        :class="settingsTestResults[provider.id].success ? 'success' : 'fail'"
                        @mouseenter="!settingsTestResults[provider.id].success && showErrorTooltip($event, settingsTestResults[provider.id].message)"
                        @mouseleave="hideErrorTooltip"
                      >
                        {{ settingsTestResults[provider.id].success ? 'Successfully' : 'Unsuccessfully' }}
                      </span>
                    </div>
                    <button
                      class="test-btn"
                      :disabled="settingsTestingProvider === provider.id"
                      @click="runTestConnection(provider.id)"
                    >
                      <svg v-if="settingsTestingProvider === provider.id" class="spin" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <svg v-else width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      {{ settingsTestingProvider === provider.id ? 'Testing…' : 'Test Connection' }}
                    </button>
                  </div>
                </div>
              </div>

              <div class="refresh-row">
                <button class="refresh-btn" :disabled="settingsLoading" @click="reloadProviders">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Refresh
                </button>
              </div>

              <!-- ── Config Modal ─────────────────────────────────────── -->
              <Teleport to="body">
                <Transition name="modal">
                  <div v-if="configModal.open" class="modal-overlay" @click.self="configModal.open = false">
                    <div class="modal-box">
                      <div class="modal-header">
                        <div class="modal-title-row">
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                          <h3 class="modal-title">Configure {{ configModal.provider?.name }}</h3>
                        </div>
                        <button class="modal-close" @click="configModal.open = false">
                          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>

                      <div class="modal-body">
                        <!-- API Key -->
                        <div v-if="configModal.provider?.credential_key" class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                            API Key
                            <code class="modal-env-hint">{{ configModal.provider.credential_key }}</code>
                          </label>
                          <div class="modal-input-row">
                            <input
                              v-model="configModal.apiKey"
                              :type="configModal.showKey ? 'text' : 'password'"
                              class="modal-input"
                              placeholder="Enter API key…"
                              autocomplete="off"
                            />
                            <button class="toggle-vis-btn" type="button" @click="configModal.showKey = !configModal.showKey">
                              <svg v-if="configModal.showKey" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                              </svg>
                              <svg v-else width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            </button>
                          </div>
                        </div>

                        <!-- Base URL (local providers) -->
                        <div v-if="configModal.provider?.type === 'local'" class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                            </svg>
                            Base URL
                          </label>
                          <input
                            v-model="configModal.baseUrl"
                            type="text"
                            class="modal-input"
                            placeholder="http://localhost:1234"
                          />
                        </div>

                        <!-- RPM -->
                        <div class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Requests per Minute (RPM)
                          </label>
                          <input
                            v-model.number="configModal.rpm"
                            type="number"
                            min="1"
                            max="10000"
                            class="modal-input modal-input-sm"
                            placeholder="60"
                          />
                          <p class="modal-hint">Limit how many requests per minute are sent to this provider.</p>
                        </div>

                        <div v-if="configModal.saveMsg" class="modal-save-msg" :class="configModal.saveOk ? 'ok' : 'err'">
                          {{ configModal.saveMsg }}
                        </div>
                      </div>

                      <div class="modal-footer">
                        <button class="modal-cancel-btn" @click="configModal.open = false">Cancel</button>
                        <button class="modal-save-btn" :disabled="configModal.saving" @click="saveProviderConfig">
                          <svg v-if="configModal.saving" class="spin" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          {{ configModal.saving ? 'Saving…' : 'Save' }}
                        </button>
                      </div>
                    </div>
                  </div>
                </Transition>
              </Teleport>

              <!-- ── Add Provider Modal ──────────────────────────────── -->
              <Teleport to="body">
                <Transition name="modal">
                  <div v-if="addProviderModal.open" class="modal-overlay" @click.self="addProviderModal.open = false">
                    <div class="modal-box">
                      <div class="modal-header">
                        <div class="modal-title-row">
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M5 12h14"></path>
                            <path d="M12 5v14"></path>
                          </svg>
                          <h3 class="modal-title">Add AI Provider</h3>
                        </div>
                        <button class="modal-close" @click="addProviderModal.open = false">
                          <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>

                      <div class="modal-body">
                        <!-- Provider ID -->
                        <div class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                            </svg>
                            Provider ID
                            <span class="modal-hint-inline">e.g. my_provider</span>
                          </label>
                          <input
                            v-model="addProviderModal.id"
                            type="text"
                            class="modal-input"
                            placeholder="e.g. openai, anthropic, custom_llm"
                          />
                        </div>

                        <!-- Display Name -->
                        <div class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
                            </svg>
                            Display Name
                          </label>
                          <input
                            v-model="addProviderModal.name"
                            type="text"
                            class="modal-input"
                            placeholder="e.g. OpenAI, Anthropic"
                          />
                        </div>

                        <!-- Type -->
                        <div class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                            </svg>
                            Type
                          </label>
                          <div class="type-toggle">
                            <button
                              type="button"
                              :class="['type-btn', { active: addProviderModal.type === 'cloud' }]"
                              @click="addProviderModal.type = 'cloud'"
                            >☁ Cloud</button>
                            <button
                              type="button"
                              :class="['type-btn', { active: addProviderModal.type === 'local' }]"
                              @click="addProviderModal.type = 'local'"
                            >🖥 Local</button>
                          </div>
                        </div>

                        <!-- API Key env var name (cloud) -->
                        <div v-if="addProviderModal.type === 'cloud'" class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                            API Key
                          </label>
                          <div class="modal-input-row">
                            <input
                              v-model="addProviderModal.apiKey"
                              :type="addProviderModal.showKey ? 'text' : 'password'"
                              class="modal-input"
                              placeholder="Paste your API key…"
                              autocomplete="off"
                            />
                            <button class="toggle-vis-btn" type="button" @click="addProviderModal.showKey = !addProviderModal.showKey">
                              <svg v-if="addProviderModal.showKey" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                              </svg>
                              <svg v-else width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            </button>
                          </div>
                          <p class="modal-hint">Will be stored as <code>{{ addProviderModal.id ? addProviderModal.id.toUpperCase() + '_API_KEY' : 'PROVIDER_API_KEY' }}</code> in .env</p>
                        </div>

                        <!-- Base URL -->
                        <div class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                            </svg>
                            Base URL
                            <span class="modal-hint-inline">{{ addProviderModal.type === 'local' ? 'required' : 'optional' }}</span>
                          </label>
                          <input
                            v-model="addProviderModal.baseUrl"
                            type="text"
                            class="modal-input"
                            :placeholder="addProviderModal.type === 'local' ? 'http://localhost:1234' : 'https://api.example.com/v1'"
                          />
                        </div>

                        <!-- RPM -->
                        <div class="modal-field">
                          <label class="modal-label">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Requests per Minute (RPM)
                            <span class="modal-hint-inline">optional</span>
                          </label>
                          <input
                            v-model.number="addProviderModal.rpm"
                            type="number"
                            min="1"
                            max="10000"
                            class="modal-input modal-input-sm"
                            placeholder="60"
                          />
                        </div>

                        <div v-if="addProviderModal.saveMsg" class="modal-save-msg" :class="addProviderModal.saveOk ? 'ok' : 'err'">
                          {{ addProviderModal.saveMsg }}
                        </div>
                      </div>

                      <div class="modal-footer">
                        <button class="modal-cancel-btn" @click="addProviderModal.open = false">Cancel</button>
                        <button
                          class="modal-save-btn"
                          :disabled="addProviderModal.saving || !addProviderModal.id.trim() || !addProviderModal.name.trim()"
                          @click="saveNewProvider"
                        >
                          <svg v-if="addProviderModal.saving" class="spin" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          {{ addProviderModal.saving ? 'Adding…' : 'Add Provider' }}
                        </button>
                      </div>
                    </div>
                  </div>
                </Transition>
              </Teleport>
            </section>

            <!-- Tier Config Tab -->
            <section v-if="settingsTab === 'tiers'">
              <div class="settings-section-header">
                <div class="section-header-row">
                  <div>
                    <h2 class="settings-section-title">Tier Configuration</h2>
                    <p class="settings-section-desc">Select Provider → Model for each feature and tier. Changes apply immediately.</p>
                  </div>
                  <div class="tier-header-actions">
                    <span v-if="tierSaveMsg" class="tier-save-msg" :class="tierSaveOk ? 'ok' : 'err'">
                      {{ tierSaveMsg }}
                    </span>
                    <button class="add-provider-btn" :disabled="tierSaving" @click="saveTierConfig">
                      <svg v-if="tierSaving" class="spin" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <svg v-else width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                      {{ tierSaving ? 'Saving…' : 'Save Changes' }}
                    </button>
                  </div>
                </div>
              </div>

              <div v-if="settingsTierConfig && settingsProviders.length" class="tier-table-wrapper">
                <table class="tier-table">
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th v-for="tier in settingsTierConfig.tiers.filter((t: string) => t !== 'Multimodal')" :key="tier">{{ tier }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in tierRows" :key="row.feature">
                      <td class="feature-cell">{{ row.label }}</td>
                      <td v-for="tier in settingsTierConfig.tiers.filter((t: string) => t !== 'Multimodal')" :key="tier" class="tier-cell">
                        <select
                          class="tier-select"
                          :value="getTierSelectValue(row.feature, tier)"
                          @change="(e) => onTierSelectChange(row.feature, tier, (e.target as HTMLSelectElement).value)"
                        >
                          <option value="">— select model —</option>
                          <optgroup v-for="p in settingsProviders.filter((p: any) => p.models?.length && p.ready)" :key="p.id" :label="p.name">
                            <option
                              v-for="m in p.models"
                              :key="m.model_id"
                              :value="`${p.id}::${m.model_id}`"
                            >
                              {{ m.name }}
                            </option>
                          </optgroup>
                          <!-- Show non-ready providers as disabled group -->
                          <optgroup
                            v-for="p in settingsProviders.filter((p: any) => p.models?.length && !p.ready)"
                            :key="`nr-${p.id}`"
                            :label="`${p.name} (not ready — test connection first)`"
                          >
                            <option
                              v-for="m in p.models"
                              :key="m.model_id"
                              :value="`${p.id}::${m.model_id}`"
                              disabled
                            >
                              {{ m.name }}
                            </option>
                          </optgroup>
                        </select>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="settings-loading">
                <div class="spinner"></div>
                <span>Loading tier config…</span>
              </div>
            </section>

            <!-- Language Tab -->
            <section v-if="settingsTab === 'language'">
              <div class="settings-section-header">
                <div class="section-header-row">
                  <div>
                    <h2 class="settings-section-title">Language / Ngôn ngữ</h2>
                    <p class="settings-section-desc">Choose your preferred display language. The setting is saved automatically.</p>
                  </div>
                </div>
              </div>

              <div class="language-options">
                <label class="language-option" :class="{ active: locale === 'en' }">
                  <input type="radio" name="language" value="en" :checked="locale === 'en'" @change="setLocale('en')" />
                  <div class="language-option-content">
                    <span class="language-flag">🇺🇸</span>
                    <div class="language-info">
                      <span class="language-name">English</span>
                      <span class="language-native">English</span>
                    </div>
                  </div>
                  <span v-if="locale === 'en'" class="language-check">✓</span>
                </label>

                <label class="language-option" :class="{ active: locale === 'vi' }">
                  <input type="radio" name="language" value="vi" :checked="locale === 'vi'" @change="setLocale('vi')" />
                  <div class="language-option-content">
                    <span class="language-flag">🇻🇳</span>
                    <div class="language-info">
                      <span class="language-name">Vietnamese</span>
                      <span class="language-native">Tiếng Việt</span>
                    </div>
                  </div>
                  <span v-if="locale === 'vi'" class="language-check">✓</span>
                </label>
              </div>
            </section>

          </main>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import { useOCR } from '~/composables/useOCR'
import { useFilePreview } from '~/composables/useFilePreview'
import { useProviders } from '~/composables/useProviders'
import { useLocale } from '~/composables/useLocale'
import { useTranslation } from '~/composables/useTranslation'
import ConfigPanel from '~/components/ConfigPanel.vue'
import ClassifyConfigPanel from '~/components/ClassifyConfigPanel.vue'
import SplitConfigPanel from '~/components/SplitConfigPanel.vue'
import JourneyWorkflow from '~/components/JourneyWorkflow.vue'
import JourneyDashboard from '~/components/JourneyDashboard.vue'
import JourneyWorkflowDetail from '~/components/JourneyWorkflowDetail.vue'
import HelpDialog from '~/components/HelpDialog.vue'
import DeployDialog from '~/components/DeployDialog.vue'
import ModelSelector from '~/components/ModelSelector.vue'
import DataStorePanel from '~/components/DataStorePanel.vue'
import SearchPanel from '~/components/SearchPanel.vue'

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
  cancelProcessing,
  loadUploads
} = useOCR()

const { locale, setLocale } = useLocale()
const { t } = useTranslation()

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
const journeyBuilderOpen = ref(false)
const journeyDetailOpen = ref(false)
const editingWorkflowId = ref<string | null>(null)
const selectedFile = ref<any>(null)
const uploadedFiles = ref<Map<string, File>>(new Map())
const previewFileUrl = ref<string>('')
const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const isSidebarDragging = ref(false)
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

const tabs = computed(() => [
  { 
    id: 'build', 
    label: t('tab.build'),
    icon: 'sliders'
  },
  { 
    id: 'raw', 
    label: t('tab.raw'),
    icon: 'document'
  },
  { 
    id: 'parsed', 
    label: t('tab.parsed'),
    icon: 'document'
  }
])

const extractionTabs = computed(() => [
  { 
    id: 'build', 
    label: t('tab.build'),
    icon: 'sliders'
  },
  { 
    id: 'result', 
    label: t('tab.result'),
    icon: 'document'
  }
])

const classifyTabs = computed(() => [
  { 
    id: 'build', 
    label: t('tab.build'),
    icon: 'sliders'
  },
  { 
    id: 'result', 
    label: t('tab.result'),
    icon: 'document'
  }
])

const splitTabs = computed(() => [
  { 
    id: 'build', 
    label: t('tab.build'),
    icon: 'sliders'
  },
  { 
    id: 'result', 
    label: t('tab.result'),
    icon: 'document'
  }
])

const extractionActiveTab = ref('build')
const classifyActiveTab = ref('build')
const splitActiveTab = ref('build')
const parseSelectedModel = ref('')

// Settings view state
const settingsTab = ref<'providers' | 'tiers' | 'language'>('providers')
const settingsProviders = ref<any[]>([])
const settingsLoading = ref(false)
const settingsError = ref<string | null>(null)
const settingsTestResults = ref<Record<string, any>>({})
const settingsTestingProvider = ref<string | null>(null)
const settingsTierConfig = ref<any>(null)

// Inline key editing state
const inlineKeyValues = ref<Record<string, string>>({})
const inlineKeyEditing = ref<Record<string, boolean>>({})
const inlineKeyVisible = ref<Record<string, boolean>>({})

// Inline URL editing state
const inlineUrlValues = ref<Record<string, string>>({})
const inlineUrlEditing = ref<Record<string, boolean>>({})

// Inline RPM editing state
const inlineRpmValues = ref<Record<string, number | undefined>>({})
const inlineRpmEditing = ref<Record<string, boolean>>({})

// Saving indicator per field
const inlineSaving = ref<Record<string, boolean>>({})

// Debounce timers
const _debounceTimers: Record<string, ReturnType<typeof setTimeout>> = {}

const _debounce = (key: string, fn: () => void, delay = 800) => {
  clearTimeout(_debounceTimers[key])
  _debounceTimers[key] = setTimeout(fn, delay)
}

const debounceSaveKey = (provider: any, value: string) => {
  inlineKeyValues.value[provider.id] = value
  if (!value.trim() || !provider.credential_key) return
  _debounce(`${provider.id}_key`, async () => {
    inlineSaving.value[`${provider.id}_key`] = true
    try {
      const apiBaseUrl = (config.public.apiBaseUrl as string)
      await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, {
        method: 'POST', body: { api_key: value.trim() },
      })
      await reloadProviders()
    } catch (e) { console.error('Auto-save key failed:', e) }
    finally { inlineSaving.value[`${provider.id}_key`] = false }
  })
}

const debounceSaveUrl = (provider: any, value: string) => {
  inlineUrlValues.value[provider.id] = value
  _debounce(`${provider.id}_url`, async () => {
    inlineSaving.value[`${provider.id}_url`] = true
    try {
      const apiBaseUrl = (config.public.apiBaseUrl as string)
      await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, {
        method: 'POST', body: { base_url: value.trim() },
      })
      await reloadProviders()
    } catch (e) { console.error('Auto-save URL failed:', e) }
    finally { inlineSaving.value[`${provider.id}_url`] = false }
  })
}

const debounceSaveRpm = (provider: any, value: number) => {
  inlineRpmValues.value[provider.id] = value
  _debounce(`${provider.id}_rpm`, async () => {
    inlineSaving.value[`${provider.id}_rpm`] = true
    try {
      const apiBaseUrl = (config.public.apiBaseUrl as string)
      await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, {
        method: 'POST', body: { rpm: Math.max(1, Math.floor(value)) },
      })
      await reloadProviders()
    } catch (e) { console.error('Auto-save RPM failed:', e) }
    finally { inlineSaving.value[`${provider.id}_rpm`] = false }
  })
}

// Error tooltip state
const errorTooltip = reactive({
  visible: false,
  message: '',
  x: 0,
  y: 0,
})

const showErrorTooltip = (event: MouseEvent, message: string) => {
  const rect = (event.target as HTMLElement).getBoundingClientRect()
  errorTooltip.message = message
  errorTooltip.x = rect.left
  errorTooltip.y = rect.top - 8  // anchor to top of badge, CSS will translateY(-100%)
  errorTooltip.visible = true
}

const hideErrorTooltip = () => {
  errorTooltip.visible = false
}

const startInlineEdit = (providerId: string) => {
  inlineKeyEditing.value[providerId] = true
}

const onInlineKeyInput = (providerId: string, value: string) => {
  inlineKeyValues.value[providerId] = value
}

const cancelInlineEdit = (providerId: string) => {
  inlineKeyEditing.value[providerId] = false
  delete inlineKeyValues.value[providerId]
}

const saveInlineKey = async (provider: any) => {
  const value = inlineKeyValues.value[provider.id]
  if (!value?.trim()) {
    cancelInlineEdit(provider.id)
    return
  }
  try {
    const apiBaseUrl = (config.public.apiBaseUrl as string)
    await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, {
      method: 'POST',
      body: { api_key: value.trim() },
    })
    inlineKeyEditing.value[provider.id] = false
    delete inlineKeyValues.value[provider.id]
    await reloadProviders()
  } catch (e: any) {
    console.error('Failed to save key:', e)
  }
}

const cancelInlineUrl = (providerId: string) => {
  inlineUrlEditing.value[providerId] = false
  delete inlineUrlValues.value[providerId]
}

const saveInlineUrl = async (provider: any) => {
  const value = inlineUrlValues.value[provider.id]
  inlineUrlEditing.value[provider.id] = false
  if (value === undefined) return
  try {
    const apiBaseUrl = (config.public.apiBaseUrl as string)
    await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, {
      method: 'POST',
      body: { base_url: value.trim() },
    })
    delete inlineUrlValues.value[provider.id]
    await reloadProviders()
  } catch (e: any) {
    console.error('Failed to save URL:', e)
  }
}

const cancelInlineRpm = (providerId: string) => {
  inlineRpmEditing.value[providerId] = false
  delete inlineRpmValues.value[providerId]
}

const saveInlineRpm = async (provider: any) => {
  const value = inlineRpmValues.value[provider.id]
  inlineRpmEditing.value[provider.id] = false
  if (value === undefined || value === null) return
  const rpm = Math.max(1, Math.floor(value))
  try {
    const apiBaseUrl = (config.public.apiBaseUrl as string)
    await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, {
      method: 'POST',
      body: { rpm },
    })
    delete inlineRpmValues.value[provider.id]
    await reloadProviders()
  } catch (e: any) {
    console.error('Failed to save RPM:', e)
  }
}

// Tier editing state
const tierEdits = ref<Record<string, Record<string, { provider: string; model: string }>>>({})
const tierSaving = ref(false)
const tierSaveMsg = ref('')
const tierSaveOk = ref(false)

const tierRows = [
  { feature: 'parser',         label: 'Parser (OCR)' },
  { feature: 'classifier_llm', label: 'Classifier' },
  { feature: 'extractor',      label: 'Extractor' },
  { feature: 'splitter',       label: 'Splitter' },
]

// Full tier spec (with provider) from backend
const settingsTierFull = ref<any>(null)

const getFullTierSpec = (feature: string, tier: string) => {
  return settingsTierFull.value?.[feature]?.[tier] ?? { model: '', provider: '' }
}

const getModelsForProvider = (providerId: string | null | undefined) => {
  if (!providerId) {
    return settingsProviders.value.flatMap((p: any) => p.models || [])
  }
  const provider = settingsProviders.value.find((p: any) => p.id === providerId)
  return provider?.models ?? []
}

// Combined handler: value is "providerId::modelId"
const onTierSelectChange = (feature: string, tier: string, value: string) => {
  if (!tierEdits.value[feature]) tierEdits.value[feature] = {}
  const [provider, model] = value.includes('::') ? value.split('::') : ['', value]
  tierEdits.value[feature][tier] = { provider: provider ?? '', model: model ?? '' }
}

const getProviderName = (providerId: string | null | undefined) => {
  if (!providerId) return ''
  const p = settingsProviders.value.find((p: any) => p.id === providerId)
  return p?.name ?? providerId
}

// Compute the current select value as "providerId::modelId"
const getTierSelectValue = (feature: string, tier: string) => {
  const edit = tierEdits.value[feature]?.[tier]
  const spec = edit ?? getFullTierSpec(feature, tier)
  if (!spec?.model) return ''
  return spec.provider ? `${spec.provider}::${spec.model}` : spec.model
}

const saveTierConfig = async () => {
  tierSaving.value = true
  tierSaveMsg.value = ''
  try {
    const apiBaseUrl = (config.public.apiBaseUrl as string)
    const updates: any[] = []
    for (const [feature, tiers] of Object.entries(tierEdits.value)) {
      for (const [tier, spec] of Object.entries(tiers as any)) {
        if ((spec as any).model) {
          updates.push({ feature, tier, provider: (spec as any).provider || 'auto', model: (spec as any).model })
        }
      }
    }
    if (updates.length === 0) {
      tierSaveMsg.value = 'No changes to save'
      tierSaveOk.value = false
      return
    }
    const res = await $fetch<any>(`${apiBaseUrl}/tier-config`, { method: 'PUT', body: { updates } })
    if (res.success) {
      tierSaveMsg.value = `Saved ${updates.length} change${updates.length > 1 ? 's' : ''}`
      tierSaveOk.value = true
      // Refresh tier config
      const tc = await fetchTierConfig()
      settingsTierConfig.value = tc
      tierEdits.value = {}
    } else {
      tierSaveMsg.value = res.errors?.join(', ') ?? 'Save failed'
      tierSaveOk.value = false
    }
  } catch (e: any) {
    tierSaveMsg.value = e?.data?.detail ?? e?.message ?? 'Save failed'
    tierSaveOk.value = false
  } finally {
    tierSaving.value = false
    setTimeout(() => { tierSaveMsg.value = '' }, 3000)
  }
}

// Config modal state
const configModal = reactive({
  open: false,
  provider: null as any,
  apiKey: '',
  baseUrl: '',
  rpm: null as number | null,
  showKey: false,
  saving: false,
  saveMsg: '',
  saveOk: false,
})

// Add provider modal state
const addProviderModal = reactive({
  open: false,
  id: '',
  name: '',
  type: 'cloud' as 'cloud' | 'local',
  apiKey: '',
  baseUrl: '',
  rpm: null as number | null,
  showKey: false,
  saving: false,
  saveMsg: '',
  saveOk: false,
})

// Use tier config from backend (with fallback)
const { getParserModel, fetchTierConfig } = useTierConfig()

// Fetch providers for selector
const { providers, fetchProviders } = useProviders()
const { saveEntry: saveToDataStore } = useDataStore()
const config = useRuntimeConfig()

const openAddProviderModal = () => {
  addProviderModal.open = true
  addProviderModal.id = ''
  addProviderModal.name = ''
  addProviderModal.type = 'cloud'
  addProviderModal.apiKey = ''
  addProviderModal.baseUrl = ''
  addProviderModal.rpm = null
  addProviderModal.showKey = false
  addProviderModal.saving = false
  addProviderModal.saveMsg = ''
  addProviderModal.saveOk = false
}

const saveNewProvider = async () => {
  if (!addProviderModal.id.trim() || !addProviderModal.name.trim()) return
  addProviderModal.saving = true
  addProviderModal.saveMsg = ''
  try {
    const apiBaseUrl = (config.public.apiBaseUrl as string)
    const body: any = {
      name: addProviderModal.name.trim(),
      type: addProviderModal.type,
      base_url: addProviderModal.baseUrl.trim() || null,
      rpm: addProviderModal.rpm || null,
    }
    if (addProviderModal.type === 'cloud' && addProviderModal.apiKey.trim()) {
      body.api_key = addProviderModal.apiKey.trim()
    }
    await $fetch(`${apiBaseUrl}/providers/${addProviderModal.id.trim()}/add`, {
      method: 'POST',
      body,
    })
    addProviderModal.saveMsg = 'Provider added successfully!'
    addProviderModal.saveOk = true
    await reloadProviders()
    setTimeout(() => { addProviderModal.open = false }, 1200)
  } catch (e: any) {
    addProviderModal.saveMsg = e?.data?.detail ?? e?.message ?? 'Failed to add provider'
    addProviderModal.saveOk = false
  } finally {
    addProviderModal.saving = false
  }
}

const openConfigModal = (provider: any) => {  configModal.provider = provider
  configModal.apiKey = ''
  configModal.baseUrl = provider.base_url || ''
  configModal.rpm = provider.rpm ?? null
  configModal.showKey = false
  configModal.saving = false
  configModal.saveMsg = ''
  configModal.saveOk = false
  configModal.open = true
}

const saveProviderConfig = async () => {
  if (!configModal.provider) return
  configModal.saving = true
  configModal.saveMsg = ''
  try {
    const apiBaseUrl = (config.public.apiBaseUrl as string)
    const body: any = { rpm: configModal.rpm }
    if (configModal.provider.credential_key && configModal.apiKey !== '') {
      body.api_key = configModal.apiKey
    }
    if (configModal.provider.type === 'local' && configModal.baseUrl) {
      body.base_url = configModal.baseUrl
    }
    await $fetch(`${apiBaseUrl}/providers/${configModal.provider.id}/config`, {
      method: 'POST',
      body,
    })
    configModal.saveMsg = 'Saved successfully!'
    configModal.saveOk = true
    // Refresh providers list
    await reloadProviders()
    setTimeout(() => { configModal.open = false }, 1200)
  } catch (e: any) {
    configModal.saveMsg = e?.data?.detail ?? e?.message ?? 'Failed to save'
    configModal.saveOk = false
  } finally {
    configModal.saving = false
  }
}

const reloadProviders = async () => {  settingsLoading.value = true
  settingsError.value = null
  try {
    const apiBaseUrl = (config.public.apiBaseUrl as string)
    const res = await $fetch<{ success: boolean; providers: any[] }>(`${apiBaseUrl}/providers`)
    settingsProviders.value = res.providers
    // Also refresh the selector providers
    await fetchProviders()
  } catch (e: any) {
    settingsError.value = e?.data?.detail ?? e?.message ?? 'Failed to load providers'
  } finally {
    settingsLoading.value = false
  }
}

const runTestConnection = async (providerId: string) => {
  settingsTestingProvider.value = providerId
  try {
    const apiBaseUrl = (config.public.apiBaseUrl as string)
    const res = await $fetch<any>(`${apiBaseUrl}/providers/${providerId}/test`, { method: 'POST' })
    settingsTestResults.value[providerId] = res
    // Reload providers so ready status updates in Tier Config dropdown
    await reloadProviders()
  } catch (e: any) {
    settingsTestResults.value[providerId] = {
      success: false,
      provider: providerId,
      message: e?.data?.detail ?? e?.message ?? 'Connection test failed',
      latency_ms: null,
    }
  } finally {
    settingsTestingProvider.value = null
  }
}

// Load settings data when switching to settings view
watch(activeView, async (newView) => {
  // Reset journey builder when switching away
  if (newView !== 'journey') {
    journeyBuilderOpen.value = false
    journeyDetailOpen.value = false
  }

  if (newView === 'settings') {
    if (settingsProviders.value.length === 0) {
      await reloadProviders()
    }
    if (!settingsTierConfig.value) {
      const tc = await fetchTierConfig()
      settingsTierConfig.value = tc
      // Also fetch full spec with provider info
      try {
        const apiBaseUrl = (config.public.apiBaseUrl as string)
        const full = await $fetch<any>(`${apiBaseUrl}/tier-config`)
        settingsTierFull.value = full.full ?? null
      } catch {}
    }  }
})

// Check health on mount and load persisted uploads
onMounted(async () => {
  // Run independently so one failure doesn't block others
  checkHealth().catch(() => {})
  fetchProviders().catch(() => {})
  loadUploads().catch(() => {})
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
  // If "{{ t('page.processAllFiles') }}" is enabled, check if there are any files without results
  if (processAllFiles.value) {
    return files.value.some(f => !f.result || f.status === 'pending' || f.status === 'error') && !isProcessing.value
  }
  // Otherwise, check if a file is selected
  return selectedFile.value && !isProcessing.value
})

// selectedModel now comes directly from the ModelSelector dropdown
const selectedModel = computed(() => {
  return parseSelectedModel.value
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
    const pages = text.split(/--- Page \d+ ---\n/).filter((p: string) => p.trim())
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
      
      let processedText = text.replace(/<table[\s\S]*?<\/table>/gi, (match: string) => {
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
        
        const cells = line.split('|').filter((cell: string) => cell.trim())
        const isHeader = i === 0 || (i === 1 && /^\|[\s\-:]+\|$/.test(lines[i - 1] ?? ''))

        if (isHeader && tableHtml === '<table><tbody>') {
          tableHtml = '<table><thead><tr>'
          cells.forEach((cell: string) => {
            tableHtml += `<th>${cell.trim()}</th>`
          })
          tableHtml += '</tr></thead><tbody>'
        } else {
          tableHtml += '<tr>'
          cells.forEach((cell: string) => {
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

// Handlers (tier is now fixed to 'Normal', model is selected directly)

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
      const file = uniqueNewFiles[index]
      if (file) uploadedFiles.value.set(fileItem.id, file)
    })
  }
}

/**
 * Handle drag start from sidebar file list
 */
const handleFileDragStart = (event: DragEvent, file: any) => {
  if (!event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-drvision-file', JSON.stringify({
    id: file.id,
    name: file.name,
    type: file.type,
  }))
  // Activate drop zones over iframes
  isSidebarDragging.value = true
  
  // Reset on drag end
  const cleanup = () => {
    isSidebarDragging.value = false
    document.removeEventListener('dragend', cleanup)
  }
  document.addEventListener('dragend', cleanup)
}

/**
 * Handle drop on preview area — load file from sidebar into the active view
 */
const handlePreviewDrop = async (event: DragEvent) => {
  isDragging.value = false
  isSidebarDragging.value = false
  const data = event.dataTransfer?.getData('application/x-drvision-file')
  if (data) {
    // Dropped from sidebar file list
    const fileInfo = JSON.parse(data)
    const file = files.value.find(f => f.id === fileInfo.id)
    if (file) {
      selectedFile.value = file
      setPreviewFile(file)
      
      // Load preview URL
      const fileObj = uploadedFiles.value.get(file.id)
      if (fileObj) {
        if (previewFileUrl.value) URL.revokeObjectURL(previewFileUrl.value)
        previewFileUrl.value = URL.createObjectURL(fileObj)
      } else {
        // File loaded from backend — use download URL directly
        const cfg = useRuntimeConfig()
        const base = cfg.public.apiBaseUrl as string
        previewFileUrl.value = `${base}/api/v1/uploads/${file.id}/download`
      }
    }
    return
  }
  
  // Fallback: dropped external files from OS
  const newFiles = Array.from(event.dataTransfer?.files || [])
  await handleUpload(newFiles)
}

const handleSelectFile = async (file: any) => {
  // Click on sidebar file = open compare popup (does NOT load into preview area)
  // To load into preview, user must drag-drop the file onto the preview area
  
  // Resolve preview URL for the popup
  let resolvedPreviewUrl = ''
  const fileObj = uploadedFiles.value.get(file.id)
  
  if (fileObj) {
    try {
      resolvedPreviewUrl = URL.createObjectURL(fileObj)
    } catch {
      resolvedPreviewUrl = ''
    }
  } else {
    // File loaded from backend — use download URL directly
    const config = useRuntimeConfig()
    const apiBaseUrl = config.public.apiBaseUrl as string
    resolvedPreviewUrl = `${apiBaseUrl}/api/v1/uploads/${file.id}/download`
  }
  
  // Open compare popup
  compareFile.value = file
  comparePreviewUrl.value = resolvedPreviewUrl
  showFileCompareDialog.value = true
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

/**
 * Get File object for processing — either from local map or download from backend
 */
const getFileForProcessing = async (fileId: string, fileName: string): Promise<File | null> => {
  // Try local map first
  const localFile = uploadedFiles.value.get(fileId)
  if (localFile) return localFile
  
  // Download from backend
  try {
    const config = useRuntimeConfig()
    const apiBaseUrl = config.public.apiBaseUrl as string
    const response = await fetch(`${apiBaseUrl}/api/v1/uploads/${fileId}/download`)
    if (!response.ok) return null
    const blob = await response.blob()
    return new File([blob], fileName, { type: blob.type })
  } catch (error) {
    console.error('Failed to download file for processing:', error)
    return null
  }
}

const handleProcess = async () => {
  console.log('handleProcess called')
  console.log('selectedFile:', selectedFile.value)
  console.log('processAllFiles:', processAllFiles.value)
  console.log('canProcess:', canProcess.value)
  console.log('isProcessing:', isProcessing.value)
  
  // If "{{ t('page.processAllFiles') }}" is enabled, process all files without results
  if (processAllFiles.value) {
    const filesToProcess = files.value.filter(f => !f.result || f.status === 'pending' || f.status === 'error')
    
    if (filesToProcess.length === 0) {
      console.log('No files to process - all files already have results')
      return
    }
    
    console.log(`Processing ${filesToProcess.length} files`)
    
    // Process each file sequentially
    for (const fileItem of filesToProcess) {
      const file = await getFileForProcessing(fileItem.id, fileItem.name)
      
      if (!file) {
        console.error('File not available for processing:', fileItem.id)
        continue
      }
      
      console.log('Processing file:', fileItem.name, 'with model:', selectedModel.value)
      
      await processFile(fileItem.id, file, {
        modelId: selectedModel.value,
        tier: 'Normal',
        processAllPages: processAllPages.value,
      })
      
      // Auto-save to Data Store if successful
      if (fileItem.result?.success) {
        saveToDataStore({
          filename: fileItem.name,
          action_tag: 'Parse',
          result_data: fileItem.result,
          model_used: selectedModel.value,
        })
      }
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
  
  const file = await getFileForProcessing(selectedFile.value.id, selectedFile.value.name)
  console.log('File for processing:', file)
  
  if (!file) {
    console.error('File not available for processing')
    return
  }
  
  console.log('Processing with model:', selectedModel.value)
  
  // Reset to page 1 before processing
  currentResultPage.value = 1
  
  // Clear parsed HTML cache when processing new file
  parsedHtmlCache.value.clear()
  
  await processFile(selectedFile.value.id, file, {
    modelId: selectedModel.value,
    tier: 'Normal',
    processAllPages: processAllPages.value,
  })
  
  // Auto-save to Data Store if successful
  if (selectedFile.value?.result?.success) {
    saveToDataStore({
      filename: selectedFile.value.name,
      action_tag: 'Parse',
      result_data: selectedFile.value.result,
      model_used: selectedModel.value,
    })
  }
  
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

const handleOpenJourneyBuilder = (workflowId?: string) => {
  editingWorkflowId.value = workflowId || null
  journeyBuilderOpen.value = true
}

const handleOpenJourneyDetail = (workflowId: string) => {
  editingWorkflowId.value = workflowId
  journeyDetailOpen.value = true
}

const handleOpenJourneyBuilderFromDetail = (workflowId: string) => {
  editingWorkflowId.value = workflowId
  journeyBuilderOpen.value = true
}

const handleBackFromBuilder = () => {
  journeyBuilderOpen.value = false
  // If we came from detail page, go back to detail; otherwise go to dashboard
  // journeyDetailOpen stays as-is
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
const showFileCompareDialog = ref(false)
const compareFile = ref<any>(null)
const comparePreviewUrl = ref('')

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
      const updatedPages = resultPages.value.map((page: string, idx: number) => {
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
      const file = await getFileForProcessing(fileItem.id, fileItem.name)
      if (file) {
        console.log(`Processing file: ${fileItem.name}`)
        await processFile(fileItem.id, file, config)
        
        // Auto-save to Data Store if successful
        if (fileItem.result?.success) {
          saveToDataStore({
            filename: fileItem.name,
            action_tag: 'Extract',
            result_data: fileItem.result,
            model_used: config.modelId,
          })
        }
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
  
  const file = await getFileForProcessing(selectedFile.value.id, selectedFile.value.name)
  
  if (!file) {
    console.error('File not available for extraction processing')
    return
  }
  
  console.log('Processing extraction with config:', config)
  
  // Reset to page 1 before processing
  currentResultPage.value = 1
  
  // Clear parsed HTML cache when processing new file
  parsedHtmlCache.value.clear()
  
  await processFile(selectedFile.value.id, file, config)
  
  // Auto-save to Data Store if successful
  if (selectedFile.value?.result?.success) {
    saveToDataStore({
      filename: selectedFile.value.name,
      action_tag: 'Extract',
      result_data: selectedFile.value.result,
      model_used: config.modelId,
    })
  }
  
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
      const file = await getFileForProcessing(fileItem.id, fileItem.name)
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
      
      // Auto-save to Data Store
      for (const fileItem of unprocessedFiles) {
        if (fileItem.result?.success) {
          saveToDataStore({
            filename: fileItem.name,
            action_tag: 'Classify',
            result_data: fileItem.result,
            model_used: config.classifierModelId,
          })
        }
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
  
  const file = await getFileForProcessing(selectedFile.value.id, selectedFile.value.name)
  
  if (!file) {
    console.error('File not available for classification processing')
    return
  }
  
  console.log('Classifying with config:', config)
  
  await classifyFile(selectedFile.value.id, file, config)
  
  // Auto-save to Data Store if successful
  if (selectedFile.value?.result?.success) {
    saveToDataStore({
      filename: selectedFile.value.name,
      action_tag: 'Classify',
      result_data: selectedFile.value.result,
      model_used: config.classifierModelId,
    })
  }
  
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
      const file = await getFileForProcessing(fileItem.id, fileItem.name)
      if (file) {
        console.log(`[index.vue] Splitting file: ${fileItem.name}`)
        await splitFile(fileItem.id, file, config)
        
        // Auto-save to Data Store if successful
        if (fileItem.result?.success) {
          saveToDataStore({
            filename: fileItem.name,
            action_tag: 'Split',
            result_data: fileItem.result,
            model_used: config.splitterModelId || undefined,
          })
        }
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
  
  const file = await getFileForProcessing(selectedFile.value.id, selectedFile.value.name)
  
  if (!file) {
    console.error('[index.vue] File not available for split processing')
    return
  }
  
  console.log('[index.vue] Calling splitFile with:', {
    fileId: selectedFile.value.id,
    fileName: file.name,
    config
  })
  
  await splitFile(selectedFile.value.id, file, config)
  
  console.log('[index.vue] splitFile completed, switching to result tab')
  
  // Auto-save to Data Store if successful
  if (selectedFile.value?.result?.success) {
    saveToDataStore({
      filename: selectedFile.value.name,
      action_tag: 'Split',
      result_data: selectedFile.value.result,
      model_used: config.splitterModelId || undefined,
    })
  }
  
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

/* ── File Compare Dialog ───────────────────────────────────────────────── */
.file-compare-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.file-compare-container {
  background: #fff;
  border-radius: 1rem;
  width: 100%;
  max-width: 1400px;
  height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.file-compare-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.file-compare-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.file-compare-close {
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

.file-compare-close:hover {
  background: #f3f4f6;
  color: #111827;
}

.file-compare-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.file-compare-left,
.file-compare-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-compare-left {
  border-right: 1px solid #e5e7eb;
}

.file-compare-panel-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid #f3f4f6;
  background: #f9fafb;
  flex-shrink: 0;
}

.file-compare-preview {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
}

.file-compare-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.file-compare-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  padding: 1rem;
}

.file-compare-unavailable,
.file-compare-no-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  color: #9ca3af;
  text-align: center;
  padding: 2rem;
}

.file-compare-unavailable p,
.file-compare-no-result p {
  margin: 0;
  font-size: 0.875rem;
}

.file-compare-hint {
  font-size: 0.75rem !important;
  color: #d1d5db !important;
}

.file-compare-result {
  flex: 1;
  overflow-y: auto;
  background: #fff;
}

.file-compare-result-content {
  padding: 1.25rem;
  height: 100%;
  overflow-y: auto;
}

.file-compare-text {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.8125rem;
  line-height: 1.7;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

/* ── Settings View ─────────────────────────────────────────────────────── */
.settings-view {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: calc(100vh - 73px);
}

.settings-inner {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 0;
  min-height: 0;
}

.settings-aside {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-color);
  padding: 1rem 0.75rem;
  background: var(--bg-primary);
  overflow-y: auto;
  position: fixed;
  left: 240px; /* var(--sidebar-width) */
  top: 73px;
  height: calc(100vh - 73px);
  z-index: 90;
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.settings-nav-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.875rem;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
  width: 100%;
}
.settings-nav-item:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.settings-nav-item.active { background: #fff3ee; color: #FF6F3C; font-weight: 600; }

.settings-main {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem;
  background: #f9fafb;
  min-height: 0;
  margin-left: 200px;
}

.settings-section-header { margin-bottom: 1.5rem; }
.settings-section-title { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 0.4rem; }
.settings-section-desc { font-size: 0.875rem; color: #6b7280; margin: 0; }

.settings-loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 2rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.settings-error-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 0.875rem;
}

/* Language Options */
.language-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 400px;
}

.language-option {
  display: flex;
  align-items: center;
  padding: 16px;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.language-option:hover {
  border-color: #d1d5db;
  background: #f9fafb;
}

.language-option.active {
  border-color: #FF6F3C;
  background: #fff7ed;
}

.language-option input[type="radio"] {
  display: none;
}

.language-option-content {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.language-flag {
  font-size: 28px;
}

.language-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.language-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.language-native {
  font-size: 12px;
  color: #6b7280;
}

.language-check {
  font-size: 18px;
  font-weight: bold;
  color: #FF6F3C;
}

/* Provider grid */
.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.provider-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  transition: box-shadow 0.15s;
}
.provider-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.provider-card.configured { border-left: 3px solid #10b981; }
.provider-card.unconfigured { border-left: 3px solid #f59e0b; }

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.provider-identity { display: flex; align-items: center; gap: 0.75rem; }

.provider-icon {
  width: 40px; height: 40px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 1.125rem; color: #fff;
  background: #6366f1; flex-shrink: 0;
}
.icon-google_studio { background: #4285f4; }
.icon-poe_api       { background: #7c3aed; }
.icon-lm_studio     { background: #059669; }
.icon-bedrock       { background: #f59e0b; }
.icon-ollama        { background: #374151; }

.provider-name { font-size: 0.9375rem; font-weight: 600; color: #111827; margin: 0 0 0.2rem; }

.provider-type-badge {
  font-size: 0.75rem; font-weight: 500;
  padding: 0.1rem 0.5rem; border-radius: 999px;
}
.provider-type-badge.cloud { background: #eff6ff; color: #3b82f6; }
.provider-type-badge.local { background: #f0fdf4; color: #16a34a; }

.status-pill {
  display: flex; align-items: center; gap: 0.35rem;
  font-size: 0.75rem; font-weight: 500;
  padding: 0.25rem 0.625rem; border-radius: 999px;
  white-space: nowrap; flex-shrink: 0;
}
.status-pill.ok            { background: #f0fdf4; color: #16a34a; }
.status-pill.warn          { background: #fffbeb; color: #d97706; }
.status-pill.ready         { background: #eff6ff; color: #2563eb; }
/* New unified status classes */
.status-pill.not_configured { background: #fffbeb; color: #d97706; }
.status-pill.configured     { background: #f0fdf4; color: #16a34a; }
.status-pill.ready          { background: #eff6ff; color: #2563eb; }
.status-pill.timeout        { background: #fff7ed; color: #ea580c; }
.status-pill.error          { background: #fef2f2; color: #dc2626; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.provider-desc { font-size: 0.8125rem; color: #6b7280; line-height: 1.5; margin: 0; }

.credential-row, .url-row {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #6b7280;
}

/* ── Card fields (API Key, URL, RPM, Models) ────────────────────────────── */
.card-fields {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.card-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.card-field-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.7rem;
  font-weight: 600;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.card-field-count {
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}

.card-field-input-wrap {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.card-field-input-wrap:focus-within {
  border-color: #FF6F3C;
  box-shadow: 0 0 0 2px rgba(255, 111, 60, 0.1);
  background: #fff;
}
.card-field-input-wrap.disabled {
  opacity: 0.5;
}

.card-field-rpm {
  max-width: 160px;
}

.card-field-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 0.8125rem;
  color: #374151;
  outline: none;
  min-width: 0;
  font-family: 'Courier New', monospace;
}
.card-field-input[type="number"] {
  font-family: inherit;
  width: 60px;
  flex: none;
}
.card-field-input[type="number"]::-webkit-inner-spin-button,
.card-field-input[type="number"]::-webkit-outer-spin-button {
  opacity: 1;
}
.card-field-input::placeholder { color: #c4c4c4; font-style: italic; letter-spacing: 0; }
.card-field-input[readonly] { cursor: text; }

.rpm-unit {
  font-size: 0.75rem;
  color: #9ca3af;
  white-space: nowrap;
  flex-shrink: 0;
}

.card-field-actions {
  display: flex;
  align-items: center;
  gap: 0.15rem;
  flex-shrink: 0;
}

.field-action-btn {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px;
  background: transparent; border: none; border-radius: 4px;
  color: #9ca3af; cursor: pointer; transition: all 0.12s; padding: 0;
}
.field-action-btn:hover { background: #f3f4f6; color: #374151; }
.field-action-btn.save:hover  { background: #f0fdf4; color: #16a34a; }
.field-action-btn.cancel:hover { background: #fef2f2; color: #dc2626; }

/* ── Inline key editor ──────────────────────────────────────────────────── */
.inline-key-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.key-icon { flex-shrink: 0; color: #9ca3af; }

.inline-key-field {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 0.2rem 0.4rem;
  transition: border-color 0.15s, box-shadow 0.15s;
  min-width: 0;
}
.inline-key-field:focus-within {
  border-color: #FF6F3C;
  box-shadow: 0 0 0 2px rgba(255, 111, 60, 0.1);
  background: #fff;
}

.inline-key-input {
  flex: 1;
  border: none;
  background: transparent;
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  color: #374151;
  outline: none;
  min-width: 0;
  letter-spacing: 0.03em;
}
.inline-key-input::placeholder { color: #c4c4c4; font-style: italic; letter-spacing: 0; font-family: inherit; }
.inline-key-input.has-value::placeholder { color: #9ca3af; }
.inline-key-input.no-key { color: #9ca3af; cursor: default; }
.inline-key-input[readonly] { cursor: text; }

.inline-key-actions { display: flex; align-items: center; gap: 0.15rem; flex-shrink: 0; }

.inline-key-btn {
  display: flex; align-items: center; justify-content: center;
  width: 22px; height: 22px;
  background: transparent; border: none; border-radius: 4px;
  color: #9ca3af; cursor: pointer; transition: all 0.12s; padding: 0;
}
.inline-key-btn:hover { background: #f3f4f6; color: #374151; }
.inline-key-btn.save:hover  { background: #f0fdf4; color: #16a34a; }
.inline-key-btn.cancel:hover { background: #fef2f2; color: #dc2626; }

.cred-status { font-size: 0.75rem; font-weight: 600; flex-shrink: 0; }
.cred-status.set    { color: #16a34a; }
.cred-status.missing { color: #dc2626; }

.url-row { align-items: center; }
.base-url { font-size: 0.75rem; color: #9ca3af; word-break: break-all; }

.models-section { display: flex; flex-direction: column; gap: 0.4rem; }
.models-label { font-size: 0.75rem; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; margin: 0; }
.models-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.model-chip {
  background: #f3f4f6; color: #374151;
  font-size: 0.75rem; padding: 0.2rem 0.5rem;
  border-radius: 6px; max-width: 160px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.no-models { font-size: 0.8125rem; color: #d1d5db; font-style: italic; }

.card-footer {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.75rem; margin-top: auto; padding-top: 0.5rem;
  border-top: 1px solid #f3f4f6;
}

.test-result { flex: 1; min-width: 0; }
.test-badge {
  display: inline-flex; align-items: center; gap: 0.35rem;
  font-size: 0.8125rem; font-weight: 600;
  padding: 0.25rem 0.625rem; border-radius: 6px;
}
.test-badge.success { background: #f0fdf4; color: #16a34a; }
.test-badge.fail {
  background: #fef2f2; color: #dc2626;
  cursor: default;
}
.latency { color: #9ca3af; margin-left: 0.25rem; font-weight: 400; font-size: 0.75rem; }

/* Error tooltip */
.error-tooltip {
  position: fixed;
  z-index: 9999;
  max-width: 360px;
  background: #fff;
  border: 1px solid #fecaca;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  pointer-events: none;
  transform: translateY(calc(-100% - 8px));
}

.error-tooltip-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.875rem;
  background: #fef2f2;
  border-bottom: 1px solid #fecaca;
  color: #dc2626;
  font-size: 0.75rem;
  font-weight: 600;
}

.error-tooltip-body {
  padding: 0.75rem 0.875rem;
  font-size: 0.75rem;
  color: #374151;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.test-btn {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.4rem 0.875rem;
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 8px; color: #374151; font-size: 0.8125rem;
  cursor: pointer; transition: all 0.15s; white-space: nowrap; flex-shrink: 0;
}
.test-btn:hover:not(:disabled) { background: #f9fafb; border-color: #d1d5db; }
.test-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.retry-btn {
  margin-left: auto; padding: 0.3rem 0.75rem;
  background: #fff; border: 1px solid #fca5a5;
  border-radius: 6px; color: #dc2626; font-size: 0.8125rem;
  cursor: pointer;
}

.refresh-row { margin-top: 1rem; display: flex; justify-content: flex-end; }
.refresh-btn {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.4rem 0.875rem;
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 8px; color: #6b7280; font-size: 0.8125rem;
  cursor: pointer; transition: all 0.15s;
}
.refresh-btn:hover:not(:disabled) { background: #f9fafb; color: #374151; }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Tier table */
.tier-table-wrapper { overflow-x: auto; }
.tier-table {
  width: 100%; border-collapse: collapse;
  background: #fff; border-radius: 12px; overflow: hidden;
  border: 1px solid #e5e7eb;
}
.tier-table th {
  padding: 0.75rem 1rem; text-align: left;
  font-size: 0.8125rem; font-weight: 600; color: #6b7280;
  background: #f9fafb; border-bottom: 1px solid #e5e7eb;
}
.tier-table td {
  padding: 0.75rem 1rem;
  font-size: 0.875rem; color: #374151;
  border-bottom: 1px solid #f3f4f6;
}
.tier-table tr:last-child td { border-bottom: none; }
.feature-cell { font-weight: 600; color: #111827; }
.model-tag {
  background: #f3f4f6; color: #374151;
  font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 6px;
  font-family: monospace;
}

/* Tier cell with grouped select */
.tier-cell {
  padding: 0.5rem 0.75rem !important;
  min-width: 200px;
}

.tier-select {
  width: 100%;
  padding: 0.5rem 0.625rem;
  font-size: 0.8125rem;
  color: #374151;
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: inherit;
}
.tier-select:focus {
  outline: none;
  border-color: #FF6F3C;
  box-shadow: 0 0 0 2px rgba(255, 111, 60, 0.1);
}
.tier-select:hover { border-color: #d1d5db; }

/* Provider badge shown below the select */

/* Tier header actions */
.tier-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.tier-save-msg {
  font-size: 0.8125rem;
  font-weight: 500;
  padding: 0.3rem 0.75rem;
  border-radius: 6px;
}
.tier-save-msg.ok  { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.tier-save-msg.err { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Card header right (status + gear) ─────────────────────────────────── */
.card-header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.gear-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}
.gear-btn:hover { background: #f3f4f6; border-color: #d1d5db; color: #FF6F3C; }

/* RPM row */
.rpm-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #6b7280;
}
.rpm-label { font-weight: 500; }
.rpm-value { color: #374151; }

/* ── Config Modal ───────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-box {
  background: #fff;
  border-radius: 14px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem 1rem;
  border-bottom: 1px solid #f3f4f6;
}

.modal-title-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  color: #111827;
}

.modal-title {
  font-size: 1rem;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.15s;
}
.modal-close:hover { background: #f3f4f6; color: #374151; }

.modal-body {
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.modal-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.modal-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.modal-env-hint {
  background: #f3f4f6;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 400;
  margin-left: 0.25rem;
}

.modal-input-row {
  display: flex;
  gap: 0.5rem;
}

.modal-input {
  flex: 1;
  padding: 0.625rem 0.875rem;
  font-size: 0.875rem;
  color: #111827;
  background: #fff;
  border: 1.5px solid #d1d5db;
  border-radius: 0.5rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.modal-input:focus {
  outline: none;
  border-color: #FF6F3C;
  box-shadow: 0 0 0 3px rgba(255, 111, 60, 0.1);
}
.modal-input-sm { max-width: 140px; flex: none; }

.toggle-vis-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  background: #f9fafb;
  border: 1.5px solid #d1d5db;
  border-radius: 0.5rem;
  color: #6b7280;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}
.toggle-vis-btn:hover { background: #f3f4f6; color: #374151; }

.modal-hint {
  font-size: 0.8125rem;
  color: #9ca3af;
  margin: 0;
}

.modal-save-msg {
  padding: 0.625rem 0.875rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}
.modal-save-msg.ok  { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.modal-save-msg.err { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #f3f4f6;
  background: #fafafa;
}

.modal-cancel-btn {
  padding: 0.5rem 1.25rem;
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  color: #374151;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.modal-cancel-btn:hover { background: #f9fafb; border-color: #d1d5db; }

.modal-save-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1.25rem;
  background: #FF6F3C;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.modal-save-btn:hover:not(:disabled) { background: #E55A2B; }
.modal-save-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* Modal transition */
.modal-enter-active,
.modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from,
.modal-leave-to { opacity: 0; }

/* ── Section header row ─────────────────────────────────────────────────── */
.section-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.add-provider-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: #FF6F3C;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background 0.15s;
}
.add-provider-btn:hover { background: #E55A2B; }

/* Type toggle inside modal */
.type-toggle {
  display: flex;
  gap: 0.5rem;
}

.type-btn {
  flex: 1;
  padding: 0.5rem 0.75rem;
  background: #f9fafb;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}
.type-btn:hover { background: #f3f4f6; border-color: #d1d5db; }
.type-btn.active {
  background: #fff3ee;
  border-color: #FF6F3C;
  color: #FF6F3C;
  font-weight: 600;
}

.modal-hint-inline {
  font-size: 0.75rem;
  font-weight: 400;
  color: #9ca3af;
  margin-left: 0.25rem;
}</style>