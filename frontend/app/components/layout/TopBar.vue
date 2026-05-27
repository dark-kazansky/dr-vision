<script setup lang="ts">
/**
 * TopBar — App header with logo and action buttons.
 */
import { useTranslation } from '~/composables/useTranslation'

const { t } = useTranslation()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'feedback'): void
  (e: 'help'): void
}>()
</script>

<template>
  <div class="top-bar">
    <div class="logo logo-clickable">
      <img src="/assets/logo.png" alt="Dr.Vision" class="logo-icon" @click="emit('refresh')" />
      <span class="logo-text" @click="emit('refresh')">Dr.Vision</span>
    </div>
    <div class="top-bar-actions">
      <button class="top-bar-btn" @click="emit('feedback')">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
        {{ t('topbar.feedback') }}
      </button>
      <button class="top-bar-btn" @click="emit('help')">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ t('topbar.help') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 48px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-clickable {
  cursor: pointer;
}

.logo-icon {
  width: 28px;
  height: 28px;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: #1f2937;
}

.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.top-bar-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  background: none;
  border-radius: 6px;
  font-size: 12px;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s;
}

.top-bar-btn:hover {
  background: #f3f4f6;
  color: #374151;
}
</style>
