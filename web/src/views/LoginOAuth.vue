<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSession } from '../composables/useSession'
import { ElMessage } from 'element-plus'
import {
  Loading,
  CircleCheckFilled,
  CircleCloseFilled,
  Clock,
  Refresh,
  HomeFilled
} from '@element-plus/icons-vue'

// Type definitions
type LoginStatus = 'idle' | 'loading' | 'success' | 'error'

interface UserInfo {
  uuid: string
  display_name: string
  email: string
  join_date: string
  last_login: string
  login_source: string
  groups: string[]
  msg?: string
  success?: boolean
}

const route = useRoute()
const router = useRouter()
const { saveSession } = useSession()

const status = ref<LoginStatus>('idle')
const message = ref<string>('Waiting to process login...')
const userInfo = ref<UserInfo | null>(null)

const providerName = computed<string>(() => (route.params.providerName || '').toString())
const queryString = computed<string>(() => {
  const search = new URLSearchParams(route.query as Record<string, string>).toString()
  return search ? `?${search}` : ''
})

const apiUrl = computed<string>(() => {
  if (!providerName.value) return ''
  return `/api/login-oauth/${encodeURIComponent(providerName.value)}${queryString.value}`
})

// Status configuration mapping
const statusConfig = computed(() => ({
  idle: { type: 'info' as const, icon: Clock, text: 'Waiting' },
  loading: { type: 'info' as const, icon: Loading, text: 'Verifying authorization, please wait...' },
  success: { type: 'success' as const, icon: CircleCheckFilled, text: 'Login Successful' },
  error: { type: 'error' as const, icon: CircleCloseFilled, text: 'Login Failed' }
}))

const currentStatusConfig = computed(() => statusConfig.value[status.value])

const fetchUserInfo = async (): Promise<void> => {
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
    
    ElMessage.success('Login successful!')
    
    // Save user session info to frontend
    if (data.uuid && data.display_name) {
      saveSession({
        uuid: data.uuid,
        display_name: data.display_name
      })
    }
  } catch (err) {
    status.value = 'error'
    message.value = (err as Error)?.message || 'Request failed, please try again later.'
    ElMessage.error(message.value)
  }
}

const handleRetry = (): void => {
  router.push('/login')
}

const handleGoHome = (): void => {
  router.push('/')
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
  <div class="login-oauth-container">
    <el-card class="oauth-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-tag type="info" effect="plain" size="small">OAuth Callback</el-tag>
          <h1 class="title">
            Processing
            <el-tag type="primary" effect="dark" size="large" class="provider-tag">
              {{ providerName || 'Unknown Provider' }}
            </el-tag>
            Login
          </h1>
          <p class="description">
            This page reads the query parameters from current URL and forwards them to
            <el-tag type="info" size="small">
              /api/login-oauth/{{ providerName }}
            </el-tag>
            for verification.
          </p>
        </div>
      </template>

      <!-- Status Display -->
      <el-alert
        :title="currentStatusConfig.text"
        :type="currentStatusConfig.type"
        :closable="false"
        show-icon
        class="status-alert"
      >
        <template #default>
          <div class="status-content">
            <el-icon v-if="status === 'loading'" class="is-loading">
              <Loading />
            </el-icon>
            <span class="status-message">{{ message }}</span>
          </div>
        </template>
      </el-alert>

      <!-- User Info Display -->
      <el-collapse-transition>
        <div v-if="status === 'success' && userInfo" class="user-info-section">
          <el-divider content-position="left">
            <el-icon><CircleCheckFilled /></el-icon>
            User Information
          </el-divider>
          
          <el-descriptions
            :column="2"
            border
            class="user-descriptions"
          >
            <el-descriptions-item label="User UUID" :span="2">
              <el-text type="primary" tag="code">{{ userInfo.uuid }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="Display Name">
              <el-text type="success" tag="b">{{ userInfo.display_name }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="Email">
              <el-link type="primary" :underline="false">{{ userInfo.email }}</el-link>
            </el-descriptions-item>
            <el-descriptions-item label="Joined At">
              <el-icon><Clock /></el-icon>
              {{ userInfo.join_date }}
            </el-descriptions-item>
            <el-descriptions-item label="Last Login">
              <el-icon><Clock /></el-icon>
              {{ userInfo.last_login }}
            </el-descriptions-item>
            <el-descriptions-item label="Login Source">
              <el-tag type="warning" effect="plain">{{ userInfo.login_source }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Groups">
              <el-space wrap>
                <el-tag
                  v-for="group in (userInfo.groups || [])"
                  :key="group"
                  type="success"
                  effect="light"
                  size="small"
                >
                  {{ group }}
                </el-tag>
                <el-text v-if="!userInfo.groups?.length" type="info">None</el-text>
              </el-space>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-collapse-transition>

      <!-- Action Buttons -->
      <div class="actions">
        <el-button
          type="primary"
          :icon="Refresh"
          @click="handleRetry"
        >
          Retry
        </el-button>
        <el-button
          :icon="HomeFilled"
          @click="handleGoHome"
        >
          Back to Home
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.login-oauth-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.oauth-card {
  width: 100%;
  max-width: 680px;
  border-radius: 16px;
  overflow: hidden;
}

.card-header {
  text-align: center;
}

.title {
  margin: 12px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.provider-tag {
  font-size: 18px;
  padding: 8px 16px;
}

.description {
  color: #909399;
  font-size: 14px;
  margin: 0;
  line-height: 1.6;
}

.status-alert {
  margin-bottom: 20px;
}

.status-content {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.status-message {
  color: #606266;
}

.is-loading {
  animation: rotate 1.5s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.user-info-section {
  margin-top: 16px;
}

.user-descriptions {
  margin-top: 16px;
}

.user-descriptions :deep(.el-descriptions__label) {
  font-weight: 500;
  min-width: 100px;
}

.user-descriptions :deep(code) {
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
}

.actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  gap: 16px;
}

@media (max-width: 768px) {
  .user-descriptions :deep(.el-descriptions__body) {
    display: block;
  }
  
  .title {
    font-size: 20px;
  }
  
  .actions {
    flex-direction: column;
  }
  
  .actions .el-button {
    width: 100%;
  }
}
</style>
