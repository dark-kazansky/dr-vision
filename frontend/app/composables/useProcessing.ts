/**
 * Composable for document processing — parse, classify, extract, split.
 */
import { useOCR } from '~/composables/useOCR'
import { useDataStore } from '~/composables/useDataStore'

export function useProcessing() {
  const {
    files,
    isProcessing,
    results,
    processFile,
    classifyFile,
    splitFile,
    cancelProcessing,
  } = useOCR()

  const { saveEntry: saveToDataStore } = useDataStore()

  const isCancelling = ref(false)

  /**
   * Process a single file or all unprocessed files (Parse mode).
   */
  const handleProcess = async (opts: {
    selectedFile: any
    processAllFiles: boolean
    processAllPages: boolean
    selectedModel: string
    getFileForProcessing: (id: string, name: string) => Promise<File | null>
  }) => {
    const { selectedFile, processAllFiles, processAllPages, selectedModel, getFileForProcessing } = opts

    if (processAllFiles) {
      const filesToProcess = files.value.filter(f => !f.result || f.status === 'pending' || f.status === 'error')
      if (filesToProcess.length === 0) return

      for (const fileItem of filesToProcess) {
        const file = await getFileForProcessing(fileItem.id, fileItem.name)
        if (!file) continue
        await processFile(fileItem.id, file, {
          modelId: selectedModel,
          tier: 'Normal',
          processAllPages,
        })
        if (fileItem.result?.success) {
          saveToDataStore({
            filename: fileItem.name,
            action_tag: 'Parse',
            result_data: fileItem.result,
            model_used: selectedModel,
          })
        }
      }
      return
    }

    if (!selectedFile) return
    const file = await getFileForProcessing(selectedFile.id, selectedFile.name)
    if (!file) return

    await processFile(selectedFile.id, file, {
      modelId: selectedModel,
      tier: 'Normal',
      processAllPages,
    })

    if (selectedFile?.result?.success) {
      saveToDataStore({
        filename: selectedFile.name,
        action_tag: 'Parse',
        result_data: selectedFile.result,
        model_used: selectedModel,
      })
    }
  }

  /**
   * Process extraction on a single file or all unprocessed files.
   */
  const handleExtractionProcess = async (
    config: any,
    selectedFile: any,
    getFileForProcessing: (id: string, name: string) => Promise<File | null>
  ) => {
    results.value = null

    if (config.processAllFiles) {
      const unprocessedFiles = files.value.filter(f => f.status === 'pending')
      if (unprocessedFiles.length === 0) return

      for (const fileItem of unprocessedFiles) {
        const file = await getFileForProcessing(fileItem.id, fileItem.name)
        if (file) {
          await processFile(fileItem.id, file, config)
          if (fileItem.result?.success) {
            saveToDataStore({
              filename: fileItem.name,
              action_tag: 'Extract',
              result_data: fileItem.result,
              model_used: config.modelId,
            })
          }
        }
      }
      return
    }

    if (!selectedFile) return
    const file = await getFileForProcessing(selectedFile.id, selectedFile.name)
    if (!file) return

    await processFile(selectedFile.id, file, config)

    if (selectedFile?.result?.success) {
      saveToDataStore({
        filename: selectedFile.name,
        action_tag: 'Extract',
        result_data: selectedFile.result,
        model_used: config.modelId,
      })
    }
  }

  /**
   * Process classification on a single file or all unprocessed files.
   */
  const handleClassifyProcess = async (
    config: any,
    selectedFile: any,
    getFileForProcessing: (id: string, name: string) => Promise<File | null>
  ) => {
    results.value = null

    if (config.processAllFiles) {
      const unprocessedFiles = files.value.filter(f => f.status === 'pending')
      if (unprocessedFiles.length === 0) return

      const allResults: any[] = []
      for (const fileItem of unprocessedFiles) {
        const file = await getFileForProcessing(fileItem.id, fileItem.name)
        if (file) {
          await classifyFile(fileItem.id, file, config)
          if (fileItem.result?.success && (fileItem.result as any)?.results) {
            allResults.push(...(fileItem.result as any).results)
          }
        }
      }

      if (allResults.length > 0) {
        results.value = { success: true, results: allResults }
        for (const fileItem of unprocessedFiles) {
          if (fileItem.result?.success) {
            saveToDataStore({
              filename: fileItem.name,
              action_tag: 'Classify',
              result_data: fileItem.result,
              model_used: config.classifierModelId,
            })
          }
        }
      }
      return
    }

    if (!selectedFile) return
    const file = await getFileForProcessing(selectedFile.id, selectedFile.name)
    if (!file) return

    await classifyFile(selectedFile.id, file, config)

    if (selectedFile?.result?.success) {
      saveToDataStore({
        filename: selectedFile.name,
        action_tag: 'Classify',
        result_data: selectedFile.result,
        model_used: config.classifierModelId,
      })
    }
  }

  /**
   * Process split on a single file or all unprocessed files.
   */
  const handleSplitProcess = async (
    config: any,
    selectedFile: any,
    getFileForProcessing: (id: string, name: string) => Promise<File | null>
  ) => {
    results.value = null

    if (config.processAllFiles) {
      const unprocessedFiles = files.value.filter(f => f.status === 'pending')
      if (unprocessedFiles.length === 0) return

      for (const fileItem of unprocessedFiles) {
        const file = await getFileForProcessing(fileItem.id, fileItem.name)
        if (file) {
          await splitFile(fileItem.id, file, config)
          if (fileItem.result?.success) {
            saveToDataStore({
              filename: fileItem.name,
              action_tag: 'Split',
              result_data: fileItem.result,
              model_used: config.splitterModelId || undefined,
            })
          }
        }
      }
      return
    }

    if (!selectedFile) return
    const file = await getFileForProcessing(selectedFile.id, selectedFile.name)
    if (!file) return

    await splitFile(selectedFile.id, file, config)

    if (selectedFile?.result?.success) {
      saveToDataStore({
        filename: selectedFile.name,
        action_tag: 'Split',
        result_data: selectedFile.result,
        model_used: config.splitterModelId || undefined,
      })
    }
  }

  const handleCancel = () => {
    isCancelling.value = true
    isProcessing.value = false
    files.value.forEach(file => {
      if (file.status === 'processing') file.status = 'error'
    })
    setTimeout(() => { isCancelling.value = false }, 100)
  }

  return {
    isProcessing,
    results,
    isCancelling,
    handleProcess,
    handleExtractionProcess,
    handleClassifyProcess,
    handleSplitProcess,
    handleCancel,
    cancelProcessing,
  }
}
