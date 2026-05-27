<script setup lang="ts">
/**
 * Context Menu Component
 * 
 * Right-click context menu for nodes, edges, and canvas.
 */
import type { ContextMenuItem } from '~/types/workflow'

const props = defineProps<{
  visible: boolean
  x: number
  y: number
  items: ContextMenuItem[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'action', item: ContextMenuItem): void
}>()

const menuRef = ref<HTMLElement | null>(null)

const onAction = (item: ContextMenuItem) => {
  if (item.disabled) return
  item.action?.()
  emit('action', item)
  emit('close')
}

// Close on click outside
const onClickOutside = (event: MouseEvent) => {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      ref="menuRef"
      class="context-menu"
      :style="{ left: `${x}px`, top: `${y}px` }"
    >
      <template v-for="item in items" :key="item.id">
        <div v-if="item.separator" class="menu-separator"></div>
        <button
          v-else
          class="menu-item"
          :class="{ disabled: item.disabled, danger: item.danger }"
          @click="onAction(item)"
        >
          <span v-if="item.icon" class="menu-icon">{{ item.icon }}</span>
          <span class="menu-label">{{ item.label }}</span>
          <span v-if="item.shortcut" class="menu-shortcut">{{ item.shortcut }}</span>
        </button>
      </template>
    </div>
  </Teleport>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 9999;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12);
  padding: 4px;
  min-width: 180px;
  animation: fadeIn 0.1s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: #374151;
  text-align: left;
  transition: background 0.1s;
}

.menu-item:hover:not(.disabled) {
  background: #f3f4f6;
}

.menu-item.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.menu-item.danger {
  color: #dc2626;
}

.menu-item.danger:hover:not(.disabled) {
  background: #fef2f2;
}

.menu-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
}

.menu-label {
  flex: 1;
}

.menu-shortcut {
  font-size: 11px;
  color: #9ca3af;
  font-family: 'SF Mono', monospace;
}

.menu-separator {
  height: 1px;
  background: #e5e7eb;
  margin: 4px 8px;
}
</style>
