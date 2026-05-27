/**
 * Composable for workflow import/export functionality.
 */
import type { Ref } from 'vue'

interface IOOptions {
  exportToJSON: () => string
  importFromJSON: (json: string) => void
  fitView: () => void
}

export function useWorkflowIO(opts: IOOptions) {
  const { exportToJSON, importFromJSON, fitView } = opts

  const fileInput = ref<HTMLInputElement | null>(null)

  const handleExport = () => {
    const json = exportToJSON()
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'workflow.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = () => {
    fileInput.value?.click()
  }

  const onFileImport = (event: Event) => {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        importFromJSON(e.target?.result as string)
        nextTick(() => fitView())
      } catch (err) {
        alert('Invalid workflow file')
      }
    }
    reader.readAsText(file)
  }

  return {
    fileInput,
    handleExport,
    handleImport,
    onFileImport,
  }
}
