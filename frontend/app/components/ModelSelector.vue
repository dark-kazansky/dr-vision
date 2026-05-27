<template>
  <div class="model-selector-section">
    <!-- Label row -->
    <div class="selector-header">
      <label class="selector-label">{{ label || 'AI Model' }}</label>
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
        <span class="trigger-text" :class="{ placeholder: !selectedModel }">
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

      <!-- Dropdown list -->
      <Transition name="dropdown">
        <ul v-if="isOpen" class="dropdown-list" role="listbox">
          <li
            class="dropdown-item placeholder-item"
            :class="{ selected: !selectedModel }"
            @click="selectModel('')"
            role="option"
          >
            <span>Select a model…</span>
          </li>
          <template v-for="group in groupedModels" :key="group.providerId">
            <li class="dropdown-group-header">
              <span class="group-name">{{ group.providerName }}</span>
              <span class="group-badge" :class="group.providerType">
                {{ group.providerType === 'cloud' ? '☁' : '🖥' }}
              </span>
            </li>
            <li
              v-for="model in group.models"
              :key="model.model_id"
              class="dropdown-item model-item"
              :class="{ selected: selectedModel === model.model_id }"
              @click="selectModel(model.model_id)"
              role="option"
            >
              <span class="item-name">{{ model.name }}</span>
            </li>
          </template>
        </ul>
      </Transition>
    </div>

    <!-- No models warning -->
    <div v-if="allModels.length === 0" class="warning-message">
      <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span>No models available. Configure providers in Settings.</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface ProviderModel {
  model_id: string
  name: string
  provider: string
}

interface Provider {
  id: string
  name: string
  type: string
  configured: boolean
  models: ProviderModel[]
}

interface Props {
  providers: Provider[]
  modelValue?: string
  disabled?: boolean
  label?: string
}

interface Emits {
  (e: 'update:modelValue', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isOpen = ref(false)
const wrapperRef = ref<HTMLElement | null>(null)

const selectedModel = computed({
  get: () => props.modelValue || '',
  set: (value: string) => emit('update:modelValue', value),
})

// Flatten all models from configured providers
const allModels = computed(() => {
  const models: (ProviderModel & { providerName: string; providerType: string })[] = []
  for (const provider of props.providers) {
    if (!provider.configured) continue
    for (const model of provider.models) {
      models.push({
        ...model,
        providerName: provider.name,
        providerType: provider.type,
      })
    }
  }
  return models
})

// Group models by provider for display
const groupedModels = computed(() => {
  const groups: { providerId: string; providerName: string; providerType: string; models: ProviderModel[] }[] = []
  for (const provider of props.providers) {
    if (!provider.configured || provider.models.length === 0) continue
    groups.push({
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      models: provider.models,
    })
  }
  return groups
})

const selectedLabel = computed(() => {
  if (!selectedModel.value) return 'Select a model…'
  const found = allModels.value.find(m => m.model_id === selectedModel.value)
  return found ? `${found.name}` : selectedModel.value
})

const toggleDropdown = () => {
  if (!props.disabled) isOpen.value = !isOpen.value
}

const selectModel = (modelId: string) => {
  selectedModel.value = modelId
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
.model-selector-section {
  margin-bottom: 1.25rem;
}

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

.dropdown-wrapper {
  position: relative;
}

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

.chevron {
  flex-shrink: 0;
  color: #6b7280;
  transition: transform 0.2s ease;
}
.chevron.rotated {
  transform: rotate(180deg);
}

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
  max-height: 300px;
  overflow-y: auto;
}

.dropdown-group-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.75rem 0.25rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  pointer-events: none;
}

.group-name {
  flex: 1;
}

.group-badge {
  font-size: 0.7rem;
}

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

.dropdown-item.model-item {
  padding-left: 1.25rem;
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
</style>
