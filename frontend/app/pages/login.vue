<template>
  <div class="min-h-screen w-full flex bg-white overflow-hidden">
    <!-- Left: form panel -->
    <div class="w-full lg:w-1/2 flex flex-col items-center justify-center px-8 py-12">
      <div class="w-full max-w-[380px]">
        <!-- Logo -->
        <div class="mb-10 mx-auto flex justify-center">
          <NuxtLink to="/login" class="flex items-center gap-2">
            <img src="~/assets/logo.png" alt="M.DocAI" class="h-10" />
            <span class="text-2xl font-semibold text-login-black">M<span class="text-login-orange text-3xl font-bold">.</span>DocAI</span>
          </NuxtLink>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleSubmit" class="w-full">
          <h1 class="text-2xl font-semibold text-login-black mb-6">
            {{ isLogin ? 'Sign in' : 'Create account' }}
          </h1>

          <div class="space-y-3">
            <!-- Email -->
            <input
              v-model="form.email"
              type="email"
              required
              placeholder="Email"
              autocomplete="email"
              class="w-full h-12 px-4 rounded-lg bg-login-gray-bg border border-transparent text-login-black placeholder-login-gray-text outline-none focus:border-login-orange transition-colors"
            />

            <!-- Nickname (register only) -->
            <input
              v-if="!isLogin"
              v-model="form.nickname"
              type="text"
              required
              placeholder="Nickname"
              autocomplete="username"
              class="w-full h-12 px-4 rounded-lg bg-login-gray-bg border border-transparent text-login-black placeholder-login-gray-text outline-none focus:border-login-orange transition-colors"
            />

            <!-- Password -->
            <div class="relative">
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                required
                placeholder="Password"
                :autocomplete="isLogin ? 'current-password' : 'new-password'"
                class="w-full h-12 px-4 pr-14 rounded-lg bg-login-gray-bg border border-transparent text-login-black placeholder-login-gray-text outline-none focus:border-login-orange transition-colors"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-login-gray-text hover:text-login-black text-sm"
              >
                {{ showPassword ? 'Hide' : 'Show' }}
              </button>
            </div>
          </div>

          <!-- Remember me + Forgot -->
          <div v-if="isLogin" class="flex items-center justify-between mt-4 text-sm">
            <label class="flex items-center gap-2 text-login-gray-text cursor-pointer">
              <input
                v-model="form.remember"
                type="checkbox"
                class="h-4 w-4 rounded accent-login-orange"
              />
              Remember me
            </label>
            <button type="button" class="text-login-orange font-medium hover:underline">
              Forgot Password
            </button>
          </div>

          <!-- Error -->
          <p v-if="error" class="mt-4 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
            {{ error }}
          </p>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="loading || !form.email || !form.password"
            class="mt-6 w-full h-12 rounded-lg bg-login-orange text-white font-semibold hover:bg-login-orange-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {{ loading ? 'Signing in...' : isLogin ? 'Sign in' : 'Create account' }}
          </button>

          <!-- Divider -->
          <div class="flex items-center gap-3 my-6">
            <span class="h-px flex-1 bg-login-gray-bg"></span>
            <span class="text-xs text-login-gray-text">OR</span>
            <span class="h-px flex-1 bg-login-gray-bg"></span>
          </div>

          <!-- Toggle -->
          <p class="text-center text-sm text-login-gray-text">
            {{ isLogin ? 'No account?' : 'Already have an account?' }}
            {{ ' ' }}
            <button
              type="button"
              @click="toggleMode"
              class="text-login-orange font-medium hover:underline"
            >
              {{ isLogin ? 'Get started here' : 'Sign in' }}
            </button>
          </p>
        </form>
      </div>
    </div>

    <!-- Right: brand visual panel -->
    <div class="hidden lg:flex w-1/2 p-4">
      <div class="relative w-full h-[calc(100vh-2rem)] rounded-3xl overflow-hidden bg-login-black">
        <!-- Carousel images -->
        <div
          v-for="(img, i) in carouselImages"
          :key="i"
          class="absolute inset-0 transition-opacity duration-1000"
          :class="i === activeSlide ? 'opacity-100' : 'opacity-0'"
        >
          <img :src="img" alt="M.DocAI" class="w-full h-full object-cover" />
        </div>
        <!-- Gradient overlay -->
        <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent"></div>
        <!-- Bottom text -->
        <div class="absolute bottom-10 left-10 right-10 text-white">
          <h2 class="text-3xl font-bold mb-2">Intelligent Document Processing</h2>
          <p class="text-white/70 text-sm">AI-powered OCR, classification, extraction, and splitting for enterprise documents.</p>
        </div>
        <!-- Dots indicator -->
        <div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
          <span
            v-for="(_, i) in carouselImages"
            :key="i"
            class="w-2 h-2 rounded-full transition-all"
            :class="i === activeSlide ? 'bg-white w-6' : 'bg-white/40'"
          ></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false,
})

const router = useRouter()
const route = useRoute()
const { login } = useAuth()
const config = useRuntimeConfig()
const apiBase = config.public.apiBaseUrl as string

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const error = ref<string | null>(null)
const showPassword = ref(false)

const isLogin = computed(() => mode.value === 'login')
const returnUrl = computed(() => (route.query.returnUrl as string) || '/')

const form = reactive({
  email: '',
  password: '',
  nickname: '',
  remember: false,
})

// Carousel
const carouselImages = [
  '/login-visual-1.jpg',
  '/login-visual-2.jpg',
  '/login-visual-3.jpg',
]
const activeSlide = ref(0)
let carouselTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  carouselTimer = setInterval(() => {
    activeSlide.value = (activeSlide.value + 1) % carouselImages.length
  }, 5000)
})

onUnmounted(() => {
  if (carouselTimer) clearInterval(carouselTimer)
})

async function handleSubmit() {
  error.value = null

  if (!form.email.trim()) { error.value = 'Please enter your email'; return }
  if (!form.password.trim()) { error.value = 'Please enter your password'; return }
  if (!isLogin.value && !form.nickname.trim()) { error.value = 'Please enter a nickname'; return }

  loading.value = true
  try {
    if (isLogin.value) {
      const response = await fetch(`${apiBase}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email.trim(), password: form.password }),
      })
      const data = await response.json()
      if (data.code === 0 && data.data) {
        login(data.data.token, {
          id: data.data.user_id,
          nickname: data.data.nickname,
          email: data.data.email,
          avatar: data.data.avatar,
          tenantId: data.data.tenant_id || '',
          role: data.data.role || 'user',
        })
        await router.replace(returnUrl.value)
      } else {
        error.value = data.message || 'Invalid email or password'
      }
    } else {
      const response = await fetch(`${apiBase}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email.trim(), password: form.password, nickname: form.nickname.trim() }),
      })
      const data = await response.json()
      if (data.code === 0) { mode.value = 'login'; error.value = null }
      else { error.value = data.message || 'Registration failed' }
    }
  } catch { error.value = 'Network error. Please try again later.' }
  finally { loading.value = false }
}

function toggleMode() {
  mode.value = isLogin.value ? 'register' : 'login'
  error.value = null
}
</script>

<style scoped>
.bg-login-gray-bg { background-color: #f4f5f7; }
.bg-login-black { background-color: #1a1a1a; }
.bg-login-orange { background-color: #f37021; }
.bg-login-orange-hover { background-color: #d95b16; }
.text-login-black { color: #1a1a1a; }
.text-login-orange { color: #f37021; }
.text-login-gray-text { color: #666666; }
.placeholder-login-gray-text::placeholder { color: #666666; }
.border-login-orange { border-color: #f37021; }
.accent-login-orange { accent-color: #f37021; }
.focus\:border-login-orange:focus { border-color: #f37021; }
.hover\:bg-login-orange-hover:hover { background-color: #d95b16; }
.hover\:text-login-black:hover { color: #1a1a1a; }
</style>
