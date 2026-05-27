<script setup lang="ts">
/**
 * ConfirmDialog — Reusable confirmation dialog with cancel/danger actions.
 */

defineProps<{
  visible: boolean
  message: string
  confirmLabel?: string
  cancelLabel?: string
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()
</script>

<template>
  <div v-if="visible" class="confirm-overlay" @click="emit('cancel')">
    <div class="confirm-dialog" @click.stop>
      <p class="confirm-message">{{ message }}</p>
      <div class="confirm-actions">
        <button class="confirm-btn confirm-cancel" @click="emit('cancel')">
          {{ cancelLabel || 'Cancel' }}
        </button>
        <button class="confirm-btn confirm-danger" @click="emit('confirm')">
          {{ confirmLabel || 'Delete' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.confirm-dialog {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  min-width: 320px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.confirm-message {
  font-size: 14px;
  color: #1f2937;
  margin: 0 0 20px;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.confirm-btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.confirm-cancel {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  color: #6b7280;
}

.confirm-cancel:hover {
  background: #f3f4f6;
}

.confirm-danger {
  background: #dc2626;
  border: none;
  color: #ffffff;
}

.confirm-danger:hover {
  background: #b91c1c;
}
</style>
