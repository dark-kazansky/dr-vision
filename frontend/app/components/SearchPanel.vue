<template>
  <div class="search-panel">
    <!-- Header -->
    <div class="search-header">
      <h2 class="search-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.3-4.3"></path>
        </svg>
        Document Search
      </h2>
      <span v-if="hasSearched" class="search-count">{{ total }} results</span>
    </div>

    <!-- Search Bar -->
    <div class="search-bar">
      <div class="search-input-wrapper">
        <svg class="search-icon" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="query"
          type="text"
          class="search-input"
          placeholder="Search across all OCR document content..."
          @input="onInput"
          @keyup.enter="performSearch"
        />
        <button v-if="query" class="search-clear" @click="clear">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <button class="search-btn" :disabled="isLoading || !query.trim()" @click="performSearch">
        <span v-if="isLoading" class="btn-spinner"></span>
        <template v-else>Search</template>
      </button>
    </div>

    <!-- Filters -->
    <div class="filter-row">
      <div class="filter-field">
        <label>From</label>
        <input v-model="dateFrom" type="date" @change="applyFilters" />
      </div>
      <div class="filter-field">
        <label>To</label>
        <input v-model="dateTo" type="date" @change="applyFilters" />
      </div>
      <button
        v-if="dateFrom || dateTo"
        class="filter-clear"
        @click="dateFrom = ''; dateTo = ''; applyFilters()"
      >
        Clear filters
      </button>
    </div>

    <!-- Error State -->
    <div v-if="errorMessage" class="error-state">
      <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="error-title">Search failed</p>
      <p class="error-detail">{{ errorMessage }}</p>
    </div>

    <!-- Loading State -->
    <div v-else-if="isLoading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Searching documents...</p>
    </div>

    <!-- Results -->
    <div v-else-if="results.length > 0" class="results-list">
      <div
        v-for="hit in results"
        :key="hit.id"
        class="result-card"
      >
        <div class="result-header">
          <div class="result-info">
            <span class="result-filename">{{ hit.filename }}</span>
            <div class="result-meta">
              <span v-if="hit.provider" class="meta-tag">{{ hit.provider }}</span>
              <span v-if="hit.model_id" class="meta-tag">{{ hit.model_id }}</span>
              <span v-if="hit.tier" class="meta-tag">{{ hit.tier }}</span>
              <span class="meta-time">{{ formatTime(hit.created_at) }}</span>
            </div>
          </div>
          <span class="result-rank" :title="`Relevance score: ${hit.rank.toFixed(3)}`">
            {{ (hit.rank * 100).toFixed(0) }}%
          </span>
        </div>
        <p class="result-snippet" v-html="renderSnippet(hit.snippet)"></p>
      </div>
    </div>

    <!-- Empty: no results after search -->
    <div v-else-if="hasSearched && !isLoading" class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.3-4.3"></path>
      </svg>
      <p class="empty-title">No matching documents</p>
      <p class="empty-subtitle">Try different keywords or a quoted phrase for an exact match.</p>
    </div>

    <!-- Empty: initial state (before any search) -->
    <div v-else class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.3-4.3"></path>
      </svg>
      <p class="empty-title">Search your documents</p>
      <p class="empty-subtitle">Enter keywords to search across the full text of every processed OCR document.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSearch } from '~/composables/useSearch'
import { renderSnippet } from '~/utils/searchSnippet'

const {
  query,
  results,
  total,
  isLoading,
  hasSearched,
  errorMessage,
  dateFrom,
  dateTo,
  performSearch,
  onInput,
  clear,
  applyFilters,
} = useSearch()

function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.search-panel {
  padding: 24px 32px;
  max-width: 1100px;
  margin: 0 auto;
  color: #1f2937;
}

.search-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}

.search-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: #111827;
}

.search-count {
  font-size: 13px;
  color: #6b7280;
}

/* Search bar */
.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #9ca3af;
  pointer-events: none;
}

.search-input {
  flex: 1;
  padding: 10px 36px 10px 38px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  color: #1f2937;
  background: #ffffff;
  outline: none;
  transition: all 0.15s;
}

.search-input::placeholder { color: #9ca3af; }

.search-input:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
}

.search-clear {
  position: absolute;
  right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: none;
  color: #9ca3af;
  cursor: pointer;
  border-radius: 50%;
}

.search-clear:hover { background: #f3f4f6; color: #374151; }

.search-btn {
  padding: 10px 22px;
  border: none;
  border-radius: 8px;
  background: #7c3aed;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  min-width: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-btn:hover:not(:disabled) { background: #6d28d9; }
.search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Filters */
.filter-row {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-field label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.filter-field input {
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  color: #1f2937;
  background: #ffffff;
  outline: none;
}

.filter-field input:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1);
}

.filter-clear {
  padding: 7px 12px;
  border: none;
  background: none;
  color: #7c3aed;
  font-size: 13px;
  cursor: pointer;
  border-radius: 6px;
}

.filter-clear:hover { background: #f5f3ff; }

/* Results */
.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px 18px;
  background: #ffffff;
  transition: box-shadow 0.15s, border-color 0.15s;
}

.result-card:hover {
  border-color: #c4b5fd;
  box-shadow: 0 2px 8px rgba(124, 58, 237, 0.08);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.result-info { min-width: 0; }

.result-filename {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  word-break: break-all;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  align-items: center;
}

.meta-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #f3f4f6;
  color: #6b7280;
}

.meta-time {
  font-size: 11px;
  color: #9ca3af;
}

.result-rank {
  font-size: 12px;
  font-weight: 600;
  color: #7c3aed;
  background: #f5f3ff;
  padding: 3px 8px;
  border-radius: 8px;
  white-space: nowrap;
  flex-shrink: 0;
}

.result-snippet {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.result-snippet :deep(mark) {
  background: #fef08a;
  color: #713f12;
  padding: 0 2px;
  border-radius: 3px;
  font-weight: 600;
}

/* States */
.loading-state, .empty-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #9ca3af;
  text-align: center;
}

.empty-state svg, .error-state svg { margin-bottom: 12px; color: #d1d5db; }

.empty-title, .error-title {
  font-size: 15px;
  font-weight: 600;
  color: #6b7280;
  margin: 0 0 4px;
}

.empty-subtitle, .error-detail {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
  max-width: 420px;
}

.error-state svg { color: #ef4444; }
.error-title { color: #dc2626; }

.loading-state { color: #6b7280; }

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e5e7eb;
  border-top-color: #7c3aed;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}
</style>
