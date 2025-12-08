<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const status = ref('idle') // idle | loading | success | error
const message = ref('等待处理登录...')
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
    message.value = '缺少 provider_name 参数，无法继续登录。'
    return
  }

  status.value = 'loading'
  message.value = '正在与服务器交换授权信息，请稍候...'
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
      throw new Error(data?.msg || '登录失败，请稍后重试。')
    }

    userInfo.value = {
      ...data,
      join_date: data.join_date ? new Date(data.join_date).toLocaleString() : '',
    }
    message.value = data.msg || '登录成功，正在为你创建会话。'
    status.value = 'success'
  } catch (err) {
    status.value = 'error'
    message.value = err?.message || '请求失败，请稍后再试。'
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
    <p class="eyebrow">OAuth 回调</p>
    <h1 class="title">
      正在处理
      <span class="highlight">{{ providerName || '未知服务' }}</span>
      登录
    </h1>
    <p class="muted">
      本页会读取当前地址的查询参数，并将其转发至
      <code>/api/login-oauth/{{ providerName }}</code> 完成验证。
    </p>

    <div class="status" :class="status">
      <span v-if="status === 'loading'">正在校验授权，请稍候...</span>
      <span v-else-if="status === 'success'">登录成功</span>
      <span v-else-if="status === 'error'">登录失败</span>
      <span v-else>等待处理</span>
      <p class="message">{{ message }}</p>
    </div>

    <div v-if="status === 'success' && userInfo" class="info-grid">
      <div class="info-item">
        <label>用户 UUID</label>
        <div>{{ userInfo.uuid }}</div>
      </div>
      <div class="info-item">
        <label>显示名称</label>
        <div>{{ userInfo.display_name }}</div>
      </div>
      <div class="info-item">
        <label>邮箱</label>
        <div>{{ userInfo.email }}</div>
      </div>
      <div class="info-item">
        <label>加入时间</label>
        <div>{{ userInfo.join_date }}</div>
      </div>
      <div class="info-item">
        <label>登录来源</label>
        <div>{{ userInfo.login_source }}</div>
      </div>
      <div class="info-item">
        <label>用户组</label>
        <div>{{ userInfo.groups?.join(', ') || '无' }}</div>
      </div>
    </div>

    <div class="actions">
      <button type="button" class="primary" @click="fetchUserInfo">重新尝试</button>
      <a class="link" href="/">返回首页</a>
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

