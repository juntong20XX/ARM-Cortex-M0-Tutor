<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSession } from '../composables/useSession'
import { ElMessage } from 'element-plus'
import {
  User,
  Lock,
  Loading,
  CircleCheckFilled,
  Clock,
  SwitchButton,
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

const router = useRouter()
const { session, isAuthenticated, userUuid, clearSession } = useSession()

const status = ref<LoginStatus>('idle')
const message = ref<string>('')
const userInfo = ref<UserInfo | null>(null)

// Status configuration mapping
const statusConfig = {
  idle: { type: 'info' as const, text: 'Waiting' },
  loading: { type: 'info' as const, text: 'Loading, please wait...' },
  success: { type: 'success' as const, text: 'Info loaded successfully' },
  error: { type: 'error' as const, text: 'Loading failed' }
}

const fetchUserInfo = async (): Promise<void> => {
  if (!userUuid.value) {
    status.value = 'idle'
    message.value = 'You are not logged in'
    return
  }

  status.value = 'loading'
  message.value = 'Fetching user information, please wait...'
  userInfo.value = null

  try {
    const res = await fetch(`/api/user/info/${encodeURIComponent(userUuid.value)}`, {
      method: 'GET',
      credentials: 'include',
    })
    const data = await res.json()

    if (!res.ok) {
      throw new Error(data?.msg || `HTTP ${res.status}`)
    }

    if (!data?.success) {
      throw new Error(data?.msg || 'Failed to fetch user info, please try again later')
    }

    userInfo.value = {
      ...data,
      join_date: data.join_date ? new Date(data.join_date).toLocaleString() : '',
      last_login: data.last_login ? new Date(data.last_login).toLocaleString() : '',
    }
    message.value = 'User information loaded successfully'
    status.value = 'success'
  } catch (err) {
    status.value = 'error'
    message.value = (err as Error)?.message || 'Request failed, please try again later'
    ElMessage.error(message.value)
  }
}

const handleLogin = (): void => {
  window.location.href = '/api/login'
}

const handleLogout = (): void => {
  clearSession()
  ElMessage.success('Logged out successfully')
  // 跳转到后端登出接口，清除服务端 session 后再重定向到 /login，否则无法重新登录
  window.location.href = '/api/logout'
}

const handleGoHome = (): void => {
  router.push('/')
}

onMounted(() => {
  if (isAuthenticated.value) {
    fetchUserInfo()
  } else {
    message.value = 'You are not logged in, please log in first'
  }
})
</script>

<template>
  <div class="login-container">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <!-- Logged In Header -->
          <template v-if="isAuthenticated">
            <el-tag type="success" effect="plain" size="small">
              <el-icon><User /></el-icon>
              User Center
            </el-tag>
            <h1 class="title">
              Welcome back,
              <el-text type="primary" tag="b" size="large">
                {{ session?.display_name || 'User' }}
              </el-text>
            </h1>
            <p class="description">
              You are logged in. Here is your account information.
            </p>
          </template>
          <!-- Not Logged In Header -->
          <template v-else>
            <el-tag type="info" effect="plain" size="small">
              <el-icon><Lock /></el-icon>
              User Login
            </el-tag>
            <h1 class="title">
              Welcome to
              <el-text type="primary" tag="b" size="large">
                ARM Cortex-M0 Tutor
              </el-text>
            </h1>
            <p class="description">
              You are not logged in. Please click the button below to log in.
            </p>
          </template>
        </div>
      </template>

      <!-- Logged In Content -->
      <template v-if="isAuthenticated">
        <!-- Status Display -->
        <el-alert
          :title="statusConfig[status].text"
          :type="statusConfig[status].type"
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
              Account Details
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
            type="danger"
            :icon="SwitchButton"
            @click="handleLogout"
          >
            Logout
          </el-button>
          <el-button
            :icon="HomeFilled"
            @click="handleGoHome"
          >
            Back to Home
          </el-button>
        </div>
      </template>

      <!-- Not Logged In Content -->
      <template v-else>
        <!-- Status Display -->
        <el-alert
          title="Not Logged In"
          type="info"
          :closable="false"
          show-icon
          class="status-alert"
        >
          <template #default>
            <span class="status-message">{{ message }}</span>
          </template>
        </el-alert>

        <!-- Login Illustration -->
        <div class="login-illustration">
          <el-icon class="login-icon" :size="80" color="#409EFF">
            <User />
          </el-icon>
        </div>

        <!-- Action Buttons -->
        <div class="actions center">
          <el-button
            type="primary"
            size="large"
            :icon="Lock"
            @click="handleLogin"
          >
            Login
          </el-button>
          <el-button
            size="large"
            :icon="HomeFilled"
            @click="handleGoHome"
          >
            Back to Home
          </el-button>
        </div>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
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

.login-illustration {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}

.login-icon {
  opacity: 0.6;
  transition: opacity 0.3s, transform 0.3s;
}

.login-icon:hover {
  opacity: 1;
  transform: scale(1.1);
}

.actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  gap: 16px;
}

.actions.center {
  flex-direction: column;
  align-items: center;
}

.actions.center .el-button {
  width: 200px;
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
