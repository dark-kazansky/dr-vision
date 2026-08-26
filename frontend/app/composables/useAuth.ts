/**
 * Authentication composable — ported from MSB Knowledge Discovery's AuthContext.
 *
 * Manages JWT token storage, user info, automatic token refresh,
 * and provides login/logout/updateUser actions.
 */

export interface UserInfo {
  id: string
  nickname: string
  email: string
  avatar?: string
  tenantId: string
  role: string
}

export interface AuthState {
  token: string | null
  user: UserInfo | null
  isAuthenticated: boolean
}

const TOKEN_KEY = 'mdocai_token'
const USER_KEY = 'mdocai_user'
const REFRESH_INTERVAL_MS = 4 * 60 * 1000 // 4 minutes

function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeSetItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // ignore
  }
}

function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch {
    // ignore
  }
}

function loadStoredAuth(): AuthState {
  try {
    const token = safeGetItem(TOKEN_KEY)
    const userStr = safeGetItem(USER_KEY)
    const user = userStr ? JSON.parse(userStr) : null
    return { token, user, isAuthenticated: !!token && !!user }
  } catch {
    return { token: null, user: null, isAuthenticated: false }
  }
}

// Shared reactive state (singleton across the app)
const authState = ref<AuthState>(loadStoredAuth())
let refreshTimer: ReturnType<typeof setInterval> | null = null

export function useAuth() {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBaseUrl as string

  const isAuthenticated = computed(() => authState.value.isAuthenticated)
  const user = computed(() => authState.value.user)
  const token = computed(() => authState.value.token)

  function login(newToken: string, userInfo: UserInfo) {
    safeSetItem(TOKEN_KEY, newToken)
    safeSetItem(USER_KEY, JSON.stringify(userInfo))
    authState.value = { token: newToken, user: userInfo, isAuthenticated: true }
    startRefreshTimer()
  }

  function logout() {
    safeRemoveItem(TOKEN_KEY)
    safeRemoveItem(USER_KEY)
    authState.value = { token: null, user: null, isAuthenticated: false }
    stopRefreshTimer()
  }

  function updateUser(partial: Partial<UserInfo>) {
    if (!authState.value.user) return
    const updated = { ...authState.value.user, ...partial }
    safeSetItem(USER_KEY, JSON.stringify(updated))
    authState.value = { ...authState.value, user: updated }
  }

  async function refreshToken() {
    const currentToken = safeGetItem(TOKEN_KEY)
    if (!currentToken) return

    try {
      const response = await fetch(`${apiBase}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${currentToken}`,
        },
      })

      if (!response.ok) {
        if (response.status === 401) {
          logout()
        }
        return
      }

      const data = await response.json()
      if (data.code === 0 && data.data?.token) {
        safeSetItem(TOKEN_KEY, data.data.token)
        authState.value = { ...authState.value, token: data.data.token }
      }
    } catch {
      // Network error — keep current token, retry next interval
    }
  }

  function startRefreshTimer() {
    stopRefreshTimer()
    refreshTimer = setInterval(refreshToken, REFRESH_INTERVAL_MS)
  }

  function stopRefreshTimer() {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  // Start refresh timer if already authenticated on mount
  if (authState.value.isAuthenticated && !refreshTimer) {
    startRefreshTimer()
  }

  return {
    isAuthenticated,
    user,
    token,
    login,
    logout,
    updateUser,
    refreshToken,
  }
}
