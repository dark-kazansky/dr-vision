/**
 * Composable for tier configuration management.
 */
import { useTierConfig } from '~/composables/useTierConfig'

export function useTierSettings(settingsProviders: Ref<any[]>) {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  const { fetchTierConfig } = useTierConfig()

  const settingsTierConfig = ref<any>(null)
  const settingsTierFull = ref<any>(null)

  const tierEdits = ref<Record<string, Record<string, { provider: string; model: string }>>>({})
  const tierSaving = ref(false)
  const tierSaveMsg = ref('')
  const tierSaveOk = ref(false)

  const tierRows = [
    { feature: 'parser', label: 'Parser (OCR)' },
    { feature: 'classifier_llm', label: 'Classifier' },
    { feature: 'extractor', label: 'Extractor' },
    { feature: 'splitter', label: 'Splitter' },
  ]

  const getFullTierSpec = (feature: string, tier: string) => {
    return settingsTierFull.value?.[feature]?.[tier] ?? { model: '', provider: '' }
  }

  const getModelsForProvider = (providerId: string | null | undefined) => {
    if (!providerId) return settingsProviders.value.flatMap((p: any) => p.models || [])
    const provider = settingsProviders.value.find((p: any) => p.id === providerId)
    return provider?.models ?? []
  }

  const onTierSelectChange = (feature: string, tier: string, value: string) => {
    if (!tierEdits.value[feature]) tierEdits.value[feature] = {}
    const parts = value.includes('::') ? value.split('::') : ['', value]
    tierEdits.value[feature][tier] = { provider: parts[0] ?? '', model: parts[1] ?? value }
  }

  const getProviderName = (providerId: string | null | undefined) => {
    if (!providerId) return ''
    const p = settingsProviders.value.find((p: any) => p.id === providerId)
    return p?.name ?? providerId
  }

  const getTierSelectValue = (feature: string, tier: string) => {
    const edit = tierEdits.value[feature]?.[tier]
    const spec = edit ?? getFullTierSpec(feature, tier)
    if (!spec?.model) return ''
    return spec.provider ? `${spec.provider}::${spec.model}` : spec.model
  }

  const saveTierConfig = async () => {
    tierSaving.value = true
    tierSaveMsg.value = ''
    try {
      const updates: any[] = []
      for (const [feature, tiers] of Object.entries(tierEdits.value)) {
        for (const [tier, spec] of Object.entries(tiers as any)) {
          if ((spec as any).model) {
            updates.push({ feature, tier, provider: (spec as any).provider || 'auto', model: (spec as any).model })
          }
        }
      }
      if (updates.length === 0) {
        tierSaveMsg.value = 'No changes to save'
        tierSaveOk.value = false
        return
      }
      const res = await $fetch<any>(`${apiBaseUrl}/tier-config`, { method: 'PUT', body: { updates } })
      if (res.success) {
        tierSaveMsg.value = `Saved ${updates.length} change${updates.length > 1 ? 's' : ''}`
        tierSaveOk.value = true
        const tc = await fetchTierConfig()
        settingsTierConfig.value = tc
        tierEdits.value = {}
      } else {
        tierSaveMsg.value = res.errors?.join(', ') ?? 'Save failed'
        tierSaveOk.value = false
      }
    } catch (e: any) {
      tierSaveMsg.value = e?.data?.detail ?? e?.message ?? 'Save failed'
      tierSaveOk.value = false
    } finally {
      tierSaving.value = false
      setTimeout(() => { tierSaveMsg.value = '' }, 3000)
    }
  }

  const loadTierData = async () => {
    if (!settingsTierConfig.value) {
      const tc = await fetchTierConfig()
      settingsTierConfig.value = tc
      try {
        const full = await $fetch<any>(`${apiBaseUrl}/tier-config`)
        settingsTierFull.value = full.full ?? null
      } catch {}
    }
  }

  return {
    settingsTierConfig,
    settingsTierFull,
    tierEdits,
    tierSaving,
    tierSaveMsg,
    tierSaveOk,
    tierRows,
    getFullTierSpec,
    getModelsForProvider,
    onTierSelectChange,
    getProviderName,
    getTierSelectValue,
    saveTierConfig,
    loadTierData,
  }
}
