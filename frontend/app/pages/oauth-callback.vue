<template>
  <div class="flex justify-center items-center min-h-screen bg-cream">
    <!-- Error state -->
    <div v-if="error" class="w-[400px] max-w-[90vw] text-center">
      <div class="bg-red-50 border border-red-200 rounded-comfortable p-6 mb-4">
        <h2 class="text-lg font-semibold text-red-700 mb-2">Authentication Failed</h2>
        <p class="text-sm text-red-600">{{ error }}</p>
      </div>
      <NuxtLink to="/login" class="text-ds-orange hover:opacity-80 font-medium text-sm">
        Back to Login
      </NuxtLink>
    </div>

    <!-- Loading state -->
    <div v-else class="text-center">
      <div class="animate-spin h-8 w-8 border-4 border-ds-orange border-t-transparent rounded-full mx-auto mb-4" />
      <p class="text-ds-gray text-sm">Completing sign in...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false,
})

const route = useRoute()
const router = useRouter()
const { login } = useAuth()

const error = ref<string | null>(null)

onMounted(() => {
  const errorParam = route.query.error as string | undefined
  if (errorParam) {
    error.value = decodeURIComponent(errorParam)
    return
  }

  const token = route.query.token as string | undefined
  if (!token) {
    error.value = 'No authentication token received. Please try again.'
    return
  }

  // Extract user info from query params
  const user = {
    id: (route.query.user_id as string) || '',
    nickname: (route.query.nickname as string) || (route.query.name as string) || '',
    email: (route.query.email as string) || '',
    avatar: (route.query.avatar as string) || undefined,
    tenantId: (route.query.tenant_id as string) || '',
    role: (route.query.role as string) || 'user',
  }

  login(token, user)

  const returnUrl = (route.query.returnUrl as string) || '/'
  router.replace(returnUrl)
})
</script>
