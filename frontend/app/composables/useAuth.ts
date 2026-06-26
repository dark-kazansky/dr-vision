import { ref, computed } from 'vue'
import { useCookie, useRouter, useRuntimeConfig } from '#app'

interface User {
  id: string
  email: string
  role: string
}

export const useAuth = () => {
  const router = useRouter()
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl

  const accessToken = useCookie<string | null>('access_token', { maxAge: 30 * 60 }) // 30 mins
  const refreshToken = useCookie<string | null>('refresh_token', { maxAge: 7 * 24 * 60 * 60 }) // 7 days

  const user = computed<User | null>(() => {
    if (!accessToken.value) return null
    try {
      const payload = accessToken.value.split('.')[1]
      if (!payload) return null
      const decoded = JSON.parse(atob(payload))
      return {
        id: decoded.sub,
        email: decoded.email,
        role: decoded.role,
      }
    } catch {
      return null
    }
  })

  const isAuthenticated = computed(() => !!accessToken.value)

  const login = async (email: string, password: string) => {
    try {
      // Use raw fetch to avoid interceptor loop
      const response = await fetch(`${apiBaseUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      if (!response.ok) {
        if (response.status === 429) {
          throw new Error('Too many login attempts. Please try again later.')
        }
        throw new Error('Invalid email or password')
      }

      const data = await response.json()
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token
      return { success: true }
    } catch (error: any) {
      return { success: false, error: error.message }
    }
  }

  const logout = () => {
    accessToken.value = null
    refreshToken.value = null
    router.push('/login')
  }

  const refresh = async () => {
    if (!refreshToken.value) {
      logout()
      return false
    }

    try {
      const response = await fetch(`${apiBaseUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${refreshToken.value}`
        }
      })

      if (!response.ok) {
        logout()
        return false
      }

      const data = await response.json()
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token
      return true
    } catch {
      logout()
      return false
    }
  }

  return {
    user,
    isAuthenticated,
    accessToken,
    refreshToken,
    login,
    logout,
    refresh
  }
}
