<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSession } from '../composables/useSession'

const route = useRoute()
const router = useRouter()
const { saveSession } = useSession()

const status = ref('idle') // idle | loading | success | error
const message = ref('Waiting to process login...')
const userInfo = ref(null)

const providerName = computed(() => (route.params.providerName || '').toString())
const queryString = computed(() => {
  const search = new URLSearchParams(route.query).toString()
  return search ? `?${search}` : ''
})

const apiUrl = computed(() => {
  if (!providerName.value) return ''
  return `/api/login-oauth/${encodeURIComponent(providerName.value)}${queryString.value}`
})

const fetchUserInfo = async () => {
  if (!providerName.value) {
    status.value = 'error'
    message.value = 'Missing provider_name parameter, cannot proceed with login.'
    return
  }

  status.value = 'loading'
  message.value = 'Exchanging authorization info with server, please wait...'
  userInfo.value = null

  try {
    const res = await fetch(apiUrl.value, {
      method: 'GET',
      credentials: 'include',
    })
    const data = await res.json()

    if (!res.ok) {
      throw new Error(data?.msg || `HTTP ${res.status}`)
    }

    if (!data?.success) {
      throw new Error(data?.msg || 'Login failed, please try again later.')
    }

    userInfo.value = {
      ...data,
      join_date: data.join_date ? new Date(data.join_date).toLocaleString() : '',
      last_login: data.last_login ? new Date(data.last_login).toLocaleString() : '',
    }
    message.value = data.msg || 'Login successful, creating session for you.'
    status.value = 'success'
    
    // 保存用户会话信息到前端
    if (data.uuid && data.display_name) {
      saveSession({
        uuid: data.uuid,
        display_name: data.display_name
      })
    }
  } catch (err) {
    status.value = 'error'
    message.value = err?.message || 'Request failed, please try again later.'
  }
}

onMounted(fetchUserInfo)
watch(
  () => [providerName.value, route.fullPath],
  () => {
    fetchUserInfo()
  }
)
</script>

<template>
  <section class="panel">
    <p class="eyebrow">OAuth Callback</p>
    <h1 class="title">
      Processing
      <span class="highlight">{{ providerName || 'Unknown Provider' }}</span>
      Login
    </h1>
    <p class="muted">
      This page reads the query parameters from current URL and forwards them to
      <code>/api/login-oauth/{{ providerName }}</code> for verification.
    </p>

    <div class="status" :class="status">
      <span v-if="status === 'loading'">Verifying authorization, please wait...</span>
      <span v-else-if="status === 'success'">Login Successful</span>
      <span v-else-if="status === 'error'">Login Failed</span>
      <span v-else>Waiting</span>
      <p class="message">{{ message }}</p>
    </div>

    <div v-if="status === 'success' && userInfo" class="info-grid">
      <div class="info-item">
        <label>User UUID</label>
        <div>{{ userInfo.uuid }}</div>
      </div>
      <div class="info-item">
        <label>Display Name</label>
        <div>{{ userInfo.display_name }}</div>
      </div>
      <div class="info-item">
        <label>Email</label>
        <div>{{ userInfo.email }}</div>
      </div>
      <div class="info-item">
        <label>Joined At</label>
        <div>{{ userInfo.join_date }}</div>
      </div>
      <div class="info-item">
        <label>Last Login</label>
        <div>{{ userInfo.last_login }}</div>
      </div>
      <div class="info-item">
        <label>Login Source</label>
        <div>{{ userInfo.login_source }}</div>
      </div>
      <div class="info-item">
        <label>Groups</label>
        <div>{{ userInfo.groups?.join(', ') || 'None' }}</div>
      </div>
    </div>

    <div class="actions">
      <button type="button" class="primary" @click="router.push('/login')">Retry</button>
      <a class="link" href="/">Back to Home</a>
    </div>
  </section>
</template>

<style scoped>
.highlight {
  color: #2563eb;
}

.status {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
}

.status.loading {
  border-color: #93c5fd;
  background: #eff6ff;
}

.status.success {
  border-color: #86efac;
  background: #f0fdf4;
}

.status.error {
  border-color: #fca5a5;
  background: #fef2f2;
}

.status .message {
  margin-top: 6px;
  color: #4b5563;
}

.info-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.info-item {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
}

.info-item label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.actions {
  margin-top: 18px;
  display: flex;
  gap: 12px;
  align-items: center;
}

.primary {
  border: none;
  background: #2563eb;
  color: #fff;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
}

.primary:hover {
  background: #1d4ed8;
}

.link {
  color: #2563eb;
}
</style>

