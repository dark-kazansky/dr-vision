/**
 * Auth middleware — redirects unauthenticated users to /login.
 * Ported from MSB Knowledge Discovery's AuthGuard component.
 *
 * Apply to pages with: definePageMeta({ middleware: 'auth' })
 */
export default defineNuxtRouteMiddleware((to) => {
  // Only run on client side (localStorage not available on server)
  if (import.meta.server) return

  const { isAuthenticated } = useAuth()

  if (!isAuthenticated.value) {
    const returnUrl = to.fullPath !== '/' ? `?returnUrl=${encodeURIComponent(to.fullPath)}` : ''
    return navigateTo(`/login${returnUrl}`)
  }
})
