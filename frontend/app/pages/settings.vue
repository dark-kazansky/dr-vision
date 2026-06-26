<template>
  <div class="settings-page">
    <!-- Top Bar -->
    <div class="top-bar">
      <div class="logo logo-clickable">
        <img src="/assets/logo.png" alt="Doc Intelligence" class="logo-icon" @click="navigateTo('/')" />
        <span class="logo-text" @click="navigateTo('/')">Doc Intelligence</span>
      </div>
      <div class="top-bar-actions">
        <button class="top-bar-btn" @click="navigateTo('/')">
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back
        </button>
      </div>
    </div>

    <div class="settings-layout">
      <!-- Sidebar nav -->
      <aside class="settings-sidebar">
        <nav class="settings-nav">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="settings-nav-item"
            :class="{ active: activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </nav>
      </aside>

      <!-- Main content -->
      <main class="settings-main">
        <ProvidersTab
          v-if="activeTab === 'providers'"
          :providers="providers"
          :is-loading="isLoading"
          :error="error"
          :testing-provider="testingProvider"
          @fetch="fetchProviders"
          @test="testConnection"
        />
        <TierConfigTab
          v-if="activeTab === 'tiers'"
          :tier-config="tierConfig"
        />
        <JobQueueTab v-if="activeTab === 'queue'" />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import ProvidersTab from '~/components/settings/ProvidersTab.vue'
import TierConfigTab from '~/components/settings/TierConfigTab.vue'
import JobQueueTab from '~/components/settings/JobQueueTab.vue'

const { providers, isLoading, error, testingProvider, fetchProviders, testConnection } = useProviders()
const { tierConfig, fetchTierConfig } = useTierConfig()

const activeTab = ref<'providers' | 'tiers' | 'queue'>('providers')

const tabs: { id: 'providers' | 'tiers' | 'queue'; label: string }[] = [
  { id: 'providers', label: 'Providers' },
  { id: 'tiers', label: 'Tier Config' },
  { id: 'queue', label: 'Job Queue' },
]

onMounted(async () => {
  await Promise.all([fetchProviders(), fetchTierConfig()])
})
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  background: #f9fafb;
  display: flex;
  flex-direction: column;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 52px;
  background: #1a1a2e;
  border-bottom: 1px solid #2d2d44;
  flex-shrink: 0;
}

.logo { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.logo-icon { width: 28px; height: 28px; border-radius: 6px; }
.logo-text { color: #fff; font-weight: 600; font-size: 1rem; }

.top-bar-actions { display: flex; align-items: center; gap: 8px; }
.top-bar-btn {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.4rem 0.9rem;
  background: transparent; border: 1px solid #3d3d5c;
  border-radius: 6px; color: #c4c4d4; font-size: 0.8125rem;
  cursor: pointer; transition: all 0.15s;
}
.top-bar-btn:hover { background: #2d2d44; color: #fff; }

.settings-layout {
  display: flex;
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  padding: 2rem 1.5rem;
  gap: 2rem;
}

.settings-sidebar { width: 200px; flex-shrink: 0; }
.settings-nav { display: flex; flex-direction: column; gap: 0.25rem; }
.settings-nav-item {
  display: flex; align-items: center; gap: 0.6rem;
  padding: 0.6rem 0.875rem;
  background: transparent; border: none; border-radius: 8px;
  color: #6b7280; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; text-align: left; transition: all 0.15s;
}
.settings-nav-item:hover { background: #f3f4f6; color: #111827; }
.settings-nav-item.active { background: #fff3ee; color: #FF6F3C; font-weight: 600; }

.settings-main { flex: 1; min-width: 0; }
</style>
