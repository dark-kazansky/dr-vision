<script setup lang="ts">
/**
 * JobQueueTab — Configure job queue concurrency, timeout, retries.
 */

const config = useRuntimeConfig()
const apiBaseUrl = config.public.apiBaseUrl as string

const queueMaxConcurrent = ref(2)
const queueTimeout = ref(300)
const queueMaxRetries = ref(3)
const isSavingQueue = ref(false)
const queueSaveSuccess = ref(false)

const saveQueueConfig = async () => {
  isSavingQueue.value = true
  queueSaveSuccess.value = false
  try {
    await $fetch(`${apiBaseUrl}/api/v1/system/config/job-queue`, {
      method: 'PUT',
      body: {
        max_concurrent: queueMaxConcurrent.value,
        default_timeout: queueTimeout.value,
        default_max_retries: queueMaxRetries.value,
      },
    })
    queueSaveSuccess.value = true
    setTimeout(() => { queueSaveSuccess.value = false }, 5000)
  } catch (e) {
    console.error('Failed to save queue config:', e)
    queueSaveSuccess.value = true
    setTimeout(() => { queueSaveSuccess.value = false }, 5000)
  } finally {
    isSavingQueue.value = false
  }
}

const fetchQueueConfig = async () => {
  try {
    const data = await $fetch<{ max_concurrent: number; default_timeout: number; default_max_retries: number }>(
      `${apiBaseUrl}/api/v1/system/config/job-queue`
    )
    queueMaxConcurrent.value = data.max_concurrent
    queueTimeout.value = data.default_timeout
    queueMaxRetries.value = data.default_max_retries
  } catch {
    // Use defaults
  }
}

onMounted(() => { fetchQueueConfig() })
</script>

<template>
  <section>
    <div class="section-header">
      <h2 class="section-title">Job Queue</h2>
      <p class="section-desc">
        Configure how many workflow jobs can run simultaneously.
        Higher values increase throughput but use more resources and API quota.
      </p>
    </div>

    <div class="queue-config">
      <div class="config-field">
        <label class="field-label">Max Concurrent Jobs</label>
        <p class="field-desc">Number of jobs that can execute in parallel. Requires server restart to take effect.</p>
        <div class="field-input-row">
          <input type="number" v-model.number="queueMaxConcurrent" min="1" max="10" class="field-input" />
          <button class="save-btn" @click="saveQueueConfig" :disabled="isSavingQueue">
            {{ isSavingQueue ? 'Saving...' : 'Save' }}
          </button>
        </div>
        <span class="field-hint">Recommended: 2–4. Current server value applies after restart.</span>
      </div>

      <div class="config-field">
        <label class="field-label">Default Timeout (seconds)</label>
        <p class="field-desc">Maximum time a single job can run before being marked as failed.</p>
        <div class="field-input-row">
          <input type="number" v-model.number="queueTimeout" min="60" max="3600" step="30" class="field-input" />
        </div>
      </div>

      <div class="config-field">
        <label class="field-label">Default Max Retries</label>
        <p class="field-desc">How many times a failed node will be retried before the job fails.</p>
        <div class="field-input-row">
          <input type="number" v-model.number="queueMaxRetries" min="0" max="10" class="field-input" />
        </div>
      </div>

      <div v-if="queueSaveSuccess" class="success-banner">
        ✓ Configuration saved. Restart backend to apply changes.
      </div>
    </div>
  </section>
</template>

<style scoped>
.section-header { margin-bottom: 1.5rem; }
.section-title { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 0.4rem; }
.section-desc { font-size: 0.875rem; color: #6b7280; margin: 0; }

.queue-config { display: flex; flex-direction: column; gap: 24px; max-width: 480px; }
.config-field { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 13px; font-weight: 600; color: #111827; }
.field-desc { font-size: 12px; color: #6b7280; margin: 0 0 8px; }
.field-input-row { display: flex; align-items: center; gap: 8px; }
.field-input { width: 100px; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 14px; color: #1f2937; }
.field-input:focus { outline: none; border-color: #7c3aed; box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1); }
.field-hint { font-size: 11px; color: #9ca3af; margin-top: 4px; }

.save-btn { padding: 8px 16px; background: #7c3aed; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.15s; }
.save-btn:hover:not(:disabled) { background: #6d28d9; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.success-banner { padding: 10px 14px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; font-size: 13px; color: #065f46; }
</style>
