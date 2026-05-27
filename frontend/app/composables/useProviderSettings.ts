/**
 * Composable for provider management — CRUD, inline editing, test connection.
 */
import { useProviders } from '~/composables/useProviders'

export function useProviderSettings() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  const { fetchProviders } = useProviders()

  // Provider state
  const settingsProviders = ref<any[]>([])
  const settingsLoading = ref(false)
  const settingsError = ref<string | null>(null)
  const settingsTestResults = ref<Record<string, any>>({})
  const settingsTestingProvider = ref<string | null>(null)

  // Inline key editing
  const inlineKeyValues = ref<Record<string, string>>({})
  const inlineKeyEditing = ref<Record<string, boolean>>({})
  const inlineKeyVisible = ref<Record<string, boolean>>({})

  // Inline URL editing
  const inlineUrlValues = ref<Record<string, string>>({})
  const inlineUrlEditing = ref<Record<string, boolean>>({})

  // Inline RPM editing
  const inlineRpmValues = ref<Record<string, number | undefined>>({})
  const inlineRpmEditing = ref<Record<string, boolean>>({})

  // Saving indicator
  const inlineSaving = ref<Record<string, boolean>>({})

  // Debounce
  const _debounceTimers: Record<string, ReturnType<typeof setTimeout>> = {}
  const _debounce = (key: string, fn: () => void, delay = 800) => {
    clearTimeout(_debounceTimers[key])
    _debounceTimers[key] = setTimeout(fn, delay)
  }

  const reloadProviders = async () => {
    settingsLoading.value = true
    settingsError.value = null
    try {
      const res = await $fetch<{ success: boolean; providers: any[] }>(`${apiBaseUrl}/providers`)
      settingsProviders.value = res.providers
      await fetchProviders()
    } catch (e: any) {
      settingsError.value = e?.data?.detail ?? e?.message ?? 'Failed to load providers'
    } finally {
      settingsLoading.value = false
    }
  }

  const runTestConnection = async (providerId: string) => {
    settingsTestingProvider.value = providerId
    try {
      const res = await $fetch<any>(`${apiBaseUrl}/providers/${providerId}/test`, { method: 'POST' })
      settingsTestResults.value[providerId] = res
      await reloadProviders()
    } catch (e: any) {
      settingsTestResults.value[providerId] = {
        success: false, provider: providerId,
        message: e?.data?.detail ?? e?.message ?? 'Connection test failed',
        latency_ms: null,
      }
    } finally {
      settingsTestingProvider.value = null
    }
  }

  // --- Debounced saves ---

  const debounceSaveKey = (provider: any, value: string) => {
    inlineKeyValues.value[provider.id] = value
    if (!value.trim() || !provider.credential_key) return
    _debounce(`${provider.id}_key`, async () => {
      inlineSaving.value[`${provider.id}_key`] = true
      try {
        await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, { method: 'POST', body: { api_key: value.trim() } })
        await reloadProviders()
      } catch (e) { console.error('Auto-save key failed:', e) }
      finally { inlineSaving.value[`${provider.id}_key`] = false }
    })
  }

  const debounceSaveUrl = (provider: any, value: string) => {
    inlineUrlValues.value[provider.id] = value
    _debounce(`${provider.id}_url`, async () => {
      inlineSaving.value[`${provider.id}_url`] = true
      try {
        await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, { method: 'POST', body: { base_url: value.trim() } })
        await reloadProviders()
      } catch (e) { console.error('Auto-save URL failed:', e) }
      finally { inlineSaving.value[`${provider.id}_url`] = false }
    })
  }

  const debounceSaveRpm = (provider: any, value: number) => {
    inlineRpmValues.value[provider.id] = value
    _debounce(`${provider.id}_rpm`, async () => {
      inlineSaving.value[`${provider.id}_rpm`] = true
      try {
        await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, { method: 'POST', body: { rpm: Math.max(1, Math.floor(value)) } })
        await reloadProviders()
      } catch (e) { console.error('Auto-save RPM failed:', e) }
      finally { inlineSaving.value[`${provider.id}_rpm`] = false }
    })
  }

  // --- Inline edit actions ---

  const startInlineEdit = (providerId: string) => { inlineKeyEditing.value[providerId] = true }

  const cancelInlineEdit = (providerId: string) => {
    inlineKeyEditing.value[providerId] = false
    delete inlineKeyValues.value[providerId]
  }

  const saveInlineKey = async (provider: any) => {
    const value = inlineKeyValues.value[provider.id]
    if (!value?.trim()) { cancelInlineEdit(provider.id); return }
    try {
      await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, { method: 'POST', body: { api_key: value.trim() } })
      inlineKeyEditing.value[provider.id] = false
      delete inlineKeyValues.value[provider.id]
      await reloadProviders()
    } catch (e: any) { console.error('Failed to save key:', e) }
  }

  const cancelInlineUrl = (providerId: string) => { inlineUrlEditing.value[providerId] = false; delete inlineUrlValues.value[providerId] }

  const saveInlineUrl = async (provider: any) => {
    const value = inlineUrlValues.value[provider.id]
    inlineUrlEditing.value[provider.id] = false
    if (value === undefined) return
    try {
      await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, { method: 'POST', body: { base_url: value.trim() } })
      delete inlineUrlValues.value[provider.id]
      await reloadProviders()
    } catch (e: any) { console.error('Failed to save URL:', e) }
  }

  const cancelInlineRpm = (providerId: string) => { inlineRpmEditing.value[providerId] = false; delete inlineRpmValues.value[providerId] }

  const saveInlineRpm = async (provider: any) => {
    const value = inlineRpmValues.value[provider.id]
    inlineRpmEditing.value[provider.id] = false
    if (value === undefined || value === null) return
    try {
      await $fetch(`${apiBaseUrl}/providers/${provider.id}/config`, { method: 'POST', body: { rpm: Math.max(1, Math.floor(value)) } })
      delete inlineRpmValues.value[provider.id]
      await reloadProviders()
    } catch (e: any) { console.error('Failed to save RPM:', e) }
  }

  // --- Config modal ---

  const configModal = reactive({
    open: false, provider: null as any, apiKey: '', baseUrl: '',
    rpm: null as number | null, showKey: false, saving: false, saveMsg: '', saveOk: false,
  })

  const openConfigModal = (provider: any) => {
    Object.assign(configModal, {
      provider, apiKey: '', baseUrl: provider.base_url || '',
      rpm: provider.rpm ?? null, showKey: false, saving: false, saveMsg: '', saveOk: false, open: true,
    })
  }

  const saveProviderConfig = async () => {
    if (!configModal.provider) return
    configModal.saving = true; configModal.saveMsg = ''
    try {
      const body: any = { rpm: configModal.rpm }
      if (configModal.provider.credential_key && configModal.apiKey !== '') body.api_key = configModal.apiKey
      if (configModal.provider.type === 'local' && configModal.baseUrl) body.base_url = configModal.baseUrl
      await $fetch(`${apiBaseUrl}/providers/${configModal.provider.id}/config`, { method: 'POST', body })
      configModal.saveMsg = 'Saved successfully!'; configModal.saveOk = true
      await reloadProviders()
      setTimeout(() => { configModal.open = false }, 1200)
    } catch (e: any) {
      configModal.saveMsg = e?.data?.detail ?? e?.message ?? 'Failed to save'; configModal.saveOk = false
    } finally { configModal.saving = false }
  }

  // --- Add provider modal ---

  const addProviderModal = reactive({
    open: false, id: '', name: '', type: 'cloud' as 'cloud' | 'local',
    apiKey: '', baseUrl: '', rpm: null as number | null,
    showKey: false, saving: false, saveMsg: '', saveOk: false,
  })

  const openAddProviderModal = () => {
    Object.assign(addProviderModal, {
      open: true, id: '', name: '', type: 'cloud',
      apiKey: '', baseUrl: '', rpm: null, showKey: false, saving: false, saveMsg: '', saveOk: false,
    })
  }

  const saveNewProvider = async () => {
    if (!addProviderModal.id.trim() || !addProviderModal.name.trim()) return
    addProviderModal.saving = true; addProviderModal.saveMsg = ''
    try {
      const body: any = {
        name: addProviderModal.name.trim(), type: addProviderModal.type,
        base_url: addProviderModal.baseUrl.trim() || null, rpm: addProviderModal.rpm || null,
      }
      if (addProviderModal.type === 'cloud' && addProviderModal.apiKey.trim()) body.api_key = addProviderModal.apiKey.trim()
      await $fetch(`${apiBaseUrl}/providers/${addProviderModal.id.trim()}/add`, { method: 'POST', body })
      addProviderModal.saveMsg = 'Provider added successfully!'; addProviderModal.saveOk = true
      await reloadProviders()
      setTimeout(() => { addProviderModal.open = false }, 1200)
    } catch (e: any) {
      addProviderModal.saveMsg = e?.data?.detail ?? e?.message ?? 'Failed to add provider'; addProviderModal.saveOk = false
    } finally { addProviderModal.saving = false }
  }

  // --- Error tooltip ---

  const errorTooltip = reactive({ visible: false, message: '', x: 0, y: 0 })
  const showErrorTooltip = (event: MouseEvent, message: string) => {
    const rect = (event.target as HTMLElement).getBoundingClientRect()
    errorTooltip.message = message; errorTooltip.x = rect.left; errorTooltip.y = rect.top - 8; errorTooltip.visible = true
  }
  const hideErrorTooltip = () => { errorTooltip.visible = false }

  return {
    settingsProviders, settingsLoading, settingsError, settingsTestResults, settingsTestingProvider,
    inlineKeyValues, inlineKeyEditing, inlineKeyVisible,
    inlineUrlValues, inlineUrlEditing, inlineRpmValues, inlineRpmEditing, inlineSaving,
    configModal, addProviderModal, errorTooltip,
    reloadProviders, runTestConnection,
    debounceSaveKey, debounceSaveUrl, debounceSaveRpm,
    startInlineEdit, cancelInlineEdit, saveInlineKey,
    cancelInlineUrl, saveInlineUrl, cancelInlineRpm, saveInlineRpm,
    openConfigModal, saveProviderConfig, openAddProviderModal, saveNewProvider,
    showErrorTooltip, hideErrorTooltip,
  }
}
