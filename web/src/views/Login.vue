<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSession } from '../composables/useSession'
import '../assets/login.css'

const router = useRouter()
const { session, isAuthenticated, userUuid, clearSession } = useSession()

const status = ref('idle') // idle | loading | success | error
const message = ref('')
const userInfo = ref(null)

const fetchUserInfo = async () => {
  if (!userUuid.value) {
    status.value = 'idle'
    message.value = '您尚未登录'
    return
  }

  status.value = 'loading'
  message.value = '正在获取用户信息，请稍候...'
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
      throw new Error(data?.msg || '获取用户信息失败，请稍后重试')
    }

    userInfo.value = {
      ...data,
      join_date: data.join_date ? new Date(data.join_date).toLocaleString('zh-CN') : '',
      last_login: data.last_login ? new Date(data.last_login).toLocaleString('zh-CN') : '',
    }
    message.value = '用户信息加载成功'
    status.value = 'success'
  } catch (err) {
    status.value = 'error'
    message.value = err?.message || '请求失败，请稍后重试'
  }
}

const handleLogin = () => {
  window.location.href = '/api/login'
}

const handleLogout = () => {
  clearSession()
  router.push('/logout')
}

onMounted(() => {
  if (isAuthenticated.value) {
    fetchUserInfo()
  } else {
    message.value = '您尚未登录，请先登录'
  }
})
</script>

<template>
  <section class="panel login-page">
    <!-- 已登录状态 -->
    <template v-if="isAuthenticated">
      <p class="eyebrow">用户中心</p>
      <h1 class="title">
        欢迎回来，<span class="highlight">{{ session?.display_name || '用户' }}</span>
      </h1>
      <p class="muted">
        您已登录，以下是您的账户信息。
      </p>

      <div class="status" :class="status">
        <span v-if="status === 'loading'">正在加载，请稍候...</span>
        <span v-else-if="status === 'success'">信息加载成功</span>
        <span v-else-if="status === 'error'">加载失败</span>
        <span v-else>等待中</span>
        <p class="message">{{ message }}</p>
      </div>

      <div v-if="status === 'success' && userInfo" class="info-grid">
        <div class="info-item">
          <label>用户 UUID</label>
          <div class="value">{{ userInfo.uuid }}</div>
        </div>
        <div class="info-item">
          <label>显示名称</label>
          <div class="value">{{ userInfo.display_name }}</div>
        </div>
        <div class="info-item">
          <label>邮箱</label>
          <div class="value">{{ userInfo.email }}</div>
        </div>
        <div class="info-item">
          <label>注册时间</label>
          <div class="value">{{ userInfo.join_date }}</div>
        </div>
        <div class="info-item">
          <label>最后登录</label>
          <div class="value">{{ userInfo.last_login }}</div>
        </div>
        <div class="info-item">
          <label>登录方式</label>
          <div class="value">{{ userInfo.login_source }}</div>
        </div>
        <div class="info-item full-width">
          <label>用户组</label>
          <div class="value groups">
            <span v-if="userInfo.groups?.length" v-for="group in userInfo.groups" :key="group" class="tag">
              {{ group }}
            </span>
            <span v-else class="empty">无</span>
          </div>
        </div>
      </div>

      <div class="actions">
        <button type="button" class="logout-btn" @click="handleLogout">登出</button>
        <a class="link" href="/">返回首页</a>
      </div>
    </template>

    <!-- 未登录状态 -->
    <template v-else>
      <p class="eyebrow">用户登录</p>
      <h1 class="title">
        欢迎使用 <span class="highlight">ARM Cortex-M0 Tutor</span>
      </h1>
      <p class="muted">
        您尚未登录，请点击下方按钮进行登录。
      </p>

      <div class="status idle">
        <span>未登录</span>
        <p class="message">{{ message }}</p>
      </div>

      <div class="actions center">
        <button type="button" class="primary login-btn" @click="handleLogin">登录</button>
        <a class="link" href="/">返回首页</a>
      </div>
    </template>
  </section>
</template>

<style scoped>
.login-btn {
  padding: 12px 32px;
  font-size: 16px;
  font-weight: 500;
}

.logout-btn {
  border: none;
  background: #dc2626;
  color: #fff;
  padding: 10px 20px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: #b91c1c;
}

.actions.center {
  justify-content: center;
}
</style>
