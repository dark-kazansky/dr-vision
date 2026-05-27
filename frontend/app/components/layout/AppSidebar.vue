<script setup lang="ts">
/**
 * AppSidebar — Navigation + file list sidebar.
 */
import { useTranslation } from '~/composables/useTranslation'

const { t } = useTranslation()

const props = defineProps<{
  activeView: string
  files: any[]
  selectedFile: any
}>()

const emit = defineEmits<{
  (e: 'navigate', view: string): void
  (e: 'add-file'): void
  (e: 'select-file', file: any): void
  (e: 'remove-file', fileId: string): void
  (e: 'drag-start', event: DragEvent, file: any): void
}>()

const navItems = [
  { id: 'parse', icon: 'parse', labelKey: 'sidebar.parse' },
  { id: 'classify', icon: 'classify', labelKey: 'sidebar.classify' },
  { id: 'extraction', icon: 'extraction', labelKey: 'sidebar.extract' },
  { id: 'split', icon: 'split', labelKey: 'sidebar.split' },
  { id: 'data', icon: 'data', label: 'Data' },
  { id: 'journey', icon: 'journey', labelKey: 'sidebar.journey' },
]
</script>

<template>
  <div class="sidebar">
    <div class="sidebar-nav">
      <a
        v-for="item in navItems"
        :key="item.id"
        href="#"
        class="nav-item"
        :class="{ active: activeView === item.id }"
        @click.prevent="emit('navigate', item.id)"
      >
        <!-- Parse -->
        <svg v-if="item.icon === 'parse'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 22h14a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v4" /><path d="M14 2v4a2 2 0 0 0 2 2h4" /><path d="m5 12-3 3 3 3" /><path d="m9 18 3-3-3-3" />
        </svg>
        <!-- Classify -->
        <svg v-else-if="item.icon === 'classify'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m15 5 6.3 6.3a2.4 2.4 0 0 1 0 3.4L17 19" /><path d="M9.586 5.586A2 2 0 0 0 8.172 5H3a1 1 0 0 0-1 1v5.172a2 2 0 0 0 .586 1.414L8.29 18.29a2.426 2.426 0 0 0 3.42 0l3.58-3.58a2.426 2.426 0 0 0 0-3.42z" /><circle cx="6.5" cy="9.5" r=".5" fill="currentColor" />
        </svg>
        <!-- Extraction -->
        <svg v-else-if="item.icon === 'extraction'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2v4a2 2 0 0 0 2 2h4" /><path d="M4 7V4a2 2 0 0 1 2-2 2 2 0 0 0-2 2" /><path d="M4.063 20.999a2 2 0 0 0 2 1L18 22a2 2 0 0 0 2-2V7l-5-5H6" /><path d="m5 11-3 3" /><path d="m5 17-3-3h10" />
        </svg>
        <!-- Split -->
        <svg v-else-if="item.icon === 'split'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="6" cy="6" r="3" /><path d="M8.12 8.12 12 12" /><path d="M20 4 8.12 15.88" /><circle cx="6" cy="18" r="3" /><path d="M14.8 14.8 20 20" />
        </svg>
        <!-- Data -->
        <svg v-else-if="item.icon === 'data'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5V19A9 3 0 0 0 21 19V5" /><path d="M3 12A9 3 0 0 0 21 12" />
        </svg>
        <!-- Journey -->
        <svg v-else-if="item.icon === 'journey'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 12H3" /><path d="M16 6H3" /><path d="M12 18H3" /><path d="m16 12 5 3-5 3v-6Z" />
        </svg>
        {{ item.labelKey ? t(item.labelKey) : item.label }}
      </a>
    </div>

    <!-- File List -->
    <div class="file-list-section">
      <div class="file-list-header">
        <span class="file-list-title">{{ t('page.uploadedFiles') }}</span>
        <button class="add-more-btn" @click="emit('add-file')">
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
          @dragstart="emit('drag-start', $event, file)"
          @click="emit('select-file', file)"
        >
          <svg class="file-item-icon" width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
            <path v-if="file.type === 'pdf'" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
            <path v-else fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
          </svg>
          <span class="file-item-name">{{ file.name }}</span>
          <div v-if="file.status === 'processing'" class="file-item-status">
            <div class="file-item-spinner" />
          </div>
          <button class="file-item-delete" @click.stop="emit('remove-file', file.id)">
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Settings at bottom -->
    <div class="sidebar-bottom">
      <a
        href="#"
        class="nav-item nav-item-settings"
        :class="{ active: activeView === 'settings' }"
        @click.prevent="emit('navigate', 'settings')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
        Settings
      </a>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: 48px;
  left: 0;
  bottom: 0;
  width: 200px;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  z-index: 90;
}

.sidebar-nav {
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  transition: all 0.15s;
}

.nav-item:hover { background: #f3f4f6; color: #374151; }
.nav-item.active { background: #ede9fe; color: #7c3aed; font-weight: 500; }

.file-list-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-top: 1px solid #e5e7eb;
  padding: 12px 8px;
}

.file-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 8px;
}

.file-list-title { font-size: 11px; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; }

.add-more-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: none;
  border-radius: 4px;
  color: #9ca3af;
  cursor: pointer;
}
.add-more-btn:hover { background: #f3f4f6; color: #374151; }

.file-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.file-item:hover { background: #f3f4f6; }
.file-item.selected { background: #ede9fe; }
.file-item.processing { opacity: 0.7; }
.file-item.completed .file-item-icon { color: #10b981; }
.file-item.error .file-item-icon { color: #ef4444; }

.file-item-icon { color: #9ca3af; flex-shrink: 0; }
.file-item-name { flex: 1; font-size: 12px; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.file-item-status { flex-shrink: 0; }
.file-item-spinner {
  width: 12px; height: 12px;
  border: 2px solid #e5e7eb;
  border-top-color: #7c3aed;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.file-item-delete {
  display: none;
  align-items: center;
  justify-content: center;
  width: 20px; height: 20px;
  border: none; background: none;
  border-radius: 4px;
  color: #9ca3af;
  cursor: pointer;
}
.file-item:hover .file-item-delete { display: flex; }
.file-item-delete:hover { background: #fef2f2; color: #dc2626; }

.sidebar-bottom {
  padding: 8px;
  border-top: 1px solid #e5e7eb;
}

.nav-item-settings { margin-top: 0; }

@keyframes spin { to { transform: rotate(360deg); } }
</style>
