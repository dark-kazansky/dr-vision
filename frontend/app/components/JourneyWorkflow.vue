<template>
  <div class="journey-container">
    <div class="journey-content">
      <!-- Workflow Canvas -->
      <div class="workflow-canvas">
        <div class="canvas-area" 
             ref="canvasArea"
             :class="{ 'panning': isPanning || isSpacePressed }"
             @click="handleCanvasClick"
             @mousedown="handleCanvasMouseDown"
             @mousemove="handleCanvasMouseMove"
             @mouseup="handleCanvasMouseUp"
             @mouseleave="handleCanvasMouseUp">
          <div v-if="nodes.length === 0" class="canvas-empty">
            <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <p>Add nodes to build your workflow</p>
          </div>

          <!-- Connection lines SVG -->
          <svg class="connections-svg" v-if="nodes.length > 0">
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                <polygon points="0 0, 10 3, 0 6" fill="#9ca3af" />
              </marker>
              <marker id="arrowhead-blue" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                <polygon points="0 0, 10 3, 0 6" fill="#3b82f6" />
              </marker>
            </defs>
            
            <!-- Existing connections -->
            <g v-for="node in nodes" :key="`connections-${node.id}`">
              <path
                v-for="targetId in node.connections || []"
                :key="`${node.id}-${targetId}`"
                :d="getConnectionPath(node.id, targetId)"
                :stroke="selectedConnection?.fromId === node.id && selectedConnection?.toId === targetId ? '#ff8c5a' : '#9ca3af'"
                :stroke-width="selectedConnection?.fromId === node.id && selectedConnection?.toId === targetId ? '3' : '2'"
                fill="none"
                class="connection-line"
                @click="handleConnectionClick(node.id, targetId, $event)"
              />
            </g>
            
            <!-- Dragging connection line -->
            <path
              v-if="isDraggingConnection && connectingFrom"
              :d="getDragConnectionPath()"
              :stroke="nearbyInputNode ? '#3b82f6' : '#9ca3af'"
              stroke-width="2"
              fill="none"
              stroke-dasharray="5,5"
            />
          </svg>

          <div v-for="(node, index) in nodes" :key="node.id" 
               class="workflow-node" 
               :class="[
                 `node-${node.type}`, 
                 { 
                   'node-active': node.status === 'processing', 
                   'node-complete': node.status === 'completed', 
                   'node-error': node.status === 'error',
                   'node-inactive': node.inactive || node.status === 'inactive',
                   'node-selected': selectedNode === node.id,
                   'node-dragging': draggedNode === node.id
                 }
               ]"
               :style="{ top: `${node.y}px`, left: `${node.x}px` }">
            
            <!-- Input connection point (left side) -->
            <div 
              v-if="node.type !== 'upload'"
              class="connection-point input-point"
              :class="{ 
                'connecting': connectingFrom && connectingFrom !== node.id,
                'nearby': nearbyInputNode === node.id
              }"
              @mouseup="handleInputMouseUp($event, node.id)"
              @click="handleInputClick($event, node.id)"
              title="Input">
              <div class="connection-dot"></div>
            </div>
            
            <div class="node-header" @mousedown="handleNodeMouseDown($event, node.id)">
              <div class="node-icon">
                <component :is="getNodeIcon(node.type)" />
              </div>
              <span class="node-title">{{ node.label }}</span>
              <button class="node-remove" @click="removeNode(node.id)" :disabled="isProcessing">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div class="node-body">
              <div v-if="node.type === 'upload'" class="node-config">
                <input type="file" :ref="`fileInput-${node.id}`" @change="handleFileSelect($event, node.id)" multiple accept=".png,.jpg,.jpeg,.pdf,.txt,.md,.docx" style="display: none" />
                <button class="config-btn" @click="triggerFileInput(node.id)" :disabled="isProcessing">
                  {{ node.files?.length ? `${node.files.length} file(s)` : 'Select Files' }}
                </button>
              </div>
              <div v-else class="node-config">
                <select v-model="node.tier" class="config-select" :disabled="isProcessing">
                  <option value="Rapid">Rapid</option>
                  <option value="Normal">Normal</option>
                  <option value="Advance">Advance</option>
                </select>
              </div>
            </div>
            <div class="node-status">
              <span v-if="node.status === 'pending'" class="status-badge status-pending">Pending</span>
              <span v-else-if="node.status === 'processing'" class="status-badge status-processing">Processing...</span>
              <span v-else-if="node.status === 'completed'" class="status-badge status-completed">✓ Completed</span>
              <span v-else-if="node.status === 'error'" class="status-badge status-error">✗ Error</span>
              <span v-else-if="node.status === 'inactive'" class="status-badge status-inactive">⚠ Inactive</span>
            </div>
            
            <!-- Output connection point (right side) -->
            <div 
              class="connection-point output-point"
              :class="{ 'connecting': connectingFrom === node.id }"
              @mousedown="handleOutputMouseDown($event, node.id)"
              @click="handleOutputClick($event, node.id)"
              title="Output">
              <div class="connection-dot"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Control Panel -->
      <div class="control-panel">
        <div class="panel-section add-nodes-section">
          <div class="section-header">
            <h3>Add Nodes</h3>
            <button class="reset-workflow-btn" @click="handleClearWorkflow" :disabled="nodes.length === 0 || isProcessing" title="Clear workflow">
              <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
          <div class="node-buttons">
            <button class="node-btn" @click="addNode('upload')" :disabled="hasUploadNode || isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span>Upload</span>
            </button>
            <button class="node-btn" @click="addNode('parse')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Parse</span>
            </button>
            <button class="node-btn" @click="addNode('ocr')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span>OCR</span>
            </button>
            <button class="node-btn" @click="addNode('classify')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              <span>Classify</span>
            </button>
            <button class="node-btn" @click="addNode('extract')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Extract</span>
            </button>
            <button class="node-btn" @click="addNode('split')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12M8 12h12m-12 5h12M3 7h.01M3 12h.01M3 17h.01" />
              </svg>
              <span>Split</span>
            </button>
            <button class="node-btn node-btn-inactive" disabled title="Coming soon - Backend implementation pending">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Condition</span>
            </button>
            <button class="node-btn node-btn-inactive" disabled title="Coming soon - Backend implementation pending">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Validate</span>
            </button>
            <button class="node-btn node-btn-inactive" disabled title="Coming soon - Backend implementation pending">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <span>User Script</span>
            </button>
          </div>
        </div>

        <!-- Uploaded Files Section -->
        <div v-if="selectedNode && getSelectedNodeObject" class="panel-section node-settings-section">
          <h3>Node Settings: {{ getSelectedNodeObject.label }}</h3>
          
          <!-- Upload Node Settings -->
          <div v-if="getSelectedNodeObject.type === 'upload'" class="node-config-content">
            <div class="config-group">
              <label class="config-label">Uploaded Files</label>
              <div v-if="getSelectedNodeObject.files && getSelectedNodeObject.files.length > 0" class="file-items">
                <div v-for="(file, index) in getSelectedNodeObject.files" :key="`${getSelectedNodeObject.id}-${index}`" class="file-item-small">
                  <svg class="file-icon" width="14" height="14" fill="currentColor" viewBox="0 0 20 20">
                    <path v-if="file.name.endsWith('.pdf')" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
                    <path v-else fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
                  </svg>
                  <span class="file-name">{{ file.name }}</span>
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  <button class="file-remove-btn" @click="removeFileFromNode(getSelectedNodeObject.id, index)" :disabled="isProcessing">
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              <div v-else class="no-files">
                <span>No files uploaded</span>
              </div>
            </div>
          </div>
          
          <!-- Classify Node Settings -->
          <div v-else-if="getSelectedNodeObject.type === 'classify'" class="node-config-content">
            <div class="config-group">
              <label class="config-label">Classification Rules</label>
              <div class="rules-list">
                <div v-for="(rule, index) in getSelectedNodeObject.config?.rules || []" :key="index" class="rule-item">
                  <input 
                    v-model="rule.doc_type" 
                    placeholder="Doc Type"
                    class="rule-type-input"
                    :disabled="isProcessing"
                  />
                  <input 
                    v-model="rule.description" 
                    placeholder="Description"
                    class="rule-description-input"
                    :disabled="isProcessing"
                  />
                  <button class="rule-remove-btn" @click="removeRule(index)" :disabled="isProcessing">
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              <button class="add-rule-btn" @click="addRule" :disabled="isProcessing">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                Add Rule
              </button>
            </div>
          </div>
          
          <!-- Extract Node Settings -->
          <div v-else-if="getSelectedNodeObject.type === 'extract'" class="node-config-content">
            <div class="config-group">
              <label class="config-label">Extraction Target</label>
              <select v-model="getSelectedNodeObject.config.target" class="config-select" :disabled="isProcessing">
                <option value="document">Document</option>
                <option value="page">Page</option>
                <option value="table_row">Table Row</option>
              </select>
            </div>
            
            <div class="config-group">
              <div class="schema-mode-header">
                <label class="config-label">Schema Mode</label>
                <div class="view-toggle-group">
                  <button 
                    type="button"
                    @click="getSelectedNodeObject.config.schemaMode = 'auto'"
                    :class="{ active: getSelectedNodeObject.config.schemaMode === 'auto' }"
                    class="view-toggle-btn"
                    :disabled="isProcessing"
                    title="Auto Schema">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="toggle-icon">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </button>
                  <button 
                    type="button"
                    @click="getSelectedNodeObject.config.schemaMode = 'manual'"
                    :class="{ active: getSelectedNodeObject.config.schemaMode === 'manual' }"
                    class="view-toggle-btn"
                    :disabled="isProcessing"
                    title="Manual Schema">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="toggle-icon">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            <!-- Auto Schema Mode -->
            <div v-if="getSelectedNodeObject.config.schemaMode === 'auto'" class="config-group">
              <label class="config-label">Generation Prompt</label>
              <textarea 
                v-model="getSelectedNodeObject.config.schemaPrompt" 
                placeholder="Describe what data to extract (e.g., 'Extract invoice details including number, date, total amount, and vendor information')"
                class="schema-prompt-textarea"
                rows="3"
                :disabled="isProcessing"
              ></textarea>
              <button 
                class="generate-schema-btn-full" 
                @click="generateSchema" 
                :disabled="isProcessing || isGeneratingSchema || !getSelectedNodeObject.config.schemaPrompt"
                title="Generate schema from prompt">
                <svg v-if="!isGeneratingSchema" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <svg v-else class="spinner-small" width="14" height="14" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/>
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" opacity="0.75"/>
                </svg>
                {{ isGeneratingSchema ? 'Generating Schema...' : 'Generate Schema' }}
              </button>
              
              <!-- Preview generated schema -->
              <div v-if="getSelectedNodeObject.config?.schema?.fields?.length > 0" class="generated-schema-preview">
                <div class="preview-header">
                  <span class="preview-label">Generated Fields ({{ getSelectedNodeObject.config.schema.fields.length }})</span>
                  <button class="clear-schema-btn" @click="clearGeneratedSchema" :disabled="isProcessing">
                    Clear
                  </button>
                </div>
                <div class="preview-fields">
                  <div v-for="(field, index) in getSelectedNodeObject.config.schema.fields" :key="index" class="preview-field">
                    <span class="field-name-preview">{{ field.name }}</span>
                    <span class="field-type-badge">{{ field.type }}</span>
                    <span class="field-desc-preview">{{ field.description }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Manual Schema Mode -->
            <div v-if="getSelectedNodeObject.config.schemaMode === 'manual'" class="config-group">
              <div class="manual-input-header">
                <label class="config-label">Schema Input</label>
                <div class="view-toggle-group">
                  <button 
                    type="button"
                    @click="getSelectedNodeObject.config.manualMode = 'form'"
                    :class="{ active: getSelectedNodeObject.config.manualMode === 'form' }"
                    class="view-toggle-btn"
                    :disabled="isProcessing"
                    title="Form Input">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="toggle-icon">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </button>
                  <button 
                    type="button"
                    @click="getSelectedNodeObject.config.manualMode = 'json'"
                    :class="{ active: getSelectedNodeObject.config.manualMode === 'json' }"
                    class="view-toggle-btn"
                    :disabled="isProcessing"
                    title="JSON Input">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="toggle-icon">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                  </button>
                </div>
              </div>
              
              <!-- Form Input -->
              <div v-if="getSelectedNodeObject.config.manualMode === 'form'" class="manual-form-input">
                <div class="schema-fields-list">
                  <div v-for="(field, index) in getSelectedNodeObject.config?.schema?.fields || []" :key="index" class="schema-field-item">
                    <input 
                      v-model="field.name" 
                      placeholder="Field Name"
                      class="field-name-input"
                      :disabled="isProcessing"
                    />
                    <select v-model="field.type" class="field-type-select" :disabled="isProcessing">
                      <option value="string">String</option>
                      <option value="number">Number</option>
                      <option value="boolean">Boolean</option>
                      <option value="date">Date</option>
                    </select>
                    <input 
                      v-model="field.description" 
                      placeholder="Description"
                      class="field-description-input"
                      :disabled="isProcessing"
                    />
                    <button class="field-remove-btn" @click="removeSchemaField(index)" :disabled="isProcessing">
                      <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
                <button class="add-field-btn" @click="addSchemaField" :disabled="isProcessing">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                  </svg>
                  Add Field
                </button>
              </div>
              
              <!-- JSON Input -->
              <div v-if="getSelectedNodeObject.config.manualMode === 'json'" class="manual-json-input">
                <textarea 
                  v-model="schemaJsonInput" 
                  @blur="parseSchemaJson"
                  placeholder='{"fields": [{"name": "field1", "type": "string", "description": "Description"}]}'
                  class="schema-json-textarea"
                  rows="8"
                  :disabled="isProcessing"
                ></textarea>
                <div v-if="jsonParseError" class="json-error">
                  {{ jsonParseError }}
                </div>
                <button class="apply-json-btn" @click="parseSchemaJson" :disabled="isProcessing">
                  Apply JSON
                </button>
              </div>
            </div>
          </div>
          
          <!-- Split Node Settings -->
          <div v-else-if="getSelectedNodeObject.type === 'split'" class="node-config-content">
            <div class="config-group">
              <label class="config-label">Split Categories</label>
              <div class="categories-list">
                <div v-for="(category, index) in getSelectedNodeObject.config?.categories || []" :key="index" class="category-item">
                  <input 
                    v-model="category.name" 
                    placeholder="Category"
                    class="category-name-input"
                    :disabled="isProcessing"
                  />
                  <input 
                    v-model="category.description" 
                    placeholder="Description"
                    class="category-description-input"
                    :disabled="isProcessing"
                  />
                  <button class="category-remove-btn" @click="removeCategory(index)" :disabled="isProcessing">
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              <button class="add-category-btn" @click="addCategory" :disabled="isProcessing">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                Add Category
              </button>
            </div>
          </div>
          
          <!-- Condition Node Settings (Inactive) -->
          <div v-else-if="getSelectedNodeObject.type === 'condition'" class="node-config-content">
            <div class="inactive-notice">
              <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h4>Coming Soon</h4>
              <p>Condition node is not yet implemented in the backend. You can add it to your workflow, but it won't execute.</p>
            </div>
            <div class="config-group">
              <label class="config-label">Conditions</label>
              <div class="conditions-list">
                <div v-for="(condition, index) in getSelectedNodeObject.config?.conditions || []" :key="index" class="condition-item">
                  <input 
                    v-model="condition.field" 
                    placeholder="Field name"
                    class="condition-field-input"
                    disabled
                  />
                  <select v-model="condition.operator" class="condition-operator-select" disabled>
                    <option value="equals">Equals</option>
                    <option value="not_equals">Not Equals</option>
                    <option value="greater_than">Greater Than</option>
                    <option value="less_than">Less Than</option>
                    <option value="contains">Contains</option>
                  </select>
                  <input 
                    v-model="condition.value" 
                    placeholder="Value"
                    class="condition-value-input"
                    disabled
                  />
                  <button class="condition-remove-btn" @click="removeCondition(index)" disabled>
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              <button class="add-condition-btn" @click="addCondition" disabled>
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                Add Condition
              </button>
            </div>
            <div class="config-group">
              <label class="config-label">Logic</label>
              <select v-model="getSelectedNodeObject.config.logic" class="config-select" disabled>
                <option value="AND">AND (all conditions must match)</option>
                <option value="OR">OR (any condition must match)</option>
              </select>
            </div>
          </div>
          
          <!-- Validate Node Settings (Inactive) -->
          <div v-else-if="getSelectedNodeObject.type === 'validate'" class="node-config-content">
            <div class="inactive-notice">
              <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h4>Coming Soon</h4>
              <p>Validate node is not yet implemented in the backend. You can add it to your workflow, but it won't execute.</p>
            </div>
            <div class="config-group">
              <label class="config-label">Validation Rules</label>
              <div class="validation-rules-list">
                <div v-for="(rule, index) in getSelectedNodeObject.config?.rules || []" :key="index" class="validation-rule-item">
                  <input 
                    v-model="rule.field" 
                    placeholder="Field name"
                    class="rule-field-input"
                    disabled
                  />
                  <select v-model="rule.rule" class="rule-type-select" disabled>
                    <option value="required">Required</option>
                    <option value="range">Range</option>
                    <option value="date_format">Date Format</option>
                    <option value="pattern">Pattern</option>
                    <option value="email">Email</option>
                    <option value="url">URL</option>
                  </select>
                  <input 
                    v-model="rule.value" 
                    placeholder="Value/Pattern"
                    class="rule-value-input"
                    disabled
                  />
                  <button class="rule-remove-btn" @click="removeValidationRule(index)" disabled>
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              <button class="add-validation-rule-btn" @click="addValidationRule" disabled>
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                Add Rule
              </button>
            </div>
            <div class="config-group">
              <label class="config-label">On Error</label>
              <select v-model="getSelectedNodeObject.config.onError" class="config-select" disabled>
                <option value="flag">Flag for review</option>
                <option value="stop">Stop workflow</option>
                <option value="continue">Continue anyway</option>
              </select>
            </div>
          </div>
          
          <!-- User Script Node Settings (Inactive) -->
          <div v-else-if="getSelectedNodeObject.type === 'script'" class="node-config-content">
            <div class="inactive-notice">
              <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h4>Coming Soon</h4>
              <p>User Script node is not yet implemented in the backend. You can add it to your workflow, but it won't execute.</p>
            </div>
            <div class="config-group">
              <label class="config-label">Script Type</label>
              <select v-model="getSelectedNodeObject.config.scriptType" class="config-select" disabled>
                <option value="python">Python (.py)</option>
                <option value="javascript">JavaScript (.js)</option>
                <option value="bash">Bash (.sh)</option>
              </select>
            </div>
            <div class="config-group">
              <label class="config-label">Upload Script</label>
              <input type="file" accept=".py,.js,.sh" class="script-file-input" disabled />
              <p class="config-hint">Upload a script file to transform document data</p>
            </div>
            <div class="config-group">
              <label class="config-label">Script Parameters (JSON)</label>
              <textarea 
                v-model="getSelectedNodeObject.config.parametersJson" 
                placeholder='{"param1": "value1", "param2": "value2"}'
                class="script-params-textarea"
                rows="4"
                disabled
              ></textarea>
            </div>
          </div>
          
          <!-- OCR/Parse Node Settings -->
          <div v-else class="node-config-content">
            <div class="config-group">
              <label class="config-label">Processing Tier</label>
              <select v-model="getSelectedNodeObject.tier" class="config-select" :disabled="isProcessing">
                <option value="Rapid">Rapid</option>
                <option value="Normal">Normal</option>
                <option value="Advance">Advance</option>
              </select>
            </div>
            <div class="no-config">
              <p>No additional configuration needed for this node type.</p>
            </div>
          </div>
        </div>

        <div v-if="workflowResults.length > 0" class="panel-section results-section-panel" style="display: none;">
          <h3>Results</h3>
          <div class="results-list">
            <div v-for="result in workflowResults" :key="result.nodeId" class="result-item">
              <div class="result-header">
                <span class="result-node">{{ result.nodeLabel }}</span>
                <span :class="['result-status', `status-${result.status}`]">
                  {{ result.status }}
                </span>
              </div>
              <div v-if="result.data" class="result-data">
                <pre>{{ formatResult(result.data) }}</pre>
              </div>
              <div v-if="result.error" class="result-error">
                {{ result.error }}
              </div>
            </div>
          </div>
        </div>

        <div class="panel-section workflow-summary-section">
          <h3>Workflow</h3>
          <div class="workflow-summary">
            <div class="summary-item">
              <span class="summary-label">Nodes:</span>
              <span class="summary-value">{{ nodes.length }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Status:</span>
              <span class="summary-value">{{ workflowStatus }}</span>
            </div>
          </div>
        </div>

        <div class="panel-section execute-section">
          <div class="execute-buttons">
            <button 
              v-if="workflowResults.length > 0"
              class="view-results-btn" 
              @click="showResultsModal = true"
              title="View workflow results">
              <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
            <button class="execute-btn" @click="handleExecuteWorkflow" :disabled="!canExecute || isProcessing">
              <svg v-if="!isProcessing" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <svg v-else class="spinner" width="16" height="16" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/>
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" opacity="0.75"/>
              </svg>
              {{ isProcessing ? 'Processing...' : 'Execute Workflow' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Results Modal -->
    <div v-if="showResultsModal" class="results-modal-overlay" @click="closeResultsModal">
      <div class="results-modal" @click.stop>
        <div class="modal-header">
          <h2>Workflow Results</h2>
          <button class="modal-close-btn" @click="closeResultsModal">
            <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div class="modal-body">
          <div v-if="workflowResults.length === 0" class="no-results">
            <p>No results available</p>
          </div>
          
          <div v-else class="results-timeline">
            <div v-for="(result, index) in workflowResults" :key="result.nodeId" class="result-card">
              <div class="result-card-header">
                <div class="result-step">
                  <span class="step-number">{{ index + 1 }}</span>
                  <span class="step-name">{{ result.nodeLabel }}</span>
                </div>
                <span :class="['result-badge', `badge-${result.status}`]">
                  <svg v-if="result.status === 'success'" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                  </svg>
                  <svg v-else width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  {{ result.status }}
                </span>
              </div>
              
              <div class="result-card-body">
                <div v-if="result.error" class="result-error-detail">
                  <div class="error-icon">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div class="error-content">
                    <p class="error-title">Error occurred</p>
                    <p class="error-message">{{ result.error }}</p>
                  </div>
                </div>
                
                <div v-else-if="result.data" class="result-data-detail">
                  <pre class="result-json">{{ formatResultData(result.data) }}</pre>
                </div>
                
                <div v-else class="result-empty">
                  <p>No data returned</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="modal-btn modal-btn-secondary" @click="closeResultsModal">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useJourney } from '~/composables/useJourney'
import { useOCR } from '~/composables/useOCR'

const {
  nodes,
  isProcessing,
  workflowResults,
  addNode,
  removeNode,
  clearWorkflow,
  updateNodeFiles,
  executeWorkflow
} = useJourney()

const canvasArea = ref<HTMLElement | null>(null)
const draggedNode = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })
const connectingFrom = ref<string | null>(null)
const selectedNode = ref<string | null>(null)
const isDraggingConnection = ref(false)
const dragConnectionEnd = ref({ x: 0, y: 0 })
const nearbyInputNode = ref<string | null>(null)
const isGeneratingSchema = ref(false)
const schemaJsonInput = ref('')
const jsonParseError = ref('')
const showResultsModal = ref(false)
const selectedConnection = ref<{ fromId: string; toId: string } | null>(null)
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const isSpacePressed = ref(false)

const uploadNodes = computed(() => nodes.value.filter(n => n.type === 'upload'))
const totalUploadedFiles = computed(() => {
  return uploadNodes.value.reduce((total, node) => total + (node.files?.length || 0), 0)
})

const removeFileFromNode = (nodeId: string, fileIndex: number) => {
  const node = nodes.value.find(n => n.id === nodeId)
  if (node && node.files) {
    node.files = node.files.filter((_, index) => index !== fileIndex)
  }
}

const hasUploadNode = computed(() => nodes.value.some(n => n.type === 'upload'))
const canExecute = computed(() => {
  if (nodes.value.length === 0) return false
  if (!hasUploadNode.value) return false
  const uploadNode = nodes.value.find(n => n.type === 'upload')
  return uploadNode?.files && uploadNode.files.length > 0
})

const workflowStatus = computed(() => {
  if (isProcessing.value) return 'Running'
  if (nodes.value.every(n => n.status === 'completed')) return 'Completed'
  if (nodes.value.some(n => n.status === 'error')) return 'Error'
  return 'Ready'
})

const triggerFileInput = (nodeId: string) => {
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.accept = '.png,.jpg,.jpeg,.pdf,.txt,.md,.docx'
  input.onchange = async (e: Event) => {
    const target = e.target as HTMLInputElement
    if (target.files) {
      const node = nodes.value.find(n => n.id === nodeId)
      if (node && node.type === 'upload') {
        // Append new files to existing files in the node
        const newFiles = Array.from(target.files)
        const existingFiles = node.files || []
        
        // Filter out duplicates by name and size
        const uniqueNewFiles = newFiles.filter(newFile => 
          !existingFiles.some(existingFile => 
            existingFile.name === newFile.name && existingFile.size === newFile.size
          )
        )
        
        node.files = [...existingFiles, ...uniqueNewFiles]
        
        // Also upload to the main file list (left sidebar)
        const { uploadFiles } = useOCR()
        await uploadFiles(uniqueNewFiles)
      }
    }
  }
  input.click()
}

const handleFileSelect = async (event: Event, nodeId: string) => {
  const input = event.target as HTMLInputElement
  if (input.files) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node && node.type === 'upload') {
      // Append new files to existing files
      const newFiles = Array.from(input.files)
      const existingFiles = node.files || []
      
      // Filter out duplicates
      const uniqueNewFiles = newFiles.filter(newFile => 
        !existingFiles.some(existingFile => 
          existingFile.name === newFile.name && existingFile.size === newFile.size
        )
      )
      
      node.files = [...existingFiles, ...uniqueNewFiles]
      
      // Also upload to the main file list (left sidebar)
      const { uploadFiles } = useOCR()
      await uploadFiles(uniqueNewFiles)
    }
  }
}

const getNodeIcon = (type: string) => {
  // Return component name for dynamic icon rendering
  return type
}

const handleExecuteWorkflow = async () => {
  if (!canExecute.value) return
  
  try {
    await executeWorkflow()
    // Show results modal after successful execution
    showResultsModal.value = true
  } catch (error: any) {
    console.error('Workflow execution failed:', error)
    // Still show modal even on error to display partial results
    showResultsModal.value = true
  }
}

const closeResultsModal = () => {
  showResultsModal.value = false
}

const handleClearWorkflow = () => {
  if (confirm('Clear all nodes?')) {
    clearWorkflow()
  }
}

const formatResult = (data: any): string => {
  if (typeof data === 'string') return data.substring(0, 200)
  return JSON.stringify(data, null, 2).substring(0, 200)
}

const formatResultData = (data: any): string => {
  if (typeof data === 'string') return data
  return JSON.stringify(data, null, 2)
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Node dragging
const handleNodeMouseDown = (event: MouseEvent, nodeId: string) => {
  if (isProcessing.value) return
  
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return
  
  const canvas = canvasArea.value
  if (!canvas) return
  
  draggedNode.value = nodeId
  selectedNode.value = nodeId
  
  // Calculate offset relative to the node's current position
  const rect = canvas.getBoundingClientRect()
  const mouseX = event.clientX - rect.left + canvas.scrollLeft
  const mouseY = event.clientY - rect.top + canvas.scrollTop
  
  dragOffset.value = {
    x: mouseX - node.x,
    y: mouseY - node.y
  }
  
  event.preventDefault()
  event.stopPropagation()
}

const handleCanvasMouseMove = (event: MouseEvent) => {
  // Handle panning
  if (isPanning.value) {
    const canvas = canvasArea.value
    if (!canvas) return
    
    const deltaX = panStart.value.x - event.clientX
    const deltaY = panStart.value.y - event.clientY
    
    canvas.scrollLeft = deltaX
    canvas.scrollTop = deltaY
    return
  }
  
  // Handle node dragging
  if (draggedNode.value && !isDraggingConnection.value) {
    const node = nodes.value.find(n => n.id === draggedNode.value)
    if (!node) return
    
    const canvas = canvasArea.value
    if (!canvas) return
    
    const rect = canvas.getBoundingClientRect()
    
    // Calculate mouse position relative to canvas including scroll
    const mouseX = event.clientX - rect.left + canvas.scrollLeft
    const mouseY = event.clientY - rect.top + canvas.scrollTop
    
    // Update node position
    node.x = Math.max(20, mouseX - dragOffset.value.x)
    node.y = Math.max(20, mouseY - dragOffset.value.y)
  }
  
  // Handle connection dragging
  if (isDraggingConnection.value && connectingFrom.value) {
    const canvas = canvasArea.value
    if (!canvas) return
    
    const rect = canvas.getBoundingClientRect()
    const mouseX = event.clientX - rect.left + canvas.scrollLeft
    const mouseY = event.clientY - rect.top + canvas.scrollTop
    
    // Update drag end position
    dragConnectionEnd.value = { x: mouseX, y: mouseY }
    
    // Check for nearby input points
    const snapDistance = 40 // pixels
    let closestNode: string | null = null
    let closestDistance = snapDistance
    
    for (const node of nodes.value) {
      if (node.type === 'upload' || node.id === connectingFrom.value) continue
      
      // Calculate input point position (left side, middle)
      // Node height is approximately 140px, so middle is at 70px
      const inputX = node.x
      const inputY = node.y + 70
      
      const distance = Math.sqrt(
        Math.pow(mouseX - inputX, 2) + Math.pow(mouseY - inputY, 2)
      )
      
      if (distance < closestDistance) {
        closestDistance = distance
        closestNode = node.id
      }
    }
    
    nearbyInputNode.value = closestNode
    
    // Snap to nearby input point
    if (closestNode) {
      const targetNode = nodes.value.find(n => n.id === closestNode)
      if (targetNode) {
        dragConnectionEnd.value = {
          x: targetNode.x,
          y: targetNode.y + 70 // Match the input point position
        }
      }
    }
  }
}

const handleCanvasMouseUp = () => {
  if (isPanning.value) {
    isPanning.value = false
    return
  }
  
  if (isDraggingConnection.value) {
    // If near an input node, create connection
    if (nearbyInputNode.value && connectingFrom.value) {
      const fromNode = nodes.value.find(n => n.id === connectingFrom.value)
      const toNode = nodes.value.find(n => n.id === nearbyInputNode.value)
      
      if (fromNode && toNode && fromNode.id !== toNode.id) {
        if (!fromNode.connections) {
          fromNode.connections = []
        }
        
        if (!fromNode.connections.includes(toNode.id)) {
          fromNode.connections.push(toNode.id)
        }
      }
    }
    
    connectingFrom.value = null
    isDraggingConnection.value = false
    nearbyInputNode.value = null
  }
  draggedNode.value = null
}

// Node connections
const handleOutputMouseDown = (event: MouseEvent, nodeId: string) => {
  if (isProcessing.value) return
  
  connectingFrom.value = nodeId
  isDraggingConnection.value = true
  
  event.preventDefault()
  event.stopPropagation()
}

const handleInputMouseUp = (event: MouseEvent, nodeId: string) => {
  if (isProcessing.value || !connectingFrom.value || !isDraggingConnection.value) return
  
  const fromNode = nodes.value.find(n => n.id === connectingFrom.value)
  const toNode = nodes.value.find(n => n.id === nodeId)
  
  if (!fromNode || !toNode || fromNode.id === toNode.id) {
    connectingFrom.value = null
    isDraggingConnection.value = false
    return
  }
  
  // Add connection
  if (!fromNode.connections) {
    fromNode.connections = []
  }
  
  if (!fromNode.connections.includes(nodeId)) {
    fromNode.connections.push(nodeId)
  }
  
  connectingFrom.value = null
  isDraggingConnection.value = false
  
  event.preventDefault()
  event.stopPropagation()
}

const handleOutputClick = (event: MouseEvent, nodeId: string) => {
  if (isProcessing.value || isDraggingConnection.value) return
  
  // Toggle connection mode
  if (connectingFrom.value === nodeId) {
    connectingFrom.value = null
  } else {
    connectingFrom.value = nodeId
  }
  
  event.preventDefault()
  event.stopPropagation()
}

const handleInputClick = (event: MouseEvent, nodeId: string) => {
  if (isProcessing.value || !connectingFrom.value || isDraggingConnection.value) return
  
  const fromNode = nodes.value.find(n => n.id === connectingFrom.value)
  const toNode = nodes.value.find(n => n.id === nodeId)
  
  if (!fromNode || !toNode || fromNode.id === toNode.id) {
    connectingFrom.value = null
    return
  }
  
  // Add connection
  if (!fromNode.connections) {
    fromNode.connections = []
  }
  
  if (!fromNode.connections.includes(nodeId)) {
    fromNode.connections.push(nodeId)
  }
  
  connectingFrom.value = null
  
  event.preventDefault()
  event.stopPropagation()
}

const isConnected = (fromId: string, toId: string): boolean => {
  const fromNode = nodes.value.find(n => n.id === fromId)
  return fromNode?.connections?.includes(toId) || false
}

const getDragConnectionPath = (): string => {
  if (!connectingFrom.value || !isDraggingConnection.value) return ''
  
  const fromNode = nodes.value.find(n => n.id === connectingFrom.value)
  if (!fromNode) return ''
  
  const fromX = fromNode.x + 220 // Right side of node (updated width)
  const fromY = fromNode.y + 70 // Middle of node (updated height)
  const toX = dragConnectionEnd.value.x
  const toY = dragConnectionEnd.value.y
  
  const midX = (fromX + toX) / 2
  
  return `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`
}

const getConnectionPath = (fromId: string, toId: string): string => {
  const fromNode = nodes.value.find(n => n.id === fromId)
  const toNode = nodes.value.find(n => n.id === toId)
  
  if (!fromNode || !toNode) return ''
  
  const fromX = fromNode.x + 220 // Right side of node (updated width)
  const fromY = fromNode.y + 70 // Middle of node (updated height)
  const toX = toNode.x // Left side of node
  const toY = toNode.y + 70 // Middle of node (updated height)
  
  const midX = (fromX + toX) / 2
  
  return `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`
}

// Get selected node object
const getSelectedNodeObject = computed(() => {
  if (!selectedNode.value) return null
  return nodes.value.find(n => n.id === selectedNode.value) || null
})

// Node configuration management functions
const addRule = () => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'classify') return
  
  if (!node.config) {
    node.config = { rules: [] }
  }
  if (!node.config.rules) {
    node.config.rules = []
  }
  
  node.config.rules.push({ doc_type: '', description: '' })
}

const removeRule = (index: number) => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'classify' || !node.config?.rules) return
  
  node.config.rules.splice(index, 1)
}

const addSchemaField = () => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'extract') return
  
  if (!node.config) {
    node.config = { target: 'document', schema: { fields: [] } }
  }
  if (!node.config.schema) {
    node.config.schema = { fields: [] }
  }
  if (!node.config.schema.fields) {
    node.config.schema.fields = []
  }
  
  node.config.schema.fields.push({ name: '', type: 'string', description: '' })
}

const removeSchemaField = (index: number) => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'extract' || !node.config?.schema?.fields) return
  
  node.config.schema.fields.splice(index, 1)
}

const addCategory = () => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'split') return
  
  if (!node.config) {
    node.config = { categories: [] }
  }
  if (!node.config.categories) {
    node.config.categories = []
  }
  
  node.config.categories.push({ name: '', description: '' })
}

const removeCategory = (index: number) => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'split' || !node.config?.categories) return
  
  node.config.categories.splice(index, 1)
}

// Condition node helpers
const addCondition = () => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'condition') return
  
  if (!node.config) {
    node.config = { conditions: [], logic: 'AND' }
  }
  if (!node.config.conditions) {
    node.config.conditions = []
  }
  
  node.config.conditions.push({ field: '', operator: 'equals', value: '' })
}

const removeCondition = (index: number) => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'condition' || !node.config?.conditions) return
  
  node.config.conditions.splice(index, 1)
}

// Validation node helpers
const addValidationRule = () => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'validate') return
  
  if (!node.config) {
    node.config = { rules: [], onError: 'flag' }
  }
  if (!node.config.rules) {
    node.config.rules = []
  }
  
  node.config.rules.push({ field: '', rule: 'required', value: '' })
}

const removeValidationRule = (index: number) => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'validate' || !node.config?.rules) return
  
  node.config.rules.splice(index, 1)
}

// Schema generation for extract node
const generateSchema = async () => {
  if (!selectedNode.value) return
  
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'extract') return
  
  // Check if prompt is provided
  if (!node.config.schemaPrompt || node.config.schemaPrompt.trim() === '') {
    alert('Please enter a prompt describing what data to extract')
    return
  }
  
  // Find upload node to get the file
  const uploadNode = nodes.value.find(n => n.type === 'upload')
  if (!uploadNode || !uploadNode.files || uploadNode.files.length === 0) {
    alert('Please upload a file first')
    return
  }
  
  const file = uploadNode.files[0]
  isGeneratingSchema.value = true
  
  try {
    const config = useRuntimeConfig()
    const apiBaseUrl = config.public.apiBaseUrl as string
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tier', node.tier)
    formData.append('target', node.config.target || 'document')
    formData.append('prompt', node.config.schemaPrompt)
    
    const response = await $fetch<any>(`${apiBaseUrl}/generate-schema`, {
      method: 'POST',
      body: formData
    })
    
    // Update node config with generated schema
    if (response.schema && response.schema.fields) {
      if (!node.config.schema) {
        node.config.schema = { fields: [] }
      }
      node.config.schema.fields = response.schema.fields
    }
  } catch (error: any) {
    console.error('Schema generation failed:', error)
    alert(`Schema generation failed: ${error.message || 'Unknown error'}`)
  } finally {
    isGeneratingSchema.value = false
  }
}

const clearGeneratedSchema = () => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'extract') return
  
  if (confirm('Clear all generated schema fields?')) {
    if (node.config.schema) {
      node.config.schema.fields = []
    }
  }
}

const parseSchemaJson = () => {
  if (!selectedNode.value) return
  const node = nodes.value.find(n => n.id === selectedNode.value)
  if (!node || node.type !== 'extract') return
  
  jsonParseError.value = ''
  
  try {
    const parsed = JSON.parse(schemaJsonInput.value)
    
    if (!parsed.fields || !Array.isArray(parsed.fields)) {
      jsonParseError.value = 'JSON must contain a "fields" array'
      return
    }
    
    // Validate fields structure
    for (const field of parsed.fields) {
      if (!field.name || !field.type) {
        jsonParseError.value = 'Each field must have "name" and "type" properties'
        return
      }
    }
    
    // Apply the schema
    if (!node.config.schema) {
      node.config.schema = { fields: [] }
    }
    node.config.schema.fields = parsed.fields
    
    jsonParseError.value = ''
  } catch (error: any) {
    jsonParseError.value = `Invalid JSON: ${error.message}`
  }
}

// Watch for schema changes to update JSON input
watch(() => getSelectedNodeObject.value?.config?.schema, (newSchema) => {
  if (newSchema && getSelectedNodeObject.value?.config?.manualMode === 'json') {
    schemaJsonInput.value = JSON.stringify(newSchema, null, 2)
  }
}, { deep: true })

// Handle connection selection
const handleConnectionClick = (fromId: string, toId: string, event: MouseEvent) => {
  event.stopPropagation()
  selectedConnection.value = { fromId, toId }
  selectedNode.value = null // Deselect node when selecting connection
}

// Handle keyboard events for deleting connections and nodes
const handleKeyDown = (event: KeyboardEvent) => {
  // Track space key for panning
  if (event.code === 'Space' && !isSpacePressed.value) {
    isSpacePressed.value = true
    event.preventDefault()
  }
  
  if (event.key === 'Delete' || event.key === 'Backspace') {
    // Delete selected connection
    if (selectedConnection.value) {
      deleteConnection(selectedConnection.value.fromId, selectedConnection.value.toId)
      event.preventDefault()
    }
    // Delete selected node
    else if (selectedNode.value) {
      const node = nodes.value.find(n => n.id === selectedNode.value)
      if (node && !isProcessing.value) {
        removeNode(selectedNode.value)
        selectedNode.value = null
        event.preventDefault()
      }
    }
  }
}

const handleKeyUp = (event: KeyboardEvent) => {
  if (event.code === 'Space') {
    isSpacePressed.value = false
    isPanning.value = false
  }
}

// Handle canvas mouse down for panning
const handleCanvasMouseDown = (event: MouseEvent) => {
  const canvas = canvasArea.value
  if (!canvas) return
  
  // Start panning with space + left click or middle mouse button
  if ((isSpacePressed.value && event.button === 0) || event.button === 1) {
    isPanning.value = true
    panStart.value = {
      x: event.clientX + canvas.scrollLeft,
      y: event.clientY + canvas.scrollTop
    }
    event.preventDefault()
  }
}

// Delete a connection
const deleteConnection = (fromId: string, toId: string) => {
  const fromNode = nodes.value.find(n => n.id === fromId)
  if (fromNode && fromNode.connections) {
    fromNode.connections = fromNode.connections.filter(id => id !== toId)
  }
  selectedConnection.value = null
}

// Deselect connection when clicking canvas
const handleCanvasClick = () => {
  selectedConnection.value = null
}

// Setup keyboard listener
onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
})
</script>

<style scoped>
.journey-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.journey-content {
  display: flex;
  flex: 1;
  overflow: hidden;
  height: 100%;
}

.workflow-canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-right: 1px solid #e5e7eb;
  overflow: hidden;
}

.canvas-header {
  padding: 1.5rem 1.5rem 1rem 1.5rem;
  background: white;
  border-bottom: 1px solid #e5e7eb;
}

.canvas-title h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
}

.canvas-title p {
  margin: 0;
  color: #6b7280;
  font-size: 0.875rem;
}

.canvas-area {
  flex: 1;
  position: relative;
  overflow: auto;
  padding: 2rem;
  background: #fafafa;
  min-height: 0;
  cursor: default;
  min-width: 100%;
}

/* Show grab cursor when space is pressed */
.canvas-area.panning:not(:active) {
  cursor: grab;
}

/* Show grabbing cursor when actively panning */
.canvas-area.panning:active,
.canvas-area.panning {
  cursor: grabbing;
  user-select: none;
}

.connections-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.connection-line {
  pointer-events: stroke;
  cursor: pointer;
  transition: stroke 0.2s, stroke-width 0.2s;
}

.connection-line:hover {
  stroke: #ff8c5a !important;
  stroke-width: 3 !important;
}

.canvas-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9ca3af;
}

.canvas-empty svg {
  margin-bottom: 1rem;
}

.workflow-node {
  position: absolute;
  width: 220px;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.3s, border-color 0.3s;
  z-index: 2;
}

.workflow-node.node-selected {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.workflow-node.node-dragging {
  cursor: grabbing;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  z-index: 10;
}

.workflow-node.node-active {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.workflow-node.node-complete {
  border-color: #10b981;
}

.workflow-node.node-error {
  border-color: #ef4444;
}

.workflow-node.node-inactive {
  opacity: 0.6;
  border-color: #9ca3af;
  border-style: dashed;
}

.node-condition {
  border-color: #f59e0b;
}

.node-validate {
  border-color: #10b981;
}

.node-script {
  border-color: #8b5cf6;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  border-radius: 6px 6px 0 0;
  cursor: grab;
  user-select: none;
}

.node-header:active {
  cursor: grabbing;
}

.node-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-title {
  flex: 1;
  font-weight: 500;
  color: #1f2937;
  font-size: 0.8rem;
}

.node-remove {
  padding: 0.25rem;
  background: none;
  border: none;
  cursor: pointer;
  color: #6b7280;
  transition: color 0.2s;
}

.node-remove:hover:not(:disabled) {
  color: #ef4444;
}

.node-body {
  padding: 0.75rem;
}

.node-config {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-btn, .config-select {
  padding: 0.4rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
}

.config-btn {
  background: #f3f4f6;
  cursor: pointer;
  transition: background 0.2s;
}

.config-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

.node-status {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #e5e7eb;
}

.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 500;
}

.status-pending {
  background: #f3f4f6;
  color: #6b7280;
}

.status-processing {
  background: #dbeafe;
  color: #1e40af;
}

.status-completed {
  background: #d1fae5;
  color: #065f46;
}

.status-error {
  background: #fee2e2;
  color: #991b1b;
}

.connection-point {
  position: absolute;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 3;
  transition: all 0.2s;
}

.connection-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #9ca3af;
  border: 2px solid white;
  transition: all 0.2s;
}

.input-point .connection-dot {
  background: #f97316;
}

.output-point .connection-dot {
  background: #3b82f6;
}

.connection-point:hover .connection-dot {
  opacity: 0.8;
}

.connection-point.connecting .connection-dot {
  animation: pulse-connection 1s ease-in-out infinite;
}

.connection-point.nearby .connection-dot {
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.3);
}

@keyframes pulse-connection {
  0%, 100% { 
    opacity: 1;
  }
  50% { 
    opacity: 0.5;
  }
}

.input-point {
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
}

.output-point {
  right: -12px;
  top: 50%;
  transform: translateY(-50%);
}

.node-connector {
  display: none;
}

.control-panel {
  width: 360px;
  background: white;
  border-left: 1px solid #e5e7eb;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.panel-section {
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.panel-section:last-child {
  border-bottom: none;
}

.add-nodes-section {
  background: white;
}

.add-nodes-section h3 {
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #1f2937;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.node-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.node-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: #374151;
  font-size: 0.875rem;
  font-weight: 500;
}

.node-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #3b82f6;
  color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.node-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.node-btn svg {
  flex-shrink: 0;
}

/* Section Header with Reset Button */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.section-header h3 {
  margin: 0;
}

.reset-workflow-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  color: #ef4444;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
}

.reset-workflow-btn:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #fecaca;
  color: #dc2626;
}

.reset-workflow-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  color: #d1d5db;
}

.files-section {
  max-height: 300px;
  overflow-y: auto;
}

.node-settings-section {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.node-settings-section h3 {
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #1f2937;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.node-config-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.config-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-label-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.generate-schema-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #374151;
  font-weight: 500;
}

.generate-schema-btn:hover:not(:disabled) {
  background: #f0f9ff;
  border-color: #3b82f6;
  color: #3b82f6;
}

.generate-schema-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner-small {
  animation: spin 1s linear infinite;
}

.schema-mode-header,
.manual-input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.view-toggle-group {
  display: flex;
  border-radius: 0.25rem;
  border: 1px solid #e5e7eb;
  background-color: #f9fafb;
  padding: 0.075rem;
  width: fit-content;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.3rem;
  background-color: transparent;
  color: #6b7280;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.15rem;
}

.view-toggle-btn:hover:not(:disabled) {
  background-color: #e5e7eb;
  color: #4b5563;
}

.view-toggle-btn.active {
  background-color: #ffffff;
  color: #111827;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.view-toggle-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toggle-icon {
  width: 0.75rem;
  height: 0.75rem;
}

.schema-prompt-textarea,
.schema-json-textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
  font-family: inherit;
  resize: vertical;
  margin-top: 0.5rem;
}

.schema-json-textarea {
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  background: #f9fafb;
}

.generate-schema-btn-full {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
  margin-top: 0.5rem;
}

.generate-schema-btn-full:hover:not(:disabled) {
  background: #2563eb;
}

.generate-schema-btn-full:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.generated-schema-preview {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.preview-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: #374151;
  text-transform: uppercase;
}

.clear-schema-btn {
  padding: 0.25rem 0.5rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 3px;
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #dc2626;
}

.clear-schema-btn:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #dc2626;
}

.preview-fields {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.preview-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: white;
  border-radius: 3px;
  font-size: 0.7rem;
}

.field-name-preview {
  font-weight: 600;
  color: #1f2937;
  min-width: 60px;
}

.field-type-badge {
  padding: 0.125rem 0.375rem;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 3px;
  font-size: 0.65rem;
  font-weight: 500;
  text-transform: uppercase;
}

.field-desc-preview {
  flex: 1;
  color: #6b7280;
  font-size: 0.7rem;
}

.manual-form-input,
.manual-json-input {
  margin-top: 0.75rem;
}

.json-error {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 4px;
  color: #dc2626;
  font-size: 0.7rem;
}

.apply-json-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #374151;
  font-weight: 500;
  margin-top: 0.5rem;
}

.apply-json-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #3b82f6;
  color: #3b82f6;
}

.apply-json-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.config-select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  background: white;
}

.rules-list,
.schema-fields-list,
.categories-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.rule-item,
.schema-field-item,
.category-item {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.rule-type-input {
  width: 90px;
  flex-shrink: 0;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
}

.rule-description-input {
  flex: 1;
  min-width: 0;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
}

.category-name-input {
  width: 90px;
  flex-shrink: 0;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
}

.category-description-input {
  flex: 1;
  min-width: 0;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
}

.field-name-input {
  width: 80px;
  flex-shrink: 0;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
}

.field-type-select {
  width: 75px;
  flex-shrink: 0;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
  background: white;
}

.field-description-input {
  flex: 1;
  min-width: 0;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
}

.rule-remove-btn,
.field-remove-btn,
.category-remove-btn {
  flex-shrink: 0;
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 3px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rule-remove-btn:hover:not(:disabled),
.field-remove-btn:hover:not(:disabled),
.category-remove-btn:hover:not(:disabled) {
  background: #fef2f2;
  color: #dc2626;
}

.add-rule-btn,
.add-field-btn,
.add-category-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #374151;
}

.add-rule-btn:hover:not(:disabled),
.add-field-btn:hover:not(:disabled),
.add-category-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #3b82f6;
  color: #3b82f6;
}

.no-config {
  padding: 1rem;
  text-align: center;
  color: #9ca3af;
  font-size: 0.75rem;
  font-style: italic;
}

.files-section h3 {
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #1f2937;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.upload-node-files {
  margin-bottom: 1rem;
}

.upload-node-files:last-child {
  margin-bottom: 0;
}

.upload-node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: #f3f4f6;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.upload-node-name {
  font-size: 0.75rem;
  font-weight: 600;
  color: #374151;
}

.upload-node-count {
  font-size: 0.75rem;
  color: #6b7280;
}

.file-items {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.file-item-small {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  font-size: 0.75rem;
  transition: all 0.2s;
}

.file-item-small:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.file-icon {
  flex-shrink: 0;
  color: #6b7280;
}

.file-name {
  flex: 1;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.file-size {
  flex-shrink: 0;
  color: #9ca3af;
  font-size: 0.7rem;
}

.file-remove-btn {
  flex-shrink: 0;
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 3px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-remove-btn:hover:not(:disabled) {
  background: #fef2f2;
  color: #dc2626;
}

.file-remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-files {
  padding: 1rem;
  text-align: center;
  color: #9ca3af;
  font-size: 0.75rem;
  font-style: italic;
}

.results-section-panel {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.workflow-summary-section {
  margin-top: auto;
  background: white;
  border-top: 1px solid #e5e7eb;
}

.execute-section {
  position: sticky;
  bottom: 0;
  background: white;
  border-top: 1px solid #e5e7eb;
  border-bottom: none;
  z-index: 10;
}

.execute-buttons {
  display: flex;
  gap: 0.5rem;
}

.view-results-btn {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  background: white;
  color: #ff8c5a;
  border: 2px solid #ff8c5a;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 44px;
}

.view-results-btn:hover {
  background: #fff5f0;
  border-color: #ff6f3c;
  color: #ff6f3c;
}

.panel-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
}

.workflow-summary {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.summary-label {
  color: #6b7280;
}

.summary-value {
  font-weight: 500;
  color: #1f2937;
}

.execute-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #ff8c5a;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.execute-btn:hover:not(:disabled) {
  background: #ff6f3c;
}

.execute-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.result-item {
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 0.875rem;
}

.result-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.result-node {
  font-weight: 500;
  color: #1f2937;
}

.result-status {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 8px;
}

.result-status.status-success {
  background: #d1fae5;
  color: #065f46;
}

.result-status.status-error {
  background: #fee2e2;
  color: #991b1b;
}

.result-data pre {
  margin: 0;
  padding: 0.5rem;
  background: white;
  border-radius: 4px;
  font-size: 0.75rem;
  overflow-x: auto;
}

.result-error {
  color: #dc2626;
  font-size: 0.75rem;
}

/* Results Modal Styles */
.results-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.results-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
}

.modal-close-btn {
  padding: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.no-results {
  text-align: center;
  padding: 3rem;
  color: #9ca3af;
}

.results-timeline {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.result-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: white;
  border-bottom: 1px solid #e5e7eb;
}

.result-step {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: #3b82f6;
  color: white;
  border-radius: 50%;
  font-size: 0.875rem;
  font-weight: 600;
}

.step-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 0.95rem;
}

.result-badge {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.result-badge.badge-success {
  background: #d1fae5;
  color: #065f46;
}

.result-badge.badge-error {
  background: #fee2e2;
  color: #991b1b;
}

.result-card-body {
  padding: 1rem;
}

.result-error-detail {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
}

.error-icon {
  flex-shrink: 0;
  color: #dc2626;
}

.error-content {
  flex: 1;
}

.error-title {
  margin: 0 0 0.25rem 0;
  font-weight: 600;
  color: #991b1b;
  font-size: 0.875rem;
}

.error-message {
  margin: 0;
  color: #dc2626;
  font-size: 0.875rem;
  line-height: 1.5;
}

.result-data-detail {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}

.result-json {
  margin: 0;
  padding: 1rem;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  color: #1f2937;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

.result-empty {
  text-align: center;
  padding: 2rem;
  color: #9ca3af;
  font-size: 0.875rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.modal-btn {
  padding: 0.625rem 1.25rem;
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.modal-btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.modal-btn-secondary:hover {
  background: #e5e7eb;
}
</style>

/* Inactive Node Styles */
.inactive-notice {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: #fef3c7;
  border: 2px dashed #f59e0b;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  text-align: center;
}

.inactive-notice svg {
  color: #f59e0b;
  margin-bottom: 1rem;
}

.inactive-notice h4 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #92400e;
  margin: 0 0 0.5rem 0;
}

.inactive-notice p {
  font-size: 0.875rem;
  color: #78350f;
  margin: 0;
  max-width: 400px;
}

/* Inactive Node Button - Disabled Style */
.node-btn-inactive {
  position: relative;
  background: #f9fafb;
  border-color: #e5e7eb;
  color: #d1d5db;
  cursor: not-allowed;
  opacity: 0.6;
}

.node-btn-inactive svg {
  color: #e5e7eb;
}

.node-btn-inactive:hover {
  background: #f9fafb;
  border-color: #e5e7eb;
  transform: none;
  box-shadow: none;
}

/* Condition Node Styles */
.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.condition-item {
  display: grid;
  grid-template-columns: 1fr 120px 1fr 32px;
  gap: 0.5rem;
  align-items: center;
}

.condition-field-input,
.condition-value-input {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
}

.condition-operator-select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  background: white;
}

.condition-remove-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fee2e2;
  color: #dc2626;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.condition-remove-btn:hover:not(:disabled) {
  background: #fecaca;
}

.condition-remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-condition-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.add-condition-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

.add-condition-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Validation Node Styles */
.validation-rules-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.validation-rule-item {
  display: grid;
  grid-template-columns: 1fr 120px 1fr 32px;
  gap: 0.5rem;
  align-items: center;
}

.rule-field-input,
.rule-value-input {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
}

.rule-type-select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  background: white;
}

.add-validation-rule-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.add-validation-rule-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

.add-validation-rule-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Script Node Styles */
.script-file-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
}

.script-file-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f3f4f6;
}

.script-params-textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  resize: vertical;
}

.script-params-textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f3f4f6;
}

.config-hint {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.25rem;
  margin-bottom: 0;
}

/* Status Badge for Inactive */
.status-badge.status-inactive {
  background: #f3f4f6;
  color: #6b7280;
  border: 1px dashed #9ca3af;
}
