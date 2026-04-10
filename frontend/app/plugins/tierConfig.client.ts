/**
 * Tier Configuration Plugin
 * 
 * Automatically loads tier configuration from backend on app startup.
 * This ensures the frontend always uses the same tier-to-model mappings as the backend.
 */

export default defineNuxtPlugin(async () => {
  const { fetchTierConfig } = useTierConfig()
  
  // Load tier configuration on app startup
  try {
    await fetchTierConfig()
    console.log('✅ Tier configuration loaded from backend')
  } catch (error) {
    console.warn('⚠️ Failed to load tier configuration, using fallback:', error)
  }
})
