import { ref, computed } from 'vue'

const SESSION_KEY = 'user_session'

// Reactive session state
const session = ref(null)

// Load session from localStorage
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

// Save session to localStorage
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

// Clear session
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

// Initialize: load existing session
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
