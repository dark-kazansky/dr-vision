/**
 * useProviders Composable
 *
 * Fetches provider configuration from backend and exposes
 * test-connection functionality.
 */

export interface ProviderModel {
  model_id: string
  name: string
  provider: string
}

export interface Provider {
  id: string
  name: string
  type: 'cloud' | 'local'
  base_url: string | null
  configured: boolean
  credential_key: string | null
  credential_set: boolean
  models: ProviderModel[]
  description: string
}

export interface TestResult {
  success: boolean
  provider: string
  message: string
  latency_ms: number | null
}

export function useProviders() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  const providers = ref<Provider[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const testResults = ref<Record<string, TestResult>>({})
  const testingProvider = ref<string | null>(null)

  const fetchProviders = async () => {
    isLoading.value = true
    error.value = null
    try {
      const res = await $fetch<{ success: boolean; providers: Provider[] }>(
        `${apiBaseUrl}/providers`
      )
      providers.value = res.providers
    } catch (e: any) {
      error.value = e?.data?.detail ?? e?.message ?? 'Failed to load providers'
    } finally {
      isLoading.value = false
    }
  }

  const testConnection = async (providerId: string) => {
    testingProvider.value = providerId
    try {
      const res = await $fetch<TestResult>(
        `${apiBaseUrl}/providers/${providerId}/test`,
        { method: 'POST' }
      )
      testResults.value[providerId] = res
      return res
    } catch (e: any) {
      const result: TestResult = {
        success: false,
        provider: providerId,
        message: e?.data?.detail ?? e?.message ?? 'Connection test failed',
        latency_ms: null,
      }
      testResults.value[providerId] = result
      return result
    } finally {
      testingProvider.value = null
    }
  }

  const getTestResult = (providerId: string) => testResults.value[providerId] ?? null

  return {
    providers,
    isLoading,
    error,
    testingProvider,
    fetchProviders,
    testConnection,
    getTestResult,
  }
}
