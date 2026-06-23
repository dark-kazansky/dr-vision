<template>
  <div class="api-explorer">
    <!-- Top Bar -->
    <div class="top-bar">
      <div class="logo logo-clickable">
        <img src="/assets/logo.png" alt="Doc Intelligence" class="logo-icon" @click="navigateTo('/')" />
        <span class="logo-text" @click="navigateTo('/')">Doc Intelligence</span>
      </div>
      <div class="top-bar-actions">
        <button class="top-bar-btn" @click="navigateTo('/')">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Quay lại
        </button>
      </div>
    </div>

    <div class="explorer-layout">
      <!-- Sidebar: danh sách endpoint -->
      <aside class="explorer-sidebar">
        <div class="sidebar-header">
          <h2 class="sidebar-title">
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            API Explorer
          </h2>
          <span class="endpoint-count">{{ endpoints.length }} endpoints</span>
        </div>

        <div v-if="isLoadingEndpoints" class="sidebar-loading">
          <div class="spinner-sm"></div>
          <span>Đang tải...</span>
        </div>

        <div v-else class="endpoint-groups">
          <div v-for="group in groups" :key="group.name" class="endpoint-group">
            <div class="group-name">{{ group.name }}</div>
            <button
              v-for="ep in group.endpoints"
              :key="ep.id"
              class="endpoint-item"
              :class="{ active: selectedEndpoint?.id === ep.id }"
              @click="selectEndpoint(ep)"
            >
              <span class="method-badge" :class="methodColor(ep.method)">{{ ep.method }}</span>
              <span class="endpoint-path">{{ ep.path }}</span>
            </button>
          </div>
        </div>
      </aside>

      <!-- Main: form + response -->
      <main class="explorer-main">
        <!-- Placeholder khi chưa chọn -->
        <div v-if="!selectedEndpoint" class="explorer-placeholder">
          <svg width="64" height="64" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="placeholder-icon">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p class="placeholder-text">Chọn một endpoint từ danh sách bên trái để bắt đầu</p>
        </div>

        <div v-else class="endpoint-detail">
          <!-- Header endpoint -->
          <div class="detail-header">
            <div class="detail-title-row">
              <span class="method-badge-lg" :class="methodColor(selectedEndpoint.method)">
                {{ selectedEndpoint.method }}
              </span>
              <code class="detail-path">{{ selectedEndpoint.path }}</code>
            </div>
            <h3 class="detail-summary">{{ selectedEndpoint.summary }}</h3>
            <p class="detail-description">{{ selectedEndpoint.description }}</p>
          </div>

          <div class="detail-body">
            <!-- Form tham số -->
            <div class="params-section">
              <h4 class="section-title">Tham số</h4>

              <div v-if="selectedEndpoint.fields.length === 0" class="no-params">
                Endpoint này không có tham số.
              </div>

              <div v-else class="params-form">
                <div
                  v-for="field in selectedEndpoint.fields"
                  :key="field.name"
                  class="param-row"
                >
                  <label class="param-label">
                    {{ field.label }}
                    <span v-if="field.required" class="required-badge">*</span>
                    <span v-if="field.path_param" class="path-badge">path</span>
                  </label>

                  <!-- File input -->
                  <div v-if="field.type === 'file'" class="file-input-wrapper">
                    <input
                      type="file"
                      :accept="field.accept"
                      class="file-input"
                      @change="(e) => handleFileChange(field.name, e)"
                    />
                    <span v-if="fileValues[field.name]" class="file-selected">
                      ✓ {{ fileValues[field.name]?.name }}
                    </span>
                  </div>

                  <!-- Textarea -->
                  <textarea
                    v-else-if="field.type === 'textarea'"
                    v-model="fieldValues[field.name]"
                    class="param-textarea"
                    :placeholder="field.placeholder"
                    rows="4"
                    @input="updateCurl"
                  />

                  <!-- Select -->
                  <select
                    v-else-if="field.type === 'select'"
                    v-model="fieldValues[field.name]"
                    class="param-select"
                    @change="updateCurl"
                  >
                    <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
                  </select>

                  <!-- Checkbox -->
                  <label v-else-if="field.type === 'checkbox'" class="param-checkbox">
                    <input
                      type="checkbox"
                      v-model="fieldValues[field.name]"
                      @change="updateCurl"
                    />
                    <span>{{ fieldValues[field.name] ? 'true' : 'false' }}</span>
                  </label>

                  <!-- Number -->
                  <input
                    v-else-if="field.type === 'number'"
                    type="number"
                    v-model.number="fieldValues[field.name]"
                    class="param-input"
                    :placeholder="field.placeholder"
                    @input="updateCurl"
                  />

                  <!-- Text -->
                  <input
                    v-else
                    type="text"
                    v-model="fieldValues[field.name]"
                    class="param-input"
                    :placeholder="field.placeholder"
                    @input="updateCurl"
                  />
                </div>
              </div>

              <!-- Nút Execute -->
              <div class="execute-row">
                <button
                  class="execute-btn"
                  :disabled="isExecuting"
                  @click="execute"
                >
                  <div v-if="isExecuting" class="spinner-sm"></div>
                  <svg v-else width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {{ isExecuting ? 'Đang gọi...' : 'Thực thi' }}
                </button>
              </div>
            </div>

            <!-- cURL command -->
            <div class="curl-section">
              <div class="section-header-row">
                <h4 class="section-title">cURL</h4>
                <button class="copy-btn" @click="copyCurl" title="Sao chép">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Sao chép
                </button>
              </div>
              <pre class="curl-block">{{ curlCommand }}</pre>
            </div>

            <!-- Response -->
            <div v-if="response" class="response-section">
              <div class="section-header-row">
                <h4 class="section-title">
                  Kết quả
                  <span :class="statusColor(response.status)" class="status-badge">
                    {{ response.status }}
                  </span>
                  <span class="duration-badge">{{ response.duration }}ms</span>
                </h4>
                <button class="copy-btn" @click="copyResponse" title="Sao chép JSON">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Sao chép JSON
                </button>
              </div>
              <pre class="response-block" :class="response.error ? 'response-error' : 'response-success'">{{ JSON.stringify(response.data, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
const {
  endpoints,
  groups,
  isLoadingEndpoints,
  selectedEndpoint,
  fieldValues,
  fileValues,
  isExecuting,
  response,
  curlCommand,
  loadEndpoints,
  selectEndpoint,
  updateCurl,
  execute,
  copyCurl,
  copyResponse,
  methodColor,
  statusColor,
} = useApiExplorer()

// Xử lý file input
const handleFileChange = (fieldName: string, event: Event) => {
  const input = event.target as HTMLInputElement
  fileValues.value[fieldName] = input.files?.[0] ?? null
  updateCurl()
}

// Tải endpoints khi mount
onMounted(() => {
  loadEndpoints()
})

useHead({ title: 'API Explorer — Doc Intelligence' })
</script>

<style scoped>
.api-explorer {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0f1117;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ── Top Bar ── */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 48px;
  background: #161b27;
  border-bottom: 1px solid #1e2535;
  flex-shrink: 0;
  z-index: 10;
}
.logo { display: flex; align-items: center; gap: 8px; }
.logo-clickable { cursor: pointer; }
.logo-icon { width: 28px; height: 28px; border-radius: 6px; }
.logo-text { font-size: 15px; font-weight: 600; color: #e2e8f0; }
.top-bar-actions { display: flex; gap: 8px; }
.top-bar-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 6px; border: 1px solid #2d3748;
  background: transparent; color: #94a3b8; font-size: 13px; cursor: pointer;
  transition: all 0.15s;
}
.top-bar-btn:hover { background: #1e2535; color: #e2e8f0; }

/* ── Layout ── */
.explorer-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Sidebar ── */
.explorer-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: #161b27;
  border-right: 1px solid #1e2535;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #1e2535;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sidebar-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0;
}
.endpoint-count {
  font-size: 11px; color: #64748b;
  background: #1e2535; padding: 2px 8px; border-radius: 10px;
}
.sidebar-loading {
  display: flex; align-items: center; gap: 8px;
  padding: 20px 16px; color: #64748b; font-size: 13px;
}
.endpoint-groups {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.endpoint-group { margin-bottom: 4px; }
.group-name {
  padding: 8px 16px 4px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: #475569;
}
.endpoint-item {
  display: flex; align-items: center; gap: 8px;
  width: 100%; padding: 7px 16px;
  background: transparent; border: none; cursor: pointer;
  text-align: left; transition: background 0.1s;
}
.endpoint-item:hover { background: #1e2535; }
.endpoint-item.active { background: #1e2d45; }
.endpoint-path {
  font-size: 12px; color: #94a3b8; font-family: 'SF Mono', monospace;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.endpoint-item.active .endpoint-path { color: #e2e8f0; }

/* ── Method badges ── */
.method-badge {
  font-size: 10px; font-weight: 700; padding: 2px 6px;
  border-radius: 4px; flex-shrink: 0; font-family: monospace;
}
.method-badge-lg {
  font-size: 13px; font-weight: 700; padding: 3px 10px;
  border-radius: 6px; font-family: monospace;
}

/* ── Main ── */
.explorer-main {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.explorer-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; gap: 16px; color: #475569;
}
.placeholder-icon { opacity: 0.3; }
.placeholder-text { font-size: 14px; }

/* ── Endpoint detail ── */
.endpoint-detail { display: flex; flex-direction: column; height: 100%; }

.detail-header {
  padding: 24px 28px 20px;
  border-bottom: 1px solid #1e2535;
  background: #161b27;
}
.detail-title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.detail-path {
  font-size: 15px; font-family: 'SF Mono', monospace;
  color: #e2e8f0; background: #1e2535; padding: 4px 10px; border-radius: 6px;
}
.detail-summary { font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 6px; }
.detail-description { font-size: 13px; color: #64748b; margin: 0; line-height: 1.5; }

.detail-body {
  flex: 1;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
}

/* ── Sections ── */
.section-title {
  font-size: 13px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.06em;
  margin: 0 0 12px;
  display: flex; align-items: center; gap: 8px;
}
.section-header-row {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;
}
.section-header-row .section-title { margin-bottom: 0; }

/* ── Params form ── */
.no-params { font-size: 13px; color: #475569; padding: 12px 0; }
.params-form { display: flex; flex-direction: column; gap: 14px; }
.param-row { display: flex; flex-direction: column; gap: 6px; }
.param-label {
  font-size: 12px; font-weight: 500; color: #94a3b8;
  display: flex; align-items: center; gap: 6px;
}
.required-badge {
  color: #f87171; font-size: 11px;
}
.path-badge {
  font-size: 10px; background: #312e81; color: #a5b4fc;
  padding: 1px 6px; border-radius: 4px;
}

.param-input, .param-select, .param-textarea {
  background: #1e2535; border: 1px solid #2d3748; border-radius: 6px;
  color: #e2e8f0; font-size: 13px; padding: 8px 12px;
  outline: none; transition: border-color 0.15s;
  font-family: inherit;
}
.param-input:focus, .param-select:focus, .param-textarea:focus {
  border-color: #3b82f6;
}
.param-textarea { resize: vertical; font-family: 'SF Mono', monospace; font-size: 12px; }
.param-select { cursor: pointer; }
.param-checkbox {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: #94a3b8; cursor: pointer;
}
.param-checkbox input { cursor: pointer; }

.file-input-wrapper { display: flex; flex-direction: column; gap: 6px; }
.file-input {
  background: #1e2535; border: 1px dashed #2d3748; border-radius: 6px;
  color: #94a3b8; font-size: 12px; padding: 8px 12px; cursor: pointer;
}
.file-selected { font-size: 12px; color: #34d399; }

/* ── Execute button ── */
.execute-row { margin-top: 8px; }
.execute-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 20px; border-radius: 8px; border: none;
  background: #2563eb; color: #fff; font-size: 14px; font-weight: 500;
  cursor: pointer; transition: background 0.15s;
}
.execute-btn:hover:not(:disabled) { background: #1d4ed8; }
.execute-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── cURL block ── */
.curl-block {
  background: #0d1117; border: 1px solid #1e2535; border-radius: 8px;
  padding: 14px 16px; font-size: 12px; font-family: 'SF Mono', monospace;
  color: #7dd3fc; white-space: pre-wrap; word-break: break-all;
  margin: 0; line-height: 1.6;
}

/* ── Response block ── */
.response-block {
  background: #0d1117; border: 1px solid #1e2535; border-radius: 8px;
  padding: 14px 16px; font-size: 12px; font-family: 'SF Mono', monospace;
  white-space: pre-wrap; word-break: break-all; margin: 0; line-height: 1.6;
  max-height: 400px; overflow-y: auto;
}
.response-success { color: #86efac; border-color: #14532d; }
.response-error { color: #fca5a5; border-color: #7f1d1d; }

/* ── Badges ── */
.status-badge { font-size: 12px; font-weight: 600; }
.duration-badge {
  font-size: 11px; color: #475569; background: #1e2535;
  padding: 2px 8px; border-radius: 10px; font-weight: 400;
}

/* ── Copy button ── */
.copy-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 5px; border: 1px solid #2d3748;
  background: transparent; color: #64748b; font-size: 12px; cursor: pointer;
  transition: all 0.15s;
}
.copy-btn:hover { background: #1e2535; color: #94a3b8; }

/* ── Spinner ── */
.spinner-sm {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.2);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 3px; }
</style>
