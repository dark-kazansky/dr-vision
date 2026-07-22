<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="isOpen" class="dialog-overlay" @click.self="close">
        <div class="dialog-container key-dialog">
          <div class="dialog-header">
            <h2 class="dialog-title">AWS Bedrock Configuration</h2>
            <button class="dialog-close" @click="close">
              <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="dialog-content">
            <div class="form-group">
              <label class="form-label">AWS Bearer Token</label>
              <p class="form-description">
                Enter your AWS Bedrock API bearer token. This token is required to access Claude models via Bedrock.
              </p>
              <textarea
                v-model="bearerToken"
                class="form-textarea"
                placeholder="Paste your AWS_BEARER_TOKEN_BEDROCK here..."
                rows="6"
              ></textarea>
              <p class="form-hint">
                Your token will be securely stored on the server. Never share this with untrusted parties.
              </p>
            </div>

            <div class="form-group">
              <label class="form-label">AWS Region</label>
              <select v-model="awsRegion" class="form-select">
                <option value="us-east-1">us-east-1 (US East - N. Virginia)</option>
                <option value="us-west-2">us-west-2 (US West - Oregon)</option>
                <option value="eu-west-1">eu-west-1 (Europe - Ireland)</option>
                <option value="ap-southeast-1">ap-southeast-1 (Asia Pacific - Singapore)</option>
                <option value="ap-northeast-1">ap-northeast-1 (Asia Pacific - Tokyo)</option>
              </select>
            </div>
          </div>

          <div class="dialog-footer">
            <button class="btn-secondary" @click="close">Cancel</button>
            <button class="btn-primary" @click="handleSubmit" :disabled="!bearerToken.trim()">
              Update Token
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
  update: [token: string]
}>()

const bearerToken = ref('')
const awsRegion = ref('ap-southeast-1')
const isLoading = ref(false)

// Use composables
const { success: successNotif, error: errorNotif } = useNotification ? useNotification() : { success: () => {}, error: () => {} }
const config = useRuntimeConfig ? useRuntimeConfig() : { public: { apiBaseUrl: 'http://localhost:8082' } }

const close = () => {
  emit('close')
  // Reset form
  setTimeout(() => {
    bearerToken.value = ''
  }, 300)
}

const handleSubmit = async () => {
  if (!bearerToken.value.trim()) {
    return
  }

  isLoading.value = true

  try {
    // Send to backend API
    const apiBase = config.public?.apiBaseUrl || 'http://localhost:8082'
    const response = await fetch(`${apiBase}/api/config/update-bedrock-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        bearer_token: bearerToken.value.trim(),
        region: awsRegion.value,
      }),
    })

    if (!response.ok) {
      throw new Error('Failed to update token')
    }

    const data = await response.json()

    // Show success notification
    successNotif('AWS Bedrock token updated successfully')

    // Emit update event
    emit('update', bearerToken.value)

    // Close dialog
    close()
  } catch (error) {
    console.error('Error updating token:', error)
    errorNotif('Failed to update AWS token. Please try again.')
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(32, 21, 21, 0.4);
  z-index: 5000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog-container {
  background-color: var(--color-cream);
  border-radius: var(--radius-comfortable);
  box-shadow: 0 10px 40px rgba(32, 21, 21, 0.1);
  max-width: 500px;
  width: 90%;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow-y: auto;
}

.key-dialog {
  max-width: 600px;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid var(--color-sand);
}

.dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.dialog-close {
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-standard);
  transition: all 0.15s;
}

.dialog-close:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.dialog-content {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.form-description {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  line-height: 1.5;
}

.form-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--color-sand);
  border-radius: var(--radius-comfortable);
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-primary);
  background-color: var(--bg-secondary);
  resize: vertical;
  transition: all 0.15s;
}

.form-textarea:focus {
  outline: none;
  border-color: var(--accent-orange);
  box-shadow: 0 0 0 3px rgba(255, 79, 0, 0.1);
}

.form-textarea::placeholder {
  color: var(--text-tertiary);
}

.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-sand);
  border-radius: var(--radius-comfortable);
  font-size: 14px;
  color: var(--text-primary);
  background-color: var(--bg-secondary);
  cursor: pointer;
  transition: all 0.15s;
}

.form-select:hover {
  border-color: var(--text-tertiary);
}

.form-select:focus {
  outline: none;
  border-color: var(--accent-orange);
  box-shadow: 0 0 0 3px rgba(255, 79, 0, 0.1);
}

.form-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 8px;
  font-style: italic;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-sand);
  background-color: var(--bg-primary);
}

.btn-secondary {
  padding: 10px 20px;
  border: 1px solid var(--color-sand);
  border-radius: var(--radius-comfortable);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-secondary:hover {
  background-color: var(--bg-tertiary);
  border-color: var(--text-tertiary);
}

.btn-primary {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-comfortable);
  background-color: var(--accent-orange);
  color: var(--color-cream);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background-color: #e54700;
}

.btn-primary:disabled {
  background-color: var(--bg-tertiary);
  color: var(--text-tertiary);
  cursor: not-allowed;
  opacity: 0.6;
}

/* Transitions */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
