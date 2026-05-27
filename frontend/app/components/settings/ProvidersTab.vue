<script setup lang="ts">
/**
 * ProvidersTab — Provider cards grid with test connection.
 */
defineProps<{
  providers: any[]
  isLoading: boolean
  error: string | null
  testingProvider: string | null
}>()

const emit = defineEmits<{
  (e: 'fetch'): void
  (e: 'test', providerId: string): void
}>()

const getTestResult = (providerId: string) => {
  // Injected from parent via props — simplified
  return null as any
}

const providerInitial = (name: string) => name.charAt(0).toUpperCase()
</script>

<template>
  <section>
    <div class="section-header">
      <h2 class="section-title">AI Providers</h2>
      <p class="section-desc">
        Configure the AI providers used for OCR, classification, extraction, and splitting.
      </p>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="spinner" />
      <span>Loading providers…</span>
    </div>

    <div v-else-if="error" class="error-banner">
      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {{ error }}
      <button class="retry-btn" @click="emit('fetch')">Retry</button>
    </div>

    <div v-else class="provider-grid">
      <div
        v-for="provider in providers"
        :key="provider.id"
        class="provider-card"
        :class="{ configured: provider.configured, unconfigured: !provider.configured }"
      >
        <div class="card-header">
          <div class="provider-identity">
            <div class="provider-icon" :class="`icon-${provider.id}`">
              {{ providerInitial(provider.name) }}
            </div>
            <div>
              <h3 class="provider-name">{{ provider.name }}</h3>
              <span class="provider-type-badge" :class="provider.type">
                {{ provider.type === 'cloud' ? '☁ Cloud' : '🖥 Local' }}
              </span>
            </div>
          </div>
          <div class="status-pill" :class="provider.configured ? 'ok' : 'warn'">
            <span class="status-dot" />
            {{ provider.configured ? 'Configured' : 'Not configured' }}
          </div>
        </div>

        <p class="provider-desc">{{ provider.description }}</p>

        <div v-if="provider.credential_key" class="credential-row">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
          <code class="env-var">{{ provider.credential_key }}</code>
          <span class="cred-status" :class="provider.credential_set ? 'set' : 'missing'">
            {{ provider.credential_set ? '✓ Set' : '✗ Missing' }}
          </span>
        </div>

        <div v-if="provider.base_url" class="url-row">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <span class="base-url">{{ provider.base_url }}</span>
        </div>

        <div v-if="provider.models.length" class="models-section">
          <p class="models-label">Models ({{ provider.models.length }})</p>
          <div class="models-chips">
            <span v-for="model in provider.models" :key="model.model_id" class="model-chip" :title="model.model_id">
              {{ model.name }}
            </span>
          </div>
        </div>
        <div v-else class="no-models">No models configured for this provider.</div>

        <div class="card-footer">
          <button
            class="test-btn"
            :disabled="testingProvider === provider.id"
            @click="emit('test', provider.id)"
          >
            <svg v-if="testingProvider === provider.id" class="spin" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <svg v-else width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {{ testingProvider === provider.id ? 'Testing…' : 'Test Connection' }}
          </button>
        </div>
      </div>
    </div>

    <div class="refresh-row">
      <button class="refresh-btn" :disabled="isLoading" @click="emit('fetch')">
        <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>
  </section>
</template>

<style scoped>
.section-header { margin-bottom: 1.5rem; }
.section-title { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 0.4rem; }
.section-desc { font-size: 0.875rem; color: #6b7280; margin: 0; }

.loading-state { display: flex; align-items: center; gap: 0.75rem; padding: 2rem; color: #6b7280; font-size: 0.875rem; }
.spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #FF6F3C; border-radius: 50%; animation: spin 0.8s linear infinite; }

.error-banner { display: flex; align-items: center; gap: 0.75rem; padding: 0.875rem 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; color: #dc2626; font-size: 0.875rem; }
.retry-btn { margin-left: auto; padding: 0.3rem 0.75rem; background: #fff; border: 1px solid #fca5a5; border-radius: 6px; color: #dc2626; font-size: 0.8125rem; cursor: pointer; }

.provider-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1rem; }

.provider-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.25rem; display: flex; flex-direction: column; gap: 0.875rem; transition: box-shadow 0.15s; }
.provider-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.provider-card.configured { border-left: 3px solid #10b981; }
.provider-card.unconfigured { border-left: 3px solid #f59e0b; }

.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; }
.provider-identity { display: flex; align-items: center; gap: 0.75rem; }
.provider-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.125rem; color: #fff; background: #6366f1; flex-shrink: 0; }
.icon-google_studio { background: #4285f4; }
.icon-poe_api { background: #7c3aed; }
.icon-lm_studio { background: #059669; }
.icon-bedrock { background: #f59e0b; }
.icon-ollama { background: #374151; }

.provider-name { font-size: 0.9375rem; font-weight: 600; color: #111827; margin: 0 0 0.2rem; }
.provider-type-badge { font-size: 0.75rem; font-weight: 500; padding: 0.1rem 0.5rem; border-radius: 999px; }
.provider-type-badge.cloud { background: #eff6ff; color: #3b82f6; }
.provider-type-badge.local { background: #f0fdf4; color: #16a34a; }

.status-pill { display: flex; align-items: center; gap: 0.35rem; font-size: 0.75rem; font-weight: 500; padding: 0.25rem 0.625rem; border-radius: 999px; white-space: nowrap; flex-shrink: 0; }
.status-pill.ok { background: #f0fdf4; color: #16a34a; }
.status-pill.warn { background: #fffbeb; color: #d97706; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.provider-desc { font-size: 0.8125rem; color: #6b7280; line-height: 1.5; margin: 0; }
.credential-row, .url-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: #6b7280; }
.env-var { background: #f3f4f6; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.75rem; color: #374151; }
.cred-status { font-weight: 600; }
.cred-status.set { color: #16a34a; }
.cred-status.missing { color: #dc2626; }
.base-url { font-size: 0.75rem; color: #9ca3af; word-break: break-all; }

.models-section { display: flex; flex-direction: column; gap: 0.4rem; }
.models-label { font-size: 0.75rem; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; margin: 0; }
.models-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.model-chip { background: #f3f4f6; color: #374151; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 6px; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.no-models { font-size: 0.8125rem; color: #d1d5db; font-style: italic; }

.card-footer { display: flex; align-items: center; justify-content: flex-end; gap: 0.75rem; margin-top: auto; padding-top: 0.5rem; border-top: 1px solid #f3f4f6; }
.test-btn { display: flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0.875rem; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; color: #374151; font-size: 0.8125rem; cursor: pointer; transition: all 0.15s; white-space: nowrap; flex-shrink: 0; }
.test-btn:hover:not(:disabled) { background: #f9fafb; border-color: #d1d5db; }
.test-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.refresh-row { margin-top: 1rem; display: flex; justify-content: flex-end; }
.refresh-btn { display: flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0.875rem; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; color: #6b7280; font-size: 0.8125rem; cursor: pointer; transition: all 0.15s; }
.refresh-btn:hover:not(:disabled) { background: #f9fafb; color: #374151; }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
