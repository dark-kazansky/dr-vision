/**
 * Tier Configuration Composable
 * 
 * Fetches tier-to-model mappings from backend API.
 * This ensures frontend always uses the same mappings as backend.
 */

export interface TierConfig {
  parser: Record<string, string>
  extractor: Record<string, string>
  classifier_llm: Record<string, string>
  schema_generator: Record<string, string>
  splitter: Record<string, string>
  descriptions: Record<string, string>
  colors: Record<string, string>
  tiers: string[]
}

export function useTierConfig() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string
  
  // State for tier configuration
  const tierConfig = useState<TierConfig | null>('tier-config', () => null)
  const isLoading = useState<boolean>('tier-config-loading', () => false)
  const error = useState<string | null>('tier-config-error', () => null)
  
  /**
   * Fetch tier configuration from backend
   */
  const fetchTierConfig = async () => {
    if (tierConfig.value) {
      // Already loaded
      return tierConfig.value
    }
    
    isLoading.value = true
    error.value = null
    
    try {
      const response = await $fetch<{ success: boolean; config: TierConfig }>(
        `${apiBaseUrl}/tier-config`
      )
      
      if (response.success && response.config) {
        tierConfig.value = response.config
        return response.config
      } else {
        throw new Error('Invalid tier config response')
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch tier configuration'
      console.error('Failed to fetch tier config:', err)
      
      // Return fallback configuration
      return getFallbackConfig()
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Get parser model for a tier
   */
  const getParserModel = (tier: string): string => {
    if (!tierConfig.value) {
      return getFallbackConfig().parser[tier] || 'gemini-3-flash'
    }
    return tierConfig.value.parser[tier] || 'gemini-3-flash'
  }
  
  /**
   * Get extractor model for a tier
   */
  const getExtractorModel = (tier: string): string => {
    if (!tierConfig.value) {
      return getFallbackConfig().extractor[tier] || 'qwen3-max'
    }
    return tierConfig.value.extractor[tier] || 'qwen3-max'
  }
  
  /**
   * Get classifier parser model for a tier (uses parser config)
   */
  const getClassifierParserModel = (tier: string): string => {
    // Classifier parser now uses the same models as parser
    return getParserModel(tier)
  }
  
  /**
   * Get classifier LLM model for a tier
   */
  const getClassifierLLMModel = (tier: string): string => {
    if (!tierConfig.value) {
      return getFallbackConfig().classifier_llm[tier] || 'gemini-3-flash'
    }
    return tierConfig.value.classifier_llm[tier] || 'gemini-3-flash'
  }
  
  /**
   * Get schema generator model for a tier
   */
  const getSchemaGeneratorModel = (tier: string): string => {
    if (!tierConfig.value) {
      return getFallbackConfig().schema_generator[tier] || 'qwen3-max'
    }
    return tierConfig.value.schema_generator[tier] || 'qwen3-max'
  }
  
  /**
   * Get splitter model for a tier
   */
  const getSplitterModel = (tier: string): string => {
    if (!tierConfig.value) {
      return getFallbackConfig().splitter[tier] || 'gemini-3-pro'
    }
    return tierConfig.value.splitter[tier] || 'gemini-3-pro'
  }
  
  /**
   * Get all available tiers
   */
  const getTiers = (): string[] => {
    if (!tierConfig.value) {
      return ['Rapid', 'Normal', 'Advance']
    }
    return tierConfig.value.tiers || ['Rapid', 'Normal', 'Advance']
  }
  
  /**
   * Get tier description
   */
  const getTierDescription = (tier: string): string => {
    if (!tierConfig.value) {
      return ''
    }
    return tierConfig.value.descriptions[tier] || ''
  }
  
  /**
   * Get tier color
   */
  const getTierColor = (tier: string): string => {
    if (!tierConfig.value) {
      const fallback: Record<string, string> = {
        'Rapid': '#FFB399',
        'Normal': '#FF8C5A',
        'Advance': '#FF6F3C',
        'Multimodal': '#E55A2B'
      }
      return fallback[tier] || '#FF8C5A'
    }
    return tierConfig.value.colors[tier] || '#FF8C5A'
  }
  
  /**
   * Fallback configuration if API fails
   */
  const getFallbackConfig = (): TierConfig => {
    return {
      parser: {
        'Rapid': 'lightonocr-2-1b',
        'Normal': 'claude-haiku',
        'Advance': 'claude-sonnet'
      },
      extractor: {
        'Rapid': 'lightonocr-2-1b',
        'Normal': 'claude-haiku',
        'Advance': 'claude-sonnet'
      },
      classifier_llm: {
        'Rapid': 'lightonocr-2-1b',
        'Normal': 'claude-haiku',
        'Advance': 'claude-sonnet',
        'Multimodal': 'claude-sonnet'
      },
      schema_generator: {
        'Rapid': 'assistant',
        'Normal': 'qwen3-max',
        'Advance': 'claude-opus-4.5'
      },
      splitter: {
        'Rapid': 'lightonocr-2-1b',
        'Normal': 'claude-haiku',
        'Advance': 'claude-sonnet'
      },
      descriptions: {
        'Rapid': 'Fast processing with good accuracy',
        'Normal': 'Balanced speed and quality',
        'Advance': 'Highest quality processing',
        'Multimodal': 'Direct vision processing'
      },
      colors: {
        'Rapid': '#FFB399',
        'Normal': '#FF8C5A',
        'Advance': '#FF6F3C',
        'Multimodal': '#E55A2B'
      },
      tiers: ['Rapid', 'Normal', 'Advance']
    }
  }
  
  return {
    // State
    tierConfig,
    isLoading,
    error,
    
    // Methods
    fetchTierConfig,
    getParserModel,
    getExtractorModel,
    getClassifierParserModel,
    getClassifierLLMModel,
    getSchemaGeneratorModel,
    getSplitterModel,
    getTiers,
    getTierDescription,
    getTierColor,
  }
}
