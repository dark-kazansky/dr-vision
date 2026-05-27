<script setup lang="ts">
/**
 * TierConfigTab — Display tier-to-model mapping table.
 */

defineProps<{
  tierConfig: any
}>()
</script>

<template>
  <section>
    <div class="section-header">
      <h2 class="section-title">Tier Configuration</h2>
      <p class="section-desc">
        Each tier maps to a specific model. Tiers are configured in
        <code>backend/config/tier_config.py</code>.
      </p>
    </div>

    <div v-if="tierConfig" class="tier-table-wrapper">
      <table class="tier-table">
        <thead>
          <tr>
            <th>Feature</th>
            <th v-for="tier in tierConfig.tiers" :key="tier">{{ tier }}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="feature-cell">Parser (OCR)</td>
            <td v-for="tier in tierConfig.tiers" :key="tier">
              <span class="model-tag">{{ tierConfig.parser[tier] ?? '—' }}</span>
            </td>
          </tr>
          <tr>
            <td class="feature-cell">Classifier</td>
            <td v-for="tier in tierConfig.tiers" :key="tier">
              <span class="model-tag">{{ tierConfig.classifier_llm[tier] ?? '—' }}</span>
            </td>
          </tr>
          <tr>
            <td class="feature-cell">Extractor</td>
            <td v-for="tier in tierConfig.tiers" :key="tier">
              <span class="model-tag">{{ tierConfig.extractor[tier] ?? '—' }}</span>
            </td>
          </tr>
          <tr>
            <td class="feature-cell">Splitter</td>
            <td v-for="tier in tierConfig.tiers" :key="tier">
              <span class="model-tag">{{ tierConfig.splitter[tier] ?? '—' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="loading-state">
      <div class="spinner" />
      <span>Loading tier config…</span>
    </div>
  </section>
</template>

<style scoped>
.section-header { margin-bottom: 1.5rem; }
.section-title { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 0.4rem; }
.section-desc { font-size: 0.875rem; color: #6b7280; margin: 0; }

.tier-table-wrapper { overflow-x: auto; }
.tier-table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; border: 1px solid #e5e7eb; }
.tier-table th { padding: 0.75rem 1rem; text-align: left; font-size: 0.8125rem; font-weight: 600; color: #6b7280; background: #f9fafb; border-bottom: 1px solid #e5e7eb; }
.tier-table td { padding: 0.75rem 1rem; font-size: 0.875rem; color: #374151; border-bottom: 1px solid #f3f4f6; }
.tier-table tr:last-child td { border-bottom: none; }
.feature-cell { font-weight: 600; color: #111827; }
.model-tag { background: #f3f4f6; color: #374151; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 6px; font-family: monospace; }

.loading-state { display: flex; align-items: center; gap: 0.75rem; padding: 2rem; color: #6b7280; font-size: 0.875rem; }
.spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #FF6F3C; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
