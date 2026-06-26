<template>
  <div class="schema-builder">
    <div class="schema-header">
      <label class="config-label">
        Extraction Schema
      </label>
      <div v-if="flattenedSchema.length > 0" class="header-actions">
        <div class="view-toggle-group">
          <button
            @click="viewMode = 'visual'"
            :class="viewMode === 'visual' ? 'view-toggle-btn active' : 'view-toggle-btn'"
            type="button"
            :disabled="disabled"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="toggle-icon">
              <path d="M12 3v18"></path>
              <rect width="18" height="18" x="3" y="3" rx="2"></rect>
              <path d="M3 9h18"></path>
              <path d="M3 15h18"></path>
            </svg>
          </button>
          <button
            @click="viewMode = 'code'"
            :class="viewMode === 'code' ? 'view-toggle-btn active' : 'view-toggle-btn'"
            type="button"
            :disabled="disabled"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="toggle-icon">
              <path d="m18 16 4-4-4-4"></path>
              <path d="m6 8-4 4 4 4"></path>
              <path d="m14.5 4-5 16"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div v-if="flattenedSchema.length === 0 && !showAutoGenerate" class="empty-state">
      <p>No fields defined. The schema will start empty.</p>
      <button
        @click="showAutoGenerate = true"
        :disabled="disabled"
        class="auto-generate-button"
        type="button"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
          <path d="M13.5 8c-.28 0-.5.22-.5.5s.22.5.5.5.5-.22.5-.5-.22-.5-.5-.5zm-3 0c-.28 0-.5.22-.5.5s.22.5.5.5.5-.22.5-.5-.22-.5-.5-.5z"/>
        </svg>
        Auto Generate
      </button>
      <button
        @click="addField"
        :disabled="disabled"
        class="add-first-field-button"
        type="button"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Create Manually
      </button>
    </div>

    <!-- Auto-Generate Schema View -->
    <div v-if="showAutoGenerate && flattenedSchema.length === 0" class="auto-generate-view">
      <h3 class="auto-generate-title">Auto-Generate Schema</h3>
      <p class="auto-generate-subtitle">Provide a file, prompt, or both to generate your schema.</p>
      
      <div class="file-upload-hint">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
        </svg>
        <span v-if="props.selectedFile">Using file: {{ props.selectedFile.name }}</span>
        <span v-else>Upload a file in the preview to use for schema generation</span>
      </div>
      
      <div class="prompt-section">
        <label class="prompt-label">Schema Generation Prompt</label>
        <textarea
          v-model="autoGeneratePrompt"
          :disabled="disabled || isGenerating"
          class="prompt-textarea"
          placeholder="Describe the structure you want to extract (e.g., 'Extract person information including name, age, and contact details')"
          rows="4"
        ></textarea>
      </div>
      
      <!-- Error message -->
      <div v-if="generateError" class="generate-error">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <span>{{ generateError }}</span>
      </div>
      
      <div class="auto-generate-actions">
        <button
          @click="handleBackFromAutoGenerate"
          :disabled="disabled || isGenerating"
          class="back-button"
          type="button"
        >
          Back
        </button>
        <button
          @click="handleGenerateSchema"
          :disabled="disabled || !autoGeneratePrompt.trim() || isGenerating"
          class="generate-button"
          type="button"
        >
          <svg v-if="isGenerating" class="spinner" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ isGenerating ? 'Generating...' : 'Generate' }}
        </button>
      </div>
    </div>

    <!-- Visual View -->
    <div v-else-if="viewMode === 'visual' && flattenedSchema.length > 0" class="table-container">
      <table class="schema-table">
        <thead>
          <tr>
            <th class="hierarchy-header"></th>
            <th>Field Name</th>
            <th>Field Type</th>
            <th>Field Description</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(field, index) in flattenedSchema" :key="index">
            <tr class="schema-row">
              <td class="hierarchy-cell">
                <div class="hierarchy-controls" :style="{ paddingLeft: `${(field.level || 0) * 1.5}rem` }">
                  <button
                    type="button"
                    class="add-field-inline"
                    :disabled="disabled"
                    @click="addFieldAfter(index)"
                    title="Add field below"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button
                    v-if="field.type === 'object'"
                    type="button"
                    class="expand-toggle"
                    :class="{ expanded: field.expanded }"
                    :disabled="disabled"
                    @click="toggleExpand(index)"
                    title="Expand/collapse children"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </td>
              <td>
                <div class="field-input-container">
                  <input
                    v-model="field.name"
                    type="text"
                    placeholder="Enter field name"
                    :disabled="disabled"
                    class="field-input"
                    @input="handleFieldChange"
                  />
                </div>
              </td>
              <td>
                <select
                  v-model="field.type"
                  :disabled="disabled"
                  class="field-select"
                  @change="handleTypeChange(index)"
                >
                  <option value="string">String</option>
                  <option value="number">Number</option>
                  <option value="boolean">Boolean</option>
                  <option value="date">Date</option>
                  <option value="object">Object</option>
                </select>
              </td>
              <td>
                <input
                  v-model="field.description"
                  type="text"
                  placeholder="Enter description"
                  :disabled="disabled"
                  class="field-input"
                  @input="handleFieldChange"
                />
              </td>
              <td class="action-cell">
                <div class="action-buttons">
                  <button
                    v-if="(field.level || 0) > 0"
                    type="button"
                    class="outdent-button"
                    :disabled="disabled"
                    @click="outdentField(index)"
                    title="Move to same level as parent"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M7.707 14.707a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l2.293 2.293a1 1 0 010 1.414z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button
                    v-if="index > 0 && canIndent(index)"
                    type="button"
                    class="indent-button"
                    :disabled="disabled"
                    @click="indentField(index)"
                    title="Make child of field above"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M12.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-2.293-2.293a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="required-toggle"
                    :class="{ active: field.required }"
                    :disabled="disabled"
                    @click="toggleRequired(index)"
                    title="Click to toggle required/optional"
                  >
                    *
                  </button>
                  <!-- Warning icon if field has errors -->
                  <div v-if="hasErrors(index)" class="warning-icon" :title="getErrors(index).join(', ')">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <button
                    @click="removeField(index)"
                    :disabled="disabled"
                    class="remove-button"
                    type="button"
                    title="Remove field"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Code View -->
    <div v-else-if="viewMode === 'code' && flattenedSchema.length > 0" class="code-container">
      <div v-if="jsonError" class="json-error">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <span>{{ jsonError }}</span>
      </div>
      <textarea
        v-model="jsonText"
        @input="handleJsonInput"
        :disabled="disabled"
        class="json-editor"
        :class="{ 'has-error': jsonError }"
        spellcheck="false"
      ></textarea>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SchemaField, FieldType } from '~/types/extraction'

interface Props {
  modelValue: SchemaField[]
  disabled?: boolean
  selectedFile?: File | null
}

interface Emits {
  (e: 'update:modelValue', schema: SchemaField[]): void
  (e: 'validation-change', isValid: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// View mode state
const viewMode = ref<'visual' | 'code'>('visual')

// Local copy of schema for editing
const localSchema = ref<SchemaField[]>([...props.modelValue])

// Flattened schema for display (includes all nested fields)
const flattenedSchema = ref<SchemaField[]>([])

// JSON text for code view
const jsonText = ref<string>('')

// JSON validation error
const jsonError = ref<string>('')

// Validation errors for each field
const validationErrors = ref<Map<number, string[]>>(new Map())

// Auto-generate state
const showAutoGenerate = ref(false)
const autoGeneratePrompt = ref('')
const isGenerating = ref(false)
const generateError = ref('')

// Flatten schema for display
const flattenSchema = (schema: SchemaField[], level: number = 0, parentExpanded: boolean = true): SchemaField[] => {
  const result: SchemaField[] = []
  
  for (const field of schema) {
    // Set level and ensure expanded state is defined
    const flatField = {
      ...field,
      level: level,
      expanded: field.expanded !== undefined ? field.expanded : true,
      hasChildren: field.type === 'object' && field.properties && field.properties.length > 0
    }
    
    // Always add the field itself if parent is expanded
    if (parentExpanded) {
      result.push(flatField)
      
      // Recursively flatten children if field is object type and has properties
      if (field.type === 'object' && field.properties && field.properties.length > 0) {
        // Pass this field's expanded state to determine if children should be shown
        const childrenFlattened = flattenSchema(field.properties, level + 1, flatField.expanded)
        result.push(...childrenFlattened)
      }
    }
  }
  
  return result
}

// Unflatten schema for storage (convert flat list back to nested structure)
const unflattenSchema = (flat: SchemaField[]): SchemaField[] => {
  const result: SchemaField[] = []
  const stack: { level: number; parent: SchemaField[] }[] = [{ level: -1, parent: result }]
  
  for (const field of flat) {
    const level = field.level || 0
    
    // Pop stack until we find the right parent level
    while (stack.length > 0 && (stack[stack.length - 1]!.level || 0) >= level) {
      stack.pop()
    }

    const parent = stack.length > 0 ? stack[stack.length - 1]!.parent : null
    
    // Create clean field without UI-specific properties
    const cleanField: SchemaField = {
      name: field.name,
      type: field.type,
      description: field.description,
      required: field.required
    }
    
    // If field is object type, initialize properties array and preserve expanded state
    if (field.type === 'object') {
      cleanField.properties = []
      cleanField.expanded = field.expanded !== undefined ? field.expanded : true
      stack.push({ level, parent: cleanField.properties })
    }
    
    if (parent) parent.push(cleanField)
  }

  return result
}

// Update flattened schema whenever local schema changes
const updateFlattenedSchema = () => {
  flattenedSchema.value = flattenSchema(localSchema.value)
}

// Watch for external changes to modelValue
watch(() => props.modelValue, (newValue) => {
  localSchema.value = [...newValue]
  updateJsonText()
  validateSchema()
}, { deep: true })

// Watch for view mode changes to sync JSON
watch(viewMode, (newMode) => {
  if (newMode === 'code') {
    updateJsonText()
  }
})

// Update JSON text from schema
const updateJsonText = () => {
  try {
    jsonText.value = JSON.stringify(localSchema.value, null, 2)
    jsonError.value = ''
  } catch (error) {
    jsonError.value = 'Failed to serialize schema to JSON'
  }
}

// Handle JSON input in code view
const handleJsonInput = () => {
  // Clear any previous errors
  let hasError = false
  
  try {
    // Handle empty input
    if (!jsonText.value || jsonText.value.trim() === '') {
      jsonError.value = 'JSON cannot be empty'
      return
    }
    
    const parsed = JSON.parse(jsonText.value)
    
    // Validate that parsed data is an array
    if (!Array.isArray(parsed)) {
      jsonError.value = 'Schema must be an array of field objects'
      return
    }
    
    // Handle empty array
    if (parsed.length === 0) {
      jsonError.value = 'Schema must contain at least one field'
      return
    }
    
    // Validate each field has required properties
    for (let i = 0; i < parsed.length; i++) {
      const field = parsed[i]
      
      // Check if field is an object
      if (typeof field !== 'object' || field === null) {
        jsonError.value = `Field at index ${i} must be an object`
        return
      }
      
      // Validate name property
      if (!field.name || typeof field.name !== 'string') {
        jsonError.value = `Field at index ${i} is missing or has invalid 'name' property`
        return
      }
      
      // Validate name is not empty after trimming
      if (field.name.trim() === '') {
        jsonError.value = `Field at index ${i} has an empty 'name' property`
        return
      }
      
      // Validate type property
      if (!field.type || !['string', 'number', 'boolean', 'date'].includes(field.type)) {
        jsonError.value = `Field at index ${i} has invalid 'type' property. Must be one of: string, number, boolean, date`
        return
      }
      
      // Validate description is a string if present
      if (field.description !== undefined && typeof field.description !== 'string') {
        jsonError.value = `Field at index ${i} has invalid 'description' property. Must be a string`
        return
      }
      
      // Validate required is a boolean if present
      if (field.required !== undefined && typeof field.required !== 'boolean') {
        jsonError.value = `Field at index ${i} has invalid 'required' property. Must be a boolean`
        return
      }
      
      // Set defaults for optional properties
      if (field.description === undefined) {
        field.description = ''
      }
      if (field.required === undefined) {
        field.required = false
      }
    }
    
    // Check for duplicate field names
    const fieldNames = parsed.map((f: any) => f.name.trim().toLowerCase())
    const uniqueNames = new Set(fieldNames)
    if (fieldNames.length !== uniqueNames.size) {
      jsonError.value = 'Schema contains duplicate field names'
      return
    }
    
    // Valid JSON - clear error and update schema
    jsonError.value = ''
    localSchema.value = parsed as SchemaField[]
    validateSchema()
    emit('update:modelValue', [...localSchema.value])
  } catch (error) {
    if (error instanceof SyntaxError) {
      jsonError.value = `Invalid JSON syntax: ${error.message}`
    } else {
      jsonError.value = 'Failed to parse JSON'
    }
    // Don't update schema when there's an error
  }
}

// Validate a single field and return errors
const validateField = (field: SchemaField, index: number): string[] => {
  const errors: string[] = []
  
  // Check if field name is empty
  if (!field.name || field.name.trim() === '') {
    errors.push('Field name cannot be empty')
  }
  
  // Check if field name is unique within the flattened schema
  const duplicateIndex = flattenedSchema.value.findIndex((f, i) => 
    i !== index && f.name.trim().toLowerCase() === field.name.trim().toLowerCase()
  )
  if (duplicateIndex !== -1 && field.name.trim() !== '') {
    errors.push('Field name must be unique')
  }
  
  return errors
}

// Validate entire schema
const validateSchema = () => {
  const newErrors = new Map<number, string[]>()
  
  flattenedSchema.value.forEach((field, index) => {
    const errors = validateField(field, index)
    if (errors.length > 0) {
      newErrors.set(index, errors)
    }
  })
  
  validationErrors.value = newErrors
  
  // Emit validation state
  // Schema is valid if there are no errors and at least one field exists
  const isValid = newErrors.size === 0 && flattenedSchema.value.length > 0
  emit('validation-change', isValid)
}

// Check if a specific field has errors
const hasErrors = (index: number): boolean => {
  return validationErrors.value.has(index)
}

// Get errors for a specific field
const getErrors = (index: number): string[] => {
  return validationErrors.value.get(index) || []
}

const addField = () => {
  const newField: SchemaField = {
    name: '',
    type: 'string',
    description: '',
    required: false,
    level: 0
  }
  localSchema.value.push(newField)
  updateFlattenedSchema()
  handleFieldChange()
}

const addFieldAfter = (index: number) => {
  const currentField = flattenedSchema.value[index]
  const newField: SchemaField = {
    name: '',
    type: 'string',
    description: '',
    required: false,
    level: currentField?.level || 0
  }
  
  // Insert after current field in flattened array
  flattenedSchema.value.splice(index + 1, 0, newField)
  
  // Rebuild nested structure
  localSchema.value = unflattenSchema(flattenedSchema.value)
  updateFlattenedSchema()
  handleFieldChange()
}

const removeField = (index: number) => {
  // Remove field and all its children
  const field = flattenedSchema.value[index]
  const level = field?.level || 0
  let removeCount = 1

  // Count children to remove
  for (let i = index + 1; i < flattenedSchema.value.length; i++) {
    if ((flattenedSchema.value[i]?.level || 0) > level) {
      removeCount++
    } else {
      break
    }
  }
  
  flattenedSchema.value.splice(index, removeCount)
  localSchema.value = unflattenSchema(flattenedSchema.value)
  updateFlattenedSchema()
  handleFieldChange()
}

const toggleRequired = (index: number) => {
  const field = flattenedSchema.value[index]
  if (field) field.required = !field.required
  localSchema.value = unflattenSchema(flattenedSchema.value)
  updateFlattenedSchema()
  handleFieldChange()
}

const toggleExpand = (index: number) => {
  const field = flattenedSchema.value[index]
  if (!field) return
  const newExpandedState = !field.expanded

  // Update the expanded state in the flattened array
  field.expanded = newExpandedState
  
  // Find and update the corresponding field in the nested structure
  const updateExpandedInNested = (schema: SchemaField[], targetName: string, targetLevel: number, currentLevel: number = 0): boolean => {
    for (const f of schema) {
      if (f.name === targetName && currentLevel === targetLevel) {
        f.expanded = newExpandedState
        return true
      }
      if (f.properties && f.properties.length > 0) {
        if (updateExpandedInNested(f.properties, targetName, targetLevel, currentLevel + 1)) {
          return true
        }
      }
    }
    return false
  }
  
  updateExpandedInNested(localSchema.value, field!.name, field!.level || 0)

  // Re-flatten to show/hide children
  updateFlattenedSchema()
}

const canIndent = (index: number): boolean => {
  if (index === 0) return false
  const currentLevel = flattenedSchema.value[index]!.level || 0
  const prevLevel = flattenedSchema.value[index - 1]!.level || 0
  return currentLevel <= prevLevel
}

const indentField = (index: number) => {
  if (!canIndent(index)) return

  const field = flattenedSchema.value[index]!
  const prevField = flattenedSchema.value[index - 1]!

  // Increase level
  field.level = (prevField.level || 0) + 1

  // Make previous field an object if it isn't already
  if (prevField.type !== 'object') {
    prevField.type = 'object'
  }

  // Update all children of this field
  const currentLevel = field.level - 1
  for (let i = index + 1; i < flattenedSchema.value.length; i++) {
    const childField = flattenedSchema.value[i]!
    if ((childField.level || 0) > currentLevel) {
      childField.level = (childField.level || 0) + 1
    } else {
      break
    }
  }

  localSchema.value = unflattenSchema(flattenedSchema.value)
  updateFlattenedSchema()
  handleFieldChange()
}

const outdentField = (index: number) => {
  const field = flattenedSchema.value[index]!
  if ((field.level || 0) === 0) return

  // Decrease level
  const oldLevel = field.level || 0
  field.level = oldLevel - 1

  // Update all children of this field
  for (let i = index + 1; i < flattenedSchema.value.length; i++) {
    const childField = flattenedSchema.value[i]!
    if ((childField.level || 0) > oldLevel) {
      childField.level = (childField.level || 0) - 1
    } else {
      break
    }
  }

  localSchema.value = unflattenSchema(flattenedSchema.value)
  updateFlattenedSchema()
  handleFieldChange()
}

const handleTypeChange = (index: number) => {
  const field = flattenedSchema.value[index]!

  // If changing to object type, initialize properties if needed
  if (field.type === 'object' && !field.properties) {
    field.expanded = true
  }
  
  // If changing from object type, we keep the children but they'll be hidden
  
  localSchema.value = unflattenSchema(flattenedSchema.value)
  updateFlattenedSchema()
  handleFieldChange()
}

const handleFieldChange = () => {
  // Validate schema
  validateSchema()
  
  // Update JSON text if in code view
  updateJsonText()
  
  // Emit the updated schema
  emit('update:modelValue', [...localSchema.value])
}

// Auto-generate handlers
// Auto-generate handlers
const handleBackFromAutoGenerate = () => {
  showAutoGenerate.value = false
  autoGeneratePrompt.value = ''
  generateError.value = ''
}

const handleGenerateSchema = async () => {
  // Validate prompt is not empty
  if (!autoGeneratePrompt.value.trim()) {
    generateError.value = 'Please enter a prompt to generate the schema.'
    return
  }
  
  isGenerating.value = true
  generateError.value = ''
  
  try {
    // Get API base URL from runtime config
    const config = useRuntimeConfig()
    const apiBaseUrl = config.public.apiBaseUrl as string || 'http://localhost:8882'
    
    // Create FormData for the request
    const formData = new FormData()
    formData.append('prompt', autoGeneratePrompt.value.trim())
    
    // Add file if one is selected
    if (props.selectedFile) {
      formData.append('file', props.selectedFile)
      console.log('Including file in schema generation:', props.selectedFile.name)
    }
    
    console.log('Calling /generate-schema endpoint with prompt:', autoGeneratePrompt.value.trim())
    
    // Make API request to generate schema
    const response = await $fetch<{ success: boolean; schema: SchemaField[] }>(`${apiBaseUrl}/generate-schema`, {
      method: 'POST',
      body: formData
    })
    
    console.log('Schema generation response:', response)
    
    // Validate response structure
    if (!response || typeof response !== 'object') {
      throw new Error('Invalid response format from server')
    }
    
    if (response.success && response.schema && Array.isArray(response.schema) && response.schema.length > 0) {
      // Validate each field has required properties
      const validatedSchema = response.schema.map((field, index) => {
        if (!field.name || typeof field.name !== 'string') {
          throw new Error(`Field at index ${index} has invalid or missing name`)
        }
        if (!field.type || !['string', 'number', 'boolean', 'date', 'object'].includes(field.type)) {
          throw new Error(`Field at index ${index} has invalid type: ${field.type}`)
        }
        
        return {
          name: field.name,
          type: field.type as FieldType,
          description: field.description || '',
          required: field.required || false
        }
      })
      
      // Populate schema with generated fields
      localSchema.value = validatedSchema
      
      // Update flattened schema and validate
      updateFlattenedSchema()
      validateSchema()
      updateJsonText()
      
      // Emit the updated schema
      emit('update:modelValue', [...localSchema.value])
      
      console.log('Schema successfully generated and populated:', localSchema.value)
      
      // Close auto-generate view and transition to table view
      showAutoGenerate.value = false
      autoGeneratePrompt.value = ''
      viewMode.value = 'visual'
    } else if (response.success && (!response.schema || response.schema.length === 0)) {
      generateError.value = 'Schema generation returned no fields. Please try a more detailed prompt or provide a sample file.'
    } else {
      generateError.value = 'Schema generation failed. Please try again with a different prompt.'
    }
    
  } catch (error: any) {
    console.error('Schema generation error:', error)
    
    // Handle different error types with more specific messages
    if (error.data?.detail) {
      // Backend returned a specific error message
      generateError.value = error.data.detail
    } else if (error.statusCode === 400) {
      generateError.value = 'Invalid request. Please check your prompt and try again.'
    } else if (error.statusCode === 413) {
      generateError.value = 'File size is too large. Please use a smaller file.'
    } else if (error.statusCode === 500) {
      generateError.value = 'Server error during schema generation. Please try again.'
    } else if (error.statusCode === 504) {
      generateError.value = 'Schema generation timed out. Please try with a simpler prompt or smaller file.'
    } else if (error.message) {
      generateError.value = `Error: ${error.message}`
    } else {
      generateError.value = 'Failed to generate schema. Please check your connection and try again.'
    }
  } finally {
    isGenerating.value = false
  }
}

// Initial validation and JSON sync
onMounted(() => {
  updateFlattenedSchema()
  validateSchema()
  updateJsonText()
})

</script>

<style scoped>
.schema-builder {
  margin-bottom: 1.25rem;
}

.schema-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.view-toggle-group {
  display: flex;
  border-radius: 0.375rem;
  border: 1px solid #e5e7eb;
  background-color: #f9fafb;
  padding: 0.125rem;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  border-radius: 0.25rem;
  padding: 0.375rem;
  transition: all 0.2s;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #6b7280;
}

.view-toggle-btn:hover:not(:disabled) {
  color: #374151;
}

.view-toggle-btn.active {
  background-color: #ffffff;
  color: #111827;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.view-toggle-btn:disabled {
  color: #d1d5db;
  cursor: not-allowed;
}

.toggle-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.config-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #4a5568;
}

.help-icon {
  display: inline-flex;
  align-items: center;
  cursor: help;
  color: #718096;
  transition: color 0.2s;
}

.help-icon:hover {
  color: #4299e1;
}

.help-icon svg {
  width: 1rem;
  height: 1rem;
}

.add-field-button {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  background-color: #4299e1;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.add-field-button:hover:not(:disabled) {
  background-color: #3182ce;
}

.add-field-button:disabled {
  background-color: #a0aec0;
  cursor: not-allowed;
}

.add-field-button svg {
  width: 1rem;
  height: 1rem;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  background-color: #f7fafc;
  border: 2px dashed #cbd5e0;
  border-radius: 0.375rem;
  color: #718096;
  font-size: 0.875rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.auto-generate-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background-color: var(--accent-orange, #FF6F3C);
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.auto-generate-button:hover:not(:disabled) {
  background-color: #E55A2B;
}

.auto-generate-button:disabled {
  background-color: #a0aec0;
  cursor: not-allowed;
}

.auto-generate-button svg {
  width: 1.25rem;
  height: 1.25rem;
}

.add-first-field-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  background-color: white;
  color: #4a5568;
  border: 1px solid #cbd5e0;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.add-first-field-button:hover:not(:disabled) {
  background-color: #f7fafc;
  border-color: #4a5568;
}

.add-first-field-button:disabled {
  background-color: #f7fafc;
  color: #a0aec0;
  cursor: not-allowed;
}

.add-first-field-button svg {
  width: 1.25rem;
  height: 1.25rem;
}

/* Auto-Generate View */
.auto-generate-view {
  padding: 2rem;
  background-color: white;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
}

.auto-generate-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
}

.auto-generate-subtitle {
  margin: 0 0 1.5rem 0;
  font-size: 0.875rem;
  color: #6b7280;
}

.file-upload-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background-color: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  margin-bottom: 1.5rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.file-upload-hint svg {
  flex-shrink: 0;
  color: #9ca3af;
}

.prompt-section {
  margin-bottom: 1.5rem;
}

.prompt-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #2d3748;
}

.prompt-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #cbd5e0;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-family: inherit;
  color: #2d3748;
  background-color: white;
  resize: vertical;
  transition: border-color 0.2s;
}

.prompt-textarea:hover:not(:disabled) {
  border-color: #4299e1;
}

.prompt-textarea:focus {
  outline: none;
  border-color: #4299e1;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}

.prompt-textarea:disabled {
  background-color: #f7fafc;
  cursor: not-allowed;
  opacity: 0.6;
}

.prompt-textarea::placeholder {
  color: #9ca3af;
}

.auto-generate-actions {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.back-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background-color: white;
  color: #4a5568;
  border: 1px solid #cbd5e0;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.back-button:hover:not(:disabled) {
  background-color: #f7fafc;
  border-color: #4a5568;
}

.back-button:disabled {
  background-color: #f7fafc;
  color: #a0aec0;
  cursor: not-allowed;
  opacity: 0.6;
}

.generate-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  background-color: #4299e1;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.generate-button:hover:not(:disabled) {
  background-color: #3182ce;
}

.generate-button:disabled {
  background-color: #a0aec0;
  cursor: not-allowed;
  opacity: 0.6;
}

.table-container {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
}

.schema-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.schema-table thead {
  background-color: #f7fafc;
}

.schema-table th {
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #4a5568;
  border-bottom: 2px solid #e2e8f0;
}

.hierarchy-header {
  width: 6rem;
}

.hierarchy-cell {
  width: 6rem;
  padding: 0.75rem 0;
  text-align: center;
}

.schema-table th:nth-child(2) {
  width: 25%;
}

.schema-table th:nth-child(3) {
  width: 20%;
}

.schema-table th:nth-child(4) {
  width: 35%;
}

.schema-table th:nth-child(5) {
  width: 8rem;
}

.hierarchy-controls {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.add-field-inline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  background-color: transparent;
  color: #4299e1;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.add-field-inline:hover:not(:disabled) {
  background-color: #ebf8ff;
}

.add-field-inline:disabled {
  color: #a0aec0;
  cursor: not-allowed;
}

.add-field-inline svg {
  width: 1.25rem;
  height: 1.25rem;
}

.expand-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  background-color: transparent;
  color: #6b7280;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.expand-toggle:hover:not(:disabled) {
  background-color: #f3f4f6;
}

.expand-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.expand-toggle svg {
  width: 1rem;
  height: 1rem;
  transition: transform 0.2s;
  transform: rotate(-90deg);
}

.expand-toggle.expanded svg {
  transform: rotate(0deg);
}

.schema-table tbody tr {
  border-bottom: 1px solid #e2e8f0;
  transition: background-color 0.2s;
}

.schema-table tbody tr:hover {
  background-color: #f7fafc;
}

.schema-table tbody tr:last-child {
  border-bottom: none;
}

.schema-table td {
  padding: 0.75rem;
  vertical-align: middle;
}

.field-input-container {
  width: 100%;
}

.field-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e0;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #2d3748;
  background-color: white;
  transition: border-color 0.2s;
}

.field-input:hover:not(:disabled) {
  border-color: #4299e1;
}

.field-input:focus {
  outline: none;
  border-color: #4299e1;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}

.field-input:disabled {
  background-color: #f7fafc;
  cursor: not-allowed;
  opacity: 0.6;
}

.field-select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e0;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #2d3748;
  background-color: white;
  cursor: pointer;
  transition: border-color 0.2s;
}

.field-select:hover:not(:disabled) {
  border-color: #4299e1;
}

.field-select:focus {
  outline: none;
  border-color: #4299e1;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
}

.field-select:disabled {
  background-color: #f7fafc;
  cursor: not-allowed;
  opacity: 0.6;
}

.required-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background-color: transparent;
  color: #9ca3af;
  border: none;
  border-radius: 0.375rem;
  font-size: 1.5rem;
  font-weight: normal;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1;
}

.required-toggle:hover:not(:disabled) {
  background-color: #f3f4f6;
}

.required-toggle.active {
  color: #111827;
  font-weight: bold;
  font-style: italic;
}

.required-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.action-cell {
  text-align: right;
  width: 8rem;
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.05rem;
}

.indent-button,
.outdent-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem;
  background-color: transparent;
  color: #6b7280;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.indent-button:hover:not(:disabled),
.outdent-button:hover:not(:disabled) {
  background-color: #f3f4f6;
  color: #4299e1;
}

.indent-button:disabled,
.outdent-button:disabled {
  color: #d1d5db;
  cursor: not-allowed;
}

.indent-button svg,
.outdent-button svg {
  width: 1rem;
  height: 1rem;
}

.remove-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem;
  background-color: transparent;
  color: #e53e3e;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.remove-button:hover:not(:disabled) {
  background-color: #fed7d7;
}

.remove-button:disabled {
  color: #a0aec0;
  cursor: not-allowed;
}

.remove-button svg {
  width: 1.25rem;
  height: 1.25rem;
}

.warning-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem;
  color: #f59e0b;
  cursor: help;
}

.warning-icon svg {
  width: 1.25rem;
  height: 1.25rem;
}

.code-container {
  position: relative;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  overflow: hidden;
}

.json-error {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.875rem;
  background-color: #fef2f2;
  border: 1px solid #fca5a5;
  border-left: 4px solid #dc2626;
  border-radius: 0.375rem;
  color: #991b1b;
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.5;
  margin-bottom: 0.5rem;
}

.json-error svg {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
  color: #dc2626;
  margin-top: 0.125rem;
}

.json-editor {
  width: 100%;
  min-height: 300px;
  padding: 1rem;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'source-code-pro', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #2d3748;
  background-color: #f7fafc;
  border: none;
  resize: vertical;
  outline: none;
  tab-size: 2;
}

.json-editor:focus {
  background-color: white;
}

.json-editor.has-error {
  background-color: #fff5f5;
}

.json-editor:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.generate-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.375rem;
  color: #dc2626;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.generate-error svg {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
}

.spinner {
  width: 1rem;
  height: 1rem;
  animation: spin 1s linear infinite;
  margin-right: 0.5rem;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
