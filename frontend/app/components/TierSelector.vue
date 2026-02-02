<template>
  <div class="config-section">
    <div class="config-header">
      <span class="config-label">{{ label }}</span>
    </div>
    <div class="tier-selector">
      <div class="tier-bars">
        <button 
          class="tier-bar rapid" 
          @click="$emit('update:modelValue', 'Rapid')" 
          :disabled="disabled"
        ></button>
        <button 
          class="tier-bar normal" 
          @click="$emit('update:modelValue', 'Normal')" 
          :disabled="disabled"
        ></button>
        <button 
          class="tier-bar advance" 
          @click="$emit('update:modelValue', 'Advance')" 
          :disabled="disabled"
        ></button>
      </div>
      <div class="tier-labels">
        <button
          v-for="tier in tiers"
          :key="tier"
          class="tier-label-btn"
          :class="{ active: modelValue === tier }"
          @click="$emit('update:modelValue', tier)"
          :disabled="disabled"
        >
          <div class="tier-indicator"></div>
          <span class="tier-label-text">{{ tier }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  modelValue: string
  label: string
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string): void
}

defineProps<Props>()
defineEmits<Emits>()

const tiers = ['Rapid', 'Normal', 'Advance']
</script>

<style scoped>
.config-section {
  margin-bottom: 1.25rem;
  width: 100%;
  box-sizing: border-box;
}

.config-header {
  margin-bottom: 0.75rem;
}

.config-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #4a5568;
}

.tier-selector {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  width: 100%;
}

.tier-bars {
  display: flex;
  gap: 3px;
  height: 0.5rem;
}

.tier-bar {
  flex: 1;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.tier-bar:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.tier-bar.rapid {
  background: #FFB399;
}

.tier-bar.normal {
  background: #FF8C5A;
}

.tier-bar.advance {
  background: #FF6F3C;
}

.tier-bar:hover:not(:disabled) {
  opacity: 0.8;
}

.tier-labels {
  display: flex;
  gap: 3px;
  margin-top: 0.25rem;
}

.tier-label-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0.5rem;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
  color: #6b7280;
}

.tier-label-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.tier-label-btn.active {
  color: #111827;
  font-weight: 600;
}

.tier-indicator {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: transparent;
  transition: all 0.15s;
}

.tier-label-btn.active .tier-indicator {
  background-color: var(--accent-orange, #FF6F3C);
}

.tier-label-text {
  font-weight: inherit;
}
</style>
