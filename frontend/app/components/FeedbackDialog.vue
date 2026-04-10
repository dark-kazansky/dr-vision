<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="close">
        <div class="modal-container">
          <div class="modal-header">
            <h2 class="modal-title">Send Feedback</h2>
            <button class="modal-close" @click="close">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div class="modal-body">
            <div class="form-group">
              <label for="feedback-type" class="form-label">Feedback Type</label>
              <select id="feedback-type" v-model="feedbackType" class="form-select">
                <option value="bug">Bug Report</option>
                <option value="feature">Feature Request</option>
                <option value="improvement">Improvement</option>
                <option value="other">Other</option>
              </select>
            </div>
            
            <div class="form-group">
              <label for="feedback-message" class="form-label">Message</label>
              <textarea
                id="feedback-message"
                v-model="feedbackMessage"
                class="form-textarea"
                rows="6"
                placeholder="Tell us what you think..."
                @keydown.esc="close"
              ></textarea>
            </div>
            
            <div v-if="error" class="error-message">
              {{ error }}
            </div>
            
            <div v-if="success" class="success-message">
              Thank you for your feedback!
            </div>
          </div>
          
          <div class="modal-footer">
            <button class="btn-secondary" @click="close">Cancel</button>
            <button 
              class="btn-primary" 
              @click="submit"
              :disabled="!feedbackMessage.trim() || isSubmitting"
            >
              {{ isSubmitting ? 'Sending...' : 'Send Feedback' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
  submit: [feedback: { type: string; message: string }]
}>()

const feedbackType = ref('bug')
const feedbackMessage = ref('')
const isSubmitting = ref(false)
const error = ref('')
const success = ref(false)

const close = () => {
  if (!isSubmitting.value) {
    emit('close')
    // Reset form after animation
    setTimeout(() => {
      feedbackType.value = 'bug'
      feedbackMessage.value = ''
      error.value = ''
      success.value = false
    }, 300)
  }
}

const submit = async () => {
  if (!feedbackMessage.value.trim()) {
    error.value = 'Please enter your feedback'
    return
  }
  
  error.value = ''
  isSubmitting.value = true
  
  try {
    emit('submit', {
      type: feedbackType.value,
      message: feedbackMessage.value
    })
    
    success.value = true
    
    // Close after showing success message
    setTimeout(() => {
      close()
    }, 1500)
  } catch (err) {
    error.value = 'Failed to send feedback. Please try again.'
  } finally {
    isSubmitting.value = false
  }
}

// Close on Escape key
onMounted(() => {
  const handleEscape = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && props.isOpen) {
      close()
    }
  }
  window.addEventListener('keydown', handleEscape)
  
  onUnmounted(() => {
    window.removeEventListener('keydown', handleEscape)
  })
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
}

.modal-close:hover {
  background-color: #f3f4f6;
  color: #111827;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #111827;
  background-color: white;
  transition: all 0.2s;
}

.form-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #111827;
  font-family: inherit;
  resize: vertical;
  transition: all 0.2s;
}

.form-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-textarea::placeholder {
  color: #9ca3af;
}

.error-message {
  padding: 12px;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 14px;
  margin-top: 12px;
}

.success-message {
  padding: 12px;
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  color: #16a34a;
  font-size: 14px;
  margin-top: 12px;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
}

.btn-secondary {
  padding: 10px 20px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  background-color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.btn-primary {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: white;
  background-color: #3b82f6;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
