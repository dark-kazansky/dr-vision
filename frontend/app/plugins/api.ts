import { defineNuxtPlugin, useRuntimeConfig } from '#app'
import { useAuth } from '~/composables/useAuth'

export default defineNuxtPlugin((nuxtApp) => {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  // Create a custom fetcher
  const apiFetch = $fetch.create({
    onRequest({ request, options }) {
      const url = request.toString()
      // Only attach tokens to requests going to the API
      if (!url.startsWith(apiBaseUrl) && !url.includes('/api/') && !url.includes('/auth/')) {
        return
      }

      const { accessToken } = useAuth()
      
      // Skip adding token for auth endpoints
      if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
        return
      }

      if (accessToken.value) {
        options.headers = new Headers(options.headers || {})
        options.headers.set('Authorization', `Bearer ${accessToken.value}`)
      }
    },

    async onResponseError({ request, response, options }) {
      const url = request.toString()
      // Only intercept 401s for API requests
      if (!url.startsWith(apiBaseUrl) && !url.includes('/api/') && !url.includes('/auth/')) {
        return
      }

      // Handle 401 Unauthorized globally
      if (response.status === 401) {
        // Exclude auth endpoints from refresh logic to prevent infinite loops
        if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
          return
        }

        const auth = useAuth()
        
        // Attempt to refresh the token
        const success = await auth.refresh()
        
        if (success) {
          // Retry the original request
          options.headers = new Headers(options.headers || {})
          options.headers.set('Authorization', `Bearer ${auth.accessToken.value}`)
          
          try {
            const data = await $fetch(request as any, options as any)
            // Override the response body to return the successful retry data
            response._data = data
          } catch (error) {
            auth.logout()
          }
        } else {
          // Refresh failed, logout
          auth.logout()
        }
      }
    }
  })

  // Override global $fetch so we don't have to rewrite all $fetch calls in the app
  globalThis.$fetch = apiFetch as any
})
