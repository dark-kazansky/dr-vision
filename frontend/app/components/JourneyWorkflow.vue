<template>
  <div class="journey-container">
    <div class="journey-content">
      <!-- Workflow Canvas -->
      <div class="workflow-canvas">
        <!-- Zoom Controls -->
        <div class="zoom-controls">
          <button class="zoom-btn" @click="zoomIn" title="Zoom In">
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </button>
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <button class="zoom-btn" @click="zoomOut" title="Zoom Out">
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
            </svg>
          </button>
          <button class="zoom-btn zoom-fit-btn" @click="zoomToFit" title="Fit All Nodes">
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>
        </div>
        
        <div class="canvas-area" 
             ref="canvasArea"
             :class="{ 'panning': isPanning }"
             @click="handleCanvasClick($event)"
             @mousedown="handleCanvasMouseDown"
             @mousemove="handleCanvasMouseMove"
             @mouseup="handleCanvasMouseUp"
             @mouseleave="handleCanvasMouseUp"
             @wheel="handleWheel"
             @contextmenu.prevent>
          <!-- Large canvas content area to ensure scrollable space -->
          <div class="canvas-content" :style="{ transform: `scale(${zoomLevel})`, transformOrigin: 'top left' }">
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
            <g v-for="node in nodes" :key="`connections-${node.id}-${node.x}-${node.y}`">
              <path
                v-for="(connection, connIndex) in node.connections || []"
                :key="`${node.id}-${connection.targetId || connection}-${connIndex}`"
                :d="getConnectionPath(node.id, typeof connection === 'string' ? connection : connection.targetId, typeof connection === 'object' ? connection.outputIndex : undefined)"
                :stroke="selectedConnection?.fromId === node.id && selectedConnection?.toId === (typeof connection === 'string' ? connection : connection.targetId) ? '#ff8c5a' : '#9ca3af'"
                :stroke-width="selectedConnection?.fromId === node.id && selectedConnection?.toId === (typeof connection === 'string' ? connection : connection.targetId) ? '3' : '2'"
                fill="none"
                class="connection-line"
                @click="handleConnectionClick(node.id, typeof connection === 'string' ? connection : connection.targetId, $event)"
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
               :style="{ top: `${node.y}px`, left: `${node.x}px` }"
               @click.stop>
            
            <!-- Input connection point (left side) -->
            <div 
              v-if="node.type !== 'upload'"
              class="connection-point input-point"
              :class="{ 
                'connecting': connectingFrom && connectingFrom.nodeId !== node.id,
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
              <span 
                v-if="editingNodeId !== node.id"
                class="node-title" 
                @dblclick="startRenaming(node.id)"
                :title="'Double-click to rename'"
              >
                {{ node.label }}
              </span>
              <input
                v-else
                ref="renameInput"
                :value="editingNodeLabel"
                @input="editingNodeLabel = ($event.target as HTMLInputElement).value"
                class="node-title-input"
                @blur="finishRenaming(node.id)"
                @keydown.enter="finishRenaming(node.id)"
                @keydown.esc="cancelRenaming(node.id)"
                @mousedown.stop
                @click.stop
              />
              <button class="node-remove" @click="removeNode(node.id)" :disabled="isProcessing">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div class="node-body" :style="node.type === 'condition' ? { minHeight: `${getConditionNodeBodyHeight(node)}px` } : {}">
              <div v-if="node.type === 'upload'" class="node-config">
                <input type="file" :ref="`fileInput-${node.id}`" @change="handleFileSelect($event, node.id)" multiple accept=".png,.jpg,.jpeg,.pdf,.txt,.md,.docx" style="display: none" />
                <button class="config-btn" @click="triggerFileInput(node.id)" :disabled="isProcessing">
                  {{ node.files?.length ? `${node.files.length} file(s)` : 'Select Files' }}
                </button>
              </div>
              <div v-else-if="node.type === 'condition'" class="node-config">
                <div class="condition-summary">
                  <span class="condition-count">{{ (node.config?.conditions || []).length }} Condition{{ (node.config?.conditions || []).length !== 1 ? 's' : '' }}</span>
                </div>
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
            
            <!-- Output connection points (right side) -->
            <!-- For condition nodes, show multiple outputs -->
            <template v-if="node.type === 'condition'">
              <div 
                v-for="(condition, index) in (node.config?.conditions || [])"
                :key="`output-${index}`"
                class="connection-point output-point"
                :class="{ 'connecting': connectingFrom?.nodeId === node.id && connectingFrom?.outputIndex === index }"
                :style="{ top: `${getConditionOutputPosition(node, index)}%` }"
                @mousedown="handleOutputMouseDown($event, node.id, index)"
                @click="handleOutputClick($event, node.id, index)"
                :title="`Output ${index + 1}: ${condition.operator} ${condition.value || condition.valueMin + '-' + condition.valueMax}`">
                <div class="connection-dot"></div>
                <span class="output-label">{{ index + 1 }}</span>
              </div>
              <!-- Else output (when no conditions match) -->
              <div 
                class="connection-point output-point"
                :class="{ 'connecting': connectingFrom?.nodeId === node.id && connectingFrom?.outputIndex === (node.config?.conditions || []).length }"
                :style="{ top: `${getConditionOutputPosition(node, (node.config?.conditions || []).length)}%` }"
                @mousedown="handleOutputMouseDown($event, node.id, (node.config?.conditions || []).length)"
                @click="handleOutputClick($event, node.id, (node.config?.conditions || []).length)"
                title="Output: Else (no match)">
                <div class="connection-dot"></div>
                <span class="output-label">Else</span>
              </div>
            </template>
            <!-- For other nodes, show single output -->
            <div 
              v-else
              class="connection-point output-point"
              :class="{ 'connecting': connectingFrom?.nodeId === node.id }"
              @mousedown="handleOutputMouseDown($event, node.id)"
              @click="handleOutputClick($event, node.id)"
              title="Output">
              <div class="connection-dot"></div>
            </div>
          </div>
          </div><!-- End canvas-content -->
        </div>
      </div>

      <!-- Control Panel -->
      <div class="control-panel">
        <!-- Workflow management toolbar -->
        <div class="panel-section workflow-mgmt-section">
          <div class="section-header">
            <h3>Workflow</h3>
            <div class="workflow-mgmt-actions">
              <button
                class="workflow-mgmt-btn"
                @click="handleSaveWorkflow"
                :disabled="nodes.length === 0 || isProcessing"
                title="Save current workflow"
              >
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                </svg>
                Save
              </button>
              <button
                class="workflow-mgmt-btn"
                @click="showLoadDialog = true"
                :disabled="isProcessing"
                title="Load saved workflow"
              >
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
                </svg>
                Load
              </button>
            </div>
          </div>
          <div v-if="currentWorkflowName" class="workflow-mgmt-current">
            <span class="workflow-mgmt-current-label">Editing:</span>
            <span class="workflow-mgmt-current-name">{{ currentWorkflowName }}</span>
          </div>
        </div>

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
            <button class="node-btn" @click="addNodeInViewport('upload')" :disabled="hasUploadNode || isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span>Upload</span>
            </button>
            <button class="node-btn" @click="addNodeInViewport('parse')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Parse</span>
            </button>
            <button class="node-btn" @click="addNodeInViewport('ocr')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span>OCR</span>
            </button>
            <button class="node-btn" @click="addNodeInViewport('classify')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              <span>Classify</span>
            </button>
            <button class="node-btn" @click="addNodeInViewport('extract')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Extract</span>
            </button>
            <button class="node-btn" @click="addNodeInViewport('split')" :disabled="isProcessing">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12M8 12h12m-12 5h12M3 7h.01M3 12h.01M3 17h.01" />
              </svg>
              <span>Split</span>
            </button>
            <button class="node-btn" @click="addNodeInViewport('condition')" :disabled="isProcessing">
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
          <h3 class="node-settings-title">NODE SETTINGS: {{ getSelectedNodeObject.label.toUpperCase() }}</h3>
          
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
          
          <!-- Condition Node Settings -->
          <div v-else-if="getSelectedNodeObject.type === 'condition'" class="node-config-content">
            <div class="config-group">
              <table class="conditions-table">
                <thead>
                  <tr>
                    <th class="order-cell"></th>
                    <th class="condition-header">Condition</th>
                    <th class="value-header">Value</th>
                    <th class="delete-cell"></th>
                  </tr>
                </thead>
                <tbody class="conditions-table-body">
                  <tr v-for="(condition, index) in getSelectedNodeObject.config?.conditions || []" :key="index" class="condition-table-row">
                    <td class="order-cell">
                      <span class="order-number">{{ index + 1 }}</span>
                    </td>
                    <td class="table-cell">
                      <select 
                        v-model="condition.operator" 
                        class="condition-operator-select-table"
                        :disabled="isProcessing">
                        <option value="equals">Equals</option>
                        <option value="not_equals">Not Equals</option>
                        <option value="greater_than">Greater Than</option>
                        <option value="less_than">Less Than</option>
                        <option value="contains">Contains</option>
                        <option value="between">Between</option>
                      </select>
                    </td>
                    <td class="table-cell">
                      <div v-if="condition.operator === 'between'" class="condition-between-inputs-table">
                        <input 
                          v-model="condition.valueMin" 
                          placeholder="Min"
                          class="condition-value-input-table"
                          :disabled="isProcessing"
                        />
                        <span class="between-separator-table">to</span>
                        <input 
                          v-model="condition.valueMax" 
                          placeholder="Max"
                          class="condition-value-input-table"
                          :disabled="isProcessing"
                        />
                      </div>
                      <input 
                        v-else
                        v-model="condition.value" 
                        placeholder="Enter value"
                        class="condition-value-input-table"
                        :disabled="isProcessing"
                      />
                    </td>
                    <td class="delete-cell">
                      <button class="delete-btn-x" @click="removeCondition(index)" :disabled="isProcessing || (getSelectedNodeObject.config?.conditions || []).length <= 1">
                        ×
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
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

        <!-- Add Condition Button Section (only visible for condition nodes) -->
        <div v-if="selectedNode && getSelectedNodeObject?.type === 'condition'" class="panel-section add-condition-section">
          <button class="add-condition-btn" @click="addCondition" :disabled="isProcessing">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Condition
          </button>
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

    <!-- Save Workflow Dialog -->
    <div v-if="showSaveDialog" class="results-modal-overlay" @click="showSaveDialog = false">
      <div class="results-modal save-modal" @click.stop>
        <div class="modal-header">
          <h2>Save Workflow</h2>
          <button class="modal-close" @click="showSaveDialog = false">×</button>
        </div>
        <div class="modal-body save-modal-body">
          <label class="save-modal-label">Name</label>
          <input
            v-model="saveDialogName"
            class="save-modal-input"
            placeholder="My document workflow"
            @keydown.enter="confirmSaveWorkflow"
            ref="saveNameInputRef"
          />
          <label class="save-modal-label">Description (optional)</label>
          <textarea
            v-model="saveDialogDescription"
            class="save-modal-textarea"
            rows="3"
            placeholder="What this workflow does, when to use it…"
          ></textarea>
        </div>
        <div class="modal-footer">
          <button class="modal-btn modal-btn-secondary" @click="showSaveDialog = false">Cancel</button>
          <button
            class="modal-btn modal-btn-primary"
            :disabled="!saveDialogName.trim()"
            @click="confirmSaveWorkflow"
          >
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- Load Workflow Dialog -->
    <div v-if="showLoadDialog" class="results-modal-overlay" @click="showLoadDialog = false">
      <div class="results-modal load-modal" @click.stop>
        <div class="modal-header">
          <h2>Load Workflow</h2>
          <button class="modal-close" @click="showLoadDialog = false">×</button>
        </div>
        <div class="modal-body load-modal-body">
          <div v-if="savedWorkflows.length === 0" class="load-empty">
            <p>No saved workflows yet.</p>
            <p class="load-empty-hint">Build a workflow and click Save to add one.</p>
          </div>
          <div
            v-for="wf in savedWorkflows"
            :key="wf.id"
            class="load-row"
            @click="confirmLoadWorkflow(wf.id)"
          >
            <div class="load-row-main">
              <div class="load-row-name">{{ wf.name }}</div>
              <div v-if="wf.description" class="load-row-desc">{{ wf.description }}</div>
              <div class="load-row-meta">
                {{ wf.nodes.length }} node<template v-if="wf.nodes.length !== 1">s</template>
                · saved {{ formatRelativeTime(wf.updatedAt) }}
              </div>
            </div>
            <button
              class="load-row-delete"
              @click.stop="confirmDeleteWorkflow(wf.id)"
              title="Delete saved workflow"
            >
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="modal-btn modal-btn-secondary" @click="showLoadDialog = false">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick, h } from 'vue'
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
  executeWorkflow,
  loadWorkflow
} = useJourney()

// Saved workflow store (localStorage-backed for now; backend swap is trivial)
const workflowStore = useWorkflowStore()
const showSaveDialog = ref(false)
const showLoadDialog = ref(false)
const saveDialogName = ref('')
const saveDialogDescription = ref('')
const saveNameInputRef = ref<HTMLInputElement | null>(null)
const currentWorkflowId = ref<string | null>(null)
const currentWorkflowName = ref<string>('')
const savedWorkflows = computed(() => workflowStore.list())

const handleSaveWorkflow = async () => {
  // Pre-fill the name when re-saving an existing one
  saveDialogName.value = currentWorkflowName.value || `Workflow ${new Date().toLocaleDateString()}`
  saveDialogDescription.value = ''
  showSaveDialog.value = true
  await nextTick()
  saveNameInputRef.value?.focus()
}

const confirmSaveWorkflow = () => {
  const name = saveDialogName.value.trim()
  if (!name) return
  if (currentWorkflowId.value) {
    // Update existing workflow
    workflowStore.update(currentWorkflowId.value, {
      name,
      description: saveDialogDescription.value.trim() || undefined,
      nodes: nodes.value,
    })
    currentWorkflowName.value = name
  } else {
    const wf = workflowStore.save(
      name,
      nodes.value,
      saveDialogDescription.value.trim() || undefined,
    )
    currentWorkflowId.value = wf.id
    currentWorkflowName.value = wf.name
  }
  showSaveDialog.value = false
}

const confirmLoadWorkflow = (id: string) => {
  const wf = workflowStore.get(id)
  if (!wf) return
  loadWorkflow(wf.nodes)
  currentWorkflowId.value = wf.id
  currentWorkflowName.value = wf.name
  showLoadDialog.value = false
}

const confirmDeleteWorkflow = (id: string) => {
  if (!confirm('Delete this saved workflow?')) return
  workflowStore.remove(id)
  if (currentWorkflowId.value === id) {
    currentWorkflowId.value = null
    currentWorkflowName.value = ''
  }
}

const formatRelativeTime = (ts: number): string => {
  const diff = Date.now() - ts
  if (diff < 60_000) return 'just now'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`
  return `${Math.floor(diff / 86_400_000)}d ago`
}

// Pass canvas ref to addNode for viewport-aware positioning
const addNodeInViewport = (type: WorkflowNode['type']) => {
  const canvas = canvasArea.value
  if (!canvas) {
    // Fallback if canvas not available
    addNode(type)
    return
  }
  
  // Calculate center of visible viewport
  const viewportCenterX = canvas.scrollLeft + canvas.clientWidth / 2
  const viewportCenterY = canvas.scrollTop + canvas.clientHeight / 2
  
  // Add node with viewport-aware positioning
  addNode(type, viewportCenterX, viewportCenterY)
}

const canvasArea = ref<HTMLElement | null>(null)
const draggedNode = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })
const connectingFrom = ref<{ nodeId: string; outputIndex?: number } | null>(null)
const selectedNode = ref<string | null>(null)
const isDraggingConnection = ref(false)
const dragConnectionEnd = ref({ x: 0, y: 0 })
const nearbyInputNode = ref<string | null>(null)
const generatingSchemaNodes = ref<Set<string>>(new Set())
const schemaJsonInput = ref('')
const jsonParseError = ref('')
const showResultsModal = ref(false)
const selectedConnection = ref<{ fromId: string; toId: string } | null>(null)
const isPanning = ref(false)
const hasPanned = ref(false)
const panStart = ref({ x: 0, y: 0 })
const zoomLevel = ref(1)
const editingNodeId = ref<string | null>(null)
const editingNodeLabel = ref('')
const renameInput = ref<HTMLInputElement | null>(null)

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
  const icons: Record<string, any> = {
    upload: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12' })
    ]),
    parse: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' })
    ]),
    ocr: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z' })
    ]),
    classify: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z' }),
      h('circle', { cx: '7', cy: '7', r: '0.5', fill: 'currentColor' })
    ]),
    extract: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M14 2v4a2 2 0 002 2h4' })
    ]),
    split: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('circle', { cx: '6', cy: '6', r: '3', 'stroke-width': '2' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8.12 8.12L12 12' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M20 4L8.12 15.88' }),
      h('circle', { cx: '6', cy: '18', r: '3', 'stroke-width': '2' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M14.8 14.8L20 20' })
    ]),
    condition: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z' })
    ]),
    validate: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' })
    ]),
    script: h('svg', { width: 20, height: 20, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4' })
    ])
  }
  
  return icons[type] || icons.parse
}

const handleExecuteWorkflow = async () => {
  if (!canExecute.value) return
  
  try {
    await executeWorkflow({
      workflowId: currentWorkflowId.value,
      workflowName: currentWorkflowName.value || 'Ad-hoc workflow',
    })
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
    currentWorkflowId.value = null
    currentWorkflowName.value = ''
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
    
    // Mark that we've actually panned (moved)
    if (Math.abs(deltaX - canvas.scrollLeft) > 2 || Math.abs(deltaY - canvas.scrollTop) > 2) {
      hasPanned.value = true
    }
    
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
    
    // Update dimensions cache for this node
    updateNodeDimensions(draggedNode.value)
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
      if (node.type === 'upload' || node.id === connectingFrom.value.nodeId) continue
      
      // Get cached dimensions or use defaults
      const nodeDims = nodeDimensionsCache.value.get(node.id) || { width: 220, height: 140 }
      
      // Calculate input point position (left side, middle)
      const inputX = node.x
      const inputY = node.y + (nodeDims.height / 2)
      
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
        const targetDims = nodeDimensionsCache.value.get(closestNode) || { width: 220, height: 140 }
        dragConnectionEnd.value = {
          x: targetNode.x,
          y: targetNode.y + (targetDims.height / 2) // Match the input point position
        }
      }
    }
  }
}

const handleCanvasMouseUp = () => {
  if (isPanning.value) {
    isPanning.value = false
    // Set flag to prevent click event
    if (hasPanned.value) {
      setTimeout(() => {
        hasPanned.value = false
      }, 10)
    }
    return
  }
  
  if (isDraggingConnection.value) {
    // If near an input node, create connection
    if (nearbyInputNode.value && connectingFrom.value) {
      const fromNode = nodes.value.find(n => n.id === connectingFrom.value.nodeId)
      const toNode = nodes.value.find(n => n.id === nearbyInputNode.value)
      
      if (fromNode && toNode && fromNode.id !== toNode.id) {
        if (!fromNode.connections) {
          fromNode.connections = []
        }
        
        // Check if connection already exists
        const existingConnection = fromNode.connections.find(conn => {
          const targetId = typeof conn === 'string' ? conn : conn.targetId
          const outputIdx = typeof conn === 'object' ? conn.outputIndex : undefined
          return targetId === toNode.id && outputIdx === connectingFrom.value!.outputIndex
        })
        
        if (!existingConnection) {
          // Add new connection with output index
          if (connectingFrom.value.outputIndex !== undefined) {
            fromNode.connections.push({ targetId: toNode.id, outputIndex: connectingFrom.value.outputIndex })
          } else {
            fromNode.connections.push({ targetId: toNode.id })
          }
          // Force dimension update after connection is made
          nextTick(() => {
            updateNodeDimensions()
          })
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
const handleOutputMouseDown = (event: MouseEvent, nodeId: string, outputIndex?: number) => {
  if (isProcessing.value) return
  
  connectingFrom.value = { nodeId, outputIndex }
  isDraggingConnection.value = true
  
  event.preventDefault()
  event.stopPropagation()
}

const handleInputMouseUp = (event: MouseEvent, nodeId: string) => {
  if (isProcessing.value || !connectingFrom.value || !isDraggingConnection.value) return
  
  const fromNode = nodes.value.find(n => n.id === connectingFrom.value!.nodeId)
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
  
  // Check if connection already exists
  const existingConnection = fromNode.connections.find(conn => {
    const targetId = typeof conn === 'string' ? conn : conn.targetId
    const outputIdx = typeof conn === 'object' ? conn.outputIndex : undefined
    return targetId === nodeId && outputIdx === connectingFrom.value!.outputIndex
  })
  
  if (!existingConnection) {
    // Add new connection with output index
    if (connectingFrom.value.outputIndex !== undefined) {
      fromNode.connections.push({ targetId: nodeId, outputIndex: connectingFrom.value.outputIndex })
    } else {
      fromNode.connections.push({ targetId: nodeId })
    }
  }
  
  connectingFrom.value = null
  isDraggingConnection.value = false
  
  event.preventDefault()
  event.stopPropagation()
}

const handleOutputClick = (event: MouseEvent, nodeId: string, outputIndex?: number) => {
  if (isProcessing.value || isDraggingConnection.value) return
  
  // Toggle connection mode
  if (connectingFrom.value?.nodeId === nodeId && connectingFrom.value?.outputIndex === outputIndex) {
    connectingFrom.value = null
  } else {
    connectingFrom.value = { nodeId, outputIndex }
  }
  
  event.preventDefault()
  event.stopPropagation()
}

const handleInputClick = (event: MouseEvent, nodeId: string) => {
  if (isProcessing.value || !connectingFrom.value || isDraggingConnection.value) return
  
  const fromNode = nodes.value.find(n => n.id === connectingFrom.value!.nodeId)
  const toNode = nodes.value.find(n => n.id === nodeId)
  
  if (!fromNode || !toNode || fromNode.id === toNode.id) {
    connectingFrom.value = null
    return
  }
  
  // Add connection
  if (!fromNode.connections) {
    fromNode.connections = []
  }
  
  // Check if connection already exists
  const existingConnection = fromNode.connections.find(conn => {
    const targetId = typeof conn === 'string' ? conn : conn.targetId
    const outputIdx = typeof conn === 'object' ? conn.outputIndex : undefined
    return targetId === nodeId && outputIdx === connectingFrom.value!.outputIndex
  })
  
  if (!existingConnection) {
    // Add new connection with output index
    if (connectingFrom.value.outputIndex !== undefined) {
      fromNode.connections.push({ targetId: nodeId, outputIndex: connectingFrom.value.outputIndex })
    } else {
      fromNode.connections.push({ targetId: nodeId })
    }
  }
  
  connectingFrom.value = null
  
  event.preventDefault()
  event.stopPropagation()
}

const isConnected = (fromId: string, toId: string): boolean => {
  const fromNode = nodes.value.find(n => n.id === fromId)
  if (!fromNode?.connections) return false
  return fromNode.connections.some(conn => {
    const targetId = typeof conn === 'string' ? conn : conn.targetId
    return targetId === toId
  })
}

const getDragConnectionPath = (): string => {
  if (!connectingFrom.value || !isDraggingConnection.value) return ''
  
  const fromNode = nodes.value.find(n => n.id === connectingFrom.value!.nodeId)
  if (!fromNode) return ''
  
  // Get cached dimensions or use defaults
  const fromDims = nodeDimensionsCache.value.get(connectingFrom.value.nodeId) || { width: 220, height: 140 }
  
  const fromX = fromNode.x + fromDims.width // Right edge of node
  
  // Calculate Y position based on output index for condition nodes
  let fromY: number
  if (fromNode.type === 'condition' && connectingFrom.value.outputIndex !== undefined) {
    const outputPosition = getConditionOutputPosition(fromNode, connectingFrom.value.outputIndex)
    fromY = fromNode.y + (fromDims.height * outputPosition / 100)
  } else {
    fromY = fromNode.y + (fromDims.height / 2) // Vertical center of node
  }
  
  const toX = dragConnectionEnd.value.x
  const toY = dragConnectionEnd.value.y
  
  const midX = (fromX + toX) / 2
  
  return `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`
}

// Cache for node dimensions to avoid repeated DOM queries
const nodeDimensionsCache = ref<Map<string, { width: number; height: number }>>(new Map())

// Update node dimensions cache with retry mechanism
const updateNodeDimensions = (nodeId?: string) => {
  const updateDims = () => {
    const allNodes = document.querySelectorAll('.workflow-node')
    let updated = 0
    
    allNodes.forEach((el) => {
      const htmlEl = el as HTMLElement
      const style = htmlEl.getAttribute('style') || ''
      // Extract position to match with node data
      const topMatch = style.match(/top:\s*(\d+(?:\.\d+)?)px/)
      const leftMatch = style.match(/left:\s*(\d+(?:\.\d+)?)px/)
      if (topMatch && leftMatch) {
        const top = parseFloat(topMatch[1])
        const left = parseFloat(leftMatch[1])
        const node = nodes.value.find(n => Math.abs(n.y - top) < 1 && Math.abs(n.x - left) < 1)
        if (node && (!nodeId || node.id === nodeId)) {
          const width = htmlEl.offsetWidth
          const height = htmlEl.offsetHeight
          // Only update if dimensions are valid (not 0)
          if (width > 0 && height > 0) {
            const cached = nodeDimensionsCache.value.get(node.id)
            // Update if different or not cached
            if (!cached || cached.width !== width || cached.height !== height) {
              nodeDimensionsCache.value.set(node.id, { width, height })
              updated++
            }
          }
        }
      }
    })
    
    return updated
  }
  
  // Update immediately
  nextTick(() => {
    updateDims()
    // Update again after a short delay to catch any late renders
    setTimeout(() => {
      updateDims()
    }, 50)
    // One more update after a longer delay for complex nodes
    setTimeout(() => {
      updateDims()
    }, 200)
  })
}

// Watch nodes for changes and update dimensions
watch(() => nodes.value.length, () => {
  updateNodeDimensions()
}, { immediate: true })

// Watch for node position changes (for dragging)
watch(() => nodes.value.map(n => `${n.id}-${n.x}-${n.y}`).join(','), () => {
  updateNodeDimensions()
})

// Watch for node selection changes (config panels might change height)
watch(selectedNode, () => {
  updateNodeDimensions()
})

// Deep watch for node config changes that might affect height
watch(() => nodes.value.map(n => JSON.stringify(n.config)).join(','), () => {
  updateNodeDimensions()
})

// Watch zoom level changes
watch(zoomLevel, () => {
  nextTick(() => {
    updateNodeDimensions()
  })
})

const getConnectionPath = (fromId: string, toId: string, outputIndex?: number): string => {
  const fromNode = nodes.value.find(n => n.id === fromId)
  const toNode = nodes.value.find(n => n.id === toId)
  
  if (!fromNode || !toNode) return ''
  
  // Get cached dimensions or use defaults
  const fromDims = nodeDimensionsCache.value.get(fromId) || { width: 220, height: 140 }
  const toDims = nodeDimensionsCache.value.get(toId) || { width: 220, height: 140 }
  
  // Connection points
  const fromX = fromNode.x + fromDims.width // Right edge of from node
  
  // Calculate Y position based on output index for condition nodes
  let fromY: number
  if (fromNode.type === 'condition' && outputIndex !== undefined) {
    const outputPosition = getConditionOutputPosition(fromNode, outputIndex)
    fromY = fromNode.y + (fromDims.height * outputPosition / 100)
  } else {
    fromY = fromNode.y + (fromDims.height / 2) // Vertical center of from node
  }
  
  const toX = toNode.x // Left edge of to node
  const toY = toNode.y + (toDims.height / 2) // Vertical center of to node
  
  const midX = (fromX + toX) / 2
  
  return `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`
}

// Get selected node object
const getSelectedNodeObject = computed(() => {
  if (!selectedNode.value) return null
  return nodes.value.find(n => n.id === selectedNode.value) || null
})

// Check if selected node is generating schema
const isGeneratingSchema = computed(() => {
  if (!selectedNode.value) return false
  return generatingSchemaNodes.value.has(selectedNode.value)
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
    node.config = { conditions: [] }
  }
  if (!node.config.conditions) {
    node.config.conditions = []
  }
  
  node.config.conditions.push({ operator: 'equals', value: '', valueMin: '', valueMax: '' })
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
  
  // Check if this node is already generating
  if (generatingSchemaNodes.value.has(node.id)) return
  
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
  generatingSchemaNodes.value.add(node.id)
  
  try {
    const config = useRuntimeConfig()
    const apiBaseUrl = config.public.apiBaseUrl as string
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('tier', node.tier)
    formData.append('prompt', node.config.schemaPrompt)
    
    const response = await $fetch<any>(`${apiBaseUrl}/generate-schema`, {
      method: 'POST',
      body: formData
    })
    
    // Update node config with generated schema
    // Backend returns { success: true, schema: [...] }
    if (response.schema && Array.isArray(response.schema)) {
      if (!node.config.schema) {
        node.config.schema = { fields: [] }
      }
      node.config.schema.fields = response.schema
    }
  } catch (error: any) {
    console.error('Schema generation failed:', error)
    alert(`Schema generation failed: ${error.message || 'Unknown error'}`)
  } finally {
    generatingSchemaNodes.value.delete(node.id)
  }
}

// Generate schemas for all extract nodes in parallel
const generateAllSchemas = async () => {
  // Find all extract nodes with prompts
  const extractNodes = nodes.value.filter(n => 
    n.type === 'extract' && 
    n.config?.schemaPrompt && 
    n.config.schemaPrompt.trim() !== '' &&
    !generatingSchemaNodes.value.has(n.id)
  )
  
  if (extractNodes.length === 0) {
    alert('No extract nodes with prompts found')
    return
  }
  
  // Find upload node to get the file
  const uploadNode = nodes.value.find(n => n.type === 'upload')
  if (!uploadNode || !uploadNode.files || uploadNode.files.length === 0) {
    alert('Please upload a file first')
    return
  }
  
  const file = uploadNode.files[0]
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  
  // Generate schemas in parallel
  const promises = extractNodes.map(async (node) => {
    generatingSchemaNodes.value.add(node.id)
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('tier', node.tier)
      formData.append('prompt', node.config.schemaPrompt)
      
      const response = await $fetch<any>(`${apiBaseUrl}/generate-schema`, {
        method: 'POST',
        body: formData
      })
      
      // Update node config with generated schema
      // Backend returns { success: true, schema: [...] }
      if (response.schema && Array.isArray(response.schema)) {
        if (!node.config.schema) {
          node.config.schema = { fields: [] }
        }
        node.config.schema.fields = response.schema
      }
      
      return { nodeId: node.id, success: true }
    } catch (error: any) {
      console.error(`Schema generation failed for node ${node.id}:`, error)
      return { nodeId: node.id, success: false, error: error.message }
    } finally {
      generatingSchemaNodes.value.delete(node.id)
    }
  })
  
  const results = await Promise.all(promises)
  const successCount = results.filter(r => r.success).length
  const failCount = results.filter(r => !r.success).length
  
  if (failCount > 0) {
    alert(`Schema generation completed: ${successCount} succeeded, ${failCount} failed`)
  } else {
    alert(`All ${successCount} schemas generated successfully!`)
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
  // Check if user is typing in an input field
  const target = event.target as HTMLElement
  const isInputField = target.tagName === 'INPUT' || 
                       target.tagName === 'TEXTAREA' || 
                       target.tagName === 'SELECT' ||
                       target.isContentEditable
  
  // Don't handle Delete/Backspace when typing in input fields
  if ((event.key === 'Delete' || event.key === 'Backspace') && !isInputField) {
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
  // No longer needed for panning
}

// Handle canvas mouse down for panning
const handleCanvasMouseDown = (event: MouseEvent) => {
  // If currently editing a node name, finish the rename first
  if (editingNodeId.value) {
    finishRenaming(editingNodeId.value)
    // Don't return - allow the rest of the function to execute
  }
  
  const canvas = canvasArea.value
  if (!canvas) return
  
  // Check if clicking on elements that should not trigger panning
  const target = event.target as HTMLElement
  const isInteractiveElement = 
    target.tagName === 'BUTTON' ||
    target.tagName === 'INPUT' ||
    target.tagName === 'SELECT' ||
    target.tagName === 'TEXTAREA' ||
    target.closest('button') ||
    target.closest('input') ||
    target.closest('select') ||
    target.closest('textarea') ||
    target.classList.contains('connection-point') ||
    target.closest('.connection-point') ||
    target.classList.contains('node-header') ||
    target.closest('.node-header')
  
  // Start panning with left click (except on interactive elements and node headers) or middle mouse button
  if ((!isInteractiveElement && event.button === 0) || event.button === 1) {
    isPanning.value = true
    panStart.value = {
      x: event.clientX + canvas.scrollLeft,
      y: event.clientY + canvas.scrollTop
    }
    event.preventDefault()
    event.stopPropagation()
  }
}

// Delete a connection
const deleteConnection = (fromId: string, toId: string) => {
  const fromNode = nodes.value.find(n => n.id === fromId)
  if (fromNode && fromNode.connections) {
    fromNode.connections = fromNode.connections.filter(conn => {
      const targetId = typeof conn === 'string' ? conn : conn.targetId
      return targetId !== toId
    })
  }
  selectedConnection.value = null
}

// Deselect connection when clicking canvas
const handleCanvasClick = (event: MouseEvent) => {
  // Don't handle click if we just finished panning
  if (hasPanned.value) {
    return
  }
  
  // If currently editing a node name, finish the rename and save
  if (editingNodeId.value) {
    finishRenaming(editingNodeId.value)
    // Don't deselect immediately - finishRenaming will handle it
    return
  }
  
  // Deselect connection and node when clicking on canvas
  selectedConnection.value = null
  selectedNode.value = null
}

// Setup keyboard listener and center canvas
// Calculate output position for condition nodes
const getConditionOutputPosition = (node: any, index: number) => {
  const conditions = node.config?.conditions || []
  const totalOutputs = conditions.length + 1 // +1 for else
  
  // Add padding to avoid overlap with header and status
  const topPadding = 15 // percentage from top to avoid header overlap
  const bottomPadding = 15 // percentage from bottom to avoid status overlap
  const usableSpace = 100 - topPadding - bottomPadding
  
  const spacing = usableSpace / (totalOutputs + 1)
  return topPadding + spacing * (index + 1)
}

// Calculate minimum height for condition node body to accommodate output dots
const getConditionNodeBodyHeight = (node: any) => {
  const conditions = node.config?.conditions || []
  const totalOutputs = conditions.length + 1 // +1 for else
  // Base height + additional height per output (to ensure proper spacing)
  const baseHeight = 60 // increased base to account for header and status
  const heightPerOutput = 35 // spacing between each output dot
  return Math.max(baseHeight, totalOutputs * heightPerOutput + 40) // +40 for top/bottom padding
}

// Node renaming functions
const startRenaming = (nodeId: string) => {
  // If already editing another node, finish that first with the current editingNodeLabel value
  if (editingNodeId.value && editingNodeId.value !== nodeId) {
    const currentEditingNode = nodes.value.find(n => n.id === editingNodeId.value)
    if (currentEditingNode) {
      const newLabel = editingNodeLabel.value.trim()
      if (newLabel && newLabel !== currentEditingNode.label) {
        currentEditingNode.label = newLabel
      }
    }
  }
  
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return
  
  // Set the editing state with the NEW node's label
  editingNodeId.value = nodeId
  editingNodeLabel.value = node.label
  
  // Focus the input after it's rendered
  nextTick(() => {
    const input = document.querySelector('.node-title-input') as HTMLInputElement
    if (input) {
      input.focus()
      input.select()
    }
  })
}

const finishRenaming = (nodeId: string) => {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return
  
  // Trim and validate the new label
  const newLabel = editingNodeLabel.value.trim()
  if (newLabel && newLabel !== node.label) {
    node.label = newLabel
  }
  
  // Clear editing state
  editingNodeId.value = null
  editingNodeLabel.value = ''
  
  // Deselect the node
  selectedNode.value = null
}

const cancelRenaming = (nodeId: string) => {
  // Just clear the editing state without saving
  editingNodeId.value = null
  editingNodeLabel.value = ''
}

// Zoom functions
const zoomIn = () => {
  zoomLevel.value = Math.min(zoomLevel.value + 0.1, 2) // Max 200%
  updateNodeDimensions()
}

const zoomOut = () => {
  zoomLevel.value = Math.max(zoomLevel.value - 0.1, 0.5) // Min 50%
  updateNodeDimensions()
}

const zoomToFit = () => {
  if (nodes.value.length === 0) return
  
  const canvas = canvasArea.value
  if (!canvas) return
  
  // Calculate bounding box of all nodes
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  
  nodes.value.forEach(node => {
    const dims = nodeDimensionsCache.value.get(node.id) || { width: 240, height: 140 }
    minX = Math.min(minX, node.x)
    minY = Math.min(minY, node.y)
    maxX = Math.max(maxX, node.x + dims.width)
    maxY = Math.max(maxY, node.y + dims.height)
  })
  
  // Add padding
  const padding = 50
  minX -= padding
  minY -= padding
  maxX += padding
  maxY += padding
  
  // Calculate required zoom level
  const contentWidth = maxX - minX
  const contentHeight = maxY - minY
  const canvasWidth = canvas.clientWidth
  const canvasHeight = canvas.clientHeight
  
  const zoomX = canvasWidth / contentWidth
  const zoomY = canvasHeight / contentHeight
  const newZoom = Math.min(zoomX, zoomY, 1) // Don't zoom in beyond 100%
  
  zoomLevel.value = Math.max(newZoom, 0.5) // Min 50%
  
  // Center the content
  nextTick(() => {
    const scaledMinX = minX * zoomLevel.value
    const scaledMinY = minY * zoomLevel.value
    const scaledWidth = contentWidth * zoomLevel.value
    const scaledHeight = contentHeight * zoomLevel.value
    
    canvas.scrollLeft = scaledMinX - (canvasWidth - scaledWidth) / 2
    canvas.scrollTop = scaledMinY - (canvasHeight - scaledHeight) / 2
    
    updateNodeDimensions()
  })
}

const handleWheel = (event: WheelEvent) => {
  // Ctrl/Cmd + Wheel for zoom
  if (event.ctrlKey || event.metaKey) {
    event.preventDefault()
    const delta = -event.deltaY / 1000
    zoomLevel.value = Math.max(0.5, Math.min(2, zoomLevel.value + delta))
    updateNodeDimensions()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)
  
  // Center the canvas scroll position
  const canvas = canvasArea.value
  if (canvas) {
    // Use nextTick to ensure DOM is fully rendered
    nextTick(() => {
      // Center the scroll position (canvas-content is 200% of viewport)
      // So we scroll to 50% to center it
      canvas.scrollLeft = (canvas.scrollWidth - canvas.clientWidth) / 2
      canvas.scrollTop = (canvas.scrollHeight - canvas.clientHeight) / 2
      
      // Initial dimension update
      updateNodeDimensions()
    })
    
    // Setup MutationObserver to watch for DOM changes that affect node dimensions
    const observer = new MutationObserver(() => {
      updateNodeDimensions()
    })
    
    observer.observe(canvas, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['style', 'class']
    })
    
    // Store observer for cleanup
    ;(canvas as any)._dimensionObserver = observer
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
  
  // Cleanup MutationObserver
  const canvas = canvasArea.value
  if (canvas && (canvas as any)._dimensionObserver) {
    ;(canvas as any)._dimensionObserver.disconnect()
  }
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
  background: var(--color-cream);
  border-right: 1px solid var(--color-sand);
  overflow: hidden;
  position: relative;
}

/* Zoom Controls */
.zoom-controls {
  position: absolute;
  bottom: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-cream);
  border: 1px solid var(--color-sand);
  border-radius: 12px;
  padding: 8px 12px;
  z-index: 1000;
  pointer-events: auto;
}

.zoom-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-cream);
  border: 1px solid var(--color-sand);
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.zoom-btn:hover {
  background: var(--bg-tertiary);
  border-color: var(--color-sand-mid);
  color: var(--text-primary);
}

.zoom-btn:active {
  transform: scale(0.95);
}

.zoom-fit-btn {
  border-left: 1px solid var(--color-sand);
  margin-left: 4px;
  padding-left: 4px;
}

.zoom-level {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 48px;
  text-align: center;
}

.canvas-header {
  padding: 1.5rem 1.5rem 1rem 1.5rem;
  background: var(--color-cream);
  border-bottom: 1px solid var(--color-sand);
}

.canvas-title h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.canvas-title p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.canvas-area {
  flex: 1;
  position: relative;
  overflow: auto;
  background: #fafafa;
  min-height: 0;
  cursor: default;
}

.canvas-content {
  position: relative;
  min-width: 200%;
  min-height: 200%;
  padding: 2rem;
}

/* Show grabbing cursor when actively panning */
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
  color: var(--text-tertiary);
}

.canvas-empty svg {
  margin-bottom: 1rem;
}

.workflow-node {
  position: absolute;
  min-width: 200px;
  max-width: 280px;
  width: auto;
  background: var(--color-cream);
  border: 2px solid var(--color-sand);
  border-radius: 16px;
  transition: border-color 0.2s ease, transform 0.2s ease;
  z-index: 2;
  overflow: hidden;
  will-change: transform;
}

.workflow-node:hover:not(.node-dragging) {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3);
  transform: translateY(-2px);
}

.workflow-node.node-selected {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3), 0 10px 15px -3px rgba(0, 0, 0, 0.4);
  transform: translateY(-2px);
}

.workflow-node.node-dragging {
  cursor: grabbing;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
  z-index: 10;
  transition: none;
}

.workflow-node.node-active {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3), 0 10px 15px -3px rgba(0, 0, 0, 0.4);
  animation: pulse-node 2s ease-in-out infinite;
}

@keyframes pulse-node {
  0%, 100% {
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3), 0 10px 15px -3px rgba(0, 0, 0, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(59, 130, 246, 0.2), 0 10px 15px -3px rgba(0, 0, 0, 0.4);
  }
}

.workflow-node.node-complete {
  border-color: #10b981;
}

.workflow-node.node-error {
  border-color: #ef4444;
}

.workflow-node.node-inactive {
  opacity: 0.5;
  border-color: #475569;
  border-style: dashed;
  filter: grayscale(0.5);
}

/* Node type specific icon colors */
.node-upload .node-icon {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
}

.node-parse .node-icon {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}

.node-ocr .node-icon {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
}

.node-classify .node-icon {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.node-extract .node-icon {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.node-split .node-icon {
  background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
}

.node-condition .node-icon {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
}

.node-validate .node-icon {
  background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
}

.node-script .node-icon {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  background: transparent;
  border-bottom: none;
  border-radius: 16px 16px 0 0;
  cursor: grab;
  user-select: none;
}

.node-header:active {
  cursor: grabbing;
}

.node-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.node-icon svg {
  color: white;
  width: 16px;
  height: 16px;
  stroke: white;
  fill: none;
}

.node-title {
  flex: 1;
  font-weight: 600;
  color: #1e293b;
  font-size: 0.8rem;
  letter-spacing: 0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  cursor: text;
  user-select: none;
}

.node-title:hover {
  color: #0f172a;
}

.node-title-input {
  flex: 1;
  font-weight: 600;
  color: #1e293b;
  font-size: 0.8rem;
  letter-spacing: 0.01em;
  min-width: 0;
  padding: 2px 6px;
  border: 2px solid #3b82f6;
  border-radius: 4px;
  background: var(--color-cream);
  outline: none;
  font-family: inherit;
}

.node-title-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.node-remove {
  padding: 0.25rem;
  background: rgba(0, 0, 0, 0.05);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.node-remove:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.node-body {
  padding: 0 0.75rem 0.625rem 0.75rem;
  display: flex;
  align-items: center;
  min-height: 36px;
}

.node-config {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  padding-right: 30px; /* Space for output dots */
}

.config-btn, .config-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-sand);
  border-radius: 8px;
  font-size: 0.8rem;
  background: var(--bg-secondary);
  color: var(--text-primary);
  transition: all 0.2s;
}

.config-btn {
  cursor: pointer;
}

.config-btn:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.config-select {
  cursor: pointer;
}

.config-select:hover:not(:disabled) {
  border-color: #cbd5e1;
}

.condition-summary {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.625rem;
  background: var(--bg-secondary);
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  text-align: left;
  width: fit-content;
  margin: 0;
}

.condition-count {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.node-status {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid var(--color-sand);
}

.status-badge {
  display: inline-block;
  padding: 0.2rem 0.625rem;
  border-radius: 12px;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.status-pending {
  background: #f1f5f9;
  color: var(--text-secondary);
}

.status-processing {
  background: #dbeafe;
  color: #2563eb;
}

.status-completed {
  background: #d1fae5;
  color: #059669;
}

.status-error {
  background: #fee2e2;
  color: #dc2626;
}

.status-inactive {
  background: #f1f5f9;
  color: #94a3b8;
}

.connection-point {
  position: absolute;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 3;
  transition: all 0.2s;
}

.connection-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-secondary);
  border: 2px solid var(--color-cream);
  transition: all 0.2s;
}

.input-point .connection-dot {
  background: #f97316;
}

.output-point .connection-dot {
  background: #3b82f6;
}

.connection-point:hover .connection-dot {
  transform: scale(1.3);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}

.connection-point.connecting .connection-dot {
  animation: pulse-connection 1s ease-in-out infinite;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.3);
}

.connection-point.nearby .connection-dot {
  transform: scale(1.4);
  box-shadow: 0 0 0 6px rgba(59, 130, 246, 0.4);
}

@keyframes pulse-connection {
  0%, 100% { 
    transform: scale(1);
  }
  50% { 
    transform: scale(1.2);
  }
}

.input-point {
  left: -10px;
  top: 50%;
  transform: translateY(-50%);
}

.output-point {
  right: -10px;
  top: 50%;
  transform: translateY(-50%);
}

.output-label {
  position: absolute;
  right: 100%;
  margin-right: 8px;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  pointer-events: none;
  background: var(--color-cream);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--color-sand);
}

.node-connector {
  display: none;
}

.control-panel {
  width: 360px;
  background: var(--color-cream);
  border-left: 1px solid var(--color-sand);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-section {
  padding: 0.75rem;
  border-bottom: 1px solid var(--color-sand);
  flex-shrink: 0;
}

.panel-section:last-child {
  border-bottom: none;
}

.add-nodes-section {
  background: var(--color-cream);
}

.add-nodes-section h3 {
  margin: 0 0 0.5rem 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.node-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.node-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem;
  background: var(--color-cream);
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 500;
}

.node-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: #3b82f6;
  color: #3b82f6;
  transform: translateY(-1px);
}

.node-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.node-btn svg {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
}

/* Section Header with Reset Button */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
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
  background: var(--color-cream);
  color: #ef4444;
  border: 1px solid var(--color-sand);
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
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
  padding: 0.375rem 0.75rem 0;
  background: var(--color-cream);
  position: sticky;
  top: 0;
  z-index: 1;
}

.node-settings-title {
  margin: 0 0 1rem 0 !important;
  font-size: 0.75rem !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  letter-spacing: 0.05em !important;
}

.node-config-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 0 0.75rem 0.75rem;
}

.config-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.config-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
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
  background: var(--color-cream);
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
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
  border: 1px solid var(--color-sand);
  background-color: var(--bg-secondary);
  padding: 0.075rem;
  width: fit-content;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.3rem;
  background-color: transparent;
  color: var(--text-secondary);
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.15rem;
}

.view-toggle-btn:hover:not(:disabled) {
  background-color: var(--bg-tertiary);
  color: #4b5563;
}

.view-toggle-btn.active {
  background-color: var(--color-cream);
  color: var(--text-primary);
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
  background: var(--bg-secondary);
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
  background: var(--bg-secondary);
  border: 1px solid var(--color-sand);
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
  color: var(--text-secondary);
  text-transform: uppercase;
}

.clear-schema-btn {
  padding: 0.25rem 0.5rem;
  background: var(--color-cream);
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
  background: var(--color-cream);
  border-radius: 3px;
  font-size: 0.7rem;
}

.field-name-preview {
  font-weight: 600;
  color: var(--text-primary);
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
  color: var(--text-secondary);
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
  background: var(--color-cream);
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
  font-weight: 500;
  margin-top: 0.5rem;
}

.apply-json-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
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
  background: var(--color-cream);
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
  background: var(--color-cream);
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
  color: var(--text-tertiary);
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
.add-category-btn,
.add-condition-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--color-cream);
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
}

.add-rule-btn:hover:not(:disabled),
.add-field-btn:hover:not(:disabled),
.add-category-btn:hover:not(:disabled),
.add-condition-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: #3b82f6;
  color: #3b82f6;
}

.no-config {
  padding: 1rem;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-style: italic;
}

.files-section h3 {
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
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
  background: var(--bg-tertiary);
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.upload-node-name {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.upload-node-count {
  font-size: 0.75rem;
  color: var(--text-secondary);
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
  background: var(--color-cream);
  border: 1px solid var(--color-sand);
  border-radius: 4px;
  font-size: 0.75rem;
  transition: all 0.2s;
}

.file-item-small:hover {
  background: var(--bg-secondary);
  border-color: #d1d5db;
}

.file-icon {
  flex-shrink: 0;
  color: var(--text-secondary);
}

.file-name {
  flex: 1;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.file-size {
  flex-shrink: 0;
  color: var(--text-tertiary);
  font-size: 0.7rem;
}

.file-remove-btn {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--text-tertiary);
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
  color: var(--text-tertiary);
  font-size: 0.75rem;
  font-style: italic;
}

.results-section-panel {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.add-condition-section {
  background: var(--color-cream);
  padding: 1rem 0.75rem;
  border-top: none;
}

.node-settings-section:has(.node-config-content .conditions-table) {
  border-bottom: none;
}

.add-condition-section .add-condition-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem;
  background: var(--color-cream);
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
}

.add-condition-section .add-condition-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: #3b82f6;
  color: #3b82f6;
}

.add-condition-section .add-condition-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.workflow-summary-section {
  margin-top: auto;
  background: var(--color-cream);
  border-top: 1px solid var(--color-sand);
}

.execute-section {
  position: sticky;
  bottom: 0;
  background: var(--color-cream);
  border-top: 1px solid var(--color-sand);
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
  background: var(--color-cream);
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
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.workflow-summary {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.summary-label {
  color: var(--text-secondary);
}

.summary-value {
  font-weight: 500;
  color: var(--text-primary);
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
  background: var(--bg-secondary);
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
  color: var(--text-primary);
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
  background: var(--color-cream);
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
  background: var(--color-cream);
  border-radius: 12px;
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
  border-bottom: 1px solid var(--color-sand);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-close-btn {
  padding: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.no-results {
  text-align: center;
  padding: 3rem;
  color: var(--text-tertiary);
}

.results-timeline {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-card {
  background: var(--bg-secondary);
  border: 1px solid var(--color-sand);
  border-radius: 8px;
  overflow: hidden;
}

.result-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--color-cream);
  border-bottom: 1px solid var(--color-sand);
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
  color: var(--text-primary);
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
  background: var(--color-cream);
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  overflow: hidden;
}

.result-json {
  margin: 0;
  padding: 1rem;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  color: var(--text-primary);
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

.result-empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-tertiary);
  font-size: 0.875rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid var(--color-sand);
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
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.modal-btn-secondary:hover {
  background: var(--bg-tertiary);
}

/* ===== Workflow Management (Save / Load) ===== */
.workflow-mgmt-section {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
  margin-bottom: 12px;
}

.workflow-mgmt-actions {
  display: flex;
  gap: 6px;
}

.workflow-mgmt-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--color-cream);
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.15s;
}
.workflow-mgmt-btn:hover:not(:disabled) {
  background: #fff4ec;
  border-color: #ff8c5a;
  color: #c2410c;
}
.workflow-mgmt-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.workflow-mgmt-current {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  padding: 6px 10px;
  background: #fff4ec;
  border-radius: 6px;
  font-size: 11px;
}
.workflow-mgmt-current-label {
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.workflow-mgmt-current-name {
  color: #c2410c;
  font-weight: 600;
  word-break: break-all;
}

/* Save / Load dialog content */
.save-modal,
.load-modal {
  max-width: 480px;
}

.save-modal-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 20px;
}
.save-modal-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  margin-top: 6px;
}
.save-modal-input,
.save-modal-textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  font-size: 13px;
  background: var(--color-cream);
  color: var(--text-primary);
  font-family: inherit;
}
.save-modal-textarea {
  resize: vertical;
  min-height: 60px;
}
.save-modal-input:focus,
.save-modal-textarea:focus {
  outline: none;
  border-color: #ff8c5a;
  box-shadow: 0 0 0 3px rgba(255, 140, 90, 0.15);
}

.load-modal-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  max-height: 50vh;
  overflow: auto;
}
.load-empty {
  text-align: center;
  padding: 32px 12px;
  color: var(--text-secondary);
}
.load-empty-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 6px;
}
.load-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--color-sand);
  border-radius: 8px;
  background: var(--color-cream);
  cursor: pointer;
  transition: all 0.15s;
}
.load-row:hover {
  border-color: #ff8c5a;
  background: #fff4ec;
}
.load-row-main { flex: 1; min-width: 0; }
.load-row-name { font-weight: 600; color: var(--text-primary); }
.load-row-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
  word-break: break-word;
}
.load-row-meta {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 6px;
  text-transform: lowercase;
}
.load-row-delete {
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}
.load-row-delete:hover {
  color: #b91c1c;
  background: #fef2f2;
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
  background: var(--bg-secondary);
  border-color: var(--color-sand);
  color: #d1d5db;
  cursor: not-allowed;
  opacity: 0.6;
}

.node-btn-inactive svg {
  color: var(--color-sand);
}

.node-btn-inactive:hover {
  background: var(--bg-secondary);
  border-color: var(--color-sand);
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

/* Table layout for conditions */
.conditions-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 0.75rem;
  margin: 0;
  background: var(--color-cream);
  border: none;
}

.conditions-table thead th {
  background: var(--color-cream);
  border-bottom: 1px solid var(--color-sand);
  padding: 0.75rem 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  text-align: left;
}

.condition-header,
.value-header {
  font-weight: 600 !important;
  color: var(--text-primary) !important;
}

.conditions-table tbody tr {
  transition: background 0.15s;
}

.conditions-table tbody tr:last-child {
  border-bottom: none;
}

.conditions-table tbody tr:hover {
  background: #fafbfc;
}

.conditions-table td {
  padding: 0.75rem 0.5rem;
  vertical-align: middle;
}

.order-cell {
  text-align: center;
  width: 40px;
  padding: 0.75rem 0.5rem !important;
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.order-number {
  display: inline-block;
  font-weight: 600;
  color: var(--text-primary);
}

.delete-cell {
  text-align: center;
  width: 40px;
  padding: 0.75rem 0.5rem !important;
}

.delete-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid #e74c3c;
  background: #fff;
  color: #e74c3c;
  border-radius: 4px;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  transition: all 0.2s;
}

.delete-btn:hover:not(:disabled) {
  background: #ffecec;
}

.delete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.delete-btn-x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
  transition: all 0.2s;
  padding: 0;
}

.delete-btn-x:hover:not(:disabled) {
  color: #ef4444;
}

.delete-btn-x:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.table-cell {
  display: flex;
  align-items: center;
  justify-content: center;
}

.table-cell-with-action {
  position: relative;
  padding-right: 3rem;
}

.condition-operator-select-table {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  font-size: 0.875rem;
  background: var(--color-cream);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.condition-operator-select-table:hover:not(:disabled) {
  border-color: #d1d5db;
  background: #fafbfc;
}

.condition-operator-select-table:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.condition-value-input-table {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  font-size: 0.875rem;
  background: var(--color-cream);
  color: var(--text-primary);
  transition: all 0.2s;
}

.condition-value-input-table:hover:not(:disabled) {
  border-color: #d1d5db;
}

.condition-value-input-table:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.condition-between-inputs-table {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
}

.between-separator-table {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 500;
  flex-shrink: 0;
  padding: 0 0.25rem;
}

.add-condition-section {
  padding: 2rem 0.75rem 1rem;
  background: var(--color-cream);
  display: flex;
  justify-content: center;
}

/* Grid layout for condition items with 2 main columns */
.condition-item-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1rem;
  padding: 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--color-sand);
  border-radius: 8px;
  margin-bottom: 0.75rem;
}

.condition-type-column {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-right: 0.75rem;
  border-right: 2px solid var(--color-sand);
  min-width: 140px;
}

.condition-operator-dropdown {
  padding: 0.625rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  background: var(--color-cream);
  color: var(--text-primary);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.condition-operator-dropdown:hover:not(:disabled) {
  border-color: #3b82f6;
}

.condition-operator-dropdown:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.condition-operator-dropdown:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.condition-value-column {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: relative;
}

.condition-field-input-grid,
.condition-value-input-grid {
  padding: 0.625rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  background: var(--color-cream);
  width: 100%;
}

.condition-between-inputs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.between-separator {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
  flex-shrink: 0;
}

.condition-remove-btn-grid {
  position: absolute;
  top: 0;
  right: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fee2e2;
  color: #dc2626;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.condition-remove-btn-grid:hover:not(:disabled) {
  background: #fecaca;
}

.condition-remove-btn-grid:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Old 2-column layout for condition items */
.condition-item-2col {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--color-sand);
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.condition-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.condition-row.condition-between {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.condition-field-input-full,
.condition-value-input-full,
.condition-operator-select-full {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  background: var(--color-cream);
}

.condition-value-input-half {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  background: var(--color-cream);
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
  background: var(--color-cream);
}

.condition-remove-btn {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
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
  background: var(--color-cream);
}

.add-validation-rule-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.add-validation-rule-btn:hover:not(:disabled) {
  background: var(--bg-tertiary);
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
  background: var(--bg-tertiary);
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
  background: var(--bg-tertiary);
}

.config-hint {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 0.25rem;
  margin-bottom: 0;
}

/* Status Badge for Inactive */
.status-badge.status-inactive {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px dashed var(--text-tertiary);
}
