<script setup lang="ts">
/**
 * Node Sidebar Panel
 * 
 * Left sidebar with categorized node types.
 * Supports drag-to-canvas and search filtering.
 */
import type { NodeCategory, NodeTypeDefinition } from '~/types/workflow'
import { useNodeRegistry } from '~/composables/workflow/useNodeRegistry'

const emit = defineEmits<{
  (e: 'drag-start', event: DragEvent, nodeType: string): void
}>()

const { getNodeTypes, getCategories, searchNodes } = useNodeRegistry()

const searchQuery = ref('')
const expandedCategories = ref<Set<NodeCategory>>(new Set(['input', 'processing', 'ai', 'logic', 'output']))

const categories = getCategories()

const filteredNodes = computed(() => {
  if (searchQuery.value.trim()) {
    return searchNodes(searchQuery.value)
  }
  return getNodeTypes()
})

const nodesByCategory = computed(() => {
  const grouped = new Map<NodeCategory, NodeTypeDefinition[]>()
  for (const node of filteredNodes.value) {
    const list = grouped.get(node.category) || []
    list.push(node)
    grouped.set(node.category, list)
  }
  return grouped
})

const toggleCategory = (category: NodeCategory) => {
  if (expandedCategories.value.has(category)) {
    expandedCategories.value.delete(category)
  } else {
    expandedCategories.value.add(category)
  }
}

const onDragStart = (event: DragEvent, nodeType: string) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/workflow-node', nodeType)
    event.dataTransfer.effectAllowed = 'move'
  }
  emit('drag-start', event, nodeType)
}
</script>

<template>
  <aside class="node-sidebar">
    <div class="sidebar-header">
      <h3 class="sidebar-title">Nodes</h3>
    </div>

    <!-- Search -->
    <div class="sidebar-search">
      <svg class="search-icon" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search nodes..."
        class="search-input"
      />
    </div>

    <!-- Categories -->
    <div class="sidebar-categories">
      <div
        v-for="(meta, category) in categories"
        :key="category"
        class="category-section"
      >
        <button
          class="category-header"
          @click="toggleCategory(category as NodeCategory)"
          :class="{ expanded: expandedCategories.has(category as NodeCategory) }"
        >
          <span class="category-icon">{{ meta.icon }}</span>
          <span class="category-label">{{ meta.label }}</span>
          <span class="category-count">{{ nodesByCategory.get(category as NodeCategory)?.length || 0 }}</span>
          <svg class="chevron" width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>

        <div
          v-if="expandedCategories.has(category as NodeCategory)"
          class="category-nodes"
        >
          <div
            v-for="node in nodesByCategory.get(category as NodeCategory) || []"
            :key="node.type"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, node.type)"
            :title="node.description"
          >
            <span class="node-item-icon">{{ node.icon }}</span>
            <div class="node-item-info">
              <span class="node-item-label">{{ node.label }}</span>
              <span class="node-item-desc">{{ node.description }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.node-sidebar {
  width: 260px;
  min-width: 260px;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px 16px 12px;
  border-bottom: 1px solid #f3f4f6;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.sidebar-search {
  padding: 12px 16px;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 28px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
}

.search-input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.search-input:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
}

.sidebar-categories {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.category-section {
  margin-bottom: 2px;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  transition: background 0.15s;
}

.category-header:hover {
  background: #f9fafb;
}

.category-icon {
  font-size: 14px;
}

.category-label {
  flex: 1;
  text-align: left;
}

.category-count {
  font-size: 11px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 10px;
}

.chevron {
  transition: transform 0.2s;
  color: #9ca3af;
}

.category-header.expanded .chevron {
  transform: rotate(90deg);
}

.category-nodes {
  padding: 4px 12px 8px;
}

.node-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: grab;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.node-item:hover {
  background: #f3f4f6;
  border-color: #e5e7eb;
}

.node-item:active {
  cursor: grabbing;
  opacity: 0.7;
}

.node-item-icon {
  font-size: 18px;
  line-height: 1;
  margin-top: 1px;
}

.node-item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.node-item-label {
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
}

.node-item-desc {
  font-size: 11px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
