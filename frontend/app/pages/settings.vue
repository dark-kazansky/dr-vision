<template>
  <div class="settings-page">
    <!-- Top Bar -->
    <div class="settings-topbar">
      <div class="settings-topbar-left">
        <NuxtLink to="/" class="back-link">
          <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </NuxtLink>
        <h1 class="settings-title">Settings</h1>
      </div>
      <div class="settings-topbar-right">
        <span class="user-badge" :class="{ admin: user?.role === 'admin' }">
          {{ user?.role === 'admin' ? '⚙️ Admin' : '👤 User' }}
        </span>
        <span class="user-email">{{ user?.email }}</span>
        <button class="btn-logout" @click="handleLogout">Logout</button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="settings-tabs">
      <button
        v-for="tab in visibleTabs"
        :key="tab.id"
        class="settings-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Content -->
    <div class="settings-content">
      <!-- Profile Tab -->
      <div v-if="activeTab === 'profile'" class="settings-section">
        <h2 class="section-title">Profile</h2>
        <div class="form-group">
          <label>Email</label>
          <input type="email" :value="user?.email" disabled class="input-disabled" />
        </div>
        <div class="form-group">
          <label>Nickname</label>
          <input v-model="profileForm.nickname" type="text" placeholder="Your nickname" />
        </div>
        <button class="btn-primary" @click="saveProfile" :disabled="saving">
          {{ saving ? 'Saving...' : 'Save Profile' }}
        </button>

        <h3 class="subsection-title">Change Password</h3>
        <div class="form-group">
          <label>Current Password</label>
          <input v-model="passwordForm.current" type="password" />
        </div>
        <div class="form-group">
          <label>New Password</label>
          <input v-model="passwordForm.newPassword" type="password" />
        </div>
        <button class="btn-primary" @click="changePassword" :disabled="saving">
          Change Password
        </button>
        <p v-if="profileMessage" class="message" :class="{ error: profileError }">{{ profileMessage }}</p>
      </div>

      <!-- Users Tab (admin only) -->
      <div v-if="activeTab === 'users'" class="settings-section">
        <h2 class="section-title">User Management</h2>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Nickname</th>
                <th>Role</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in usersList" :key="u.id">
                <td>{{ u.email }}</td>
                <td>{{ u.nickname }}</td>
                <td>
                  <span class="role-badge" :class="u.role">{{ u.role }}</span>
                </td>
                <td>
                  <select
                    :value="u.role"
                    @change="updateRole(u.id, ($event.target as HTMLSelectElement).value)"
                    :disabled="u.email === user?.email"
                  >
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Providers Tab (admin only) -->
      <div v-if="activeTab === 'providers'" class="settings-section">
        <h2 class="section-title">LLM/VLM Providers</h2>
        <p class="section-desc">Configure API providers for AI model access.</p>

        <div class="cards-grid">
          <div v-for="(provider, idx) in providersForm" :key="idx" class="setting-card">
            <div class="card-header">
              <input v-model="provider.name" class="card-title-input" placeholder="Provider name" />
              <label class="toggle-label">
                <input type="checkbox" v-model="provider.enabled" />
                <span class="toggle-text">{{ provider.enabled ? 'Enabled' : 'Disabled' }}</span>
              </label>
            </div>
            <div class="card-body">
              <div class="form-row">
                <label>ID</label>
                <input v-model="provider.id" placeholder="e.g. google_studio" />
              </div>
              <div class="form-row">
                <label>Type</label>
                <select v-model="provider.type">
                  <option value="llm">LLM</option>
                  <option value="vlm">VLM</option>
                </select>
              </div>
              <div class="form-row">
                <label>Base URL</label>
                <input v-model="provider.base_url" placeholder="https://..." />
              </div>
              <div class="form-row">
                <label>API Key Env Var</label>
                <input v-model="provider.api_key_env" placeholder="e.g. GOOGLE_STUDIO_API_KEY" />
              </div>
              <div class="form-row">
                <label>Timeout (s)</label>
                <input v-model.number="provider.timeout" type="number" />
              </div>
            </div>
            <button class="btn-danger-sm" @click="removeProvider(idx)">Remove</button>
          </div>
        </div>

        <div class="action-bar">
          <button class="btn-secondary" @click="addProvider">+ Add Provider</button>
          <button class="btn-primary" @click="saveProviders" :disabled="saving">Save Providers</button>
        </div>
      </div>

      <!-- Models Tab (admin only) -->
      <div v-if="activeTab === 'models'" class="settings-section">
        <h2 class="section-title">Model Configuration</h2>
        <p class="section-desc">Define available models and their parameters.</p>

        <div class="table-wrapper">
          <table class="data-table models-table">
            <thead>
              <tr>
                <th>Model ID</th>
                <th>Name</th>
                <th>Provider</th>
                <th>Max Tokens</th>
                <th>Temperature</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(model, idx) in modelsForm" :key="idx">
                <td><input v-model="model.id" class="table-input" /></td>
                <td><input v-model="model.name" class="table-input" /></td>
                <td>
                  <select v-model="model.provider" class="table-select">
                    <option v-for="p in providersForm" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>
                </td>
                <td><input v-model.number="model.max_tokens" type="number" class="table-input-sm" /></td>
                <td><input v-model.number="model.temperature" type="number" step="0.1" class="table-input-sm" /></td>
                <td><button class="btn-icon-danger" @click="removeModel(idx)">✕</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="action-bar">
          <button class="btn-secondary" @click="addModel">+ Add Model</button>
          <button class="btn-primary" @click="saveModels" :disabled="saving">Save Models</button>
        </div>
      </div>

      <!-- Tiers Tab (admin only) -->
      <div v-if="activeTab === 'tiers'" class="settings-section">
        <h2 class="section-title">Tier Configuration</h2>
        <p class="section-desc">Map processing tiers to specific models for each feature.</p>

        <div v-for="(feature, featureKey) in tiersForm" :key="featureKey" class="tier-feature">
          <h3 class="tier-feature-title">{{ featureKey }}</h3>
          <div class="tier-grid">
            <div v-for="(mapping, tierName) in feature" :key="tierName" class="tier-item">
              <label class="tier-label">{{ tierName }}</label>
              <select v-model="(feature as any)[tierName].model" class="tier-select">
                <option v-for="m in modelsForm" :key="m.id" :value="m.id">{{ m.name }}</option>
              </select>
              <select v-model="(feature as any)[tierName].provider" class="tier-select-sm">
                <option v-for="p in providersForm" :key="p.id" :value="p.id">{{ p.id }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="action-bar">
          <button class="btn-primary" @click="saveTiers" :disabled="saving">Save Tier Config</button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast" :class="toast.type">{{ toast.message }}</div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const { user, token, logout } = useAuth()
const config = useRuntimeConfig()
const apiBase = config.public.apiBaseUrl as string
const router = useRouter()

const activeTab = ref('profile')
const saving = ref(false)
const profileMessage = ref('')
const profileError = ref(false)
const toast = ref<{ message: string; type: string } | null>(null)

// Profile form
const profileForm = reactive({ nickname: user.value?.nickname || '' })
const passwordForm = reactive({ current: '', newPassword: '' })

// Admin data
const usersList = ref<any[]>([])
const providersForm = ref<any[]>([])
const modelsForm = ref<any[]>([])
const tiersForm = ref<Record<string, any>>({})

const isAdmin = computed(() => user.value?.role === 'admin')

const visibleTabs = computed(() => {
  const tabs = [{ id: 'profile', label: 'Profile' }]
  if (isAdmin.value) {
    tabs.push(
      { id: 'users', label: 'Users' },
      { id: 'providers', label: 'Providers' },
      { id: 'models', label: 'Models' },
      { id: 'tiers', label: 'Tiers' },
    )
  }
  return tabs
})

function showToast(message: string, type = 'success') {
  toast.value = { message, type }
  setTimeout(() => { toast.value = null }, 3000)
}

function authHeaders() {
  return { Authorization: `Bearer ${token.value}`, 'Content-Type': 'application/json' }
}

async function fetchAdminData() {
  if (!isAdmin.value) return
  try {
    const [usersRes, providersRes, modelsRes, tiersRes] = await Promise.all([
      fetch(`${apiBase}/api/v1/admin/users`, { headers: authHeaders() }),
      fetch(`${apiBase}/api/v1/admin/providers`, { headers: authHeaders() }),
      fetch(`${apiBase}/api/v1/admin/models`, { headers: authHeaders() }),
      fetch(`${apiBase}/api/v1/admin/tiers`, { headers: authHeaders() }),
    ])
    const usersData = await usersRes.json()
    const providersData = await providersRes.json()
    const modelsData = await modelsRes.json()
    const tiersData = await tiersRes.json()

    if (usersData.code === 0) usersList.value = usersData.data
    if (providersData.code === 0) providersForm.value = providersData.data
    if (modelsData.code === 0) modelsForm.value = modelsData.data
    if (tiersData.code === 0) tiersForm.value = tiersData.data
  } catch (e) {
    console.error('Failed to load admin data', e)
  }
}

// Profile actions
async function saveProfile() {
  saving.value = true
  profileMessage.value = ''
  try {
    const res = await fetch(`${apiBase}/api/v1/users/me`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ nickname: profileForm.nickname }),
    })
    const data = await res.json()
    if (data.code === 0) {
      showToast('Profile updated')
    } else {
      profileMessage.value = data.message || 'Failed'
      profileError.value = true
    }
  } catch { profileMessage.value = 'Network error'; profileError.value = true }
  finally { saving.value = false }
}

async function changePassword() {
  if (!passwordForm.current || !passwordForm.newPassword) {
    profileMessage.value = 'Both fields are required'
    profileError.value = true
    return
  }
  saving.value = true
  profileMessage.value = ''
  try {
    const res = await fetch(`${apiBase}/api/v1/users/me/password`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ current_password: passwordForm.current, new_password: passwordForm.newPassword }),
    })
    const data = await res.json()
    if (data.code === 0) {
      showToast('Password changed')
      passwordForm.current = ''
      passwordForm.newPassword = ''
    } else {
      profileMessage.value = data.message || 'Failed'
      profileError.value = true
    }
  } catch { profileMessage.value = 'Network error'; profileError.value = true }
  finally { saving.value = false }
}

// Admin: users
async function updateRole(userId: string, role: string) {
  try {
    await fetch(`${apiBase}/api/v1/admin/users/${userId}/role`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ role }),
    })
    showToast(`Role updated to ${role}`)
    await fetchAdminData()
  } catch { showToast('Failed to update role', 'error') }
}

// Admin: providers
function addProvider() {
  providersForm.value.push({
    id: '', name: '', type: 'llm', base_url: '', api_key_env: '', timeout: 60, enabled: true,
  })
}
function removeProvider(idx: number) { providersForm.value.splice(idx, 1) }
async function saveProviders() {
  saving.value = true
  try {
    const res = await fetch(`${apiBase}/api/v1/admin/providers`, {
      method: 'PUT', headers: authHeaders(),
      body: JSON.stringify({ providers: providersForm.value }),
    })
    const data = await res.json()
    if (data.code === 0) showToast('Providers saved')
    else showToast(data.message || 'Failed', 'error')
  } catch { showToast('Network error', 'error') }
  finally { saving.value = false }
}

// Admin: models
function addModel() {
  modelsForm.value.push({ id: '', name: '', provider: '', max_tokens: 4096, temperature: 0.2 })
}
function removeModel(idx: number) { modelsForm.value.splice(idx, 1) }
async function saveModels() {
  saving.value = true
  try {
    const res = await fetch(`${apiBase}/api/v1/admin/models`, {
      method: 'PUT', headers: authHeaders(),
      body: JSON.stringify({ models: modelsForm.value }),
    })
    const data = await res.json()
    if (data.code === 0) showToast('Models saved')
    else showToast(data.message || 'Failed', 'error')
  } catch { showToast('Network error', 'error') }
  finally { saving.value = false }
}

// Admin: tiers
async function saveTiers() {
  saving.value = true
  try {
    const res = await fetch(`${apiBase}/api/v1/admin/tiers`, {
      method: 'PUT', headers: authHeaders(),
      body: JSON.stringify({ tiers: tiersForm.value }),
    })
    const data = await res.json()
    if (data.code === 0) showToast('Tier configuration saved')
    else showToast(data.message || 'Failed', 'error')
  } catch { showToast('Network error', 'error') }
  finally { saving.value = false }
}

function handleLogout() {
  logout()
  router.push('/login')
}

onMounted(() => {
  profileForm.nickname = user.value?.nickname || ''
  fetchAdminData()
})
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  background: var(--bg-primary, #fffefb);
  color: var(--text-primary, #201515);
  font-family: 'Inter', sans-serif;
}

.settings-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  border-bottom: 1px solid var(--border-color, #c5c0b1);
}

.settings-topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.settings-topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-link {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-tertiary, #939084);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}
.back-link:hover { color: var(--accent-orange, #ff4f00); }

.settings-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
}

.user-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--bg-tertiary, #eceae3);
}
.user-badge.admin {
  background: #fff3e0;
  color: #e65100;
}

.user-email {
  font-size: 13px;
  color: var(--text-tertiary);
}

.btn-logout {
  font-size: 13px;
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
}
.btn-logout:hover { background: #fee; color: #c00; border-color: #c00; }

/* Tabs */
.settings-tabs {
  display: flex;
  gap: 0;
  padding: 0 32px;
  border-bottom: 1px solid var(--border-color, #c5c0b1);
}

.settings-tab {
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-tertiary);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.settings-tab:hover { color: var(--text-primary); }
.settings-tab.active {
  color: var(--accent-orange, #ff4f00);
  border-bottom-color: var(--accent-orange, #ff4f00);
}

/* Content */
.settings-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px;
}

.settings-section { }

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.section-desc {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-bottom: 20px;
}

.subsection-title {
  font-size: 15px;
  font-weight: 600;
  margin-top: 32px;
  margin-bottom: 12px;
}

/* Forms */
.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--text-secondary);
}
.form-group input {
  width: 100%;
  max-width: 400px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-primary);
}
.input-disabled {
  background: var(--bg-tertiary, #eceae3) !important;
  color: var(--text-tertiary) !important;
  cursor: not-allowed;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.form-row label {
  width: 100px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-tertiary);
  flex-shrink: 0;
}
.form-row input, .form-row select {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 13px;
}

/* Buttons */
.btn-primary {
  padding: 8px 20px;
  background: var(--accent-orange, #ff4f00);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}
.btn-secondary:hover { background: var(--bg-tertiary); }

.btn-danger-sm {
  padding: 4px 10px;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 4px;
  color: #dc2626;
  font-size: 12px;
  cursor: pointer;
}
.btn-danger-sm:hover { background: #fee2e2; }

.btn-icon-danger {
  background: none;
  border: none;
  color: #dc2626;
  cursor: pointer;
  font-size: 14px;
  padding: 4px;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

/* Cards */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.setting-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  background: var(--bg-secondary, #fffdf9);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-title-input {
  font-size: 14px;
  font-weight: 600;
  border: none;
  background: transparent;
  padding: 0;
  width: 60%;
}
.card-title-input:focus { outline: none; border-bottom: 1px solid var(--accent-orange); }

.card-body { }

.toggle-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  cursor: pointer;
}
.toggle-text { color: var(--text-tertiary); }

/* Tables */
.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 2px solid var(--border-color);
  font-weight: 600;
  color: var(--text-secondary);
}
.data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light, #eceae3);
}

.table-input {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 13px;
}
.table-input:focus { border-color: var(--accent-orange); outline: none; }

.table-input-sm {
  width: 80px;
  padding: 4px 8px;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 13px;
}
.table-input-sm:focus { border-color: var(--accent-orange); outline: none; }

.table-select {
  padding: 4px 8px;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 13px;
}
.table-select:focus { border-color: var(--accent-orange); outline: none; }

.role-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.role-badge.admin { background: #fff3e0; color: #e65100; }
.role-badge.user { background: #e8f5e9; color: #2e7d32; }

/* Tiers */
.tier-feature {
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-light, #eceae3);
}

.tier-feature-title {
  font-size: 15px;
  font-weight: 600;
  text-transform: capitalize;
  margin-bottom: 12px;
}

.tier-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.tier-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tier-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-orange);
}

.tier-select, .tier-select-sm {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 13px;
}

/* Messages / Toast */
.message {
  margin-top: 12px;
  font-size: 13px;
  color: #16a34a;
}
.message.error { color: #dc2626; }

.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: white;
  background: #16a34a;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  animation: slideIn 0.3s ease;
}
.toast.error { background: #dc2626; }

@keyframes slideIn {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>
