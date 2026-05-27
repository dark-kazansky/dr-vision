<script setup lang="ts">
/**
 * SearchBox — Inline search input with clear button.
 */

const model = defineModel<string>({ default: '' })
</script>

<template>
  <div class="search-box">
    <svg class="search-icon" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
    <input
      v-model="model"
      type="text"
      class="search-input"
      placeholder="Tìm workflow..."
    />
    <button v-if="model" class="search-clear" @click="model = ''">
      <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: #9ca3af;
  pointer-events: none;
}

.search-input {
  padding: 8px 32px 8px 34px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  color: #1f2937;
  background: #ffffff;
  width: 220px;
  transition: all 0.15s;
  outline: none;
}

.search-input::placeholder { color: #9ca3af; }

.search-input:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
}

.search-clear {
  position: absolute;
  right: 8px;
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
  transition: all 0.15s;
}

.search-clear:hover { background: #f3f4f6; color: #374151; }
</style>
