<template>
  <div class="test-page">
    <div class="container">
      <h1>Schema Builder Test</h1>
      <SchemaBuilder
        v-model="schema"
        @validation-change="handleValidationChange"
      />
      <div class="debug-info">
        <h3>Debug Info</h3>
        <p><strong>Is Valid:</strong> {{ isValid }}</p>
        <p><strong>Schema Length:</strong> {{ schema.length }}</p>
        <pre>{{ JSON.stringify(schema, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SchemaField } from '~/types/extraction'

const schema = ref<SchemaField[]>([
  {
    name: 'invoice_number',
    type: 'string',
    description: 'The invoice number',
    required: true
  },
  {
    name: 'total_amount',
    type: 'number',
    description: 'Total amount',
    required: true
  }
])

const isValid = ref(false)

const handleValidationChange = (valid: boolean) => {
  isValid.value = valid
}
</script>

<style scoped>
.test-page {
  min-height: 100vh;
  background-color: #f7fafc;
  padding: 2rem;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #2d3748;
  margin-bottom: 2rem;
}

.debug-info {
  margin-top: 2rem;
  padding: 1.5rem;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.debug-info h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 1rem;
}

.debug-info p {
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: #4a5568;
}

.debug-info pre {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #f7fafc;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  overflow-x: auto;
}
</style>
