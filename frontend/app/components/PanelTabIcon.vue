<template>
  <!-- Sliders icon for Build tab -->
  <svg v-if="icon === 'sliders'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="21" x2="14" y1="4" y2="4"></line>
    <line x1="10" x2="3" y1="4" y2="4"></line>
    <line x1="21" x2="12" y1="12" y2="12"></line>
    <line x1="8" x2="3" y1="12" y2="12"></line>
    <line x1="21" x2="16" y1="20" y2="20"></line>
    <line x1="12" x2="3" y1="20" y2="20"></line>
    <line x1="14" x2="14" y1="2" y2="6"></line>
    <line x1="8" x2="8" y1="10" y2="14"></line>
    <line x1="16" x2="16" y1="18" y2="22"></line>
  </svg>
  <!-- Document icon for Result tabs -->
  <svg v-else-if="icon === 'document'" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
</template>

<script setup lang="ts">
interface Props {
  icon: 'sliders' | 'document'
}

defineProps<Props>()
</script>
