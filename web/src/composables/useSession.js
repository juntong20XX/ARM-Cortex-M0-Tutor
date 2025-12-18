import { ref, computed } from 'vue'

const SESSION_KEY = 'user_session'

// 响应式会话状态
const session = ref(null)

// 从 localStorage 加载会话
function loadSession() {
  try {
    const stored = localStorage.getItem(SESSION_KEY)
    if (stored) {
      session.value = JSON.parse(stored)
      return session.value
    }
  } catch (err) {
    console.error('Failed to load session:', err)
  }
  return null
}

// 保存会话到 localStorage
function saveSession(userData) {
  try {
    const sessionData = {
      uuid: userData.uuid,
      display_name: userData.display_name,
      timestamp: new Date().toISOString()
    }
    localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData))
    session.value = sessionData
    return true
  } catch (err) {
    console.error('Failed to save session:', err)
    return false
  }
}

// 清除会话
function clearSession() {
  try {
    localStorage.removeItem(SESSION_KEY)
    session.value = null
    return true
  } catch (err) {
    console.error('Failed to clear session:', err)
    return false
  }
}

// 初始化：加载已存在的会话
loadSession()

export function useSession() {
  const isAuthenticated = computed(() => session.value !== null)
  const userUuid = computed(() => session.value?.uuid || null)
  const userDisplayName = computed(() => session.value?.display_name || null)

  return {
    session: computed(() => session.value),
    isAuthenticated,
    userUuid,
    userDisplayName,
    saveSession,
    clearSession,
    loadSession
  }
}
