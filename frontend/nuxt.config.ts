// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  
  modules: ['@nuxtjs/tailwindcss'],
  
  pages: true,
  
  css: ['~/assets/css/main.css'],
  
  runtimeConfig: {
    public: {
      apiBaseUrl: process.env.API_BASE_URL || 'http://localhost:8882'
    }
  },
  
  app: {
    head: {
      title: 'Dr.Vision - OCR Web UI',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'OCR Web UI with multiple model support' }
      ]
    }
  },
  
  typescript: {
    strict: true,
    typeCheck: false  // Disabled for now due to vite-plugin-checker issue
  }
})
