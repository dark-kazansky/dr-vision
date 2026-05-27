/**
 * Composable for workflow builder keyboard shortcuts.
 */
import type { Ref } from 'vue'

interface KeyboardOptions {
  selectedNodes: Ref<string[]>
  selectedEdges: Ref<string[]>
  configNodeId: Ref<string | null>
  removeNodes: (ids: string[]) => void
  removeEdges: (ids: string[]) => void
  undo: () => void
  redo: () => void
  copySelected: () => void
  paste: () => void
  duplicateSelected: () => void
  selectAll: () => void
  clearSelection: () => void
  closeContextMenu: () => void
}

export function useWorkflowKeyboard(opts: KeyboardOptions) {
  const {
    selectedNodes, selectedEdges, configNodeId,
    removeNodes, removeEdges,
    undo, redo, copySelected, paste, duplicateSelected,
    selectAll, clearSelection, closeContextMenu,
  } = opts

  const onKeyDown = (event: KeyboardEvent) => {
    const meta = event.metaKey || event.ctrlKey

    if (event.key === 'Delete' || event.key === 'Backspace') {
      if (selectedNodes.value.length > 0) {
        removeNodes([...selectedNodes.value])
        configNodeId.value = null
      }
      if (selectedEdges.value.length > 0) {
        removeEdges([...selectedEdges.value])
      }
      return
    }

    if (meta && event.key === 'z' && !event.shiftKey) { event.preventDefault(); undo(); return }
    if (meta && event.key === 'z' && event.shiftKey) { event.preventDefault(); redo(); return }
    if (meta && event.key === 'c') { event.preventDefault(); copySelected(); return }
    if (meta && event.key === 'v') { event.preventDefault(); paste(); return }
    if (meta && event.key === 'd') { event.preventDefault(); duplicateSelected(); return }
    if (meta && event.key === 'a') { event.preventDefault(); selectAll(); return }

    if (event.key === 'Escape') {
      clearSelection()
      configNodeId.value = null
      closeContextMenu()
    }
  }

  onMounted(() => { document.addEventListener('keydown', onKeyDown) })
  onUnmounted(() => { document.removeEventListener('keydown', onKeyDown) })

  return { onKeyDown }
}
