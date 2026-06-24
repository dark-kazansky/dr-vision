import { defineNuxtRouteMiddleware, navigateTo } from '#app'
import { useAuth } from '~/composables/useAuth'

export default defineNuxtRouteMiddleware((to, from) => {
  const auth = useAuth()
  
  // Exclude pages that don't need auth (login page, etc)
  // using definePageMeta({ auth: false })
  if (to.meta.auth === false) {
    return
  }

  // TEMPORARILY DISABLED: Bypassing login requirement for development
  // if (!auth.isAuthenticated.value) {
  //   return navigateTo({
  //     path: '/login',
  //     query: { redirect: to.fullPath }
  //   })
  // }

})
