<template>
  <div class="provider-selector-section">
    <!-- Label row -->
    <div class="selector-header">
      <label class="selector-label">AI Provider</label>
    </div>

    <!-- Custom dropdown trigger -->
    <div class="dropdown-wrapper" ref="wrapperRef">
      <button
        type="button"
        class="dropdown-trigger"
        :class="{ open: isOpen, disabled: disabled }"
        :disabled="disabled"
        @click="toggleDropdown"
      >
        <span class="trigger-text" :class="{ placeholder: !selectedProvider }">
          {{ selectedLabel }}
        </span>
        <svg
          class="chevron"
          :class="{ rotated: isOpen }"
          xmlns="http://www.w3.org/2000/svg"
          width="16" height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="m6 9 6 6 6-6"></path>
        </svg>
      </button>

      <!-- Dropdown list — always renders below the trigger -->
      <Transition name="dropdown">
        <ul v-if="isOpen" class="dropdown-list" role="listbox">
          <li
            class="dropdown-item placeholder-item"
            :class="{ selected: !selectedProvider }"
            @click="selectProvider('')"
            role="option"
          >
            <span>Select a provider…</span>
          </li>
          <li
            v-for="provider in configuredProviders"
            :key="provider.id"
            class="dropdown-item"
            :class="{ selected: selectedProvider === provider.id }"
            @click="selectProvider(provider.id)"
            role="option"
          >
            <span class="item-name">{{ provider.name }}</span>
            <span class="item-badge" :class="provider.type">
              {{ provider.type === 'cloud' ? '☁' : '🖥' }} {{ provider.type }}
            </span>
          </li>
        </ul>
      </Transition>
    </div>

    <!-- No providers warning -->
    <div v-if="configuredProviders.length === 0" class="warning-message">
      <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span>No providers configured. <a href="#" @click.prevent="activeView = 'settings'" class="settings-link">Configure in Settings</a></span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Provider {
  id: string
  name: string
  type: string
  configured: boolean
}

interface Props {
  providers: Provider[]
  modelValue?: string
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isOpen = ref(false)
const wrapperRef = ref<HTMLElement | null>(null)

const selectedProvider = computed({
  get: () => props.modelValue || '',
  set: (value: string) => emit('update:modelValue', value),
})

const configuredProviders = computed(() => props.providers.filter(p => p.configured))

const selectedLabel = computed(() => {
  if (!selectedProvider.value) return 'Select a provider…'
  const found = configuredProviders.value.find(p => p.id === selectedProvider.value)
  return found ? found.name : 'Select a provider…'
})

const toggleDropdown = () => {
  if (!props.disabled) isOpen.value = !isOpen.value
}

const selectProvider = (id: string) => {
  selectedProvider.value = id
  isOpen.value = false
}

// Close on outside click
onMounted(() => {
  const handler = (e: MouseEvent) => {
    if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
      isOpen.value = false
    }
  }
  document.addEventListener('mousedown', handler)
  onUnmounted(() => document.removeEventListener('mousedown', handler))
})
</script>

<style scoped>
.provider-selector-section {
  margin-bottom: 1.25rem;
}

/* Label row */
.selector-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.selector-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.help-icon {
  display: flex;
  align-items: center;
  color: #9ca3af;
  cursor: help;
}
.help-icon:hover { color: #6b7280; }

/* Wrapper — position: relative so the list anchors below */
.dropdown-wrapper {
  position: relative;
}

/* Trigger button */
.dropdown-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 0.875rem;
  background: #fff;
  border: 1.5px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  color: #111827;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  text-align: left;
  gap: 0.5rem;
}

.dropdown-trigger:hover:not(.disabled) {
  border-color: #9ca3af;
}

.dropdown-trigger.open {
  border-color: #FF6F3C;
  box-shadow: 0 0 0 3px rgba(255, 111, 60, 0.12);
}

.dropdown-trigger.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f9fafb;
}

.trigger-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trigger-text.placeholder {
  color: #9ca3af;
}

/* Chevron — always vertically centered via flex on parent */
.chevron {
  flex-shrink: 0;
  color: #6b7280;
  transition: transform 0.2s ease;
}
.chevron.rotated {
  transform: rotate(180deg);
}

/* Dropdown list */
.dropdown-list {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 200;
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  list-style: none;
  margin: 0;
  padding: 0.25rem;
  max-height: 220px;
  overflow-y: auto;
}

/* Items */
.dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #374151;
  cursor: pointer;
  transition: background 0.1s;
}

.dropdown-item:hover {
  background: #fff3ee;
  color: #FF6F3C;
}

.dropdown-item.selected {
  background: #fff3ee;
  color: #FF6F3C;
  font-weight: 600;
}

.placeholder-item {
  color: #9ca3af;
  font-style: italic;
}
.placeholder-item:hover {
  background: #f9fafb;
  color: #6b7280;
}
.placeholder-item.selected {
  background: transparent;
  color: #9ca3af;
  font-weight: 400;
}

.item-name {
  flex: 1;
}

.item-badge {
  font-size: 0.75rem;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  white-space: nowrap;
  flex-shrink: 0;
}
.item-badge.cloud { background: #eff6ff; color: #3b82f6; }
.item-badge.local { background: #f0fdf4; color: #16a34a; }

/* Transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Warning */
.warning-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  color: #92400e;
}
.warning-message svg { flex-shrink: 0; color: #f59e0b; }
.settings-link { color: #92400e; text-decoration: underline; font-weight: 500; }
.settings-link:hover { color: #78350f; }
</style>
